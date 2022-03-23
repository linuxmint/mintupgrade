#!/usr/bin/python3
import gi
import threading
from gi.repository import GObject, Gio
import time
import os
import datetime
from common import *
from constants import *

import gettext, locale
import traceback
import subprocess

import apt

# i18n
APP = 'mintupgrade'
LOCALE_DIR = "/usr/share/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

class TableList():
    def __init__(self, columns):
        self.columns = columns
        self.values = []

class Check():
    def __init__(self, title, description, callback=None):
        self.title = title
        self.description = description
        self.callback = callback
        self.allow_recheck = True
        self.clean()

    def clean(self):
        # clean check state
        self.result = RESULT_SUCCESS
        self.message = ""
        self.finished = False
        self.fix = None
        self.info = []

    @async_function
    def run(self):
        print("Running check '%s'" % self.title)
        self.clean()
        try:
            self.do_run()
        except Exception as e:
            self.message = traceback.format_exc()
            self.result = RESULT_EXCEPTION
        self.finalize()

    def do_run(self):
        pass

    @async_function
    def run_fix(self):
        if self.fix != None:
            print("Fixing check '%s'" % self.title)
            try:
                self.fix()
                self.clean()
                self.do_run()
            except Exception as e:
                self.message = traceback.format_exc()
                self.result = RESULT_EXCEPTION
            self.finalize()

    def finalize(self):
        self.finished = True
        if self.callback != None:
            self.callback(self)

    def get_setting(self, key):
        return Gio.Settings(schema_id="com.linuxmint.mintupgrade").get_boolean(key)

# Check that the OS release/version is upgradable
class VersionCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Linux Mint version"), _("Checking your version of Linux Mint..."), callback)
        self.allow_recheck = False

    def do_run(self):
        if self.get_setting("check-version"):
            # Check the Mint info file
            if not os.path.exists("/etc/linuxmint/info"):
                self.result = RESULT_ERROR
                self.message = _("Your version of Linux Mint is unknown. /etc/linuxmint/info is missing.")
                return

            # Check the codename/edition
            codename = None
            edition = None
            with open("/etc/linuxmint/info", "r") as info:
                for line in info:
                    line = line.strip()
                    if "EDITION=" in line:
                        edition = line.split('=')[1].replace('"', '').split()[0]
                    if "CODENAME=" in line:
                        codename = line.split('=')[1].replace('"', '').split()[0]

            # Check codename
            if codename != ORIGIN_CODENAME and codename != DESTINATION_CODENAME:
                self.result = RESULT_ERROR
                self.message = _("Your version of Linux Mint is '%s'. Only %s can be upgraded to %s." % (codename.capitalize(), ORIGIN, DESTINATION))
                return

            # Check edition
            if self.mint_edition.lower() not in SUPPORTED_EDITIONS:
                self.result = RESULT_ERROR
                self.message = _("Your edition of Linux Mint is '%s'. It cannot be upgraded to %s." % (edition, DESTINATION))
                return

# Check that the computer is plugged in to AC Power
class PowerCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Power Source"), _("Checking power source..."), callback)

    def do_run(self):
        if "off-line" in subprocess.getoutput("acpi -a"):
            self.result = RESULT_ERROR
            self.message = _("Connect the computer to a power source before attempting to upgrade.")

# Check that the computer has a recent Timeshift snapshot
class TimeshiftCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Timeshift Snapshot"), _("Checking timeshift snapshots..."), callback)

    def do_run(self):
        if self.get_setting("check-timeshift"):
            self.result = RESULT_ERROR
            self.message = _("Perform a Timeshift system snapshot before attempting to upgrade.")
            if os.path.exists("/usr/bin/timeshift"):
                today = datetime.datetime.today().strftime('%Y-%m-%d')
                if today in subprocess.getoutput("timeshift --list"):
                    self.result = RESULT_SUCCESS

# Check the APT cache
class APTCacheCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Package Base"), _("Checking your package base..."), callback)
        self.cache_updated = False
        self.pkgs_to_remove = []
        self.pkgs_to_install = []

    def do_run(self):
        # Update the cache
        if not self.cache_updated:
            os.system("DEBIAN_PRIORITY=critical sudo apt-get update")
            self.cache_updated = True
        cache = apt.Cache()

        # Check broken packages
        if cache.broken_count > 0:
            self.result = RESULT_ERROR
            self.message = _("Some of your packages are broken. Run 'apt install -f' to fix the issue.")
            return

        points_to_destination = False
        if os.path.exists("/etc/apt/sources.list.d/official-package-repositories.list"):
            with open("/etc/apt/sources.list.d/official-package-repositories.list") as sources:
                for line in sources:
                    if DESTINATION_CODENAME in line:
                        points_to_destination = True
                        break

        if not points_to_destination:
            # Check updates
            if self.get_setting("check-updates"):
                for pkg in CHECK_UP_TO_DATE:
                    if pkg in cache:
                        pkg = cache[pkg]
                        if pkg.is_installed and pkg.installed.version != pkg.candidate.version:
                            self.result = RESULT_ERROR
                            self.message = _("Your operating system is not up to date. Apply available updates before attempting the upgrade.")
                            self.fix = self.launch_update_manager
                            return

            # Check pkgs to remove
            self.pkgs_to_remove = []
            for pkg_name in CHECK_ABSENT:
                if pkg_name in cache.keys():
                    pkg = cache[pkg_name]
                    if pkg.is_installed:
                        self.pkgs_to_remove.append(pkg)

            # Check pkgs to install
            self.pkgs_to_install = []
            for pkg_name in CHECK_PRESENT:
                if pkg_name in cache.keys():
                    pkg = cache[pkg_name]
                    if not pkg.is_installed:
                        self.pkgs_to_install.append(pkg)

            if len(self.pkgs_to_remove) > 0 or len(self.pkgs_to_install) > 0:
                self.result = RESULT_WARNING
                self.message = _("The following operations need to be performed:")

                table_list = TableList([_("Package"), _("Operation")])
                for pkg in self.pkgs_to_install:
                    table_list.values.append([pkg.name, _("needs to be installed")])
                for pkg in self.pkgs_to_remove:
                    table_list.values.append([pkg.name, _("needs to be removed")])

                self.info.append(table_list)
                self.fix = self.install_remove_pkgs
                return

    def launch_update_manager(self):
        subprocess.Popen("mintupdate")

    def install_remove_pkgs(self):
        print("install remove")
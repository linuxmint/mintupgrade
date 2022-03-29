#!/usr/bin/python3
import gi
import threading
from gi.repository import GObject, Gio
import time
import os
import datetime
from common import *
from constants import *
from apt_utils import *
import gettext, locale
import traceback
import subprocess

import apt
import apt_pkg
import aptsources.sourceslist
import mintcommon.aptdaemon

import pycurl

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
        self.show_column_names = True

class Check():
    def __init__(self, title, description, callback=None):
        self.title = title
        self.description = description
        self.callback = callback
        self.allow_recheck = True
        self.result = RESULT_SUCCESS
        self.clean()

    def clean(self):
        # clean check state
        if self.result != RESULT_INFO:
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

# Info just shows an info page
class ShowInfoCheck(Check):

    def __init__(self, title, callback=None):
        super().__init__(title, "", callback)
        self.result = RESULT_INFO
        self.icon_name = "dialog-info"
        self.allow_recheck = False
        self.allow_continue = True

    def do_run(self):
        pass

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
            if edition.lower() not in SUPPORTED_EDITIONS:
                self.result = RESULT_ERROR
                self.message = _("Your edition of Linux Mint is '%s'. It cannot be upgraded to %s." % (edition, DESTINATION))
                return

# Check that the computer is plugged in to AC Power
class PowerCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Power source"), _("Checking the power source..."), callback)

    def do_run(self):
        if "off-line" in subprocess.getoutput("acpi -a"):
            self.result = RESULT_ERROR
            self.message = _("Connect the computer to a power source before attempting to upgrade.")

# Check that the computer has a recent Timeshift snapshot
class TimeshiftCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Timeshift snapshot"), _("Checking timeshift snapshots..."), callback)

    def do_run(self):
        if self.get_setting("check-timeshift"):
            self.result = RESULT_ERROR
            self.message = _("Perform a Timeshift system snapshot before attempting to upgrade.")
            self.info.append(_("If the upgrade isn't successful, a system snapshot will allow you to go back in time and revert all the changes."))
            if os.path.exists("/usr/bin/timeshift"):
                today = datetime.datetime.today().strftime('%Y-%m-%d')
                if today in subprocess.getoutput("timeshift --list"):
                    self.result = RESULT_SUCCESS
                else:
                    self.fix = self.run_timeshift

    def run_timeshift(self):
        subprocess.getoutput("timeshift-gtk")

# Check the APT cache
class APTCacheCheck(Check):

    def __init__(self, window, callback=None):
        super().__init__(_("Package base"), _("Checking the package base..."), callback)
        self.cache_updated = False
        self.pkgs_to_remove = []
        self.pkgs_to_install = []
        self.window = window

    def do_run(self):
        # Update the cache
        if not self.cache_updated:
            # detect cache errors using python-apt (apt-get doesn't return proper error codes)
            try:
                cache = apt.Cache()
                cache.open()
                cache.update()
            except:
                self.result = RESULT_ERROR
                self.message = _("Your package cache can't refresh correctly. Run 'apt update' and fix the errors it displays.")
                return
            # if successfull, call apt-get to get a trace in stdout anyway
            os.system("DEBIAN_PRIORITY=critical apt-get update")
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
                            return

            # Check pkgs to remove
            self.pkgs_to_remove = []
            for pkg_name in CHECK_ABSENT:
                if pkg_name in cache.keys():
                    pkg = cache[pkg_name]
                    if pkg.is_installed:
                        self.pkgs_to_remove.append(pkg.name)

            # Check pkgs to install
            self.pkgs_to_install = []
            for pkg_name in CHECK_PRESENT:
                if pkg_name in cache.keys():
                    pkg = cache[pkg_name]
                    if not pkg.is_installed:
                        self.pkgs_to_install.append(pkg.name)

            if len(self.pkgs_to_remove) > 0 or len(self.pkgs_to_install) > 0:
                self.result = RESULT_WARNING
                self.message = _("The following operations need to be performed:")

                table_list = TableList([_("Package"), _("Operation")])
                for pkg in self.pkgs_to_install:
                    table_list.values.append([pkg, _("needs to be installed")])
                for pkg in self.pkgs_to_remove:
                    table_list.values.append([pkg, _("needs to be removed")])

                self.info.append(table_list)
                self.fix = self.install_remove_pkgs
                return

    def install_remove_pkgs(self):
        apt = mintcommon.aptdaemon.APT(self.window)
        apt.set_finished_callback(self.on_transaction_finished)
        apt.set_cancelled_callback(self.on_transaction_finished)
        if len(self.pkgs_to_remove) > 0:
            self.busy = True
            apt.remove_packages(self.pkgs_to_remove)
            while self.busy:
                time.sleep(0.2)
        if len(self.pkgs_to_install) > 0:
            self.busy = True
            apt.install_packages(self.pkgs_to_install)
            while self.busy:
                time.sleep(0.2)

    def on_transaction_finished(self, transaction=None, exit_state=None):
        self.busy = False


# Check that the APT repos are OK
class APTRepoCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Package repositories"), _("Checking package repositories..."), callback)

    def do_run(self):
        apt_pkg.init_config()
        self.sources = aptsources.sourceslist.SourcesList()
        self.mint_repos = []
        self.base_repos = []
        self.foreign_repos = []
        for source in self.sources:
            if source.disabled:
                # commented out repos
                continue
            if source.uri == "":
                # repos file entries themselves
                continue
            if ORIGIN_CODENAME in source.dist or DESTINATION_CODENAME in source.dist:
                self.mint_repos.append(source)
            elif ORIGIN_BASE_CODENAME in source.dist or DESTINATION_BASE_CODENAME in source.dist:
                self.base_repos.append(source)
            else:
                self.foreign_repos.append(source)

        # Foreign repositories which codename is not in the origin or the destination (mint or base)
        if len(self.foreign_repos) > 0:
            self.result = RESULT_ERROR
            self.message = _("The following repositories do not explictly support your version of Linux Mint.")
            self.fix = self.disable_foreign_repos
            table_list = TableList([""])
            table_list.show_column_names = False
            for repo in self.foreign_repos:
                repo_string = f"{repo.uri} {repo.dist} " + " ".join(repo.comps)
                table_list.values.append([repo_string])
            self.info.append(table_list)
            self.info.append(_("These repositories need to be disabled."))
            return

        # Check policy
        mint_layer_found = False
        output = subprocess.getoutput('apt-cache policy')
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("700") and line.endswith("Packages") and "/upstream" in line:
                mint_layer_found = True
                break
        if not mint_layer_found:
            self.result = RESULT_ERROR
            self.message = _("Your APT policy is incorrect.")
            self.info.append(_("Reboot your computer."))
            self.allow_recheck = False
            return

        # Check up-to-date-ness on Mint mirror
        problems = []
        mint_timestamp = self.get_url_last_modified("http://packages.linuxmint.com/db/version")
        mint_age = None
        if mint_timestamp != None:
            mint_date = datetime.datetime.fromtimestamp(mint_timestamp)
            now = datetime.datetime.now()
            mint_age = (now - mint_date).days
            print("Mint repository last modified on", mint_date)
        for repo in self.mint_repos:
            if "packages.linuxmint.com" in repo.uri:
                continue
            timestamp = self.get_url_last_modified("%s/db/version" % repo.uri)
            if timestamp == None:
                problems.append(_("%s is unreachable") % repo.uri)
            elif mint_age > 2:
                date = datetime.datetime.fromtimestamp(timestamp)
                offset = (mint_date - date).days
                if mint_age > 2 and offset > 2:
                    problems.append(_("%s is not up to date. Switch to a different mirror.") % repo.uri)

        # Check the base repos can handle destination codename
        for repo in self.base_repos:
            if repo.dist == "buster/updates":
                # special case, the repo syntax changed between LMDE 4 and LMDE 5
                new_dist = "bullseye-security"
            else:
                new_dist = repo.dist.replace(ORIGIN_BASE_CODENAME, DESTINATION_BASE_CODENAME)
            url = "%s/dists/%s/Release" % (repo.uri, new_dist)
            timestamp = self.get_url_last_modified(url)
            if timestamp == None:
                problems.append(_("%s does not support %s") % (repo.uri, new_dist))

        if len(problems) > 0:
            self.result = RESULT_ERROR
            self.message = _("The following problems were found:")
            table_list = TableList([""])
            table_list.show_column_names = False
            for problem in problems:
                table_list.values.append([problem])
            self.info.append(table_list)
            self.fix = self.run_mintsources
            return

    def get_url_last_modified(self, url):
        try:
            c = pycurl.Curl()
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.CONNECTTIMEOUT, 30)
            c.setopt(pycurl.TIMEOUT, 30)
            c.setopt(pycurl.FOLLOWLOCATION, 1)
            c.setopt(pycurl.NOBODY, 1)
            c.setopt(pycurl.OPT_FILETIME, 1)
            c.perform()
            filetime = c.getinfo(pycurl.INFO_FILETIME)
            if filetime < 0:
                return None
            else:
                return filetime
        except Exception as e:
            return None

    def disable_foreign_repos(self):
        for repo in self.foreign_repos:
            repo.set_enabled(False)
        self.sources.save()

    def run_mintsources(self):
        subprocess.getoutput("mintsources")

# Check APT foreign packages
class APTForeignCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Foreign packages"), _("Looking for foreign packages..."), callback)

    def do_run(self):
        orphans, self.foreigns = get_foreign_packages(find_orphans=False, find_downgradable_packages=True)
        if len(self.foreigns) > 0:
            self.result = RESULT_ERROR
            self.message = _("The following packages need to be downgraded back to official versions:")
            self.fix = self.downgrade_foreign_packages
            table_list = TableList([_("Package"), _("Installed Version"), _("Official version"), _("Archive")])
            for foreign in self.foreigns:
                installed_pkg, version, official_pkg, archive = foreign
                table_list.values.append([installed_pkg.name, version, official_pkg.version, archive])
            self.info.append(table_list)
            self.info.append(_("Otherwise these packages can break the upgrade and create conflicts."))
            return

    def downgrade_foreign_packages(self):
        if len(self.foreigns) > 0:
            pkgs = []
            for foreign in self.foreigns:
                installed_pkg, version, official_pkg, archive = foreign
                pkgs.append("%s=%s" % (installed_pkg.name, official_pkg.version))
            command = '%s apt-get install --allow-downgrades %s %s' % (APT_NONINTERACTIVE, APT_QUIET, " ".join(pkgs))
            print(command)
            os.system(command)

# Check APT orphan packages
class APTOrphanCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Orphan packages"), _("Looking for orphan packages..."), callback)

    def do_run(self):
        if self.get_setting("check-orphans"):
            self.orphans_to_remove = []
            orphans, foreigns = get_foreign_packages(find_orphans=True, find_downgradable_packages=False)
            if len(orphans) > 0:
                settings = Gio.Settings(schema_id="com.linuxmint.mintupgrade")
                to_keep = settings.get_strv("orphans-to-keep")
                for orphan in orphans:
                    pkg, version = orphan
                    if pkg.name not in to_keep:
                        self.orphans_to_remove.append(pkg.name)

                if len(self.orphans_to_remove) > 0:
                    self.result = RESULT_ERROR
                    self.message = _("The following packages do not exist in the repositories:")
                    self.fix = self.remove_orphans
                    table_list = TableList([""])
                    table_list.show_column_names = False
                    for orphan in self.orphans_to_remove:
                        table_list.values.append([orphan])
                    self.info.append(table_list)
                    self.info.append(_("They can create issues during the upgrade."))
                    self.info.append(_("Add the packages you want to keep using the preferences, then press 'Check again'."))
                    self.info.append(_("Then press 'Fix' to remove the packages listed above."))
                    return

    def remove_orphans(self):
        if len(self.orphans_to_remove) > 0:
            command = '%s apt-get remove --purge %s %s' % (APT_NONINTERACTIVE, APT_QUIET, " ".join(self.orphans_to_remove))
            print(command)
            os.system(command)

if __name__ == "__main__":
    test = APTRepoCheck()
    test.do_run()
    print (test.message)
    for info in test.info:
        if isinstance(info, TableList):
            for value in info.values:
                print("   ", value)
        else:
            print(info)
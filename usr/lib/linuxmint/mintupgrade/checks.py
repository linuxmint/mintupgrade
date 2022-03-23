#!/usr/bin/python3
import gi
import threading
from gi.repository import GObject, Gio
import time
import os
from common import *

import gettext, locale
import traceback
import subprocess

# i18n
APP = 'mintupgrade'
LOCALE_DIR = "/usr/share/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

RESULT_SUCCESS, RESULT_INFO, RESULT_WARNING, RESULT_ERROR, RESULT_EXCEPTION = range(5)

ORIGIN = "Linux Mint 19.3 'Tricia'"
ORIGIN_CODENAME = "tricia"
ORIGIN_BASE_CODENAME = "bionic"

DESTINATION = "Linux Mint 20 'Ulyana'"
DESTINATION_CODENAME = "ulyana"
DESTINATION_BASE_CODENAME = "focal"

SUPPORTED_EDITIONS = ["cinnamon", "mate", "xfce"]

CHECK_ABSENT = []

CHECK_PRESENT = ["default-jre", "os-prober"]
CHECK_UP_TO_DATE = ["mintupgrade", "apt", "dpkg", "linuxmint-keyring", "ubuntu-keyring", "mintsystem"]

BACKUP_DIR = os.path.expanduser("~/Upgrade-Backup-%s" % ORIGIN_CODENAME)
BACKUP_APT_SOURCES = os.path.join(BACKUP_DIR, "APT")
BACKUP_FSTAB = os.path.join(BACKUP_DIR, "fstab")
BACKUP_CRYPTTAB = os.path.join(BACKUP_DIR, "crypttab")

PACKAGES_PRE_REMOVALS = []

PACKAGES_REMOVALS = [
    "tomboy",
    "libxplayer-plparser18",
    "xplayer-common",
    "gksu",
    "memtest86+",
    "*hwe-18.04*",
    "linux-hwe*",
    "python3-tinycss", #
    "indicator-application",
    "grub2-theme-mint"
]

PACKAGES_ADDITIONS = [
    "neofetch",
    "ffmpegthumbnailer",
    "amd64-microcode",
    "intel-microcode",
    "celluloid",
    "drawing",
    "gnote",
    "adwaita-icon-theme-full", # 19.3->20
    "warpinator", #
    "alsa-topology-conf", #
    "alsa-ucm-conf", #
    "mesa-vdpau-drivers", #
    "mesa-vulkan-drivers", #
    "cryptsetup-initramfs",
    "cryptsetup-run",
    "libreoffice-gtk3",
    "gamemode"
]

IMPORTANT_PACKAGES = [
    "mint-meta-cinnamon",
    "mint-meta-mate",
    "mint-meta-xfce",
    "xreader",
    "xed",
    "xviewer",
    "pix",
    "mintsystem",
    "metacity",
    "nemo-preview",
    "mintdrivers",
    "mintupdate",
    "mintsources",
    "mintinstall"
]

class UpgradeInfo():
    def __init__(self):
        self.toto = None

class Check():
    def __init__(self, title, description, callback=None):
        self.title = title
        self.description = description
        self.result = RESULT_SUCCESS
        self.finished = False
        self.message = ""
        self.callback = callback
        self.allow_recheck = True

    @async_function
    def run(self):
        print("Running check '%s'" % self.title)
        try:
            self.do_run()
        except Exception as e:
            self.message = traceback.format_exc()
            self.result = RESULT_EXCEPTION
        self.finalize()

    def do_run(self):
        pass

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
        # Check override
        if not self.get_setting("check-version"):
            self.result = RESULT_SUCCESS
            return

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


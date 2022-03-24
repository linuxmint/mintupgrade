#!/usr/bin/python3
import os

RESULT_SUCCESS, RESULT_INFO, RESULT_WARNING, RESULT_ERROR, RESULT_EXCEPTION = range(5)

ORIGIN = "Linux Mint 20.3 'Una'"
ORIGIN_CODENAME = "una"
ORIGIN_BASE_CODENAME = "focal"

DESTINATION = "Linux Mint 21 'Vanessa'"
DESTINATION_CODENAME = "vanessa"
DESTINATION_BASE_CODENAME = "jammy"

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


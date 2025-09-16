ORIGIN = "LMDE 6 'Faye'"
ORIGIN_CODENAME = "faye"
ORIGIN_BASE_CODENAME = "bookworm"

DESTINATION = "LMDE 7 'Gigi'"
DESTINATION_CODENAME = "gigi"
DESTINATION_BASE_CODENAME = "trixie"

SUPPORTED_EDITIONS = ["cinnamon"]

CHECK_ABSENT = []

CHECK_PRESENT = ["os-prober"]
CHECK_UP_TO_DATE = ["mintupgrade", "apt", "dpkg", "linuxmint-keyring", "debian-keyring", "debian-archive-keyring", "mintsystem"]

KERNEL_META = ["linux-image-amd64", "linux-headers-amd64"]

PACKAGES_PRE_REMOVALS = [
    "redshift",
    "redshift-gtk",
    "gpg-wks-server",
]

PACKAGES_ADDITIONS = [
    "aptkit",
    "captain",
    "celluloid",
    "dhcpcd-base",
    "ethtool",
    "fingwit",
    "firmware-ast",
    "firmware-ath9k-htc",
    "firmware-carl9170",
    "firmware-cavium",
    "firmware-cirrus",
    "firmware-intel-graphics",
    "firmware-intel-misc",
    "firmware-intel-sound",
    "firmware-marvell-prestera",
    "firmware-mediatek",
    "firmware-myricom",
    "firmware-netronome",
    "firmware-netxen",
    "firmware-nvidia-graphics",
    "firmware-siano",
    "fonts-noto-core",
    "fwupd-amd64-signed",
    "gnome-font-viewer",
    "gnome-online-accounts-gtk",
    "heif-thumbnailer",
    "hypnotix",
    "iio-sensor-proxy",
    "libgtk-4-bin",
    "libgtk-4-media-gstreamer",
    "mdadm",
    "simple-scan",
    "sysstat",
    "thin-provisioning-tools",
    "tree",
    "xcvt",
]

PACKAGES_ADDITIONS_CINNAMON = [
    "nemo-preview"
]

PACKAGES_ADDITIONS_MATE = []

PACKAGES_ADDITIONS_XFCE = []

PACKAGES_REMOVALS = [
    "aptdaemon",
    "gdebi",
    "gdebi-core",
    "gstreamer1.0-pulseaudio",
    "postfix",
    "synaptic",
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
    "mintinstall",
    "ubuntu-system-adjustments",
    "debian-system-adjustments",
    "cinnamon",
    "cinnamon-control-center",
    "cinnamon-session",
    "cinnamon-settings-daemon",
    "cinnamon-screensaver",
    "cjs",
    "nemo",
    "xfwm4",
    "mate-panel",
    "marco",
    "caja",
    "mate-settings-daemon",
    "xfce4-xapp-status-plugin",
    "gnome-calendar",
    "onboard",
    "lightdm",
    "slick-greeter",
    "plymouth"
]

NEW_ORPHANS_TO_KEEP = [

]
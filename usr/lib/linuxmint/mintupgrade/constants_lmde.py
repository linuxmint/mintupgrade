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

PACKAGES_PRE_REMOVALS = []

PACKAGES_ADDITIONS = [
    "fingwit",
    "aptkit",
    "captain",
    "gnome-online-account",
    "hypnotix",
    "celluloid",
    "simple-scan",
]

PACKAGES_ADDITIONS_CINNAMON = [
    "nemo-preview"
]

PACKAGES_ADDITIONS_MATE = []

PACKAGES_ADDITIONS_XFCE = []

PACKAGES_REMOVALS = [
    "synaptic",
    "gdebi",
    "aptdaemon",
    "postfix",
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
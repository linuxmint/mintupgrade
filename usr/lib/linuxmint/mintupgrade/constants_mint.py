ORIGIN = "Linux Mint 21.3 'Virginia'"
ORIGIN_CODENAME = "virginia"
ORIGIN_BASE_CODENAME = "jammy"

DESTINATION = "Linux Mint 22 'Wilma'"
DESTINATION_CODENAME = "wilma"
DESTINATION_BASE_CODENAME = "noble"

SUPPORTED_EDITIONS = ["cinnamon", "mate", "xfce"]

CHECK_ABSENT = ["ippusbxd"]

CHECK_PRESENT = ["os-prober"]
CHECK_UP_TO_DATE = ["mintupgrade", "apt", "dpkg", "linuxmint-keyring", "ubuntu-keyring", "mintsystem"]

KERNEL_META = ["linux-generic"]

PACKAGES_PRE_REMOVALS = []

PACKAGES_ADDITIONS = [
    "celluloid",
    "fonts-noto-core",
    "gnome-online-accounts-gtk",
    "hplip",
    "hypnotix",
    "pipewire-alsa",
    "pipewire-audio",
    "pipewire-pulse",
    "simple-scan",
    "systemd-timesyncd",
    "wireplumber",
    "xapp-jxl-thumbnailer",
    "xcvt",
    "yt-dlp",
    "zstd"
]

PACKAGES_ADDITIONS_CINNAMON = [
    "nemo-preview"
]

PACKAGES_ADDITIONS_MATE = []

PACKAGES_ADDITIONS_XFCE = []

PACKAGES_REMOVALS = [
    "gnome-font-viewer",
    "gnome-logs",
    "gstreamer1.0-pulseaudio",
    "ntp",
    "ntpdate",
    "postfix",
    "pulseaudio",
    "pulseaudio-module-bluetooth",
    "qt5ct",
    "redshift-gtk",
    "xfce4-statusnotifier-plugin",
    "xfce4-volumed",
    "youtube-dl"
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

NEW_ORPHANS_TO_KEEP = []
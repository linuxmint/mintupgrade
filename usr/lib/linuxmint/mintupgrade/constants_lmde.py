ORIGIN = "LMDE 5 'Elsie'"
ORIGIN_CODENAME = "elsie"
ORIGIN_BASE_CODENAME = "bullseye"

DESTINATION = "LMDE 6 'Faye'"
DESTINATION_CODENAME = "faye"
DESTINATION_BASE_CODENAME = "bookworm"

SUPPORTED_EDITIONS = ["cinnamon"]

CHECK_ABSENT = []

CHECK_PRESENT = ["os-prober"]
CHECK_UP_TO_DATE = ["mintupgrade", "apt", "dpkg", "linuxmint-keyring", "debian-keyring", "debian-archive-keyring", "mintsystem"]

KERNEL_META_32 = ["linux-image-686", "linux-headers-686"]
KERNEL_META_64 = ["linux-image-amd64", "linux-headers-amd64"]

PACKAGES_PRE_REMOVALS = []

PACKAGES_ADDITIONS = [
    "wmctrl",
    "mint-l-theme",
    "mint-l-icons",
    "heif-gdk-pixbuf",
    "xdg-desktop-portal-xapp",
    "switcheroo-control",
    "mint-backgrounds-victoria",
    "systemd-timesyncd",
    "pipewire-audio",
    "touchegg",
    "zstd",
    "yt-dlp"
]

PACKAGES_REMOVALS = [
    "gnome-font-viewer",
    "gnome-control-center",
    "desktop-base",
    "malcontent"
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
    "dnscrypt-proxy"
]
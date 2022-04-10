ORIGIN = "LMDE 4 'Debbie'"
ORIGIN_CODENAME = "debbie"
ORIGIN_BASE_CODENAME = "buster"

DESTINATION = "LMDE 5 'Elsie'"
DESTINATION_CODENAME = "elsie"
DESTINATION_BASE_CODENAME = "bullseye"

SUPPORTED_EDITIONS = ["cinnamon"]

CHECK_ABSENT = ["ippusbxd"]

CHECK_PRESENT = ["os-prober"]
CHECK_UP_TO_DATE = ["mintupgrade", "apt", "dpkg", "linuxmint-keyring", "ubuntu-keyring", "mintsystem"]

PACKAGES_PRE_REMOVALS = []

PACKAGES_REMOVALS = [
    "gnote",
    "ipp-usb"
]

PACKAGES_ADDITIONS = [
    "alsa-topology-conf",
    "alsa-ucm-conf",
    "bulky",
    "cryptsetup-initramfs",
    "cryptsetup-run",
    "gamemode",
    "hypnotix",
    "libgdk-pixbuf2.0-bin",
    "libreoffice-gtk3",
    "mesa-vdpau-drivers",
    "mesa-vulkan-drivers",
    "mintreport",
    "neofetch",
    "seahorse",
    "sticky",
    "system-config-printer",
    "thingy",
    "warpinator",
    "webapp-manager",
    "xapp-appimage-thumbnailer",
    "xapp-epub-thumbnailer",
    "xapp-mp3-thumbnailer",
    "xapp-raw-thumbnailer",
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

#!/usr/bin/python3
import gettext
import gi
import locale
import os
import setproctitle
import subprocess
import warnings
import sys
import traceback

# Suppress GTK deprecation warnings
warnings.filterwarnings("ignore")

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, Gdk, Gio, XApp

from common import *
from checks import *

setproctitle.setproctitle("mintupgrade")

# i18n
APP = 'mintupgrade'
LOCALE_DIR = "/usr/share/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext


class MyApplication(Gtk.Application):

    def __init__(self, application_id, flags):
        Gtk.Application.__init__(self, application_id=application_id, flags=flags)
        self.connect("activate", self.activate)

    def activate(self, application):
        windows = self.get_windows()
        if (len(windows) > 0):
            window = windows[0]
            window.present()
            window.show()
        else:
            window = MainWindow(self)
            self.add_window(window.window)
            window.window.show()

class MainWindow():

    def __init__(self, application):

        self.application = application
        self.settings = Gio.Settings(schema_id="com.linuxmint.mintupgrade")

        # Main UI
        gladefile = "/usr/share/linuxmint/mintupgrade/mintupgrade.ui"
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(APP)
        self.builder.add_from_file(gladefile)
        self.window = self.builder.get_object("main_window")
        self.window.set_title(_("MintUpgrade"))
        self.window.set_icon_name("mintupgrade")
        self.stack = self.builder.get_object("stack")

        # CSS
        provider = Gtk.CssProvider()
        provider.load_from_path("/usr/share/linuxmint/mintupgrade/mintupgrade.css")
        screen = Gdk.Display.get_default_screen(Gdk.Display.get_default())
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Widget signals
        self.window.connect("key-press-event",self.on_key_press_event)

        #dark mode
        prefer_dark_mode = self.settings.get_boolean("prefer-dark-mode")
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", prefer_dark_mode)
        self.builder.get_object("darkmode_switch").set_active(prefer_dark_mode)
        self.builder.get_object("darkmode_switch").connect("notify::active", self.on_darkmode_switch_toggled)

        # Menubar
        accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(accel_group)
        menu = self.builder.get_object("main_menu")
        item = Gtk.ImageMenuItem()
        item.set_image(Gtk.Image.new_from_icon_name("preferences-desktop-keyboard-shortcuts-symbolic", Gtk.IconSize.MENU))
        item.set_label(_("Preferences"))
        item.connect("activate", self.open_preferences)
        menu.append(item)
        item = Gtk.ImageMenuItem()
        item.set_image(Gtk.Image.new_from_icon_name("preferences-desktop-keyboard-shortcuts-symbolic", Gtk.IconSize.MENU))
        item.set_label(_("Keyboard Shortcuts"))
        item.connect("activate", self.open_keyboard_shortcuts)
        key, mod = Gtk.accelerator_parse("<Control>K")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(item)
        item = Gtk.ImageMenuItem()
        item.set_image(Gtk.Image.new_from_icon_name("help-about-symbolic", Gtk.IconSize.MENU))
        item.set_label(_("About"))
        item.connect("activate", self.open_about)
        key, mod = Gtk.accelerator_parse("F1")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(item)
        item = Gtk.ImageMenuItem(label=_("Quit"))
        image = Gtk.Image.new_from_icon_name("application-exit-symbolic", Gtk.IconSize.MENU)
        item.set_image(image)
        item.connect('activate', self.on_menu_quit)
        key, mod = Gtk.accelerator_parse("<Control>Q")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        key, mod = Gtk.accelerator_parse("<Control>W")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(item)
        menu.show_all()

        self.window.show()

        self.builder.get_object("go_back_button").hide()
        self.builder.get_object("go_back_button").connect("clicked", self.go_back)

        self.builder.get_object("button_lets_go").connect("clicked", self.letsgo)

        self.last_check = None # the last check which finished
        self.builder.get_object("error_check_button").connect("clicked", self.check_again)

        version_check = VersionCheck(callback=self.process_check_result)
        version_check.run()

    def check_again(self, button):
        if self.last_check != None:
            self.last_check.run()

    def letsgo(self, button):
        self.checks = []
        power_check = PowerCheck(callback=self.process_check_result)
        self.checks.append(power_check)
        self.run_next_check()

    def run_next_check(self):
        if len(self.checks) > 0:
            check = self.checks[0]
            self.builder.get_object("upgrade_stack").set_visible_child_name("page_spinner")
            self.builder.get_object("label_check_title").set_text(check.title)
            self.builder.get_object("label_check_description").set_text(check.description)
            check.run()
        else:
            print("Finished running them all!")

    @idle_function
    def process_check_result(self, check):
        self.last_check = check
        if check.result == RESULT_SUCCESS:
            print("Check succeeded: ", check.title)
            if isinstance(check, VersionCheck):
                self.builder.get_object("upgrade_stack").set_visible_child_name("page_welcome")
            if check in self.checks:
                self.checks.remove(check)
                self.run_next_check()
        elif check.result == RESULT_EXCEPTION:
            self.builder.get_object("upgrade_stack").set_visible_child_name("page_exception")
            self.builder.get_object("label_stacktrace").set_text(check.message)
        else:
            self.builder.get_object("upgrade_stack").set_visible_child_name("page_error")
            self.builder.get_object("label_error_title").set_text(check.title)
            self.builder.get_object("label_error_text").set_text(check.message)
            self.builder.get_object("error_check_button").set_visible(check.allow_recheck)

    @idle_function
    def navigate_to(self, page, name=""):
        if page == "main_page":
            self.builder.get_object("go_back_button").hide()
        else:
            self.builder.get_object("go_back_button").show()
        self.stack.set_visible_child_name(page)

    def open_preferences(self, widget):
        self.navigate_to("preferences_page")

    def go_back(self, widget):
        self.navigate_to("main_page")

    def open_about(self, widget):
        dlg = Gtk.AboutDialog()
        dlg.set_transient_for(self.window)
        dlg.set_title(_("About"))
        dlg.set_program_name(_("MintUpgrade"))
        dlg.set_comments(_("Upgrade Tool"))
        try:
            h = open('/usr/share/common-licenses/GPL', encoding="utf-8")
            s = h.readlines()
            gpl = ""
            for line in s:
                gpl += line
            h.close()
            dlg.set_license(gpl)
        except Exception as e:
            print (e)

        dlg.set_version("__DEB_VERSION__")
        dlg.set_icon_name("mintupgrade")
        dlg.set_logo_icon_name("mintupgrade")
        dlg.set_website("https://www.github.com/linuxmint/mintupgrade")
        def close(w, res):
            if res == Gtk.ResponseType.CANCEL or res == Gtk.ResponseType.DELETE_EVENT:
                w.destroy()
        dlg.connect("response", close)
        dlg.show()

    def open_keyboard_shortcuts(self, widget):
        gladefile = "/usr/share/linuxmint/mintupgrade/shortcuts.ui"
        builder = Gtk.Builder()
        builder.set_translation_domain(APP)
        builder.add_from_file(gladefile)
        window = builder.get_object("shortcuts")
        window.set_title(_("MintUpgrade"))
        window.show()

    def on_darkmode_switch_toggled(self, widget, key):
        prefer_dark_mode = widget.get_active()
        self.settings.set_boolean("prefer-dark-mode", prefer_dark_mode)
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", prefer_dark_mode)

    def on_menu_quit(self, widget):
        self.application.quit()

    def on_key_press_event(self, widget, event):
        persistant_modifiers = Gtk.accelerator_get_default_mod_mask()
        modifier = event.get_state() & persistant_modifiers
        ctrl = modifier == Gdk.ModifierType.CONTROL_MASK
        shift = modifier == Gdk.ModifierType.SHIFT_MASK

        if ctrl and event.keyval == Gdk.KEY_r:
            # Ctrl + R
            pass
        elif ctrl and event.keyval == Gdk.KEY_f:
            # Ctrl + F
            pass
        elif event.keyval == Gdk.KEY_F11:
             # F11..
             pass

if __name__ == "__main__":
    application = MyApplication("com.linuxmint.mintupgrade", Gio.ApplicationFlags.FLAGS_NONE)
    application.run()

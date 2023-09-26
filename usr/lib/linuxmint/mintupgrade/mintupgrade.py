#!/usr/bin/python3
import gettext
import gi
import locale
import os
import setproctitle
import warnings

# Suppress GTK deprecation warnings
warnings.filterwarnings("ignore")

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, Gdk, Gio, XApp

from common import *
from constants import *
from checks import *
from apt_utils import *

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
        self.window.connect("delete-event", self.on_window_close)
        self.window.set_title(_("Upgrade Tool"))
        self.window.set_icon_name("mintupgrade")
        self.stack = self.builder.get_object("stack")
        self.builder.get_object("headerbar").set_subtitle(DESTINATION)

        # CSS
        provider = Gtk.CssProvider()
        provider.load_from_path("/usr/share/linuxmint/mintupgrade/mintupgrade.css")
        screen = Gdk.Display.get_default_screen(Gdk.Display.get_default())
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.builder.get_object("label_welcome").set_text(_("Upgrade to %s") % DESTINATION)

        # Widget signals
        self.window.connect("key-press-event",self.on_key_press_event)

        # preferences
        self.settings.bind("check-timeshift", self.builder.get_object("timeshift_switch"), "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("check-updates", self.builder.get_object("updates_switch"), "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("check-version", self.builder.get_object("version_switch"), "active", Gio.SettingsBindFlags.DEFAULT)

        # Menubar
        accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(accel_group)
        menu = self.builder.get_object("main_menu")
        item = Gtk.ImageMenuItem()
        item.set_image(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.MENU))
        item.set_label(_("Preferences"))
        item.connect("activate", self.open_preferences)
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
        self.builder.get_object("error_fix_button").connect("clicked", self.fix_check)
        self.builder.get_object("error_ok_button").connect("clicked", self.check_ok)
        self.builder.get_object("upgrade_stack").set_visible_child_name("page_welcome")

    def check_again(self, button):
        if self.last_check != None:
            self.builder.get_object("upgrade_stack").set_visible_child_name("page_spinner")
            self.last_check.run()

    def fix_check(self, button):
        if self.last_check != None:
            self.builder.get_object("upgrade_stack").set_visible_child_name("page_spinner")
            self.last_check.run_fix()

    def check_ok(self, button):
        if self.last_check != None:
            self.run_next_check()

    def letsgo(self, button):
        self.checks = []
        pre_upgrade_orphans = []
        skip = apt_points_to_destination()
        if skip:
            print("Note: The APT repositories point towards the destination.")
        info = ShowInfoCheck(_("Phase 1: Preparation"), callback=self.process_check_result)
        info.message = _("A series of tests will now be performed to prepare the computer for the upgrade.")
        self.checks.append(info)
        self.checks.append(VersionCheck(callback=self.process_check_result))
        self.checks.append(PowerCheck(callback=self.process_check_result))
        if not skip:
            self.checks.append(APTCacheCheck(self.window, callback=self.process_check_result))
        self.checks.append(TimeshiftCheck(callback=self.process_check_result))
        self.checks.append(APTHeldCheck(callback=self.process_check_result))
        self.checks.append(APTRepoCheck(callback=self.process_check_result))
        if not skip:
            self.checks.append(APTForeignCheck(callback=self.process_check_result))
            self.checks.append(APTOrphanCheck(pre_upgrade_orphans, self.process_check_result))
        info = ShowInfoCheck(_("Phase 2: Simulation and download"), callback=self.process_check_result)
        info.message = _("Your package repositories will now point towards the new release.")
        info.message = _("A few more tests will be run and package updates will be downloaded.")
        self.checks.append(info)
        self.checks.append(UpdateReposCheck(callback=self.process_check_result))
        self.checks.append(APTCacheCheck(self.window, callback=self.process_check_result))
        self.checks.append(SimulateUpgradeCheck(callback=self.process_check_result))
        self.checks.append(DownloadCheck(self.window, callback=self.process_check_result))
        info = ShowInfoCheck(_("Phase 3: Upgrade"), callback=self.process_check_result)
        info.message = _("The packages will now be upgraded.")
        self.checks.append(info)
        self.checks.append(InhibitCheck(callback=self.process_check_result))
        self.checks.append(PreUpgradeCheck(callback=self.process_check_result))
        self.checks.append(DistUpgradeCheck(callback=self.process_check_result))
        self.checks.append(APTForeignCheck(callback=self.process_check_result))
        if not skip:
            # Only remove orphans if we started the upgrade pointing at the origin repos
            # otherwise pre_upgrade_orphans would be empty and we could remove wanted orphan pkgs.
            self.checks.append(APTRemoveOrphansCheck(pre_upgrade_orphans, self.process_check_result))
        self.checks.append(PostUpgradeCheck(callback=self.process_check_result))
        self.run_next_check()

    def run_next_check(self):
        if len(self.checks) > 0:
            check = self.checks[0]
            self.builder.get_object("upgrade_stack").set_visible_child_name("page_spinner")
            self.builder.get_object("label_check_title").set_text(check.title)
            self.builder.get_object("label_check_description").set_text(check.description)
            check.run()
        else:
            print("Upgrade successful! You can now close this terminal and reboot your computer.")
            self.builder.get_object("upgrade_stack").set_visible_child_name("page_ready")

    @idle_function
    def process_check_result(self, check):
        self.last_check = check
        if check.result == RESULT_SUCCESS:
            print("Check succeeded: ", check.title)
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
            self.builder.get_object("error_ok_button").set_visible(False)
            if check.result == RESULT_ERROR:
                self.builder.get_object("image_error").set_from_icon_name("dialog-error", Gtk.IconSize.DIALOG)
            elif check.result == RESULT_WARNING:
                self.builder.get_object("image_error").set_from_icon_name("dialog-warning", Gtk.IconSize.DIALOG)
            elif check.result == RESULT_INFO:
                self.builder.get_object("error_ok_button").set_visible(True)
                self.builder.get_object("image_error").set_from_icon_name("dialog-info", Gtk.IconSize.DIALOG)
                if check in self.checks:
                    self.checks.remove(check)

            # Show info if any
            box_info = self.builder.get_object("box_info")
            for child in box_info.get_children():
                child.destroy()
            for info in check.info:
                if isinstance(info, str):
                    if info == "---":
                        widget = Gtk.Separator()
                    else:
                        widget = Gtk.Label()
                        widget.set_markup(info)
                        widget.set_line_wrap(True)
                elif isinstance(info, TableList):
                    widget = Gtk.ScrolledWindow()
                    widget.set_min_content_width(400)
                    widget.set_min_content_height(200)
                    widget.set_shadow_type(Gtk.ShadowType.IN)
                    treeview = Gtk.TreeView()
                    treeview.set_headers_visible(info.show_column_names)
                    widget.add(treeview)
                    index = 0
                    types = []
                    for name in info.columns:
                        column = Gtk.TreeViewColumn(name, Gtk.CellRendererText(), text=index)
                        treeview.append_column(column)
                        index += 1
                        types.append(str)
                    model = Gtk.ListStore()
                    model.set_column_types(types)
                    model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
                    for value in info.values:
                        iter = model.insert_before(None, None)
                        index = 0
                        for subval in value:
                            model.set_value(iter, index, subval)
                            index += 1
                    treeview.set_model(model)
                box_info.pack_start(widget, False, False, 0)
                box_info.show_all()
            if len(check.info) > 0:
                self.builder.get_object("scroll_info").show_all()
            else:
                self.builder.get_object("scroll_info").hide()
            if check.message == "":
                self.builder.get_object("label_error_text").hide()
            else:
                self.builder.get_object("label_error_text").show()
            # Activate Fix button if appropriate
            self.builder.get_object("error_fix_button").set_visible(check.fix != None)

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
        dlg.set_program_name(_("Upgrade Tool"))
        dlg.set_comments("mintupgrade")
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
        def close(w, res):
            if res == Gtk.ResponseType.CANCEL or res == Gtk.ResponseType.DELETE_EVENT:
                w.destroy()
        dlg.connect("response", close)
        dlg.show()

    def on_window_close(self, widget, event):
        self.cleanup_and_exit()

    def on_menu_quit(self, widget):
        self.cleanup_and_exit()

    def cleanup_and_exit(self):
        os.system("killall mintupgrade-inhibit-power")
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

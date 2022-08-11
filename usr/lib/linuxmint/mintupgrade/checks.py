#!/usr/bin/python3
from gi.repository import Gio, GLib
import time
import os
import datetime
from common import *
from constants import *
from apt_utils import *
import gettext, locale
import traceback
import subprocess
import filecmp
import platform
from pathlib import Path

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

ERROR_APT_DESTINATION = [_(f"The package repositories need to point towards the new release ({DESTINATION_BASE_CODENAME}/{DESTINATION_CODENAME}).")]
ERROR_APT_DESTINATION.append(_("This should have be done by the Upgrade Tool already."))
ERROR_APT_DESTINATION.append(_("Were the repositories modified since?"))
ERROR_APT_DESTINATION.append(_("Re-run the Upgrade tool so that it migrates the repositories again."))

class bcolors:
    MAGENTA = '\033[95m' # Magenta
    BLUE = '\033[94m' # Light Blue
    GREEN = '\033[92m' # Light Green
    ORANGE = '\033[38;5;202m' # Orange
    RED = '\033[91m' # Light Red
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def run_command(command):
    print(f"{bcolors.ORANGE}{command}{bcolors.ENDC}", flush=True)
    try:
        subprocess.check_call(f"LANGUAGE=C LANG=C {command}", shell=True, start_new_session=True)
    except subprocess.CalledProcessError as e:
        print_error(f"Error - Return code: {e.returncode}")
        return False
    return True
    # ret = os.system(command)
    # return ret

def print_error(string):
    print_output(string, bcolors.RED)

def print_output(string, color=bcolors.MAGENTA):
    print(f"{color}{string}{bcolors.ENDC}", flush=True)

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
        print_output(f"\nRunning check '{self.title}'{bcolors.BLUE}")
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
            print_output(f"\nFixing check '{self.title}'{bcolors.BLUE}")
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
        self.allow_recheck = False
        self.allow_continue = True

    def do_run(self):
        print("=================")
        print("APT Repositories:")
        print("=================")
        subprocess.call("inxi -r", shell=True)
        print("=================")

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
                self.message = _(f"Your version of Linux Mint is '{codename.capitalize()}'. Only {ORIGIN} can be upgraded to {DESTINATION}.")
                return

            # Check edition
            if edition.lower() not in SUPPORTED_EDITIONS:
                self.result = RESULT_ERROR
                self.message = _(f"Your edition of Linux Mint is '{edition}'. It cannot be upgraded to {DESTINATION}.")
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
        super().__init__(_("System snapshots"), _("Checking system snapshots..."), callback)

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
        super().__init__(_("APT cache"), _("Checking the APT cache..."), callback)
        self.cache_updated = False
        self.pkgs_to_remove = []
        self.pkgs_to_install = []
        self.window = window

    def do_run(self):
        # Update the cache
        if not self.cache_updated:
            run_command("rm -rf /var/lib/apt/lists/*")
            run_command("DEBIAN_PRIORITY=critical apt-get update")
            # detect cache errors using python-apt (apt-get doesn't return proper error codes)
            try:
                cache = apt.Cache()
                cache.open()
                cache.update()
            except:
                self.result = RESULT_ERROR
                self.message = _("Your package cache can't refresh correctly. Run 'apt update' and fix the errors it displays.")
                return
            self.cache_updated = True

        cache = apt.Cache()

        # Check broken packages
        if cache.broken_count > 0:
            self.result = RESULT_ERROR
            self.message = _("Some of your packages are broken. Run 'apt install -f' to fix the issue.")
            return

        if not apt_points_to_destination():
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

            if self.pkgs_to_remove or self.pkgs_to_install:
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
        self.sources = aptsources.sourceslist.SourcesList(withMatcher=False)
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
            if source.dist == "stable":
                # 3rd party repository which target Debian stable
                continue
            if ORIGIN_CODENAME in source.dist or DESTINATION_CODENAME in source.dist:
                self.mint_repos.append(source)
            elif ORIGIN_BASE_CODENAME in source.dist or DESTINATION_BASE_CODENAME in source.dist:
                self.base_repos.append(source)
            else:
                self.foreign_repos.append(source)

        # Foreign repositories which codename is not in the origin or the destination (mint or base)
        if self.foreign_repos:
            self.result = RESULT_ERROR
            self.message = _("The following repositories do not explicitly support your version of Linux Mint.")
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
            print_output(f"Mint repository last modified on {mint_date}")
        for repo in self.mint_repos:
            if "packages.linuxmint.com" in repo.uri:
                continue
            timestamp = self.get_url_last_modified(f"{repo.uri}/db/version")
            if timestamp is None:
                problems.append(_(f"{repo.uri} is unreachable"))
            elif mint_age > 2:
                date = datetime.datetime.fromtimestamp(timestamp)
                offset = (mint_date - date).days
                if offset > 2:
                    problems.append(_(f"{repo.uri} is not up to date. Switch to a different mirror."))

        # Check the base repos can handle destination codename
        for repo in self.base_repos:
            if repo.dist == "buster/updates":
                # special case, the repo syntax changed between LMDE 4 and LMDE 5
                new_dist = "bullseye-security"
            else:
                new_dist = repo.dist.replace(ORIGIN_BASE_CODENAME, DESTINATION_BASE_CODENAME)
            url = f"{repo.uri}/dists/{new_dist}/Release"
            timestamp = self.get_url_last_modified(url)
            if timestamp is None:
                problems.append(_(f"{repo.uri} does not support {new_dist}"))

        if problems:
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
            return None if filetime < 0 else filetime
        except Exception as e:
            return None

    def disable_foreign_repos(self):
        for repo in self.foreign_repos:
            repo.set_enabled(False)
        self.sources.save()

    def run_mintsources(self):
        subprocess.getoutput("mintsources")

# Check APT held packages
class APTHeldCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Held packages"), _("Looking for held packages..."), callback)

    def do_run(self):
        self.held = get_held_packages()
        if len(self.held) > 0:
            self.result = RESULT_ERROR
            self.message = _("The following packages are held:")
            self.fix = self.unhold_packages
            table_list = TableList([""])
            table_list.show_column_names = False
            for pkg in self.held:
                table_list.values.append([pkg.name])
            self.info.append(table_list)
            self.info.append(_("Held packages can break the upgrade."))
            return

    def unhold_packages(self):
        if len(self.held) > 0:
            pkgs = [pkg.name for pkg in self.held]
            run_command(f'apt-mark unhold {" ".join(pkgs)}')

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
            self.info.append(_("Otherwise these packages can create conflicts."))
            return

    def downgrade_foreign_packages(self):
        if len(self.foreigns) > 0:
            pkgs = []
            for foreign in self.foreigns:
                installed_pkg, version, official_pkg, archive = foreign
                pkgs.append(f"{installed_pkg.name}={official_pkg.version}")
            run_command(f'{APT_GET} install --allow-downgrades {APT_QUIET} {" ".join(pkgs)}')

# Check APT orphan packages
class APTOrphanCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Orphan packages"), _("Looking for orphan packages..."), callback)

    def do_run(self):
        if not self.get_setting("check-orphans"):
+            return
+        self.orphans_to_remove = []
+        orphans, foreigns = get_foreign_packages(find_orphans=True, find_downgradable_packages=False)
        if len(orphans) > 0:
            settings = Gio.Settings(schema_id="com.linuxmint.mintupgrade")
            to_keep = settings.get_strv("orphans-to-keep")
            for orphan in orphans:
                pkg, version = orphan
                if pkg.name == "mintupgrade":
                    continue
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
                self.info.append(_("Add the packages you want to keep using the preferences, then press 'Check again'."))
                self.info.append(_("Then press 'Fix' to remove the packages listed above."))
                return

    def remove_orphans(self):
        if len(self.orphans_to_remove) > 0:
            run_command(f'{APT_GET} remove --purge {APT_QUIET} {" ".join(self.orphans_to_remove)}')


# Switch to the target repositories
class UpdateReposCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Package repositories"), _("Pointing to the new release..."), callback)

    def do_run(self):
        apt_pkg.init_config()
        self.sources = aptsources.sourceslist.SourcesList(withMatcher=False)
        for source in self.sources:
            if source.disabled:
                # commented out repos
                continue
            if source.uri == "":
                # repos file entries themselves
                continue
            if DESTINATION_CODENAME in source.dist or DESTINATION_BASE_CODENAME in source.dist:
                # already points to target
                print_output(f"{source.uri} already points to {source.dist}")
            elif ORIGIN_CODENAME in source.dist:
                # Mint repo
                source.dist = source.dist.replace(ORIGIN_CODENAME, DESTINATION_CODENAME)
                print_output(f"Switching {source.uri} to {source.dist}")
            elif ORIGIN_BASE_CODENAME in source.dist:
                # Base repo
                if source.dist == "buster/updates":
                    # special case, the repo syntax changed between LMDE 4 and LMDE 5
                    source.dist = "bullseye-security"
                else:
                    source.dist = source.dist.replace(ORIGIN_BASE_CODENAME, DESTINATION_BASE_CODENAME)
                print_output(f"Switching {source.uri} to {source.dist}")
            if DESTINATION_BASE_CODENAME in source.dist and "partner" in source.comps:
                print_output("Disabling partner repo (discontinued).")
                source.set_enabled(False)
        self.sources.save()

# Check conflicts and HDD space
class SimulateUpgradeCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Upgrade simulation"), _("Simulating upgrade to check hard disk space and potential issues..."), callback)

    def do_run(self):
        if not apt_points_to_destination():
            self.result = RESULT_ERROR
            self.allow_recheck = False
            for line in ERROR_APT_DESTINATION:
                self.info.append(line)
            return

        cache = apt.Cache()
        cache.upgrade(True)
        changes = cache.get_changes()
        kept_packages = []
        new_packages = []
        removed_packages = []
        unwanted_removals = []
        for pkg in changes:
            if pkg.is_installed:
                if pkg.marked_delete:
                    if pkg.name in IMPORTANT_PACKAGES:
                        unwanted_removals.append(pkg.name)
                    else:
                        removed_packages.append(pkg.name)
            elif pkg.marked_install:
                new_packages.append(pkg.name)

        if cache.keep_count > 0:
            # kept packages are not part of the changes...
            upgradable_cache_packages = [pkg.name for pkg in cache if pkg.is_upgradable]
            upgradable_changes_packages = [pkg.name for pkg in changes if pkg.is_upgradable]
            kept_packages = list(set(upgradable_cache_packages).difference(set(upgradable_changes_packages)))

        num_new = len(new_packages)
        num_updated = cache.install_count - num_new

        if unwanted_removals:
            self.result = RESULT_ERROR
            self.info.append(_("The simulation was not successful."))
            self.info.append(_("Upgrading would remove the following important packages:"))
            table_list = TableList([_("Unwanted removals")])
            for pkg in unwanted_removals:
                table_list.values.append([pkg])
            self.info.append(table_list)
            self.info.append(_("This is a sign that something is wrong and needs to be fixed before going further."))
            self.info.append("---")
            self.info.append(f'<b>{_("Recommended solution")}</b>')
            self.info.append(_("Use apt-get in a terminal to troubleshoot and solve the issue."))
            self.info.append(_("Don't hesitate to seek help on the forums and the chat room."))
            self.info.append("---")
            self.info.append(f'<b>{_("Additional information")}</b>')
            self.info.append(_("The information below might help solve the issue."))
            self.show_list(_("Kept packages"), kept_packages)
            self.show_list(_("Removed packages"), removed_packages)
            self.show_list(_("Added packages"), new_packages)
            self.info.append(_(f"Packages updated: {num_updated}, added: {num_new} , kept: {len(kept_packages)}, deleted: {len(removed_packages)}"))
            return

        self.info.append(_("Upgrading will perform the following changes."))

        self.check_disk_space_requirements(cache)
        if self.result != RESULT_ERROR:
            self.result = RESULT_INFO
            self.info.append(_(f"Packages updated: {num_updated}, added: {num_new} , kept: {len(kept_packages)}, deleted: {len(removed_packages)}"))
            self.show_list(_("Kept packages"), kept_packages)
            if kept_packages:
                self.info.append(_("Note: Ideally, no packages should be kept. This might indicate an issue."))
            self.show_list(_("Added packages"), new_packages)
            self.show_list(_("Removed packages"), removed_packages)
            if removed_packages:
                self.info.append(_("Go through the list above and make sure you are happy with the removals before going further with the upgrade."))

    def show_list(self, col_name, l):
        if len(l) > 0:
            table_list = TableList([col_name])
            for i in l:
                table_list.values.append([i])
            self.info.append(table_list)

    def check_disk_space_requirements(self, cache):
        # get download size
        pm = apt_pkg.PackageManager(cache._depcache)
        fetcher = apt_pkg.Acquire()

        # this may fail, but you'll still get the download size, vs cache.required_download
        try:
            pm.get_archives(fetcher, cache._list, cache._records)
        except Exception:
            pass

        download_size = fetcher.fetch_needed
        # additional space needed when all finished
        additional_space_needed = cache._depcache.usr_size

        # gather mount info so we calculate free space correctly.
        mounted = []
        mnt_map = {}
        fs_free = {}
        with open("/proc/mounts") as mounts:
            for line in mounts:
                try:
                    (what, where, fs, options, a, b) = line.split()
                except ValueError as e:
                    continue
                if where not in mounted:
                    mounted.append(where)
        # make sure mounted is sorted by longest path
        mounted.sort(key=len, reverse=True)

        class FreeSpace(object):
            " helper class that represents the free space on each mounted fs "
            def __init__(self, initialFree):
                self.initial_free = initialFree
                self.free = initialFree
                self.need = 0

        def make_fs_id(d):
            """ return 'id' of a directory so that directories on the
                same filesystem get the same id (simply the mount_point)
            """
            for mount_point in mounted:
                if d.startswith(mount_point):
                    return mount_point
            return "/"

        archivedir = apt_pkg.config.find_dir("Dir::Cache::archives")

        for d in ["/", "/usr", "/boot", archivedir, "/tmp/"]:
            d = os.path.realpath(d)
            fs_id = make_fs_id(d)
            if os.path.exists(d):
                st = os.statvfs(d)
                free = st.f_bavail * st.f_frsize
            else:
                free = 0
            if fs_id in mnt_map:
                fs_free[d] = fs_free[mnt_map[fs_id]]
            else:
                mnt_map[fs_id] = d
                fs_free[d] = FreeSpace(free)

        # sum up space requirements
        for (dir, size) in [
            (archivedir, download_size),
            ("/usr", additional_space_needed),
            # plus 50M safety buffer in /usr
            ("/usr", 50 * 1024 * 1024), # buffer
            ("/boot", 50 * 1024 * 1024), # buffer - should we calculate real kernel/initramfs space required?
            ("/tmp", 5 * 1024 * 1024),   # /tmp for dkms LP: #427035
            ("/", 10 * 1024 * 1024),     # more buffer /
        ]:
            # we are ensuring we have more than enough free space not less
            if size < 0:
                continue
            dir = os.path.realpath(dir)
            fs_free[dir].free -= size
            fs_free[dir].need += size

        for dir in fs_free:
            free_needed_str = GLib.format_size(fs_free[dir].need)
            initial_free_str = GLib.format_size(fs_free[dir].initial_free)
            if fs_free[dir].free < 0:
                free_at_least_str = GLib.format_size(abs(fs_free[dir].free) + 1024 * 1024 * 10)
                self.result = RESULT_ERROR
                self.info.append(_(f"You need {free_needed_str} on '{make_fs_id(dir)}' but only have {initial_free_str}. You must free an additional {free_at_least_str}."))
                return

        self.info.append(_(f"Download size: {GLib.format_size(download_size)}. Additional space needed: {GLib.format_size(additional_space_needed)}."))

# Download updates
class DownloadCheck(Check):

    def __init__(self, window, callback=None):
        super().__init__(_("Package download"), _("Downloading packages..."), callback)
        self.window = window

    def do_run(self):
        if not apt_points_to_destination():
            self.result = RESULT_ERROR
            self.allow_recheck = False
            for line in ERROR_APT_DESTINATION:
                self.info.append(line)
            return
        ret = run_command(f"{APT_GET} dist-upgrade --download-only --yes")
        if not ret:
            self.message = _("An error occurred while downloading the packages.")
            self.result = RESULT_ERROR

# Inhibit session
class InhibitCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Session inhibition"), _("Inhibiting session..."), callback)

    def do_run(self):
        cmd = ["mintupgrade-inhibit-power", os.getenv("SUDO_UID")]
        subprocess.Popen(cmd)

class PreUpgradeCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Upgrade preparation"), _("Preparing the upgrade..."), callback)

    def do_run(self):
        if not apt_points_to_destination():
            self.result = RESULT_ERROR
            self.allow_recheck = False
            for line in ERROR_APT_DESTINATION:
                self.info.append(line)
            return

        if not os.path.exists(BACKUP_FSTAB):
            print_output("Saving /etc/fstab")
            os.system(f"cp /etc/fstab {BACKUP_FSTAB}")

        if IS_LMDE and not os.path.exists(BACKUP_LOCALEDEF):
            print_output("Saving locales definition")
            os.system(f"localedef --list-archive > {BACKUP_LOCALEDEF}")

        print_output("Removing blacklisted packages")
        for removal in PACKAGES_PRE_REMOVALS:
            # The return code indicates a failure if some packages were not found, so ignore it.
            run_command(f'{APT_GET} remove --yes {removal}')

        # Disable mintsystem during the upgrade
        os.system("crudini --set /etc/linuxmint/mintSystem.conf global enabled False")

class DistUpgradeCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Upgrade phase"), _("Upgrading the system..."), callback)

    def do_run(self):

        if not apt_points_to_destination():
            self.result = RESULT_ERROR
            self.allow_recheck = False
            for line in ERROR_APT_DESTINATION:
                self.info.append(line)
            return

        fallback_commands = ["dpkg --configure -a", f"{APT_GET} install -fyq"]
        # Upgrade
        if not self.try_command(5, f'{APT_GET} upgrade {APT_QUIET}', fallback_commands):
            self.result = RESULT_ERROR
            self.message = _("An issue was detected during the upgrade.")
            self.info.append(self.get_status())
            return
        # Dist-upgrade
        if not self.try_command(5, f'{APT_GET} dist-upgrade {APT_QUIET}', fallback_commands):
            self.result = RESULT_ERROR
            self.message = _("An issue was detected during the upgrade.")
            self.info.append(self.get_status())
            return

    def try_command(self, num_times, command, fallback_commands):
        for i in range(num_times):
            ret = run_command(command)
            if ret == True:
                return True
            print_error(f"Error detected on try #{(i+1)}...")
            if (i+1) < num_times:
                print_output("Retrying...")
            for fallback_command in fallback_commands:
                run_command(fallback_command)
        return False

    def get_status(self):
        cache = apt.Cache()
        cache.upgrade(True)
        return _(f"{cache.install_count} packages still need to be updated ({cache.keep_count} kept, {cache.delete_count} deleted)")

class PostUpgradeCheck(Check):

    def __init__(self, callback=None):
        super().__init__(_("Final phase"), _("Finalizing the upgrade..."), callback)

    def do_run(self):
        if not apt_points_to_destination():
            self.result = RESULT_ERROR
            self.allow_recheck = False
            for line in ERROR_APT_DESTINATION:
                self.info.append(line)
            return

        edition = subprocess.getoutput("crudini --get /etc/linuxmint/info DEFAULT EDITION")
        edition = edition.lower().replace('"', '')
        mint_meta = f"mint-meta-{edition}"

        # Install meta-package
        print_output("Re-installing the meta-package")
        if not run_command(f'{APT_GET} install --yes --no-install-recommends {mint_meta}'):
            self.result = RESULT_ERROR
            self.message = _(f"{mint_meta} could not be installed.")
            return

        # Install codecs
        print_output("Re-installing the multimedia codecs")
        if not run_command(f'{APT_GET} install --yes --no-install-recommends mint-meta-codecs'):
            self.result = RESULT_ERROR
            self.message = _("mint-meta-codecs could not be installed.")
            return

        # Install new packages
        print_output("Installing new packages")
        if len(PACKAGES_ADDITIONS) > 0:
            if not run_command(f'{APT_GET} install --yes --no-install-recommends {" ".join(PACKAGES_ADDITIONS)}'):
                self.result = RESULT_ERROR
                self.message = _("The following packages could not be installed:")
                table_list = TableList([""])
                table_list.show_column_names = False
                cache = apt.Cache()
                for name in PACKAGES_ADDITIONS:
                    if name in cache:
                        pkg = cache[name]
                        if not pkg.is_installed:
                            table_list.values.append([name])
                    else:
                        table_list.values.append([name])
                self.info.append(table_list)
                return

        # Install kernel meta
        print_output("Installing kernel meta")
        KERNEL_META = KERNEL_META_64 if platform.machine() == "x86_64" else KERNEL_META_32
        if len(KERNEL_META) > 0:
            if not run_command(f'{APT_GET} install --yes --no-install-recommends {" ".join(KERNEL_META)}'):
                self.result = RESULT_ERROR
                self.message = _("The following packages could not be installed:")
                table_list = TableList([""])
                table_list.show_column_names = False
                cache = apt.Cache()
                for name in KERNEL_META:
                    if name in cache:
                        pkg = cache[name]
                        if not pkg.is_installed:
                            table_list.values.append([name])
                    else:
                        table_list.values.append([name])
                self.info.append(table_list)
                return

        # Remove packages
        print_output("Removing obsolete packages")
        for removal in PACKAGES_REMOVALS:
            # The return code indicates a failure if some packages were not found, so ignore it.
            run_command(f'{APT_GET} purge --yes {removal}')

        # Autoremove packages
        print_output("Running autoremove to remove unused packages")
        run_command(f"{APT_GET} --purge autoremove --yes")

        # Clean cache (frees space)
        print_output("Running apt-get clean")
        run_command(f"{APT_GET} clean")

        # Adjust Grub title
        if os.path.exists("/usr/share/ubuntu-system-adjustments/systemd/adjust-grub-title"):
            os.system("/usr/share/ubuntu-system-adjustments/systemd/adjust-grub-title")
        elif os.path.exists("/usr/share/debian-system-adjustments/systemd/adjust-grub-title"):
            os.system("/usr/share/debian-system-adjustments/systemd/adjust-grub-title")

        # Re-enable mintsystem
        os.system("crudini --set /etc/linuxmint/mintSystem.conf global enabled True")
        os.system("/usr/lib/linuxmint/mintsystem/mint-adjust.py")

        # Re-define localedef locales
        if IS_LMDE and os.path.exists(BACKUP_LOCALEDEF):
            with open(BACKUP_LOCALEDEF) as defs_file:
                for line in defs_file:
                    line = line.strip().replace("utf8", "UTF-8")
                    if line == "":
                        continue
                    locale = line.split(" ")[0]
                    if "." in locale:
                        short_locale, charmap = locale.split(".")
                        cmd = f"localedef -f {charmap} -i {short_locale} {locale}"
                    else:
                        cmd = f"localedef -i {locale} {locale}"
                    run_command(cmd)

        # Restore /etc/fstab if it was changed
        if not filecmp.cmp('/etc/fstab', BACKUP_FSTAB):
            os.system("cp /etc/fstab /etc/fstab.upgraded")
            os.system(f"cp {BACKUP_FSTAB} /etc/fstab")
            self.result = RESULT_INFO
            self.message = _("/etc/fstab was modified during the upgrade.")
            self.info.append(_("To ensure a successful boot, the upgrade tool restored your original /etc/fstab"))
            self.info.append(_("A copy of the modified file was saved as /etc/fstab.upgraded"))
        else:
            os.unlink(BACKUP_FSTAB)

        # Sync new mintupdate automation flags with systemd timers
        Path("/var/lib/linuxmint").mkdir(parents=True, exist_ok=True)

        if os.path.exists("/etc/systemd/system/timers.target.wants/mintupdate-automation-upgrade.timer"):
            Path("/var/lib/linuxmint/mintupdate-automatic-upgrades-enabled").touch()
        if os.path.exists("/etc/systemd/system/timers.target.wants/mintupdate-automation-autoremove.timer"):
            Path("/var/lib/linuxmint/mintupdate-automatic-removals-enabled").touch()

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

#!/usr/bin/python3
import apt
import apt_pkg
import subprocess
APT_GET = 'DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical  apt-get'
APT_QUIET = '-fyq -o Dpkg::Options::="--force-confnew" -o Dpkg::Options::="--force-overwrite"'

# Returns a tuple containing two lists
# The first list is a list of orphaned packages (packages which have no origin)
# The second list is a list of packages which version is not the official version (this does not
# include packages which simply aren't up to date)
def get_foreign_packages(find_orphans=True, find_downgradable_packages=True):
    orphan_packages = []
    downgradable_packages = []

    cache = apt.Cache()

    for key in cache.keys():
        pkg = cache[key]
        if (pkg.is_installed):
            installed_version = pkg.installed.version

            # Find packages which aren't downloadable
            if (pkg.candidate == None) or (not pkg.candidate.downloadable):
                if find_orphans:
                    downloadable = False
                    for version in pkg.versions:
                        if version.downloadable:
                            downloadable = True
                    if not downloadable:
                        orphan_packages.append([pkg, installed_version])
            if (pkg.candidate != None):
                if find_downgradable_packages:
                    best_version = None
                    archive = None
                    for version in pkg.versions:
                        if not version.downloadable:
                            continue
                        for origin in version.origins:
                            if origin.origin != None and origin.origin.lower() in ("ubuntu", "canonical", "linuxmint"):
                                if best_version is None:
                                    best_version = version
                                    archive = origin.archive
                                else:
                                    if version.policy_priority > best_version.policy_priority:
                                        best_version = version
                                        archive = origin.archive
                                    elif version.policy_priority == best_version.policy_priority:
                                        # same priorities, compare version
                                        return_code = subprocess.call(["dpkg", "--compare-versions", version.version, "gt", best_version.version])
                                        if return_code == 0:
                                            best_version = version
                                            archive = origin.archive

                    if best_version != None and installed_version != best_version and pkg.candidate.version != best_version.version:
                        downgradable_packages.append([pkg, installed_version, best_version, archive])

    return (orphan_packages, downgradable_packages)

# Returns a list of held packages
def get_held_packages():
    held_packages = []
    cache = apt.Cache()
    for key in cache.keys():
        pkg = cache[key]
        if pkg._pkg.selected_state == apt_pkg.SELSTATE_HOLD:
            held_packages.append(pkg)
    return (held_packages)

if __name__ == "__main__":
    # orphans, foreign = get_foreign_packages()
    # if len(orphans) > 0:
    #     print("Orphan packages:")
    #     for pkg in orphans:
    #         print("  ", pkg)
    # if len(foreign) > 0:
    #     print ("Foreign packages:")
    #     for pkg in foreign:
    #         print("  ", pkg)

    held = get_held_packages()
    if len(held) > 0:
        print("Held packages:")
        for pkg in held:
            print("  ", pkg.name)

#!/usr/bin/python3
import os

RESULT_SUCCESS, RESULT_INFO, RESULT_WARNING, RESULT_ERROR, RESULT_EXCEPTION = range(5)

IS_LMDE = os.path.exists("/usr/share/doc/debian-system-adjustments/copyright")
if IS_LMDE:
    from constants_lmde import *
else:
    from constants_mint import *

BACKUP_DIR = os.path.expanduser("~/Upgrade-Backup-%s" % ORIGIN_CODENAME)
BACKUP_APT_SOURCES = os.path.join(BACKUP_DIR, "APT")
BACKUP_FSTAB = os.path.join(BACKUP_DIR, "fstab")
BACKUP_CRYPTTAB = os.path.join(BACKUP_DIR, "crypttab")
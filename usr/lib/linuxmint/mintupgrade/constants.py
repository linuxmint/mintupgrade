#!/usr/bin/python3
import os

RESULT_SUCCESS, RESULT_INFO, RESULT_WARNING, RESULT_ERROR, RESULT_EXCEPTION = range(5)

IS_LMDE = os.path.exists("/usr/share/doc/debian-system-adjustments/copyright")
if IS_LMDE:
    from constants_lmde import *
else:
    from constants_mint import *

BACKUP_FSTAB = os.path.expanduser("~/.fstab.bk")
BACKUP_LOCALEDEF = os.path.expanduser("~/.localedef.bk")

APT_CACHER_NG_HTTPS = 'http://HTTPS///'

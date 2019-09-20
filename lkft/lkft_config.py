# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

citrigger_lkft = {
    'trigger-lkft-aosp-mainline': {
        'mainline-9.0-hikey': 'lkft-android-9.0-mainline',
        'mainline-9.0-hikey-auto': 'lkft-android-9.0-mainline',
        'mainline-9.0-hikey960': 'lkft-android-9.0-mainline-hikey960',
        'mainline-9.0-hikey960-auto': 'lkft-android-9.0-mainline-hikey960',
        'mainline-9.0-x15': 'lkft-android-9.0-mainline-x15',
        'mainline-9.0-x15-auto': 'lkft-android-9.0-mainline-x15',

        'mainline-gki-10.0-gsi-hikey': 'lkft-hikey-aosp-master-mainline-gki',
        'mainline-gki-aosp-master-hikey': 'lkft-hikey-aosp-master-mainline-gki',
        },

    # configs for 4.19 kernels
    'trigger-lkft-ti-4.19': {
        '4.19-9.0-x15': 'lkft-x15-android-9.0-4.19',
        '4.19-9.0-x15-auto': 'lkft-x15-android-9.0-4.19',
        '4.19-9.0-am65x': 'lkft-am65x-android-9.0-4.19',
        '4.19-9.0-am65x-auto': 'lkft-am65x-android-9.0-4.19',
        },
    'trigger-lkft-hikey-4.19': {
        '4.19-9.0-hikey': 'lkft-hikey-android-9.0-4.19',
        '4.19-9.0-hikey-auto': 'lkft-hikey-android-9.0-4.19',
        '4.19-9.0-hikey960': 'lkft-hikey-android-9.0-4.19',
        '4.19-9.0-hikey960-auto': 'lkft-hikey-android-9.0-4.19',
        '4.19-10.0-gsi-hikey': 'lkft-hikey-android-10.0-gsi-4.19',
        '4.19-10.0-gsi-hikey960': 'lkft-hikey-android-10.0-gsi-4.19',
        },
    'trigger-lkft-hikey-aosp-4.19-r': {
        '4.19-master-hikey': 'lkft-hikey-aosp-master-4.19',
        '4.19-master-hikey960': 'lkft-hikey-aosp-master-4.19',
        },

    # configs for 4.14 kernels
    'trigger-lkft-x15-4.14': {
        '4.14-8.1-x15': 'lkft-x15-android-8.1-4.14',
        },
    'trigger-lkft-hikey-4.14-q': {
        '4.14-10.0-gsi-hikey': 'lkft-hikey-10.0-4.14-q',
        '4.14-10.0-gsi-hikey960': 'lkft-hikey-10.0-4.14-q',
        },
    'trigger-lkft-hikey-4.14-premerge-ci': {
        '4.14-9.0-hikey': 'lkft-hikey-aosp-4.14-premerge-ci',
        '4.14-9.0-hikey960': 'lkft-hikey-aosp-4.14-premerge-ci',
        },
    'trigger-lkft-hikey-4.14': {
        '4.14-8.1-hikey': 'lkft-hikey-android-8.1-4.14',
        },

    # configs for 4.9 kernels
    'trigger-lkft-hikey-4.9-q': {
        '4.9-10.0-gsi-hikey': 'lkft-hikey-10.0-4.9-q',
        '4.9-10.0-gsi-hikey960': 'lkft-hikey-10.0-4.9-q',
        },
    'trigger-lkft-hikey-4.9-premerge-ci': {
        '4.9-9.0-hikey': 'lkft-hikey-aosp-4.9-premerge-ci',
        '4.9-9.0-hikey960': 'lkft-hikey-aosp-4.9-premerge-ci',
        },
    'trigger-lkft-hikey-4.9': {
        '4.9-8.1-hikey': 'lkft-hikey-android-8.1-4.9',
        },

    # configs for 4.4 kernels
    'trigger-lkft-hikey-4.4-premerge-ci': {
        '4.4-lts-9.0-hikey': 'lkft-hikey-aosp-4.4-premerge-ci',
        },
    'trigger-lkft-hikey-4.4': {
        '4.4-8.1-hikey': 'lkft-hikey-android-8.1-4.4',
        '4.4-9.0-hikey': 'lkft-hikey-android-9.0-4.4',
        },
}

def find_citrigger(lkft_pname=""):
    if not lkft_pname:
        return None
    for trigger_name, lkft_pnames in citrigger_lkft.items():
        if lkft_pname in lkft_pnames.keys():
            return trigger_name
    return None


def find_cibuild(lkft_pname=""):
    if not lkft_pname:
        return None
    if lkft_pname == 'aosp-master-tracking':
        return 'lkft-aosp-master-tracking'
    for trigger_name, lkft_pnames in citrigger_lkft.items():
        if lkft_pname in lkft_pnames.keys():
            return lkft_pnames.get(lkft_pname)
    return None

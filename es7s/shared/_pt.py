# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------

from pytermor import filtern


def joincoal(*arg: any) -> str:
    return ''.join(map(str, filtern(arg)))

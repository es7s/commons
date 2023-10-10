# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2022-2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------

# python considers first three as line separators

FILE_SEPARATOR = "\x1c"
GROUP_SEPARATOR = "\x1d"
RECORD_SEPARATOR = "\x1e"
UNIT_SEPARATOR = "\x1f"

SEPARATORS = [
    FILE_SEPARATOR,
    GROUP_SEPARATOR,
    RECORD_SEPARATOR,
    UNIT_SEPARATOR,
]


def get_separator(level: int = 0) -> str:
    if level < len(SEPARATORS):
        return SEPARATORS[level]
    raise LookupError

# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import operator
import re
from functools import reduce


def Regex(
    pattern: str,
    ignorecase=False,
    verbose=False,
    dotall=False,
    multiline=False,
) -> re.Pattern[str]:
    flags = reduce(operator.xor, {
        re.IGNORECASE * ignorecase,
        re.VERBOSE * verbose,
        re.DOTALL * dotall,
        re.MULTILINE * multiline,
    })
    return re.compile(pattern, flags)

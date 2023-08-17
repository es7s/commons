# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import typing as t
from functools import partial

_T = t.TypeVar("_T")


def countindex(
    iterable: t.Union[t.Sized, t.Iterable[_T]], start: int = 0
) -> t.Tuple[t.Iterator[t.Tuple[int, _T]], int]:
    """
    Similar to enumerate(), but returns one extra field (total count):

        ((0, seq[0]), (1, seq[1]), (2, seq[2]), ...), 10)
    """
    try:
        total = len(iterable)
    except TypeError:
        iterable = [*iterable]
        total = len(iterable)
    for idx, el in enumerate(iterable, start=start):
        yield idx, total, el


filterf = partial(filter, None)
""" Shortcut for filtering out falsy values. """

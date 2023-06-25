# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import typing as t

_T = t.TypeVar("_T")


def countindex(
    iterable: t.Union[t.Sized, t.Iterable[_T]], start: int = 0
) -> t.Tuple[t.Iterator[t.Tuple[int, _T]], int]:
    try:
        total = len(iterable)
    except TypeError:
        iterable = [*iterable]
        total = len(iterable)
    for idx, el in enumerate(iterable, start=start):
        yield idx, total, el

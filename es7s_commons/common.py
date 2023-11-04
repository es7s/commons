# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from __future__ import annotations

import operator
import re
import time
from functools import reduce

import math
import typing as t
from typing import final


def Regex(
    pattern: str,
    ignorecase=False,
    verbose=False,
    dotall=False,
    multiline=False,
) -> re.Pattern[str]:
    flags = t.cast(
        int,
        reduce(
            operator.xor,
            {
                re.IGNORECASE * ignorecase,
                re.VERBOSE * verbose,
                re.DOTALL * dotall,
                re.MULTILINE * multiline,
            },
        ),
    )
    return re.compile(pattern, flags)


@final
class FinalSingleton:
    _instance: FinalSingleton

    def __init__(self):
        if hasattr(self.__class__, "_instance"):
            raise RuntimeError(f"{self.__class__.__name__} is a singleton")
        self.__class__._instance = self

    @classmethod
    def get_instance(cls: FinalSingleton, require: bool = True) -> FinalSingleton | None:
        if not hasattr(cls, "_instance"):
            if require:
                raise RuntimeError(f"{cls.__name__} is uninitialized")
            return None
        return cls._instance


def autogen(__origin):
    def wrapper(*args, **kwargs):
        if not hasattr(__origin, "__generator"):
            __origin.__generator = __origin(*args, **kwargs)
        return next(__origin.__generator)

    return wrapper


def percentile(
    N: t.Sequence[float],
    percent: float,
    key: t.Callable[[float], float] = lambda x: x,
) -> float:
    """
    Find the percentile of a list of values.

    :param N:        List of values. MUST BE already sorted.
    :param percent:  Float value from 0.0 to 1.0.
    :param key:      Optional key function to compute value from each element of N.
    """
    # origin: https://code.activestate.com/recipes/511478/

    if not N:
        raise ValueError("N should be a non-empty sequence of floats")
    k = (len(N) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c - k)
    d1 = key(N[int(c)]) * (k - f)
    return d0 + d1


def median(
    N: t.Sequence[float],
    key: t.Callable[[float], float] = lambda x: x,
) -> float:
    """
    Find the median of a list of values.
    Wrapper around `percentile()` with fixed ``percent`` argument (=0.5).

    :param N:    List of values. MUST BE already sorted.
    :param key:  Optional key function to compute value from each element of N.
    """
    return percentile(N, percent=0.5, key=key)


def bcs(a, b):
    while a != 0 and b != 0:
        if a > b:
            a %= b
        else:
            b %= a
    return a + b


def lcm(a, b):
    m = a * b
    while a != 0 and b != 0:
        if a > b:
            a %= b
        else:
            b %= a
    return m // (a + b)


def now() -> int:
    return int(time.time())


def nowf() -> float:
    return time.time_ns() / 1e9

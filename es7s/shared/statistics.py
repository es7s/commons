# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import typing as t
import math
def percentile(
    N: t.Sequence[float], percent: float, key: t.Callable[[float], float] = lambda x: x
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


def median(N: t.Sequence[float], key: t.Callable[[float], float] = lambda x: x) -> float:
    """
    Find the median of a list of values.
    Wrapper around `percentile()` with fixed ``percent`` argument (=0.5).

    :param N:    List of values. MUST BE already sorted.
    :param key:  Optional key function to compute value from each element of N.
    """
    return percentile(N, percent=0.5, key=key)



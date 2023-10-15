# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from __future__ import annotations

import typing as t
from functools import update_wrapper
from logging import getLogger, DEBUG
from typing import cast, Optional, Union, overload

import pytermor as pt

from .common import nowf

_F = t.TypeVar("_F", bound=t.Callable[..., t.Any])
_MFT = t.TypeVar("_MFT", bound=t.Callable[[str, t.Any, ...], Optional[Union[str, t.Iterable[str]]]])


@overload
def measure(__origin: _F) -> _F:
    ...

@overload
def measure(*, fmter: _MFT = None, level=DEBUG) -> t.Callable[[_F], _F]:
    ...

def measure(__origin: _F = None, *, fmter: _MFT = None, level=DEBUG) -> _F | t.Callable[[_F], _F]:
    def _default_formatter(delta_s: str, *_, **__) -> t.Iterable[str]:
        yield f"Done in {delta_s}"

    def decorator(origin: t.Callable[..., t.Any]):
        def wrapper(*args, **kwargs):
            logger = getLogger(__package__)
            before_s = nowf()
            result = origin(*args, **kwargs)
            delta_s = nowf() - before_s

            try:
                fmt_fn: _MFT = fmter or _default_formatter
                if msg := fmt_fn(_format_sec(delta_s), result, *args, **kwargs):
                    for m in msg if pt.isiterable(msg) else [msg]:
                        logger.log(level=level, msg=m)
            except Exception as e:  # pragma: no cover
                logger.exception(e)
            return result

        return update_wrapper(cast(_F, wrapper), origin)

    if __origin is not None:
        return decorator(__origin)
    else:
        return decorator


def _trace_render(origin: _F) -> _F:
    def measure_format_in_out(delta_s: str, out: t.Any, *args, **_) -> t.Iterable[str]:
        actor, inp, extra = args
        no_changes = out == inp
        inp_start = pt.cut(inp, 40)
        out_start = pt.cut(out, 40)
        if no_changes:
            yield f"○ {pt.get_qname(actor)} noop in {delta_s} ({len(inp)}): {inp_start!r}"
        else:
            inplen, outlen = (str(len(s or "")) for s in [inp, out])
            maxlen = max(len(inplen), len(outlen))
            yield f"╭ {actor!r} applying {extra!r}"
            yield f"│ IN  ({inplen:>{maxlen}s}): {inp_start!r}"
            yield f"│ OUT ({outlen:>{maxlen}s}): {out_start!r}"
            yield f"╰ {delta_s}"

    @measure(fmter=measure_format_in_out)
    def new_func(*args, **kwargs):
        return origin(*args, **kwargs)

    return update_wrapper(cast(_F, new_func), origin)


def _format_sec(val: float) -> str:  # pragma: no cover
    if val >= 2:
        return f"{val:.1f}s"
    if val >= 2e-3:
        return f"{val*1e3:.0f}ms"
    if val >= 2e-6:
        return f"{val*1e6:.0f}µs"
    if val >= 1e-9:
        return f"{val*1e9:.0f}ns"
    return "<1ns"

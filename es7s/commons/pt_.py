# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from __future__ import annotations

import io
import os
import typing as t
from collections import deque
from functools import partial
from logging import getLogger
from math import ceil
from pathlib import Path

import pytermor as pt
from pytermor import filtern, FT


def joincoal(*arg: any, sep="") -> str:
    return sep.join(map(str, filtern(arg)))


isempty = lambda v: bool(v) and len(str(v).strip())


filtere = partial(filter, isempty)
""" Shortcut for filtering out falsy AND empty values from sequences """


def filterev(mapping: dict) -> dict:
    """Shortcut for filtering out falsy AND empty values from mappings"""
    return dict(filter(lambda kv: isempty(kv[1]), mapping.items()))


class DisposableComposite(pt.Composite):
    pass
    # def render(self, *args) -> str:
    #    return super().render(*args).replace(' ', '_')


class AdaptiveFragment(pt.Fragment):
    COLLAPSE_CHAR = " "
    COLLAPSE_MAX_LVL = 4
    COLLAPSE_FNS = {
        1: lambda s: s.removeprefix,
        2: lambda s: s.removesuffix,
        3: lambda s: s.lstrip,
        4: lambda s: s.rstrip,
    }

    def __init__(self, min_len: int, string: str = "", fmt: FT = None):
        super().__init__(string, fmt)
        self._min_len = min_len
        self._collapse_lvl = 0

    def collapse(self, lvl: int = 0):
        self._collapse_lvl = lvl
        self._string = self.collapsed(lvl)

    def collapsed(self, lvl: int = 0) -> str:
        collapse_fn = self.COLLAPSE_FNS.get(lvl, lambda s: s.strip)
        return collapse_fn(self._string)(self.COLLAPSE_CHAR)

    def delta_collapse(self, lvl: int = 0) -> int:
        return len(self._string) - len(self.collapsed(lvl))

    @property
    def collapse_lvl(self) -> int:
        return self._collapse_lvl

    def shrink(self):
        self._string = self.shrinked()

    def shrinked(self) -> str:
        return self._string[: self._min_len]

    def delta_shrink(self):
        return len(self._string) - len(self.shrinked())


_AF = AdaptiveFragment
_DC = DisposableComposite


class CompositeCompressor(pt.Composite):
    def __init__(self, *parts: pt.RT):
        super().__init__(*parts)

    def append(self, part: pt.RT):
        self._parts.append(part)

    def extend(self, parts: t.Iterable[pt.RT]):
        self._parts.extend(parts)

    def compress(self, max_len: int):
        """
        5 levels of elements compression, from almost transparent to monstrously barbaric:

        * purge       delete special blank "disposable" pseudo-fragments that act as a ballast;
        * collapse    remove whitespace characters marked as removable in adaptive fragments;
        * shrink      decrease the length of adaptive fragments to minimum recommended values,
                      where the labels can still be comprehended (usually 3-4 letters);
        * chop        ignore minimum recommended value, forcefully cut out last characters of
                      the fragments that can be modified externally; try to distribute the
                      resections evenly between all fragments to make them distinguishable from
                      each other as long as possible;
        * eviscerate  throw away the rightmost fragments entirely, which is the only remaining
                      method if the external modification is not supported by element interfaces;
                      this allows to keep at least some parts of some of fragments.
        """
        if max_len == 0:
            self._parts.clear()
            return
        req_delta = len(self) - max_len
        if req_delta <= 0:
            return
        if len(self._parts[0]) > max_len:
            self._parts = deque[pt.IRenderable]([self._parts.popleft()])

        disposables = []
        adaptives = []
        fragments = []

        for part in self._parts:
            if isinstance(part, _DC):
                disposables.append(part)
            elif isinstance(part, _AF):
                adaptives.append(part)
                fragments.append(part)
            elif isinstance(part, pt.Fragment):
                fragments.append(part)

        cur_pack_lvl = 1

        while (req_delta := len(self) - max_len) > 0:
            if max_purge := sum(map(len, disposables)):
                self._purge(disposables, req_delta, max_purge)
                self._debug_compress_level("I")
                disposables.clear()
                continue

            if cur_pack_lvl < _AF.COLLAPSE_MAX_LVL and sum(
                map(lambda af: af.delta_collapse(cur_pack_lvl), adaptives)
            ):
                self._collapse(adaptives, cur_pack_lvl)
                self._debug_compress_level(f"II ({cur_pack_lvl})")
                cur_pack_lvl += 1
                continue

            if max_shrink := sum(map(_AF.delta_shrink, adaptives)):
                self._shrink(adaptives, req_delta - max_shrink)
                self._debug_compress_level("III")
                adaptives.clear()
                continue

            if max_chop := sum(map(len, fragments)):
                self._chop(fragments, req_delta, max_chop)
                self._debug_compress_level("IV")
                fragments.clear()
                continue

            self._eviscerate(max_len)
            self._debug_compress_level("V")
            break  # от греха

    def _debug_compress_level(self, level: str):
        getLogger(__package__).debug(f"Level {level} compression applied: length {len(self)}")

    def _purge(self, disposables: list[_DC], req_delta: int, max_purge: int):
        if req_delta - max_purge > 0:
            for d in disposables:
                self._parts.remove(d)
            return
        for d in sorted(disposables, key=lambda D: -len(D)):
            if req_delta <= 0:
                break
            req_delta -= len(d)
            self._parts.remove(d)

    def _collapse(self, adaptives: list[_AF], lvl: int):
        [a.collapse(lvl) for a in adaptives]

    def _shrink(self, adaptives: list[_AF], req_remain: int):
        [a.shrink() for a in adaptives]

    def _chop(self, fragments: list[pt.Fragment], req_delta: int, delta_chop: int):
        if req_delta - delta_chop > 0:
            for f in fragments:
                self._parts.remove(f)
            return
        chop_ratio = req_delta / len(fragments)
        for f in fragments:
            if req_delta <= 0:
                break
            req_delta -= (chop := ceil(len(f) * chop_ratio))
            if chop >= len(f):
                self._parts.remove(f)
            else:
                f._string = f._string[:-chop]

    def _eviscerate(self, max_len: int):
        while len(self) > max_len and len(self._parts):
            self._parts.pop()


def format_attrs(*o: object, keep_classname=True, level=0, flat=False) -> str:
    def _to_str(a) -> str:
        if (s := str(a)).startswith(cn := a.__class__.__name__):
            if keep_classname:
                return s
            return s.removeprefix(cn)
        return f"'{s}'" if s.count(" ") else s

    def _wrap(s):
        if flat:
            return s
        return f"({s})"

    if len(o) == 1:
        o = o[0]
    if isinstance(o, str):
        return o
    elif isinstance(o, t.Mapping):
        return _wrap(" ".join(f"{_to_str(k)}={format_attrs(v, flat=flat)}" for k, v in o.items()))
    elif issubclass(type(o), io.IOBase):
        return f"{pt.get_qname(o)}['{getattr(o, 'name', '?')}', {getattr(o, 'mode', '?')}]"
    elif isinstance(o, t.Iterable):
        return _wrap(" ".join(format_attrs(v, level=level + 1, flat=flat) for v in o))
    return _to_str(o)


def format_path(path: str | Path, *, color=False, repr=True) -> str | pt.RT:
    fmt = "{!r}" if repr else "{:s}"
    apath = os.path.abspath(str(path))
    result = pt.Text(fmt.format(apath), pt.cv.BLUE)
    if (rpath := os.path.realpath(apath)) != apath:
        result += " -> " + pt.Fragment(fmt.format(rpath), pt.cv.YELLOW)
    if not color:
        result = result.raw()
    return result

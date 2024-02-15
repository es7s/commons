from collections.abc import Iterable
from dataclasses import dataclass
from math import floor, ceil

import pytermor as pt

from .strutil import UCS_CONTROL_CHARS


_dcu = lambda s: pt.apply_filters(
    s,
    pt.SgrStringReplacer,
    pt.StringMapper({chr(k): "" for k in UCS_CONTROL_CHARS}),
)
""" decolorize + cleanup """


@dataclass
class TextStat:
    line_count: int = 0
    max_line_len: int = 0
    col_count: int = 0
    row_count: int = 0
    max_row_len: int = 0


def columns(
        text: pt.RT | Iterable[pt.RT],
        *,
        gap: int | str | pt.RT = 1,
        sectgap: int = 1,
        sectsize: int = None,
        columns_first = False,
        tabs_interval: int = None,
) -> tuple[pt.RT, TextStat]:
    if isinstance(gap, int):
        gap = pt.pad(gap)
    elif gap is None:
        gap = ""

    def __get_len(s: pt.RT):
        if isinstance(s, pt.IRenderable):
            s = s.raw()
        return len(_dcu(s + gap).expandtabs(tabsize=(tabs_interval or 8)))

    def __postprocess(ss: list[pt.RT], sep: str = "\n") -> pt.RT:
        if all(isinstance(s, str) for s in ss):
            return sep.join(ss)
        cmp = pt.Composite()
        linenum = 0
        for s in ss:
            if linenum and sectsize and linenum % sectsize == 0:
                cmp += sep * sectgap
            linenum += 1
            cmp += s + sep
        return cmp

    lines: list[pt.RT | None] = []
    if pt.isiterable(text):
        lines = [*text]
    else:
        lines = text.splitlines()  # pt.RT supports this as well
    lines = pt.flatten(lines)
    if not lines:
        return "", TextStat()

    line_lengths = [__get_len(s) for s in lines]
    ts = TextStat(len(lines), max(line_lengths))

    ts.col_count = floor(pt.get_terminal_width(pad=0) / ts.max_line_len)
    if ts.col_count < 2:
        return __postprocess(lines), ts

    ts.row_count = ceil(ts.line_count / ts.col_count)
    if columns_first and sectsize:
        ts.row_count = ceil(ts.row_count / sectsize) * sectsize

    def _iter_lines() -> Iterable[pt.RT]:
        row_idx = 0
        col_idx = 0
        buf = ""
        while row_idx < ts.row_count and col_idx < ts.col_count:
            if columns_first:
                line_idx = (col_idx * ts.row_count) + row_idx
            else:
                line_idx = (row_idx * ts.col_count) + col_idx
            if line_idx < ts.line_count:
                line = lines[line_idx]
                if line:
                    buf += line
                buf += pt.pad(ts.max_line_len - line_lengths[line_idx] - len(gap))
                if col_idx < ts.col_count - 1:
                    buf += gap
                lines[line_idx] = None
                line_lengths[line_idx] = 0
            col_idx += 1
            if col_idx >= ts.col_count:
                col_idx = 0
                row_idx += 1
                ts.max_row_len = max(ts.max_row_len, __get_len(buf))
                yield buf
                buf = ""

    return __postprocess([*_iter_lines()]), ts

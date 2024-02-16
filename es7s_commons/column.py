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
    lines: list[pt.RT|None],
    *,
    gap: int | str | pt.RT = 1,
    sectgap: int = 1,
    sectsize: int = 0,
    tabsize: int = 8,
    rows_first=False,
) -> tuple[pt.RT, TextStat]:
    """
    Input format:

    (1) list[pt.Text|pt.Composite|pt.Fragment]

        >>> [
        >>>   Text(Fragment('·'), Fragment('PYTHON', Style(fg=231, ...)), ...),  # line 1
        >>>   Text(Fragment('∴the·(op‥'), ...),   # line 2
        >>>   ...,
        >>> ]

    (2) list[str]

        >>> [
        >>>   '\x1b[0m\x1b[01;34m\x1b[23;24m\uf413 \x1b[0m\x1b[0m\x1b[01;34malsa\x1b[0m\x1b[0K',   # line 1
        >>>   '\x1b[01;34m\x1b[23;24m\uf413 \x1b[0m\x1b[01;34mavahi-daemon\x1b[0m\x1b[0K',         # line 2
        >>>   ...,
        >>> ]

    """
    if not lines:
        return "", TextStat()

    if isinstance(gap, int):
        gap = pt.pad(gap)
    elif gap is None:
        gap = ""

    def __get_len(s: pt.RT):
        if not s:
            return 0
        if isinstance(s, pt.IRenderable):
            s = s.raw()
        s = _dcu(s)
        s = s.expandtabs(tabsize)
        return len(s)

    def __postprocess(ss: list[pt.RT], sep: str = "\n") -> pt.RT:
        if all(isinstance(s, str) for s in ss):
            return sep.join(ss)
        cmp = pt.Composite()
        linenum = 0
        for s in ss:
            if sectsize and linenum % sectsize == 0 and linenum > 0:
                cmp += sep * sectgap
            linenum += 1
            cmp += s + sep
        return cmp

    line_lengths = [*map(__get_len, lines)]
    ts = TextStat(len(lines), max(line_lengths))

    # math behind this can be explained as follows: we can fit N columns and (N-1) gaps into specified width,
    # because there is no neccessity to print the very last gap (after last column). thats why we "compensate"
    # it preemptively -- with adding its width to max possible width instead of subtracting it from whenever
    # (as we do not have a value to subtract that from yet at the first place):
    max_col_w = ts.max_line_len + len(gap)
    total_w = pt.get_terminal_width(pad=0) + len(gap)
    ts.col_count = floor(total_w/max_col_w)
    if ts.col_count < 2:
        return __postprocess(lines), ts

    ts.row_count = ceil(ts.line_count / ts.col_count)
    if sectsize and not rows_first:
        ts.row_count = ceil(ts.row_count / sectsize) * sectsize

    def _iter_lines() -> Iterable[pt.RT]:
        row_idx, col_idx, buf = 0, 0, ""
        while row_idx < ts.row_count and col_idx < ts.col_count:
            if rows_first:
                line_idx = (row_idx * ts.col_count) + col_idx
            else:
                line_idx = (col_idx * ts.row_count) + row_idx

            if line_idx < ts.line_count:
                if (line := lines[line_idx]):
                    buf += line
                buf += pt.pad(ts.max_line_len - line_lengths[line_idx])
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

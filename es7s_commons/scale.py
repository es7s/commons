# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import typing as t
from math import floor

import pytermor as pt

from .strutil import to_superscript

FULL_BLOCK = "█"


class Scale(pt.Text):
    SCALE_LEN = 10

    def __init__(
        self,
        ratio: float,
        label_st: pt.FT,
        scale_st: pt.FT,
        length: int = SCALE_LEN,
        allow_partials: bool = True,
        full_block_char: str = FULL_BLOCK,
        start_char: str = None,
        require_not_empty: bool = False,
    ):
        self._ratio = ratio
        self._label_st = label_st
        self._scale_st = scale_st
        self._length = length
        self._allow_partials = allow_partials
        self._full_block_char = full_block_char
        self._start_char = start_char
        self._require_not_empty = require_not_empty

        self.label: str
        self.blocks: str
        super().__init__(*self._make())

    def _make(self) -> t.Iterable[pt.Fragment]:
        ratio_str = pt.format_auto_float(100 * self._ratio, 3)
        if ratio_str == "0.0":
            ratio_str = "e-2"
        if "e" in ratio_str:
            base, exp, power = ratio_str.partition("e")
            ratio_str = base + "10" + to_superscript(power)
        label_str = f"{ratio_str:>4s}% "
        self.label = pt.Fragment(" " + label_str, self._label_st)

        char_num: float = self._length * self._ratio
        full_block_num = floor(char_num)
        blocks_str = self._full_block_char * full_block_num
        if len(blocks_str) and self._start_char:
            blocks_str = self._start_char + blocks_str[1:]
        if self._allow_partials:
            blocks_str += get_partial_hblock(char_num - full_block_num)
        if not blocks_str and self._require_not_empty:
            blocks_str = "▏"
        self.blocks = pt.Fragment(blocks_str, self._scale_st)

        yield self.label
        yield self.blocks
        yield pt.Fragment(" " * (self._length - len(self.blocks)), self._scale_st)


def get_partial_hblock(val: float) -> str:  # @REFACTOR ME
    if val >= 7 / 8:
        return "▉"
    elif val >= 6 / 8:
        return "▊"
    elif val >= 5 / 8:
        return "▋"
    elif val >= 4 / 8:
        return "▌"
    elif val >= 3 / 8:
        return "▍"
    elif val >= 2 / 8:
        return "▎"
    elif val >= 1 / 8:
        return "▏"
    return ""

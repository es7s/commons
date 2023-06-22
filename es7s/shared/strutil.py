# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from __future__ import annotations

import pytermor as pt

SUBSCRIPT_TRANS = str.maketrans(
    {
        "a": "ₐ",
        "e": "ₑ",
        "h": "ₕ",
        "i": "ᵢ",
        "j": "ⱼ",
        "k": "ₖ",
        "l": "ₗ",
        "m": "ₘ",
        "n": "ₙ",
        "o": "ₒ",
        "p": "ₚ",
        "r": "ᵣ",
        "s": "ₛ",
        "t": "ₜ",
        "u": "ᵤ",
        "v": "ᵥ",
        "x": "ₓ",
    }
)


def to_subscript(s: str) -> str:
    return s.lower().translate(SUBSCRIPT_TRANS)


class NamedGroupsRefilter(pt.AbstractNamedGroupsRefilter):
    def _get_renderer(self) -> pt.IRenderer:
        from es7s.shared import get_stdout
        return get_stdout().renderer

    def _render(self, v: pt.RT, st: pt.FT) -> str:
        return self._get_renderer().render(v, st)


class RegexValRefilter(NamedGroupsRefilter):
    def __init__(self, pattern: pt.filter.PTT[str], val_st: pt.FT):
        super().__init__(pattern, {'val': val_st})

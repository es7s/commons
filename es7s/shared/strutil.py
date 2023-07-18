# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from __future__ import annotations

import pytermor as pt


class Transmap(dict[int, str]):
    def __init__(self, inp: str, out: str):
        if (li := len(inp)) != (lo := len(out)):
            raise ValueError(f"Strings should have equal length ({li} != {lo})")
        self._inp_set = set(inp)

        super().__init__(str.maketrans({k: v for (k, v) in zip(inp, out)}))

    def translate(self, s: str, *, strict: bool = False) -> str:
        if strict and (miss := set(s) - self._inp_set):
            raise ValueError(
                f"String contains characters without mapping: "
                + f"{' '.join([*miss][:5])}"
                + (f" (+{len(miss)} more)" if len(miss) > 5 else "")
            )
        return s.translate(self)


SUBSCRIPT_TRANS = Transmap(
    "0123456789+-=()aehijklmnoprstuvx",
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ",
)


def to_subscript(s: str, *, strict: bool = False) -> str:
    return SUBSCRIPT_TRANS.translate(s.lower(), strict=strict)


class NamedGroupsRefilter(pt.AbstractNamedGroupsRefilter):
    def _get_renderer(self) -> pt.IRenderer:
        from es7s.shared import get_stdout

        return get_stdout().renderer

    def _render(self, v: pt.RT, st: pt.FT) -> str:
        return self._get_renderer().render(v, st)


class RegexValRefilter(NamedGroupsRefilter):
    def __init__(self, pattern: pt.filter.PTT[str], val_st: pt.FT):
        super().__init__(pattern, {"val": val_st})

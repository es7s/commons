# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
SUBSCRIPT_TRANS = str.maketrans({
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
})


def to_subscript(s: str) -> str:
    return s.lower().translate(SUBSCRIPT_TRANS)


# @todo to pytermor
def fit(s: str, max_len: int, align='<', overflow='…'):
    max_len = max(0, max_len)
    if max_len <= (ov_len := len(overflow)):
        return overflow[:max_len]

    if len(s) <= max_len:
        return f'{s:{align}{max_len}s}'

    if align == '<':
        return s[:max_len - ov_len] + overflow
    if align == '>':
        return overflow + s[-max_len + ov_len:]
    if align == '^':
        s_chars = max_len - ov_len
        left_part = s_chars // 2
        right_part = s_chars - left_part
        return s[:left_part] + overflow + s[-right_part:]
    raise ValueError(f"Invalid align, expected '<'|'>'|'^', got '{align}'")


def cut(s: str, max_len: int, align='<', overflow='…'):
    if len(s) <= max_len:
        return s
    return fit(s, max_len, align, overflow)

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
def cut(s: str, max_len: int, align: str = '<', overflow = '…'):
    if len(s) > max_len:
        if align == '<':
            return s[:max_len-1] + overflow
        elif align == '>':
            return overflow + s[-max_len+1:]
        else:
            left_part = max_len//2
            right_part = max_len - left_part
            return s[:left_part - 1] + overflow + s[-right_part:]
    return f'{s:{align}{max_len}s}'

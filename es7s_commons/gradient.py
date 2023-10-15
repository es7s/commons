# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------

from logging import getLogger
import re
import typing
from abc import ABCMeta, abstractmethod
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeVar

from pytermor import RGB


_T = TypeVar("_T")


@dataclass(frozen=True)
class GradientPoint:
    pos: float
    col: RGB

    def __post_init__(self):
        getLogger(__package__).debug(f"Created {self!r}")

    def __repr__(self):
        return f"{self.__class__.__name__}[pos={100*self.pos:8.4f}%, {self.col}]"


class GradientSegment:
    def __init__(self, positions: list[float], col_left: RGB, col_right: RGB):
        pos_left, pos_mid, pos_right = positions
        self.p_left: GradientPoint = GradientPoint(pos_left, col_left)
        self.p_right: GradientPoint = GradientPoint(pos_right, col_right)

        col_mid = self._interpolate_2p(self.p_left, self.p_right, pos_mid)
        self.p_mid: GradientPoint = GradientPoint(pos_mid, col_mid)
        getLogger(__package__).debug(f"Created {self!r}")

    def interpolate(self, pos: float) -> RGB:
        if pos <= self.p_mid.pos:
            pp = self.p_left, self.p_mid
        else:
            pp = self.p_mid, self.p_right
        return self._interpolate_2p(*pp, pos=pos)

    def _interpolate_2p(self, p_left: GradientPoint, p_right: GradientPoint, pos: float) -> RGB:
        pos_rel = self._pos_to_relative(p_left.pos, p_right.pos, pos)
        return RGB.from_channels(*[(pos_rel * (cr - cl) + cl) for cl, cr in zip(p_left.col, p_right.col)])

    def _pos_to_relative(self, pos1: float, pos2: float, pos_target: float) -> float:
        return (pos_target - pos1) / (pos2 - pos1)

    def __repr__(self):
        return f"{self.__class__.__name__}[{', '.join(map(repr,[self.p_left, self.p_mid, self.p_right]))}]"


class Gradient:
    def __init__(self, segments: Iterable[GradientSegment] = None, name: str = None):
        self._segments = sorted(segments, key=lambda seg: seg.p_left.pos)
        self._name = name

    def interpolate(self, pos: float) -> RGB:
        if not self._segments:
            return RGB(0)
        idx = 0
        seg = self._segments[0]
        while idx < len(self._segments):
            seg = self._segments[idx]
            if seg.p_left.pos <= pos <= seg.p_right.pos:
                break
            idx += 1
        return seg.interpolate(pos)


class IGradientReader(metaclass=ABCMeta):
    @abstractmethod
    def make(self, data: str) -> Gradient:
        ...


class deque_ext(typing.Generic[_T], deque):
    def mpop(self, amount: int = 1) -> Iterable[_T]:
        while len(self) and amount:
            amount -= 1
            yield self.pop()

    def mpopleft(self, amount: int = 1) -> Iterable[_T]:
        while len(self) and amount:
            amount -= 1
            yield self.popleft()


class GimpGradientReader(IGradientReader):
    def make(self, data_lines: list[str]) -> Gradient:
        try:
            assert data_lines.pop(0).strip() == "GIMP Gradient", "Not a GIMP gradient format"
            gradient_name = data_lines.pop(0).partition("Name:")[2].strip()
            seg_count = int(data_lines.pop(0).strip())
            assert seg_count == len(data_lines), "Malformed gradient data (line mismatch)"
        except (AssertionError, IndexError) as e:
            raise RuntimeError("Failed to read gradient file") from e

        return Gradient(self._read(*data_lines), gradient_name)

    def _read(self, *data_lines: str) -> Iterable[GradientSegment]:
        for line in data_lines:
            if not line:
                continue
            seg_raw = re.split(r"\s+", line.strip())
            if len(seg_raw) < 11:
                continue

            seg_f = deque_ext(map(float, seg_raw))

            seg_pos = [*seg_f.mpopleft(3)]
            seg_col_left = RGB.from_ratios(*map(float, seg_f.mpopleft(3)))
            seg_f.popleft()  # alpha channel value (left)
            seg_col_right = RGB.from_ratios(*map(float, seg_f.mpopleft(3)))
            seg_f.popleft()  # alpha channel value (right)
            seg = GradientSegment(
                [*seg_pos],
                seg_col_left,
                seg_col_right,
            )
            yield seg

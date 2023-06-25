import re
import typing
from abc import ABCMeta, abstractmethod
from collections import deque
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import TypeVar

from pytermor import RGB

from es7s.shared import get_logger


@dataclass(frozen=True)
class GradientPoint:
    pos: float
    col: RGB

    def __post_init__(self):
        get_logger().debug(f"Created {self!r}")

    def __repr__(self):
        return f"{self.__class__.__name__}[pos={100*self.pos:8.4f}%, {self.col}]"


class GradientSegment:
    def __init__(self, positions: list[float], col_left: RGB, col_right: RGB):
        pos_left, pos_mid, pos_right = positions
        self.p_left: GradientPoint = GradientPoint(pos_left, col_left)
        self.p_right: GradientPoint = GradientPoint(pos_right, col_right)

        col_mid = self._interpolate_2p(self.p_left, self.p_right, pos_mid)
        self.p_mid: GradientPoint = GradientPoint(pos_mid, col_mid)
        get_logger().debug(f"Created {self!r}")

    def interpolate(self, pos: float) -> RGB:
        if pos <= self.p_mid.pos:
            pp = self.p_left, self.p_mid
        else:
            pp = self.p_mid, self.p_right
        return self._interpolate_2p(*pp, pos=pos)

    def _interpolate_2p(self, p_left: GradientPoint, p_right: GradientPoint, pos: float) -> RGB:
        pos_rel = self._pos_to_relative(p_left.pos, p_right.pos, pos)
        rgba_vals = dict()
        for k in asdict(RGB(0,0,0)).keys():
            v_left = getattr(p_left.col, k)
            v_right = getattr(p_right.col, k)
            rgba_vals[k] = pos_rel * (v_right - v_left) + v_left
        return RGB(**rgba_vals).apply_thresholds()

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
            return RGB(0, 0, 0)
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


T = TypeVar("T")


class deque_ext(typing.Generic[T], deque):
    def mpop(self, amount: int = 1) -> Iterable[T]:
        while len(self) and amount:
            amount -= 1
            yield self.pop()

    def mpopleft(self, amount: int = 1) -> Iterable[T]:
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
            seg_col_left = RGB(*seg_f.mpopleft(3))
            seg_f.popleft()  # alpha channel value (left)
            seg_col_right = RGB(*seg_f.mpopleft(3))
            seg_f.popleft()  # alpha channel value (right)
            seg = GradientSegment(
                [*seg_pos],
                RGB.from_ratios(*seg_col_left),
                RGB.from_ratios(*seg_col_right),
            )
            yield seg

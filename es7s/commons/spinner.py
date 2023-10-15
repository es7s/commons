# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2022-2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from abc import ABCMeta, abstractmethod
from functools import cached_property


class Spinner(metaclass=ABCMeta):
    def __init__(self):
        self._frame = 0
        self._max_frame = len(self._frames)

    @property
    @abstractmethod
    def _frames(self) -> list[str]:
        raise NotImplementedError

    def render(self, string: str):
        frame = self._frames[self._frame]
        self._frame += 1
        if self._frame >= self._max_frame:
            self._frame = 0
        return f"\r{frame} {string}"


class SpinnerBrailleSquare(Spinner):
    @cached_property
    def _frames(self) -> list[str]:
        # fmt: off
        return [
            "⡀ ", "⠄ ", "⠂ ", "⠁ ",
            "⠈ ", " ⠁", " ⠈", " ⠐",
            " ⠠", " ⢀", " ⡀", "⢀ ",
        ]
        # fmt: on


class SpinnerBrailleSquareCenter(Spinner):
    @cached_property
    def _frames(self) -> list[str]:
        # fmt: off
        return [
            "⡰⠆", "⠴⠆", "⠲⠆", "⠱⠆",
            "⠸⠆", "⠰⠇", "⠰⠎", "⠰⠖",
            "⠰⠦", "⠰⢆", "⠰⡆", "⢰⠆",
        ]
        # fmt: on


class SpinnerBrailleSquareFill(Spinner):
    @cached_property
    def _frames(self) -> list[str]:
        # fmt: off
        return [
            "⢿⣿", "⣻⣿", "⣽⣿", "⣾⣿",
            "⣷⣿", "⣿⣾", "⣿⣷", "⣿⣯",
            "⣿⣟", "⣿⡿", "⣿⢿", "⡿⣿",
        ]
        # fmt: on

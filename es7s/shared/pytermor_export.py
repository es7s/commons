# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------

import typing as t
from abc import abstractmethod

import pytermor as pt
from pytermor import ColorTarget, IColor, SequenceSGR

from .log import get_logger

_T = t.TypeVar("_T", bound=object)

ExtractorT = t.Union[str, t.Callable[[_T], pt.IColor], None]


class DynamicColor(t.Generic[_T], pt.IColor):
    _DEFERRED = False
    _state: _T

    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls)
        if not cls._DEFERRED:
            inst.update()
        return inst

    @classmethod
    def update(cls, **kwargs) -> None:
        cls._state = cls._update(**kwargs)

    @classmethod
    @abstractmethod
    def _update(cls, **kwargs) -> _T:
        raise NotImplementedError

    def __init__(self, extractor: ExtractorT[_T]):
        self._extractor: ExtractorT[_T] = extractor
        super().__init__(0)

    def _extract(self) -> pt.IColor:
        if not hasattr(self, '_state'):
            self.__class__.update()

        state = self.__class__._state
        if self._extractor is None:
            return t.cast(state, pt.IColor)

        if isinstance(self._extractor, t.Callable):
            return self._extractor(state)

        return getattr(state, self._extractor, pt.NOOP_COLOR)

    @property
    def hex_value(self) -> int:
        return self._extract().hex_value

    def to_sgr(self, target: ColorTarget = ColorTarget.FG, upper_bound: t.Type[IColor] = None) -> SequenceSGR:
        return self._extract().to_sgr(target, upper_bound)

    def to_tmux(self, target: ColorTarget = ColorTarget.FG) -> str:
        return self._extract().to_tmux(target)

    def repr_attrs(self, verbose: bool = True) -> str:
        return f"{{dynamic}}{self._extract().repr_attrs(verbose)}"

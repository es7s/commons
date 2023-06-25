# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import typing as t
from typing import TypeVar

T = TypeVar("T")


def only(cls: type, inp: t.Iterable[T]) -> list[T]:
    return [*(a for a in inp if isinstance(a, cls))]


def but(cls: type, inp: t.Iterable[T]) -> list[T]:
    return [*(a for a in inp if not isinstance(a, cls))]


def our(cls: type, inp: t.Iterable[T]) -> list[T]:
    return [*(a for a in inp if issubclass(type(a), cls))]


def other(cls: type, inp: t.Iterable[T]) -> list[T]:
    return [*(a for a in inp if not issubclass(type(a), cls))]

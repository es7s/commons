# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from __future__ import annotations
import typing as t


class DoublyLinkedNode:
    def __init__(self):
        self._prev: t.Self | None = None
        self._next: t.Self | None = None

    def connect(self, next: t.Self):
        self._next = next
        next._prev = self

    @property
    def prev(self) -> t.Self | None:
        return self._prev

    @property
    def next(self) -> t.Self | None:
        return self._next


_DNT = t.TypeVar("_DNT", bound=DoublyLinkedNode)


class RingList(t.Generic[_DNT]):
    def __init__(self):
        self._any: _DNT | None = None  # rings do not have a head or tail

    def insert(self, target: _DNT):
        if not self._any:
            target.connect(target)  # single ring element is linked
            self._any = target  # with itself on both sides
        else:
            target.connect(self._any.next)  # cut two connections and insert
            self._any.connect(target)  # new element into created gap
            self._any = target

    def remove(self, target: _DNT):
        for el in self:
            if el == target:
                el.prev.connect(el.next)
                if self._any == el:
                    if self._any == self._any.next:  # delete link to entrypoint
                        self._any = None  # if its getting removed
                    else:
                        self._any = el.next  # if not, pick another element as an entrypoint
                return
        raise ValueError("No such element")

    def __len__(self) -> int:
        return len([_ for _ in self])

    def __iter__(self) -> t.Iterator[_DNT]:
        if (ptr := self._any) is None:
            return
        while True:  # iterate from the entrypoint
            ptr = ptr.next  # till we encounter it again
            yield ptr
            if ptr == self._any:  # funny things will happen if the ring gets
                break  # modified in the middle of iteration process

    def __repr__(self) -> str:
        if self._any is None:
            return "[]"
        return " => ".join([f"[{rel}]" for rel in ["FIRST", *self, "LAST"]])

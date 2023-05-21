# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from __future__ import annotations

import typing as t
from collections import deque
from itertools import chain
from sys import getsizeof, stderr

try:
    from reprlib import repr
except ImportError:
    pass


def total_size(
    o: t.Any, handlers: t.Dict[t.Any, t.Iterator] = None, verbose: bool = False
) -> int:
    """
    Return the approximate memory footprint of an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses: *tuple, list, deque, dict, set* and *frozenset*.
    To search other containers, add handlers to iterate over their contents::

        handlers = {ContainerClass: iter, ContainerClass2: ContainerClass2.get_elements}

    :param o:
    :param handlers:
    :param verbose:
    """
    # origin: https://code.activestate.com/recipes/577504/

    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {
        tuple: iter,
        list: iter,
        deque: iter,
        dict: dict_handler,
        set: iter,
        frozenset: iter,
    }
    all_handlers.update(handlers or {})  # user handlers take precedence
    seen = set()  # track which object id's have already been seen
    default_size = getsizeof(0)  # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:  # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)

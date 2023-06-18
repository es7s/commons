# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
from __future__ import annotations


class FinalSingleton:
    """
    Can have children (at most one of each), but not grandchildren.
    """
    _instance: FinalSingleton

    def __init__(self):
        if hasattr(self.__class__, "_instance"):
            raise RuntimeError(f"{self.__class__.__name__} is a singleton")
        self.__class__._instance = self

    @classmethod
    def get_instance(cls: FinalSingleton, require: bool = True) -> FinalSingleton | None:
        if not hasattr(cls, "_instance"):
            if require:
                raise RuntimeError(f"{cls.__name__} is uninitialized")
            return None
        return cls._instance

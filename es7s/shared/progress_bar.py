# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import math
import time
import typing
from functools import reduce

import pytermor as pt
from pytermor import SeqIndex as sqx
from pytermor import ColorTarget as ct

from es7s.cli._terminal_state import TerminalStateController
from es7s.shared import get_color, IoProxy, Logger
from es7s.shared.exception import NotInitializedError
from es7s.shared.strutil import fit


# @todo to pytermor
class ProgressBar:
    BAR_WIDTH = 5
    MAX_FRAME_RATE = 4

    SEQ_DEFAULT = sqx.WHITE + pt.cv.GRAY_0.to_sgr(ct.BG)
    SEQ_ICON = pt.NOOP_SEQ                # deferred
    SEQ_INDEX_CURRENT = sqx.BOLD          # deferred
    SEQ_INDEX_TOTAL = pt.NOOP_SEQ
    SEQ_INDEX_DELIM = sqx.COLOR_OFF + sqx.BOLD_DIM_OFF + sqx.DIM
    SEQ_LABEL_LOCAL = sqx.DIM

    SEQ_RATIO_DIGITS = sqx.BOLD
    SEQ_RATIO_PERCENT_SIGN = sqx.DIM
    SEQ_BAR_BORDER = pt.cv.GRAY_19.to_sgr(ct.FG) + sqx.BOLD_DIM_OFF
    SEQ_BAR_FILLED = pt.cv.GRAY_0.to_sgr(ct.FG)   # deferred
    SEQ_BAR_EMPTY = pt.cv.GRAY_0.to_sgr(ct.BG)  # deferred

    FIELD_SEP = " "
    ICON = "◆"
    INDEX_DELIM = "/"
    BORDER_LEFT_CHAR = "▕"
    BORDER_RIGHT_CHAR = "▏"

    def __init__(self, io_proxy: IoProxy, logger: Logger, tstatectl: TerminalStateController|None):
        self._enabled = False
        self._io_proxy: IoProxy | None = io_proxy

        if logger.verbosity_allows_progress_bar_mode:
            self._enabled = True
            io_proxy.enable_progress_bar()

            if tstatectl:
                tstatectl.hide_cursor()
                tstatectl.disable_input()

        self._thresholds: list[float] | None = None
        self._ratio_local: float = 0.0
        self._thr_idx: int = 0
        self._thr_finished: bool = False
        self._icon_frame = 0
        self._last_redraw_ts: float = 0.0
        self._last_term_width_query_ts: float = 0.0
        self._max_label_len = 0
        self._label_thr: str = "Preparing"
        self._label_local: str = ""

        color = get_color()
        theme_color = color.get_theme_color()
        theme_bright_color = color.get_theme_bright_color()

        self.SEQ_ICON += theme_bright_color.to_sgr(ct.FG)
        self.SEQ_INDEX_CURRENT += theme_bright_color.to_sgr(ct.FG) + sqx.BOLD
        self.SEQ_BAR_FILLED += theme_color.to_sgr(ct.BG)  # sqx.BG_MAGENTA
        self.SEQ_BAR_EMPTY += theme_color.to_sgr(ct.FG)  # sqx.MAGENTA


    def setup(
        self,
        threshold_count: int = None,
        thresholds: typing.Iterable[float] = None,
    ):
        if not thresholds and threshold_count:
            thresholds = [*(t / threshold_count for t in range(1, threshold_count + 1))]

        self._thresholds = sorted(
            filter(lambda v: 0.0 <= v <= 1.0, {0.0, 1.0, *(thresholds or [])})
        )

        self._compute_max_label_len()
        self.redraw()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _compute_max_label_len(self):
        self._last_term_width_query_ts = time.time()
        self._max_label_len = pt.get_terminal_width() - (7 + len(self.ICON) + self.BAR_WIDTH + 2 + 2 * self._get_max_threshold_idx_len())

    def _get_max_threshold_idx_len(self) -> int:
        return len(str(len(self._thresholds) - 1))

    def _get_ratio_global(self):
        if self._thr_finished:
            return self._get_ratio_at(self._thr_idx)
        return self._get_ratio_at(self._thr_idx - 1)

    def _get_next_ratio_global(self):
        if self._thr_finished:
            return self._get_ratio_at(self._thr_idx + 1)
        return self._get_ratio_at(self._thr_idx)

    def _get_threshold_for_idx(self) -> int:
        return self._thr_idx

    def _get_threshold_for_ratio(self) -> int:
        if self._thr_finished:
            return self._thr_idx + 1
        return self._thr_idx

    def _get_ratio_at(self, idx: int):
        idx = max(0, min(len(self._thresholds) - 1, idx))
        return self._thresholds[idx]

    def _get_ratio(self):
        left = self._get_ratio_global()
        right = self._get_next_ratio_global()
        return left + self._ratio_local * (right - left)

    def _set_threshold(self, threshold_idx: int):
        if not 0 <= threshold_idx < len(self._thresholds):
            raise IndexError(f"Threshold index out of bounds: {threshold_idx}")
        self._thr_idx = threshold_idx

    def next_threshold(self, label_thr: str = None):
        self.set(next_threshold=1, ratio_local=0.0, label_thr=label_thr)

    # @temp finished IS ratio_local = 1.0
    def set(
        self,
        ratio_local: float = None,
        next_threshold: int = None,
        label_thr: str = None,
        label_local: str = None,
        finished: bool = None,
    ):
        if not self._thresholds:
            raise NotInitializedError(self)

        if ratio_local is not None:
            self._ratio_local = max(0.0, min(1.0, ratio_local))
        if label_thr is not None:
            self._label_thr = label_thr
        if label_local is not None:
            self._label_local = label_local
        if finished is not None:
            self._thr_finished = finished

        if next_threshold:
            self._set_threshold(self._thr_idx + next_threshold)
            if finished is None:
                self._thr_finished = False
            if label_local is None:
                self._label_local = ""

        self.redraw()

    def redraw(self):
        if not self._thresholds:
            raise NotInitializedError(self)
        if not self._enabled:
            return

        now = time.time()
        if not self._last_term_width_query_ts or (now - self._last_term_width_query_ts) > 5:
            self._compute_max_label_len()

        if not self._last_redraw_ts or (now - self._last_redraw_ts > (1 / self.MAX_FRAME_RATE)):
            self._last_redraw_ts = now
            self._icon_frame += 1
        icon = [self.ICON, " "][self._icon_frame % 2]
        ratio = self._ratio_local   # self._get_ratio()

        idx = self._get_threshold_for_idx()
        max_idx_len = self._get_max_threshold_idx_len()
        # expand right label to max minus (initial) left
        label_right = fit(self._label_local, self._max_label_len - 2 - len(self._label_thr), '<')
        label_left = self._label_thr

        result_ratio_bar = self._format_ratio_bar(ratio)
        result_index = (
            f"{self.SEQ_DEFAULT}"
            f"{self.SEQ_ICON}{icon} "
            f"{self.SEQ_INDEX_CURRENT}{idx:>{max_idx_len}d}"
            f"{self.SEQ_INDEX_DELIM}{self.INDEX_DELIM}"
            f"{self.SEQ_INDEX_TOTAL}{len(self._thresholds) - 1:<d}"
        )
        result_label = f'{self.SEQ_DEFAULT}{label_left}  {self.SEQ_LABEL_LOCAL}{label_right}'

        result = reduce(
            lambda t, s: str(t) + str(s),
            [
                self.SEQ_DEFAULT,
                self.FIELD_SEP,
                result_index,
                self.FIELD_SEP,
                *result_ratio_bar,
                self.FIELD_SEP,
                result_label,
                sqx.RESET,
            ],
        )
        self._io_proxy.echo_progress_bar(result)

    def close(self):
        if not self._thresholds:
            return
        self._thr_finished = True
        self._set_threshold(len(self._thresholds) - 1)
        if self._enabled:
            self._io_proxy.disable_progress_bar()
            self._enabled = False

    def _format_ratio_bar(self, ratio: float) -> typing.Iterable[str]:
        filled_length = math.floor(ratio * self.BAR_WIDTH)

        ratio_label = list(f"{100*ratio:>3.0f}%")
        ratio_label_len = 4  # "100%"
        ratio_label_left_pos = (self.BAR_WIDTH - ratio_label_len) // 2
        ratio_label_perc_pos = ratio_label_left_pos + 3

        bar_fmts = [self.SEQ_BAR_FILLED, self.SEQ_BAR_EMPTY]
        label_fmts = [self.SEQ_RATIO_DIGITS, self.SEQ_RATIO_PERCENT_SIGN]

        cursor = 0
        yield self.SEQ_BAR_BORDER
        yield self.BORDER_LEFT_CHAR
        yield bar_fmts.pop(0)

        while cursor < self.BAR_WIDTH:
            if cursor >= filled_length and bar_fmts:
                yield bar_fmts.pop(0)
            if cursor >= ratio_label_left_pos:
                if len(label_fmts) == 2:
                    yield label_fmts.pop(0)
                if cursor >= ratio_label_perc_pos and label_fmts:
                    yield label_fmts.pop(0)
                if len(ratio_label):
                    cursor += 1
                    yield ratio_label.pop(0)
                    continue
            cursor += 1
            yield " "

        if bar_fmts:
            yield bar_fmts.pop(0)
        yield self.SEQ_BAR_BORDER
        yield self.BORDER_RIGHT_CHAR


# thresholds: 6
# ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
# pre1      post1 pre2      post2 pre3        post3 pre4      post4 pre5       post5 pre6         post6
# |>-----(1)-----||>-----(2)-----||>-----(3)-------||>----(4)------||>-----(5)------||>-----(6)-------|
# |______________|_______________|_________________|_______________|________________|_________________|
# ╹0 ''╵''''╹10 '╵''''╹20 '╵''''╹30 '╵''''╹40 '╵''''╹50 '╵''''╹60 '╵''''╹70 '╵''''╹80 '╵''''╹90 '╵''''╹100
#
#                  LABEl      IDX     RATIO
#        pre-1    prepare     0/6| == | 0%           0
#      start-1    task 1      1/6| != | 0%           1
# post-1 pre-2    task 1      1/6| == |16%           1
# post-2 pre-3    task 2      2/6      33%           2
# post-3 pre-4    task 3      3/6      50%           3
# post-4 pre-5    task 4      4/6      66%           4
# post-5 pre-6    task 5      5/6      83%           5
# post-6          task 6      6/6     100%           6
#

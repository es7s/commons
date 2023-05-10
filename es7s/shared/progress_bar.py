# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import math
import time
import typing

import click


# @todo to pytermor
class ProgressBar:
    MAX_FRAME_RATE = 4
    MAX_LABEL_LEN = 30
    BG = "48;5;16"
    FG = "37"
    IDX1_FG = "94"
    IDX2_FG = "34"
    IDX_SEP = "/"
    RATIO_FG = "5"
    PBAR_FG = "5"
    PBAR_BORDER_FG = "38;5;236"
    SEP = " "

    PROGRESS_BAR_WIDTH = 5
    FILLED_CHAR = "▓"
    EMPTY_CHAR = "░"
    BORDER_LEFT_CHAR = "▕"
    BORDER_RIGHT_CHAR = "▏"

    def __init__(self, thresholds: typing.Iterable[float] = None, threshold_count: int = None):
        if not thresholds and threshold_count:
            thresholds = [*(t / threshold_count for t in range(1, threshold_count + 1))]

        self._thresholds = sorted(
            filter(lambda v: 0.0 <= v <= 1.0, {0.0, 1.0, *(thresholds or [])})
        )
        self._ratio_local: float = 0.0
        self._thr_idx: int = 0
        self._thr_finished: bool = False
        self._icon_frame = 0
        self._last_redraw_ts: float = 0.0
        self._label = "Preparing"
        self.redraw()

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

    def next_threshold(self, label: str = None):
        self.set(next_threshold=1, ratio_local=0.0, label=label)

    # @temp finished IS ratio_local = 1.0
    def set(
        self,
        ratio_local: float = None,
        next_threshold: int = None,
        label: str = None,
        finished: bool = None,
    ):
        if ratio_local is not None:
            self._ratio_local = max(0.0, min(1.0, ratio_local))
        if label:
            self._label = label
        if finished is not None:
            self._thr_finished = finished

        if next_threshold:
            self._set_threshold(self._thr_idx + next_threshold)
            if finished is None:
                self._thr_finished = False
        self.redraw()

    def redraw(self):
        idx = self._get_threshold_for_idx()
        max_idx = len(self._thresholds) - 1
        max_idx_len = len(str(max_idx))

        now = time.time()
        if not self._last_redraw_ts or (now - self._last_redraw_ts > 1 / self.MAX_FRAME_RATE):
            self._last_redraw_ts = now
            self._icon_frame += 1

        icon = "◆ "[self._icon_frame % 2]  #'⣿⣶⣭⣛⠿'[self._icon_frame % 5]
        ratio = self._get_ratio()
        bar = self._format_progress_bar(ratio, labeled=True)

        start_str = f"\r\x1b[0K\x1b[{self.FG};{self.BG}m"
        icon_str = f" {icon} "
        label_str = f"{self._label:{self.MAX_LABEL_LEN}.{self.MAX_LABEL_LEN}s}"
        label_idx_sep_str = f"\x1b[39;{self.FG}m{self.SEP}"
        idx_str = (
            f"\x1b[{self.IDX1_FG};1m{idx:>{max_idx_len}d}"
            + f"\x1b[22;2;39;{self.FG}m{self.IDX_SEP}"
            + f"\x1b[22;{self.IDX2_FG}m{max_idx}"
        )
        idx_ratio_sep_str = f"\x1b[39;{self.FG}m{self.SEP}"
        # ratio_str = f'\x1b[{self.RATIO_FG};1m{100*ratio:>3.0f}\x1b[22;2m%\x1b[22;39;{self.FG}m'
        bar_str = f" {bar} "
        end_str = f"\x1b[0K\x1b[m"

        click.echo(start_str + icon_str + idx_str + bar_str + label_str + end_str, nl=False)

    def echo(self, msg="", nl=True, err=False):
        click.echo("\r\x1b[0K" + msg, nl=nl, err=err)

    def close(self):
        self._thr_finished = True
        self._set_threshold(len(self._thresholds) - 1)
        self.echo(nl=False)

    def _format_progress_bar(self, ratio: float, labeled: bool) -> str:
        filled_length = math.floor(ratio * self.PROGRESS_BAR_WIDTH)
        if labeled:
            return self._format_progress_bar_labeled(ratio, filled_length)
        return self._format_progress_bar_plain(filled_length)

    def _format_progress_bar_labeled(
        self, ratio: float, filled_length: int
    ) -> str:
        ratio_label = list(f"{100*ratio:>3.0f}%")
        ratio_label_len = 4
        ratio_label_pos = (self.PROGRESS_BAR_WIDTH - ratio_label_len) // 2
        ratio_label_perc_pos = ratio_label_pos + 3

        bar_fmt_filled = f"\x1b[22;48;5;{self.PBAR_FG};38;5;16m"
        bar_fmt_empty = f"\x1b[38;5;{self.RATIO_FG};48;5;16m"
        bar_fmts = [bar_fmt_filled, bar_fmt_empty]

        label_fmt_digits = f"\x1b[1m"
        label_fmt_percent = f"\x1b[22;2m"
        label_fmts = [label_fmt_digits, label_fmt_percent]

        cursor = 0
        result = f"\x1b[39;{self.PBAR_BORDER_FG}m" + self.BORDER_LEFT_CHAR + bar_fmts.pop(0)

        while cursor < self.PROGRESS_BAR_WIDTH:
            if cursor >= filled_length and bar_fmts:
                result += bar_fmts.pop(0)
            if cursor >= ratio_label_pos:
                if len(label_fmts) == 2:
                    result += label_fmts.pop(0)
                if cursor >= ratio_label_perc_pos and label_fmts:
                    result += label_fmts.pop(0)
                if len(ratio_label):
                    cursor += 1
                    result += ratio_label.pop(0)
                    continue
            cursor += 1
            result += " "

        result += (
            f"\x1b[22;39;{self.PBAR_BORDER_FG}m"
            + self.BORDER_RIGHT_CHAR
            + f"\x1b[39;49;22;{self.FG};{self.BG}m"
        )

        return result

    def _format_progress_bar_plain(self, filled_length: int) -> str:
        empty_length = self.PROGRESS_BAR_WIDTH - filled_length
        bar = (
            f"\x1b[39;{self.PBAR_BORDER_FG}m"
            + self.BORDER_LEFT_CHAR
            + f"\x1b[{self.PBAR_FG}m"
            + (filled_length * self.FILLED_CHAR)
            + "\x1b[2m"
            + (empty_length * self.EMPTY_CHAR)
            + f"\x1b[22;39;{self.PBAR_BORDER_FG}m"
            + self.BORDER_RIGHT_CHAR
        )
        return bar


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

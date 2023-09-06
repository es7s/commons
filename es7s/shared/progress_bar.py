# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import math
import time
import typing

import pytermor as pt

from .io_ import IoProxy, get_stderr
from .log import Logger
from .styles import Styles as BaseStyles, FrozenStyle
from .theme import ThemeColor


class DummyProgressBar:
    def __init__(self, *_, **__):
        self._label = ""
        self._count = 0

    def init_tasks(self, tasks_amount: int = None, task_num: int = 1):
        ...

    def next_task(self, task_label: str = None):
        self._label = task_label
        self._count += 1

    def init_steps(self, steps_amount: int = None, step_num: int = 0):
        ...

    def next_step(self, step_label: str = None):
        self._label = step_label
        self._count += 1

    def render(self):
        get_stderr().echo(f"{pt.get_qname(self)} [{self._count}] {self._label}")

    def close(self, *args, **kwargs):
        ...


class Styles(BaseStyles):
    _THEME_COLOR = ThemeColor()
    _THEME_BRIGHT_COLOR = ThemeColor("theme_bright")

    DEFAULT = FrozenStyle(bg=pt.cv.GRAY_0)

    ICON = FrozenStyle(DEFAULT, fg=_THEME_BRIGHT_COLOR)
    TASK_NUM_CUR = FrozenStyle(ICON, bold=True)
    TASK_NUM_MAX = DEFAULT
    TASK_DELIM = FrozenStyle(DEFAULT, dim=True)
    TASK_LABEL = DEFAULT

    RATIO_DIGITS = FrozenStyle(bold=True)
    RATIO_PERC_SIGN = FrozenStyle(dim=True)
    BAR_BORDER = FrozenStyle(DEFAULT, fg=pt.cv.GRAY_19)
    BAR_FILLED = FrozenStyle(fg=pt.cv.GRAY_0, bg=_THEME_COLOR)
    BAR_EMPTY = FrozenStyle(fg=_THEME_COLOR, bg=pt.cv.GRAY_0)


class ProgressBar:
    BAR_WIDTH = 5
    LABEL_PAD = 2

    MAX_FRAME_RATE = 16
    FRAME_INTERVAL_SEC = 1 / MAX_FRAME_RATE
    TERM_WIDTH_QUERY_INTERVAL_SEC = 5
    PERSIST_MIN_INTERVAL_SEC = 5

    FIELD_SEP = " "
    ICON = "◆"
    NUM_DELIM = "/"
    BORDER_LEFT_CHAR = "▕"
    BORDER_RIGHT_CHAR = "▏"

    def __init__(
        self,
        io_proxy: IoProxy,
        logger: Logger,
        tasks_amount=1,
        task_num=1,
        task_label="Working",
        steps_amount=0,
        step_num=0,
        step_label="...",
        print_step_num=True,
    ):
        self._enabled = False
        self._created_at = time.monotonic_ns()

        self._io_proxy: IoProxy | None = io_proxy

        if logger.setup.progress_bar_mode_allowed:
            self._enabled = True
            io_proxy.enable_output_buffering()

        self._tasks_amount: int = tasks_amount
        self._task_num: int = task_num
        self._task_label: str = task_label

        self._steps_amount = steps_amount
        self._step_num = step_num
        self._step_label: str = step_label

        self._print_step_num = print_step_num

        self._next_frame_ts: int | None = None
        self._icon_frame = 0

        self._max_label_len: int | None = None
        self._last_term_width_query_ts: int | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def init_tasks(self, tasks_amount: int = None, task_num: int = 1):
        if tasks_amount is not None:
            self._tasks_amount = tasks_amount
        if task_num is not None:
            self._task_num = task_num
            self._steps_amount = 0
            self._step_num = 0
        self._task_num = min(self._task_num, self._get_max_task_num())

    def next_task(self, task_label: str = None, render=True):
        if task_label is not None:
            self._task_label = task_label
        self.init_tasks(task_num=self._task_num + 1)
        if render:
            self.render()

    def init_steps(self, steps_amount: int = None, step_num: int = 0):
        if steps_amount is not None:
            self._steps_amount = steps_amount
        if step_num is not None:
            self._step_num = step_num
        self._step_num = min(self._step_num, self._get_max_step_num())

    def next_step(self, step_label: str = None, render=True):
        if step_label is not None:
            self._step_label = step_label
        self.init_steps(step_num=self._step_num + 1)
        if render:
            self.render()

    def render(self):
        if not self._enabled:
            return

        self._compute_max_label_len()
        try:
            self._ensure_next_frame()
        except _FrameAlreadyRendered:
            return

        left_part_len = self._render_ghost()

        if self._should_persist():
            self._render_persistent(left_part_len)

    def _render_ghost(self):
        task_ratio = self._compute_task_progress()
        icon = self._format_icon()
        task_state = [*self._format_task_state()]

        field_sep = self._field_sep_nobg
        if self._io_proxy.renderer.is_format_allowed:
            field_sep = self._field_sep
        else:
            icon = ''

        result = self._io_proxy.render(
            pt.Composite(
                field_sep,
                icon,
                field_sep,
                *task_state,
                field_sep,
                *self._format_ratio_bar(task_ratio),
                field_sep,
                *self._format_labels(),
            )
        )
        self._io_proxy.echo_status_line(result)
        return len(self.FIELD_SEP) + len(icon) + sum(map(len, task_state))

    def _render_persistent(self, left_part_len: int):
        delta_str = pt.format_time_ns(time.monotonic_ns() - self._created_at)
        task_ratio = self._compute_task_progress()

        result = self._io_proxy.render(
            pt.Composite(
                self._field_sep_nobg,
                pt.fit(f'+{delta_str}', left_part_len, ">"),
                self._field_sep_nobg,
                *self._format_ratio_bar(task_ratio),
                pt.SeqIndex.BOLD_DIM_OFF.assemble(),
                self._field_sep_nobg,
                *self._format_labels(),
            )
        )
        self._io_proxy.echo_status_line(result, persist=True)

    def close(self):
        self._task_num = self._get_max_task_num()
        self._steps_amount = 0

        if self._enabled:
            self._io_proxy.disable_output_buffering()
            self._enabled = False

    @property
    def _field_sep(self) -> str:
        return f"{Styles.DEFAULT.bg.to_sgr(pt.ColorTarget.BG)}{self.FIELD_SEP}"

    @property
    def _field_sep_nobg(self) -> str:
        return self.FIELD_SEP

    def _get_max_step_num(self) -> int:
        return self._steps_amount

    def _get_max_task_num(self) -> int:
        return self._tasks_amount

    def _get_max_task_num_len(self) -> int:
        return len(str(self._get_max_task_num()))

    def _compute_task_progress(self) -> float:
        if not self._get_max_step_num():
            return 0.0
        return (self._step_num - 1) / self._get_max_step_num()

    def _compute_max_label_len(self):
        now = time.time()
        if (
            self._last_term_width_query_ts
            and (now - self._last_term_width_query_ts) < self.TERM_WIDTH_QUERY_INTERVAL_SEC
        ):
            return

        self._last_term_width_query_ts = now

        field_seps_len = 4 * len(self.FIELD_SEP)
        icon_len = len(self.ICON)
        task_state_len = 2 * self._get_max_task_num_len() + len(self.NUM_DELIM)
        task_bar_len = self.BAR_WIDTH + len(self.BORDER_LEFT_CHAR + self.BORDER_RIGHT_CHAR)

        self._max_label_len = pt.get_terminal_width() - (
            field_seps_len + icon_len + task_bar_len + task_state_len + self.LABEL_PAD
        )

    def _ensure_next_frame(self):
        now = time.time()
        if not self._next_frame_ts:
            self._next_frame_ts = now

        if now >= self._next_frame_ts:
            self._next_frame_ts = now + self.FRAME_INTERVAL_SEC
            self._icon_frame += 1
        else:
            raise _FrameAlreadyRendered

    def _should_persist(self) -> bool:
        if last_persist := self._io_proxy.last_persist_ts():
            return time.time() - last_persist >= self.PERSIST_MIN_INTERVAL_SEC
        return False

    def _format_ratio_bar(self, ratio: float) -> typing.Iterable[str | pt.Fragment]:
        filled_length = math.floor(ratio * self.BAR_WIDTH)
        ratio_label = list(f"{100*ratio:>3.0f}%")
        ratio_label_len = 4  # "100%"
        ratio_label_left_pos = (self.BAR_WIDTH - ratio_label_len) // 2
        ratio_label_perc_pos = ratio_label_left_pos + 3

        ren = self._io_proxy.renderer
        if not ren.is_format_allowed:
            yield ''.join(ratio_label)
            return

        bar_styles = [
            ren.render("\x00", Styles.BAR_FILLED).split("\x00", 1)[0],
            pt.SeqIndex.INVERSED.assemble(),
        ]
        label_styles = [
            pt.SeqIndex.BOLD.assemble(),
            pt.SeqIndex.DIM.assemble(),
        ]

        cursor = 0
        yield pt.Fragment(self.BORDER_LEFT_CHAR, Styles.BAR_BORDER)
        yield bar_styles.pop(0)

        while cursor < self.BAR_WIDTH:
            if cursor >= filled_length and bar_styles:
                yield bar_styles.pop()
            if cursor >= ratio_label_left_pos:
                if len(label_styles) == 2:
                    yield label_styles.pop(0)
                if cursor >= ratio_label_perc_pos and label_styles:
                    yield label_styles.pop()
                if len(ratio_label):
                    cursor += 1
                    yield ratio_label.pop(0)
                    continue
            cursor += 1
            yield " "

        if bar_styles:
            yield bar_styles.pop()
        yield pt.SeqIndex.INVERSED_OFF.assemble()
        yield pt.Fragment(self.BORDER_RIGHT_CHAR, Styles.BAR_BORDER)
        yield pt.SeqIndex.BOLD_DIM_OFF.assemble()

    def _format_icon(self) -> pt.Fragment:
        icon = (self.ICON, " ")[self._icon_frame % 2]
        return pt.Fragment(icon, Styles.ICON)

    def _format_task_state(self) -> typing.Iterable[pt.Fragment]:
        task_num_cur = f"{self._task_num:>{self._get_max_task_num_len()}d}"
        task_num_max = f"{self._get_max_task_num():<d}"

        yield pt.Fragment(task_num_cur, Styles.TASK_NUM_CUR)
        yield pt.Fragment(self.NUM_DELIM, Styles.TASK_DELIM)
        yield pt.Fragment(task_num_max, Styles.TASK_NUM_MAX)

    def _format_labels(self) -> typing.Iterable[pt.Fragment]:
        task_label = self._task_label
        step_label = self._step_label
        step_num = ""
        if self._print_step_num:
            step_num = f"[{self._step_num}/{self._steps_amount}] "

        # expand right label to max minus (initial) left
        label_right_text = pt.fit(
            step_label,
            self._max_label_len - self.LABEL_PAD * 2 - len(task_label) - len(step_num),
            "<",
        )
        if not self._io_proxy.renderer.is_format_allowed:
            yield from [step_num, task_label, pt.pad(self.LABEL_PAD), label_right_text]
            return
        yield pt.Fragment(f"{pt.SeqIndex.DIM}{step_num}")
        yield pt.Fragment(f"{pt.SeqIndex.BOLD_DIM_OFF}{task_label}{pt.pad(self.LABEL_PAD)}")
        yield pt.Fragment(f"{pt.SeqIndex.DIM}{label_right_text}")


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
# ------------------------------------------------------------------------------------------------------
# FEATURE: tasks with non-linear step thresholds   @TODO @MAYBE
#
#     def _get_ratio_at(self, idx: int):
#         idx = max(0, min(len(self._thresholds) - 1, idx))
#         return self._thresholds[idx]
#
#     def _get_ratio(self):
#         left = self._get_ratio_global()
#         right = self._get_next_ratio_global()
#         return left + self._ratio_local * (right - left)


def get_partial_hblock(val: float) -> str:
    if val >= 7 / 8:
        return "▉"
    elif val >= 6 / 8:
        return "▊"
    elif val >= 5 / 8:
        return "▋"
    elif val >= 4 / 8:
        return "▌"
    elif val >= 3 / 8:
        return "▍"
    elif val >= 2 / 8:
        return "▎"
    elif val >= 1 / 8:
        return "▏"
    return ""


class _FrameAlreadyRendered(Exception):
    pass

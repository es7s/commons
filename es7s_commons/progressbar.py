# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import math
import sys
import time
import typing
import typing as t
from io import StringIO

import pytermor as pt
from .scale import FULL_BLOCK, get_partial_hblock


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
        sys.stderr.write(f"{pt.get_qname(self)} [{self._count}] {self._label}\n")

    def close(self, *args, **kwargs):
        ...


class ProgressBar:
    BAR_WIDTH = 5
    LABEL_PAD = 2

    MAX_FRAME_RATE = 16
    FRAME_INTERVAL_SEC = 1 / MAX_FRAME_RATE
    TERM_WIDTH_QUERY_INTERVAL_SEC = 5
    PERSIST_MIN_INTERVAL_SEC = 5

    SGR_RESET = pt.SeqIndex.RESET.assemble()
    CSI_CHA1 = pt.make_set_cursor_column(1).assemble()
    CSI_EL0 = pt.make_clear_line_after_cursor().assemble()
    OUT_START = CSI_CHA1 + CSI_EL0
    OUT_END = pt.SeqIndex.BG_COLOR_OFF.assemble()

    FIELD_SEP = " "
    ICON = "◆"
    NUM_DELIM = "/"
    BORDER_LEFT_CHAR = "▕"
    BORDER_RIGHT_CHAR = "▏"

    def __init__(
        self,
        renderer: pt.IRenderer,
        io: t.IO,
        theme_color: pt.Color,
        tasks_amount=1,
        task_num=1,
        task_label="Working",
        steps_amount=0,
        step_num=0,
        step_label="...",
        print_step_num=True,
    ):
        self._last_persist_ts: int | None = None
        self._created_at = time.monotonic_ns()

        self._renderer = renderer
        self._io = io
        self._output_buffer = _OutputBuffer()
        self._styles = _PBarStyles(theme_color)

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
    def is_format_allowed(self) -> bool:
        return self._renderer.is_format_allowed

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
        self._compute_max_label_len()
        try:
            self._ensure_next_frame()
        except _FrameAlreadyRendered:
            return

        task_ratio = self._compute_task_progress()
        field_sep = self._format_field_sep()
        icon = self._format_icon()
        task_state = [*self._format_task_state()]

        result = pt.render(
            pt.Composite(
                field_sep,
                icon,
                field_sep,
                *task_state,
                field_sep,
                *self._format_ratio_bar(task_ratio),
                field_sep,
                *self._format_labels(),
            ),
            renderer=self._renderer,
        )
        left_part_len = len(self.FIELD_SEP) + len(icon) + sum(map(len, task_state))

        if self._should_persist():
            delta_str = pt.format_time_ns(time.monotonic_ns() - self._created_at)
            result_nofmt = pt.render(
                pt.Composite(
                    pt.fit(f"+{delta_str}", left_part_len + 1, ">"),
                    self._format_field_sep(raw=True),
                    *self._format_ratio_bar(task_ratio, raw=True),
                    self._format_field_sep(raw=True),
                    *self._format_labels(raw=True),
                ),
                renderer=self._renderer,
            )
            self._echo(result_nofmt, persist=True)
        self._echo(result)

    def _echo(self, result: str, persist=False):
        if self.is_format_allowed:
            # firstly set cursor X to 0, then clear that line,
            # then echo the result, then clear that line again
            result = self.OUT_START + result + self.CSI_EL0 + self.SGR_RESET

        if self._output_buffer.getvalue():
            # something already waiting in buffer, no need to persist progress:
            self._output_buffer.write(result)
            self._io.write(self._output_buffer.popvalue().rstrip())
            self._update_last_persist_ts()
        else:
            self._io.write(result)

        if persist:
            self._io.write("\n")
            self._update_last_persist_ts()

        self._io.flush()

    def close(self):
        self._task_num = self._get_max_task_num()
        self._steps_amount = 0

        if self._output_buffer:
            self._echo("", persist=True)
            self._output_buffer.close()
            self._output_buffer = None

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
        if not self._should_query_term_width():
            return

        field_seps_len = 4 * len(self.FIELD_SEP)
        icon_len = len(self.ICON)
        task_state_len = 2 * self._get_max_task_num_len() + len(self.NUM_DELIM)
        task_bar_len = self.BAR_WIDTH + len(self.BORDER_LEFT_CHAR + self.BORDER_RIGHT_CHAR)

        self._max_label_len = pt.get_terminal_width() - (
            field_seps_len + icon_len + task_bar_len + task_state_len + self.LABEL_PAD
        )

    def _ensure_next_frame(self):
        now = time.monotonic_ns()
        if not self._next_frame_ts:
            self._next_frame_ts = now

        if now >= self._next_frame_ts:
            self._next_frame_ts = now + self.FRAME_INTERVAL_SEC
            self._icon_frame += 1
        else:
            raise _FrameAlreadyRendered

    def _should_persist(self) -> bool:
        if self._last_persist_ts is None:
            return True  # first render
        from_last_persist = (time.monotonic_ns() - self._last_persist_ts) / 1e9
        return from_last_persist >= self.PERSIST_MIN_INTERVAL_SEC

    def _update_last_persist_ts(self):
        self._last_persist_ts = time.monotonic_ns()

    def _should_query_term_width(self) -> bool:
        now = time.monotonic_ns()
        if self._last_term_width_query_ts:
            if now - self._last_term_width_query_ts < self.TERM_WIDTH_QUERY_INTERVAL_SEC:
                return False

        self._last_term_width_query_ts = now
        return True

    def _format_field_sep(self, raw=False) -> str:
        if not self.is_format_allowed or raw:
            return self.FIELD_SEP
        return f"{self._styles.DEFAULT.bg.to_sgr(pt.ColorTarget.BG)}{self.FIELD_SEP}"

    def _format_ratio_bar(self, ratio: float, raw=False) -> typing.Iterable[str | pt.Fragment]:
        filled_length = math.floor(ratio * self.BAR_WIDTH)
        ratio_label = list(f"{100*ratio:>3.0f}%")
        ratio_label_len = 4  # "100%"
        ratio_label_left_pos = (self.BAR_WIDTH - ratio_label_len) // 2
        ratio_label_perc_pos = ratio_label_left_pos + 3

        if not self.is_format_allowed or raw:
            bar_chars = filled_length * FULL_BLOCK
            bar_chars += get_partial_hblock(ratio - filled_length * self.BAR_WIDTH)
            yield self.BORDER_LEFT_CHAR
            yield pt.fit(bar_chars, self.BAR_WIDTH)
            yield from ratio_label
            return

        bar_styles = [
            self._renderer.render("\x00", self._styles.BAR_FILLED).split("\x00", 1)[0],
            pt.SeqIndex.INVERSED.assemble(),
        ]
        label_styles = [
            pt.SeqIndex.BOLD.assemble(),
            pt.SeqIndex.DIM.assemble(),
        ]

        cursor = 0
        yield pt.Fragment(self.BORDER_LEFT_CHAR, self._styles.BAR_BORDER)
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
        yield pt.Fragment(self.BORDER_RIGHT_CHAR, self._styles.BAR_BORDER)
        yield pt.SeqIndex.BOLD_DIM_OFF.assemble()

    def _format_icon(self, raw=False) -> pt.Fragment | str:
        if not self.is_format_allowed or raw:
            return " "
        icon = (self.ICON, " ")[self._icon_frame % 2]
        return pt.Fragment(icon, self._styles.ICON)

    def _format_task_state(self) -> typing.Iterable[pt.Fragment]:
        task_num_cur = f"{self._task_num:>{self._get_max_task_num_len()}d}"
        task_num_max = f"{self._get_max_task_num():<d}"

        yield pt.Fragment(task_num_cur, self._styles.TASK_NUM_CUR)
        yield pt.Fragment(self.NUM_DELIM, self._styles.TASK_DELIM)
        yield pt.Fragment(task_num_max, self._styles.TASK_NUM_MAX)

    def _format_labels(self, raw=False) -> typing.Iterable[pt.Fragment]:
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
        if not self.is_format_allowed or raw:
            yield from [task_label, pt.pad(self.LABEL_PAD), step_num, label_right_text]
            return
        yield pt.Fragment(f"{task_label}{pt.pad(self.LABEL_PAD)}")
        yield pt.Fragment(f"{pt.SeqIndex.DIM}{step_num}")
        yield pt.Fragment(f"{label_right_text}")


class _PBarStyles(pt.Styles):
    def __init__(self, theme_color: pt.Color):
        self.THEME_COLOR = theme_color
        self.DEFAULT = pt.FrozenStyle(bg=pt.cv.GRAY_0)

        self.ICON = pt.FrozenStyle(self.DEFAULT, fg=self.THEME_COLOR)
        self.TASK_NUM_CUR = pt.FrozenStyle(self.ICON, bold=True)
        self.TASK_NUM_MAX = self.DEFAULT
        self.TASK_DELIM = pt.FrozenStyle(self.DEFAULT, dim=True)
        self.TASK_LABEL = self.DEFAULT

        self.RATIO_DIGITS = pt.FrozenStyle(bold=True)
        self.RATIO_PERC_SIGN = pt.FrozenStyle(dim=True)
        self.BAR_BORDER = pt.FrozenStyle(self.DEFAULT, fg=pt.cv.GRAY_19)
        self.BAR_FILLED = pt.FrozenStyle(fg=pt.cv.GRAY_0, bg=self.THEME_COLOR)
        self.BAR_EMPTY = pt.FrozenStyle(fg=self.THEME_COLOR, bg=pt.cv.GRAY_0)


class _FrameAlreadyRendered(Exception):
    pass


class _OutputBuffer(StringIO):
    def reset(self) -> None:
        self.truncate(0)
        self.seek(0)

    def popvalue(self) -> str:
        val = self.getvalue()
        self.reset()
        return val


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

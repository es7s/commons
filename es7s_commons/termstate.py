# ------------------------------------------------------------------------------
#  es7s/commons
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import sys
import typing as t
from contextlib import contextmanager

import pytermor as pt

from .common import logger


class InputMode(str, pt.ExtendedEnum):  # @TODO str enums will be available in python 3.11
    DEFAULT: str = "default"
    DISABLED: str = "disabled"
    DISCRETE: str = "discrete"


@contextmanager
def terminal_state(
    alt_buffer: bool = None,
    no_cursor: bool = None,
    input_mode: InputMode = None,
):
    tstate = TerminalState()

    if alt_buffer:
        tstate.enable_alt_screen_buffer()
    if no_cursor:
        tstate.hide_cursor()
    if input_mode:
        tstate.setup_input(input_mode)
    try:
        yield tstate
    finally:
        tstate.restore_state()


class TerminalState:
    def __init__(self, io: t.IO = None):
        self._io = io or sys.stdout
        self._restore_callbacks: list[t.Callable[[], None]] = []
        self._terminal_orig_settings: list | None = None
        self._debug = False
        self._force_esq = None

    def enable_alt_screen_buffer(self):
        self._add_restore_callback(self.disable_alt_screen_buffer)
        self._add_restore_callback(self._restore_cursor_position)
        self._send_sequence(pt.make_save_cursor_position)
        self._send_sequence(pt.make_enable_alt_screen_buffer)

    def disable_alt_screen_buffer(self):
        self._remove_restore_callback(self.disable_alt_screen_buffer)
        self._send_sequence(pt.make_disable_alt_screen_buffer)
        logger.debug("TSC: DISABLED ALT SCREEN BUFFER: stderr logging should work again")

    def hide_cursor(self):
        self._add_restore_callback(self.show_cursor)
        self._send_sequence(pt.make_hide_cursor)

    def show_cursor(self):
        self._remove_restore_callback(self.show_cursor)
        self._send_sequence(pt.make_show_cursor)

    def setup_input(self, input_mode: InputMode):
        match input_mode:
            case InputMode.DEFAULT:
                self.restore_input()
            case InputMode.DISABLED:
                self.disable_input()
            case InputMode.DISCRETE:
                self.discrete_input()
            case _:
                raise NotImplementedError(f"Unknown input mode: {input_mode}")

    def disable_input(self):
        logger.debug(f"TSC: Putting tty into cbreak mode: {sys.stdin}")
        if not self._isatty():
            return
        if self._terminal_orig_settings:
            logger.warning(f"TSC: Altering tty attributes skipped: already altered")
            return

        import tty
        import termios

        try:
            self._terminal_orig_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin)
            self._add_restore_callback(self.restore_input)
        except (termios.error, TypeError) as e:
            logger.error("Saving tty state failed", exc_info=e)

    def discrete_input(self):
        """
        Use with: sys.stdin.read(1)
        Origin: readchar/_posix_read.py
        """
        logger.debug(f"TSC: Enabling tty discrete input: {sys.stdin}")
        if not self._isatty():
            return
        if self._terminal_orig_settings:
            logger.warning(f"TSC: Altering tty attributes skipped: already altered")
            return

        import termios

        try:
            fd = sys.stdin.fileno()
            term = termios.tcgetattr(fd)
            # originally:
            # term[3] &= ~(termios.ICANON | termios.ECHO)
            term[3] &= ~(termios.ICANON | termios.ECHO | termios.IGNBRK | termios.BRKINT)
            # we don't need to ignore Ctrl+C though, because we handle it on the top level in init_cli()
            termios.tcsetattr(fd, termios.TCSAFLUSH, term)

            self._terminal_orig_settings = termios.tcgetattr(fd)
            self._add_restore_callback(self.restore_input)

        except (termios.error, TypeError) as e:
            logger.error("Saving tty state failed", exc_info=e)

    def restore_input(self):
        if not self._isatty():
            logger.warning(f"TSC: Restoring tty attributes skipped: not a tty")
            return
        if not self._terminal_orig_settings:
            logger.warning(f"TSC: Restoring tty attributes skipped: nothing to restore")
            return

        logger.debug(f"TSC: Restoring tty attributes: {self._terminal_orig_settings}")
        self._remove_restore_callback(self.restore_input)

        import termios

        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._terminal_orig_settings)
        except TypeError as e:
            logger.error("Restoring tty state failed", exc_info=e)
        finally:
            self._terminal_orig_settings = None

    def _restore_cursor_position(self):
        self._remove_restore_callback(self._restore_cursor_position)
        self._send_sequence(pt.make_restore_cursor_position)

    def set_horiz_tabs(self, interval: int = None, shift: int = None):
        self._add_restore_callback(self._reset_horiz_tabs)
        self._send_sequence(lambda: pt.term.compose_terminal_tabs_reset(interval, shift, debug=self._debug))

    def _reset_horiz_tabs(self):
        self._remove_restore_callback(self._reset_horiz_tabs)
        self._send_sequence(lambda: pt.term.compose_terminal_tabs_reset(8, debug=self._debug))

    def restore_state(self):
        while self._restore_callbacks:
            logger.debug(f"TSC: Restoring state ({len(self._restore_callbacks)})")
            try:
                self._restore_callbacks.pop()()
            except:  # noqa
                pass

    def _add_restore_callback(self, fn: t.Callable[[], None]) -> None:
        logger.debug(f"TSC: Registering callback: '{fn.__name__}'")
        self._restore_callbacks.append(fn)

    def _remove_restore_callback(self, fn: t.Callable[[], None]) -> None:
        if fn not in self._restore_callbacks:
            return
        logger.debug(f"TSC: Unregistering callback: '{fn.__name__}'")
        self._restore_callbacks.remove(fn)

    def _send_sequence(self, fn: t.Callable[[], pt.ISequence|str]) -> None:
        if not self._is_allowed_to_send_esq():
            logger.debug(f"TSC: Skipping control sequence: "+("not a tty" if not self._isatty() else "forced"))
            return

        sequence = fn()
        logger.debug(f"TSC: Sending control sequence: '{fn.__name__}' -> {sequence!r}")

        if sequence == pt.make_enable_alt_screen_buffer():
            logger.debug(
                "TSC: ENABLED ALT SCREEN BUFFER: ALL STDERR LOG MESSAGES ARE NOW _IGNORED_ BY THE "
                "TERMINAL (syslog should still work unless switched off explicitly)"
            )
        self._echo(sequence)

    def _echo(self, sequence: pt.ISequence):
        self._io.write(sequence.assemble())

    def _is_allowed_to_send_esq(self) -> bool:
        if self._force_esq is not None:
            return self._force_esq
        return self._isatty()

    def _isatty(self):
        return self._io.isatty()

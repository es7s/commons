# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
import enum
import sys
import typing as t

import pytermor as pt

from .io_ import IoProxy, get_stdout
from .log import get_logger


class TerminalInputMode(str, pt.ExtendedEnum):  # @TODO str enums will be available in python 3.11
    DEFAULT: str = 'default'
    DISABLED: str = 'disabled'
    DISCRETE: str = 'discrete'


class TerminalStateController:
    def __init__(self, io_proxy: IoProxy = None):
        self._io_proxy: IoProxy = io_proxy or get_stdout()
        self._restore_callbacks: list[t.Callable[[], None]] = []
        self._terminal_orig_settings: list | None = None

    def assign_proxy(self, io_proxy: IoProxy):
        self._io_proxy = io_proxy
        get_logger().debug(f"TSC: Switched to {self._io_proxy}")

    def enable_alt_screen_buffer(self):
        self._add_restore_callback(self.disable_alt_screen_buffer)
        self._add_restore_callback(self._restore_cursor_position)
        self._send_sequence(pt.make_save_cursor_position)
        self._send_sequence(pt.make_enable_alt_screen_buffer)

    def disable_alt_screen_buffer(self):
        self._remove_restore_callback(self.disable_alt_screen_buffer)
        self._send_sequence(pt.make_disable_alt_screen_buffer)
        get_logger().debug("TSC: DISABLED ALT SCREEN BUFFER: stderr logging should work again")

    def hide_cursor(self):
        self._add_restore_callback(self.show_cursor)
        self._send_sequence(pt.make_hide_cursor)

    def show_cursor(self):
        self._remove_restore_callback(self.show_cursor)
        self._send_sequence(pt.make_show_cursor)

    def setup_input(self, input_mode: TerminalInputMode):
        match input_mode:
            case TerminalInputMode.DEFAULT:
                self.restore_input()
            case TerminalInputMode.DISABLED:
                self.disable_input()
            case TerminalInputMode.DISCRETE:
                self.discrete_input()
            case _:
                raise NotImplementedError(f"Unknown input mode: {input_mode}")

    def disable_input(self):
        get_logger().debug(f"TSC: Putting tty into cbreak mode: {sys.stdin}")
        if not self._is_a_tty():
            return
        if self._terminal_orig_settings:
            get_logger().warning(f"TSC: Altering tty attributes skipped: already altered")
            return

        import tty
        import termios

        self._terminal_orig_settings = termios.tcgetattr(sys.stdin)
        self._add_restore_callback(self.restore_input)
        try:
            tty.setcbreak(sys.stdin)
        except (termios.error, TypeError) as e:
            get_logger().error("Saving tty state failed", exc_info=e)

    def discrete_input(self):
        """
        Use with: sys.stdin.read(1)
        Origin: readchar/_posix_read.py
        """
        get_logger().debug(f"TSC: Enabling tty discrete input: {sys.stdin}")
        if not self._is_a_tty():
            return
        if self._terminal_orig_settings:
            get_logger().warning(f"TSC: Altering tty attributes skipped: already altered")
            return

        import termios

        fd = sys.stdin.fileno()
        term = termios.tcgetattr(fd)
        self._terminal_orig_settings = termios.tcgetattr(fd)
        self._add_restore_callback(self.restore_input)
        try:
            #term[3] &= ~(termios.ICANON | termios.ECHO)
            # originally:
            term[3] &= ~(termios.ICANON | termios.ECHO | termios.IGNBRK | termios.BRKINT)
            # we don't need to ignore Ctrl+C though, because we handle it on the top level in init_cli()
            termios.tcsetattr(fd, termios.TCSAFLUSH, term)
        except (termios.error, TypeError) as e:
            get_logger().error("Saving tty state failed", exc_info=e)

    def restore_input(self):
        if not self._is_a_tty():
            get_logger().warning(f"TSC: Restoring tty attributes skipped: not a tty")
            return
        if not self._terminal_orig_settings:
            get_logger().warning(f"TSC: Restoring tty attributes skipped: nothing to restore")
            return

        get_logger().debug(f"TSC: Restoring tty attributes: {self._terminal_orig_settings}")
        self._remove_restore_callback(self.restore_input)

        import termios

        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._terminal_orig_settings)
        except TypeError as e:
            get_logger().error("Restoring tty state failed", exc_info=e)
        finally:
            self._terminal_orig_settings = None

    def _restore_cursor_position(self):
        self._remove_restore_callback(self._restore_cursor_position)
        self._send_sequence(pt.make_restore_cursor_position)

    def restore_state(self):
        while self._restore_callbacks:
            get_logger().debug(f"TSC: Restoring state ({len(self._restore_callbacks)})")
            try:
                self._restore_callbacks.pop()()
            except:
                pass

    def _add_restore_callback(self, fn: t.Callable[[], None]) -> None:
        get_logger().debug(f"TSC: Registering callback: '{fn.__name__}'")
        self._restore_callbacks.append(fn)

    def _remove_restore_callback(self, fn: t.Callable[[], None]) -> None:
        if fn not in self._restore_callbacks:
            return
        get_logger().debug(f"TSC: Unregistering callback: '{fn.__name__}'")
        self._restore_callbacks.remove(fn)

    def _send_sequence(self, fn: t.Callable[[], pt.ISequence]) -> None:
        if not self._is_a_tty():
            get_logger().debug(f"TSC: Skipping control sequence: not a tty")
            return

        sequence = fn()
        get_logger().debug(f"TSC: Sending control sequence: '{fn.__name__}' -> {sequence!r}")

        if sequence == pt.make_enable_alt_screen_buffer():
            get_logger().debug(
                "TSC: ENABLED ALT SCREEN BUFFER: ALL STDERR LOG MESSAGES ARE NOW _IGNORED_ BY THE "
                "TERMINAL (syslog should still work unless switched off explicitly)"
            )
        self._io_proxy.echo(sequence, bypass=True)  # do not allow to intercept and buffer these

    def _is_a_tty(self):
        return self._io_proxy.io.isatty()

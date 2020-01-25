# modified py3 version of Yinzo/reprint/

import re
import sys
import threading
import time
from builtins import input
from math import ceil
from shutil import get_terminal_size

from taskcat._tui_screen import Screen


def get_char_width(char):
    _o = ord(char)
    _chars = ["0xE", "0xF"]
    if any(_chars) == _o:
        return 0
    for num, wid in Screen.WIDTHS:
        if _o <= num:
            return wid
    return 1


def width_cal_preprocess(content):
    """
    This function also remove ANSI escape code
    to avoid the influence on line width calculation
    """
    ptn = re.compile(r"(\033|\x1b)\[.*?m", re.I)
    _content = re.sub(ptn, "", content)  # remove ANSI escape code
    return _content


def preprocess(content):
    """
    do pre-process to the content, turn it into str (for py3),
     and replace \r\t\n with space
    """
    _content = str(content)
    _content = re.sub(r"\r|\t|\n", " ", _content)
    return _content


def cut_off_at(content, width):
    if line_width(content) > width:
        _now = content[:width]
        while line_width(_now) > width:
            _now = _now[:-1]
        _now += "$" * (width - line_width(_now))
        return _now
    return content


def print_line(content, columns, force_single_line):

    padding = " " * ((columns - line_width(content)) % columns)
    _output = "{content}{padding}".format(content=content, padding=padding)
    if force_single_line:
        _output = cut_off_at(_output, columns)
    print(_output, end="")  # noqa: T001
    sys.stdout.flush()


def line_width(line):
    """
    calculate the width of output in terminal
    """
    _line = width_cal_preprocess(line)
    result = sum(map(get_char_width, _line))
    return result


def lines_of_content(content, width):
    """
    calculate the actual rows with specific terminal width
    """
    result = 0
    if isinstance(content, list):
        for line in content:
            _line = preprocess(line)
            result += ceil(line_width(_line) / width)
    elif isinstance(content, dict):
        for k, v in content.items():
            # adding 2 for the for the colon and space ": "
            _k, _v = map(preprocess, (k, v))
            result += ceil((line_width(_k) + line_width(_v) + 2) / width)
    return int(result)


def print_multi_line(content, force_single_line, sort_key):  # noqa: C901
    """
    'sort_key' parameter only available in 'dict' mode
    """

    def not_tty():
        if isinstance(content, list):
            for line in content:
                print(line)  # noqa: T001
        elif isinstance(content, dict):
            for k, v in sorted(content.items(), key=sort_key):
                print("{}: {}".format(k, v))  # noqa: T001
        else:
            raise TypeError(
                "Excepting types: list, dict. Got: {}".format(type(content))
            )

    if not Screen.IS_A_TTY:
        not_tty()

    columns, rows = get_terminal_size()
    lines = lines_of_content(content, columns)
    if force_single_line is False and lines > rows:
        Screen.OVERFLOW_FLAG = True
    elif force_single_line is True and len(content) > rows:
        Screen.OVERFLOW_FLAG = True

    # to make sure the cursor is at the left most
    print("\b" * columns, end="")  # noqa: T001

    if isinstance(content, list):
        for line in content:
            _line = preprocess(line)
            print_line(_line, columns, force_single_line)
    elif isinstance(content, dict):
        for k, v in sorted(content.items(), key=sort_key):
            _k, _v = map(preprocess, (k, v))
            print_line("{}: {}".format(_k, _v), columns, force_single_line)
    else:
        raise TypeError("Excepting types: list, dict. Got: {}".format(type(content)))

    # do extra blank lines to wipe the remaining of last output
    print(" " * columns * (Screen.LAST_OUTPUT_LINES - lines), end="")  # noqa: T001

    # back to the origin pos
    print(  # noqa: T001
        Screen.MAGIC_CHAR * (max(Screen.LAST_OUTPUT_LINES, lines) - 1), end=""
    )
    sys.stdout.flush()
    Screen.LAST_OUTPUT_LINES = lines


class Output:
    class SignalList(list):
        def __init__(self, parent, obj):
            super(Output.SignalList, self).__init__(obj)
            self.parent = parent
            self.lock = threading.Lock()

        def __setitem__(self, key, value):
            with self.lock:
                super(Output.SignalList, self).__setitem__(key, value)
                if not Screen.IS_A_TTY:
                    print("{}".format(value))  # noqa: T001
                else:
                    self.parent.refresh(int(time.time() * 1000), forced=False)

        def clear(self):
            # with self.lock: In all places you call clear, you actually already have
            # the lock
            super(Output.SignalList, self).clear()

            if Screen.IS_A_TTY:
                self.parent.refresh(int(time.time() * 1000), forced=False)

        def change(self, newlist):
            with self.lock:
                self.clear()
                self.extend(newlist)
                if Screen.IS_A_TTY:
                    self.parent.refresh(int(time.time() * 1000), forced=False)

        def append(self, x):
            with self.lock:
                super(Output.SignalList, self).append(x)
                if not Screen.IS_A_TTY:
                    print("{}".format(x))  # noqa: T001
                else:
                    self.parent.refresh(int(time.time() * 1000), forced=False)

        def insert(self, i, x):
            with self.lock:
                super(Output.SignalList, self).insert(i, x)
                if not Screen.IS_A_TTY:
                    print("{}".format(x))  # noqa: T001
                else:
                    self.parent.refresh(int(time.time() * 1000), forced=False)

        def remove(self, x):
            with self.lock:
                super(Output.SignalList, self).remove(x)
                if Screen.IS_A_TTY:
                    self.parent.refresh(int(time.time() * 1000), forced=False)

        def pop(self, i=-1):
            with self.lock:
                _rs = super(Output.SignalList, self).pop(i)
                if Screen.IS_A_TTY:
                    self.parent.refresh(int(time.time() * 1000), forced=False)
                return _rs

        def sort(self, *args, **kwargs):
            with self.lock:
                super(Output.SignalList, self).sort(*args, **kwargs)
                if Screen.IS_A_TTY:
                    self.parent.refresh(int(time.time() * 1000), forced=False)

    class SignalDict(dict):
        def __init__(self, parent, obj):
            super(Output.SignalDict, self).__init__(obj)
            self.parent = parent
            self.lock = threading.Lock()

        def change(self, newlist):
            with self.lock:
                self.clear()
                super(Output.SignalDict, self).update(newlist)
                self.parent.refresh(int(time.time() * 1000), forced=False)

        def __setitem__(self, key, value):
            with self.lock:
                super(Output.SignalDict, self).__setitem__(key, value)
                if not Screen.IS_A_TTY:
                    print("{}: {}".format(key, value))  # noqa: T001
                else:
                    self.parent.refresh(int(time.time() * 1000), forced=False)

        def clear(self):
            # with self.lock: In all places you call clear, you
            # actually already have the lock
            super(Output.SignalDict, self).clear()
            if Screen.IS_A_TTY:
                self.parent.refresh(int(time.time() * 1000), forced=False)

        def pop(self, *args, **kwargs):
            with self.lock:
                _rs = super(Output.SignalDict, self).pop(*args, **kwargs)
                if Screen.IS_A_TTY:
                    self.parent.refresh(int(time.time() * 1000), forced=False)
                return _rs

        def popitem(self, *args, **kwargs):
            with self.lock:
                _rs = super(Output.SignalDict, self).popitem(*args, **kwargs)
                if Screen.IS_A_TTY:
                    self.parent.refresh(int(time.time() * 1000), forced=False)
                return _rs

        def setdefault(self, *args, **kwargs):
            with self.lock:
                _rs = super(Output.SignalDict, self).setdefault(*args, **kwargs)
                if Screen.IS_A_TTY:
                    self.parent.refresh(int(time.time() * 1000), forced=False)
                return _rs

        def update(self, *args, **kwargs):
            with self.lock:
                super(Output.SignalDict, self).update(*args, **kwargs)
                if Screen.IS_A_TTY:
                    self.parent.refresh(int(time.time() * 1000), forced=False)

    def __init__(
        self,
        output_type="list",
        initial_len=1,
        interval=0,
        force_single_line=False,
        no_warning=False,
        sort_key=lambda x: x[0],
    ):
        self.sort_key = sort_key
        self.no_warning = no_warning

        # reprint does not work in the IDLE terminal,
        # and any other environment that can't get terminal_size
        if Screen.IS_A_TTY and not all(get_terminal_size()):
            if not no_warning:
                _r = input(
                    "Fail to get terminal size, we got {},\
                     continue anyway? (y/N)".format(
                        get_terminal_size()
                    )
                )
                if not (
                    _r and isinstance(_r, str) and _r.lower()[0] in ["y", "t", "1"]
                ):
                    sys.exit(0)

            Screen.IS_A_TTY = False

        if output_type == "list":
            self.warped_obj = Output.SignalList(self, [""] * initial_len)
        elif output_type == "dict":
            self.warped_obj = Output.SignalDict(self, {})

        self.interval = interval
        self.force_single_line = force_single_line
        self._last_update = int(time.time() * 1000)

    def refresh(self, new_time=0, forced=True):
        if new_time - self._last_update >= self.interval or forced:
            print_multi_line(
                self.warped_obj, self.force_single_line, sort_key=self.sort_key
            )
            self._last_update = new_time

    def __enter__(self):
        if not Screen.IS_A_TTY:
            if not self.no_warning:
                print(  # noqa: T001
                    "Not in terminal \
                     now using normal build-in print function.",
                )

        return self.warped_obj

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.refresh(forced=True)
        if Screen.IS_A_TTY:
            columns, _ = get_terminal_size()
            if self.force_single_line:
                print("\n" * len(self.warped_obj), end="")  # noqa: T001
            else:
                print(  # noqa: T001
                    "\n" * lines_of_content(self.warped_obj, columns), end=""
                )
            Screen.LAST_OUTPUT_LINES = 0
            if Screen.OVERFLOW_FLAG:
                if not self.no_warning:
                    print(  # noqa: T001
                        "Detected that the lines of output has been exceeded ",
                        "the height of terminal windows, which caused the ",
                        "former output remained and keep adding new lines.",
                    )

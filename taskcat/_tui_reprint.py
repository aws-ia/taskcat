# -*- coding: utf-8 -*-
# modified py3 version of Yinzo/reprint/

import re
import sys
import time
import threading
from math import ceil

import six
from shutil import get_terminal_size
from builtins import input

last_output_lines = 0
overflow_flag = False
is_atty = sys.stdout.isatty()

magic_char = "\033[F"

widths = [
    (126,    1), (159,    0), (687,     1), (710,   0), (711,   1),
    (727,    0), (733,    1), (879,     0), (1154,  1), (1161,  0),
    (4347,   1), (4447,   2), (7467,    1), (7521,  0), (8369,  1),
    (8426,   0), (9000,   1), (9002,    2), (11021, 1), (12350, 2),
    (12351,  1), (12438,  2), (12442,   0), (19893, 2), (19967, 1),
    (55203,  2), (63743,  1), (64106,   2), (65039, 1), (65059, 0),
    (65131,  2), (65279,  1), (65376,   2), (65500, 1), (65510, 2),
    (120831, 1), (262141, 2), (1114109, 1),
]


def get_char_width(char):
    global widths
    o = ord(char)
    if o == 0xe or o == 0xf:
        return 0
    for num, wid in widths:
        if o <= num:
            return wid
    return 1


def width_cal_preprocess(content):
    """
    This function also remove ANSI escape code to avoid the influence on line width calculation
    """
    ptn = re.compile(r'(\033|\x1b)\[.*?m', re.I)
    _content = re.sub(ptn, '', content) # remove ANSI escape code
    return _content


def preprocess(content):
    """
    do pre-process to the content, turn it into str (for py3), and replace \r\t\n with space
    """
    _content = str(content)
    _content = re.sub(r'\r|\t|\n', ' ', _content)
    return _content


def cut_off_at(content, width):
    if line_width(content) > width:
        now = content[:width]
        while line_width(now) > width:
            now = now[:-1]
        now += "$" * (width - line_width(now))
        return now
    else:
        return content


def print_line(content, columns, force_single_line):

    padding = " " * ((columns - line_width(content)) % columns)
    _output = "{content}{padding}".format(content=content, padding=padding)
    if force_single_line:
        _output = cut_off_at(_output, columns)
    print(_output, end='')
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


def print_multi_line(content, force_single_line, sort_key):
    """
    'sort_key' parameter only available in 'dict' mode
    """

    global last_output_lines
    global overflow_flag
    global is_atty

    if not is_atty:
        if isinstance(content, list):
            for line in content:
                print(line)
        elif isinstance(content, dict):
            for k, v in sorted(content.items(), key=sort_key):
                print("{}: {}".format(k, v))
        else:
            raise TypeError("Excepting types: list, dict. Got: {}".format(type(content)))
        return

    columns, rows = get_terminal_size()
    lines = lines_of_content(content, columns)
    if force_single_line is False and lines > rows:
        overflow_flag = True
    elif force_single_line is True and len(content) > rows:
        overflow_flag = True

    # to make sure the cursor is at the left most
    print("\b" * columns, end="")

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
    print(" " * columns * (last_output_lines - lines), end="")

    # back to the origin pos
    print(magic_char * (max(last_output_lines, lines)-1), end="")
    sys.stdout.flush()
    last_output_lines = lines


class output:

    class SignalList(list):

        def __init__(self, parent, obj):
            super(output.SignalList, self).__init__(obj)
            self.parent = parent
            self.lock = threading.Lock()

        def __setitem__(self, key, value):
            global is_atty
            with self.lock:
                super(output.SignalList, self).__setitem__(key, value)
                if not is_atty:
                    print("{}".format(value))
                else:
                    self.parent.refresh(int(time.time()*1000), forced=False)

        def clear(self):
            global is_atty
            # with self.lock: In all places you call clear, you actually already have the lock
            super(output.SignalList, self).clear()

            if is_atty:
                self.parent.refresh(int(time.time()*1000), forced=False)

        def change(self, newlist):
            with self.lock:
                self.clear()
                self.extend(newlist)
                if is_atty:
                    self.parent.refresh(int(time.time()*1000), forced=False)

        def append(self, x):
            global is_atty
            with self.lock:
                super(output.SignalList, self).append(x)
                if not is_atty:
                    print("{}".format(x))
                else:
                    self.parent.refresh(int(time.time()*1000), forced=False)

        def insert(self, i, x):
            global is_atty
            with self.lock:
                super(output.SignalList, self).insert(i, x)
                if not is_atty:
                    print("{}".format(x))
                else:
                    self.parent.refresh(int(time.time()*1000), forced=False)

        def remove(self, x):
            global is_atty
            with self.lock:
                super(output.SignalList, self).remove(x)
                if is_atty:
                    self.parent.refresh(int(time.time()*1000), forced=False)

        def pop(self, i=-1):
            global is_atty
            with self.lock:
                rs = super(output.SignalList, self).pop(i)
                if is_atty:
                    self.parent.refresh(int(time.time()*1000), forced=False)
                return rs

        def sort(self, *args, **kwargs):
            global is_atty
            with self.lock:
                super(output.SignalList, self).sort(*args, **kwargs)
                if is_atty:
                    self.parent.refresh(int(time.time()*1000), forced=False)


    class SignalDict(dict):

        def __init__(self, parent, obj):
            super(output.SignalDict, self).__init__(obj)
            self.parent = parent
            self.lock = threading.Lock()

        def change(self, newlist):
            with self.lock:
                self.clear()
                super(output.SignalDict, self).update(newlist)
                self.parent.refresh(int(time.time()*1000), forced=False)

        def __setitem__(self, key, value):
            global is_atty
            with self.lock:
                super(output.SignalDict, self).__setitem__(key, value)
                if not is_atty:
                    print("{}: {}".format(key, value))
                else:
                    self.parent.refresh(int(time.time()*1000), forced=False)

        def clear(self):
            global is_atty
            # with self.lock: In all places you call clear, you actually already have the lock
            super(output.SignalDict, self).clear()
            if is_atty:
                self.parent.refresh(int(time.time()*1000), forced=False)

        def pop(self, *args, **kwargs):
            global is_atty
            with self.lock:
                rs = super(output.SignalDict, self).pop(*args, **kwargs)
                if is_atty:
                    self.parent.refresh(int(time.time()*1000), forced=False)
                return rs

        def popitem(self, *args, **kwargs):
            global is_atty
            with self.lock:
                rs = super(output.SignalDict, self).popitem(*args, **kwargs)
                if is_atty:
                    self.parent.refresh(int(time.time()*1000), forced=False)
                return rs

        def setdefault(self, *args, **kwargs):
            global is_atty
            with self.lock:
                rs = super(output.SignalDict, self).setdefault(*args, **kwargs)
                if is_atty:
                    self.parent.refresh(int(time.time()*1000), forced=False)
                return rs

        def update(self, *args, **kwargs):
            global is_atty
            with self.lock:
                super(output.SignalDict, self).update(*args, **kwargs)
                if is_atty:
                    self.parent.refresh(int(time.time()*1000), forced=False)


    def __init__(self, output_type="list", initial_len=1, interval=0, force_single_line=False, no_warning=False, sort_key=lambda x:x[0]):
        self.sort_key = sort_key
        self.no_warning = no_warning
        no_warning and print("All reprint warning diabled.")

        global is_atty
        # reprint does not work in the IDLE terminal, and any other environment that can't get terminal_size
        if is_atty and not all(get_terminal_size()):
            if not no_warning:
                r = input("Fail to get terminal size, we got {}, continue anyway? (y/N)".format(get_terminal_size()))
                if not (r and isinstance(r, str) and r.lower()[0] in ['y','t','1']):
                    sys.exit(0)

            is_atty = False

        if output_type == "list":
            self.warped_obj = output.SignalList(self, [''] * initial_len)
        elif output_type == "dict":
            self.warped_obj = output.SignalDict(self, {})

        self.interval = interval
        self.force_single_line = force_single_line
        self._last_update = int(time.time()*1000)

    def refresh(self, new_time=0, forced=True):
        if new_time - self._last_update >= self.interval or forced:
            print_multi_line(self.warped_obj, self.force_single_line, sort_key=self.sort_key)
            self._last_update = new_time

    def __enter__(self):
        global is_atty
        if not is_atty:
            if not self.no_warning:
                print("Not in terminal, reprint now using normal build-in print function.")

        return self.warped_obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        global is_atty

        self.refresh(forced=True)
        if is_atty:
            columns, _ = get_terminal_size()
            if self.force_single_line:
                print('\n' * len(self.warped_obj), end="")
            else:
                print('\n' * lines_of_content(self.warped_obj, columns), end="")
            global last_output_lines
            global overflow_flag
            last_output_lines = 0
            if overflow_flag:
                if not self.no_warning:
                    print("Detected that the lines of output has been exceeded the height of terminal windows, which \
                    caused the former output remained and keep adding new lines.")


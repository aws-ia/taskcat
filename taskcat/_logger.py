import logging

LOG = logging.getLogger(__name__)


class PrintMsg:
    header = "\x1b[1;41;0m"
    highlight = "\x1b[0;30;47m"
    name_color = "\x1b[0;37;44m"
    aqua = "\x1b[0;30;46m"
    green = "\x1b[0;30;42m"
    white = "\x1b[0;30;47m"
    orange = "\x1b[0;30;43m"
    red = "\x1b[0;30;41m"
    rst_color = "\x1b[0m"
    CRITICAL = "{}[FATAL  ]{} : ".format(red, rst_color)
    ERROR = "{}[ERROR  ]{} : ".format(red, rst_color)
    DEBUG = "{}[DEBUG  ]{} : ".format(aqua, rst_color)
    PASS = "{}[PASS   ]{} : ".format(green, rst_color)
    INFO = "{}[INFO   ]{} : ".format(white, rst_color)
    WARNING = "{}[WARN   ]{} : ".format(orange, rst_color)
    NAMETAG = "{1}{0}{2}".format("taskcat", name_color, rst_color)
    S3 = "{}[S3: -> ]{} ".format(white, rst_color)
    S3DELETE = "{}[S3: DELETE ]{} ".format(white, rst_color)


class AppFilter(logging.Filter):
    def filter(self, record):
        if "nametag" in dir(record):
            record.color_loglevel = record.nametag
        else:
            record.color_loglevel = getattr(PrintMsg, record.levelname)
        return True


def init_taskcat_cli_logger(loglevel=None):
    log = logging.getLogger(__package__)
    cli_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(color_loglevel)s%(message)s")
    cli_handler.setFormatter(formatter)
    cli_handler.addFilter(AppFilter())
    log.addHandler(cli_handler)
    if loglevel:
        loglevel = getattr(logging, loglevel.upper(), 20)
        log.setLevel(loglevel)
    return log

class PrintMsg:
    header = '\x1b[1;41;0m'
    highlight = '\x1b[0;30;47m'
    name_color = '\x1b[0;37;44m'
    aqua = '\x1b[0;30;46m'
    green = '\x1b[0;30;42m'
    white = '\x1b[0;30;47m'
    orange = '\x1b[0;30;43m'
    red = '\x1b[0;30;41m'
    rst_color = '\x1b[0m'
    ERROR = '{}[ERROR  ]{} :'.format(red, rst_color)
    DEBUG = '{}[DEBUG  ]{} :'.format(aqua, rst_color)
    PASS = '{}[PASS   ]{} :'.format(green, rst_color)
    FAIL = '{}[FAIL   ]{} :'.format(red, rst_color)
    INFO = '{}[INFO   ]{} :'.format(orange, rst_color)

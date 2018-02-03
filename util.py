import re


def single_quote_str(string):
    return "'" + re.sub(
        r"(?P<match_char>\'|\\)",
        "\\\\\\g<match_char>",
        string) + "'"

def double_quote_str(string):
    return "\"" + re.sub(
        r"(?P<match_char>\"|\\)",
        "\\\\\\g<match_char>",
        string) + "\""

def unquote_str(string):
    return string[1:-1].replace("\\'", "'")

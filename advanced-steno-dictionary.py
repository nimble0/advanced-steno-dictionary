#!/usr/bin/python

try:
    import simplejson as json
except ImportError:
    import json
import re
import sys


class KeyLayout:
    keys = []
    break_keys = (0, 0)


class Stroke:
    key_layout = None
    keys = []

    def __init__(self, key_layout, stroke_string = ""):
        self.key_layout = key_layout
        self.keys = [False] * len(key_layout.keys)

        i = 0
        j = 0
        while i < len(stroke_string) and j < len(key_layout.keys):
            if stroke_string[i] == key_layout.keys[j]:
                i += 1
                self.keys[j] = True
            elif stroke_string[i] == "-" and j < key_layout.break_keys[1]:
                i += 1
                j = key_layout.break_keys[1] - 1

            j += 1

        # Bad stroke_string (not ordered properly or invalid keys
        if i < len(stroke_string):
            self.keys = [False] * len(key_layout.keys)

    def add(self, stroke):
        for i in range(0, len(stroke.keys)):
            self.keys[i] = self.keys[i] or stroke.keys[i]

    def remove(self, stroke):
        for i in range(0, len(stroke.keys)):
            self.keys[i] = self.keys[i] and not stroke.keys[i]

    def to_string_long(self):
        stroke_string = ""

        for i in range(0, len(self.key_layout.keys)):
            if self.keys[i]:
                stroke_string += self.key_layout.keys[i]
            else:
                stroke_string += " "

        return stroke_string

    def to_string(self):
        stroke_string = self.to_string_long()

        need_middle_divider = True
        for i in range(self.key_layout.break_keys[0], self.key_layout.break_keys[1]):
            if stroke_string[i] != " ":
                need_middle_divider = False

        if need_middle_divider:
            stroke_string = stroke_string[:self.key_layout.break_keys[0]] + "-" + stroke_string[self.key_layout.break_keys[1]:]

        stroke_string = stroke_string.replace(" ", "")

        return stroke_string


class StrokesMixin:
    strokes = []

    # 0 - none
    # 1 - left
    # 2 - right
    change_side = 0

    def __init__(self, strokes = [], change_side = 0):
        self.strokes = strokes
        self.change_side = change_side


class ParseError(Exception):
    pass


class CircularReferenceError(Exception):
    pass


class AdvancedStenoDictionary:
    key_layout = None

    left_mixins = {}
    right_mixins = {}

    entries = {}


    def __init__(self, key_layout, entries):
        self.key_layout = key_layout

        self.left_mixins["-"] = StrokesMixin([Stroke(self.key_layout, "")], 2)
        self.right_mixins["-"] = self.left_mixins["-"]
        self.left_mixins["+"] = StrokesMixin([Stroke(self.key_layout, "")], 1)
        self.right_mixins["+"] = self.left_mixins["+"]

        for i in range(len(self.key_layout.keys)):
            key = self.key_layout.keys[i]

            if i < self.key_layout.break_keys[0]:
                self.left_mixins[key.lower()] = StrokesMixin([Stroke(self.key_layout, key)])
            elif i >= self.key_layout.break_keys[1]:
                self.right_mixins[key.lower()] = StrokesMixin([Stroke(self.key_layout, "-" + key)])
            else:
                self.left_mixins[key.lower()] = StrokesMixin([Stroke(self.key_layout, key)], 2)
                self.right_mixins[key.lower()] = self.left_mixins[key.lower()]

        for entry, strokes in entries.items():
            meta_entry = ""
            meta_divider = entry.rfind("|")
            if meta_divider != -1:
                meta_entry = entry[meta_divider+1:]
                entry = entry[:meta_divider]

            # Entry meta information
            mixin_key = entry.lower()
            mixin_only = meta_entry.find("m") != -1
            entry_only = meta_entry.find("e") != -1
            # 0 - both
            # 1 - left
            # 2 - right
            mixin_side = (meta_entry.find("l") != -1) | ((meta_entry.find("r") != -1)<<1)
            change_side = (meta_entry.find("L") != -1) | ((meta_entry.find("R") != -1)<<1)


            strokes_list = strokes
            if not isinstance(strokes, list):
                strokes_list = [strokes]

            if not mixin_only:
                if not entry in self.entries:
                    self.entries[entry] = []
                self.entries[entry] += strokes_list

            if not entry_only:
                for strokes in strokes_list:
                    mixin = StrokesMixin(strokes, change_side)

                    if mixin_side == 0 or mixin_side == 1:
                        if not mixin_key in self.left_mixins:
                            self.left_mixins[mixin_key] = mixin

                    if mixin_side == 0 or mixin_side == 2:
                        if not mixin_key in self.right_mixins:
                            self.right_mixins[mixin_key] = mixin

    def to_simple_strokes(self, strokes_string, mixins_chain = []):
        parts = re.findall(r"""
            \s+                                               # Whitespace (ignored outside of quotes)
            | [*/+\-&\^]                                      # Special characters
            | (?:[A-Z][a-z_]*                                 # Non-quoted mixins
            | \"(?:[^\\\"]|(?:\\\\)*\\[^\"]|(?:\\\\)*\\\")*\" # Double-quoted mixins
            | \'(?:[^\\\']|(?:\\\\)*\\[^\']|(?:\\\\)*\\\')*\' # Single-quoted mixins
            )""",
            strokes_string,
            re.VERBOSE)

        # Don't attempt to process if the whole strokes string wasn't parsed
        parts_total_length = 0
        for part in parts:
            parts_total_length += len(part)
        if parts_total_length != len(strokes_string):
            raise ParseError("Could not parse mixin definition: " + strokes_string)

        simple_strokes = [Stroke(self.key_layout)]
        mixins = self.left_mixins
        # 0 - add
        # 1 - remove
        combine_action = 0
        for part in parts:
            if part.isspace():
                continue

            if part[0] == "\"":
                part = re.sub(r"\\([\s\S])", "\\1", part[1:-1])
            elif part[0] == "'":
                part = re.sub(r"\\([\s\S])", "\\1", part[1:-1])
            else:
                part = part.lower().replace("_", " ")

            if part == "/":
                combine_action = 0
                mixins = self.left_mixins
                simple_strokes.append(Stroke(self.key_layout))
            elif part == "&":
                combine_action = 0
                mixins = self.left_mixins
            elif part == "^":
                combine_action = 1
                mixins = self.left_mixins
            else:
                if not part in mixins:
                    raise LookupError("Mixin '" + part + "' does not exist.")

                # Mixin contains a circular reference
                if part in mixins_chain:
                    raise CircularReferenceError("Mixin '" + part + "' contains mixins that lead back to itself.")

                mixin = mixins[part]

                if isinstance(mixin.strokes, str):
                    mixin.strokes = self.to_simple_strokes(mixin.strokes, mixins_chain + [part])

                for stroke in mixin.strokes:
                    if combine_action == 0:
                        simple_strokes[-1].add(stroke)
                    elif combine_action == 1:
                        simple_strokes[-1].remove(stroke)
                    simple_strokes.append(Stroke(self.key_layout))
                if len(mixin.strokes) > 0:
                    simple_strokes.pop()

                if len(mixin.strokes) > 1:
                    mixins = self.left_mixins
                    combine_action = 0

                if mixin.change_side == 1:
                    mixins = self.left_mixins
                elif mixin.change_side == 2:
                    mixins = self.right_mixins

        return simple_strokes

    def to_simple_dictionary(self):
        simple_dictionary = {}

        for entry, strokes_list in self.entries.items():
            for strokes in strokes_list:
                strokes_string = ""

                try:
                    simple_strokes = self.to_simple_strokes(strokes)

                    for stroke in simple_strokes:
                        strokes_string += stroke.to_string() + "/"
                    strokes_string = strokes_string[:-1]

                    if strokes_string in simple_dictionary:
                        print("Conflict detected with entry: {\""
                            + entry + "\": \""+strokes+"\"} and: {\""
                            + simple_dictionary[strokes_string] + "\": \"" + strokes_string + "\"}")
                    else:
                        simple_dictionary[strokes_string] = entry
                except(ParseError, LookupError, CircularReferenceError), e:
                    print("Error processing entry: {\"" + entry + "\": \"" + strokes + "\"}")
                    print("  " + e.message)

        return simple_dictionary




if len(sys.argv) < 2:
    exit()

layout = KeyLayout()
layout.keys = "STKPWHRAO*EUFRPBLGTSDZ"
layout.break_keys = (7, 12)

with open(sys.argv[1]) as data_file:
    entries = json.load(data_file)

dictionary = AdvancedStenoDictionary(layout, entries)

simple_dictionary = dictionary.to_simple_dictionary()

if len(sys.argv) >= 3:
    with open(sys.argv[2], 'w') as out_file:
        json.dump(simple_dictionary, out_file,
                  ensure_ascii = False, sort_keys = True,
                  indent = 0, separators = (',', ': '))
else:
    print(json.dumps(simple_dictionary,
                     ensure_ascii = False, sort_keys = True,
                     indent = 0, separators = (',', ': ')))

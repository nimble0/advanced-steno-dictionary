#!/usr/bin/python

try:
    import simplejson as json
except ImportError:
    import json
import re
import sys
import copy
import logging
import collections


def escape_single_quotes(string):
    return re.sub(
        r"(?P<match_char>\'|\\)",
        "\\\\\\g<match_char>",
        string)

def escape_double_quotes(string):
    return re.sub(
        r"(?P<match_char>\"|\\)",
        "\\\\\\g<match_char>",
        string)


class KeyLayout:
    def __init__(self):
        keys = []
        break_keys = (0, 0)


class Stroke:
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


class StrokeSequence:
    def __init__(self, strokes = []):
        self.strokes = strokes

    def add(self, stroke_sequence):
        self.strokes[-1].add(stroke_sequence.strokes[0])
        self.strokes += stroke_sequence.strokes[1:]

    def remove(self, stroke_sequence):
        self.strokes[-1].remove(stroke_sequence.strokes[0])
        self.strokes += stroke_sequence.strokes[1:]

    def combine(self, stroke_sequence, action):
        if action == 0:
            self.add(stroke_sequence)
        else:
            self.remove(stroke_sequence)

    def to_string(self):
        return "/".join([stroke.to_string() for stroke in self.strokes])


class MixinPart:
    def __init__(self, mixin, action):
        self.mixin = mixin
        self.action = action


class AdvancedStrokeSequence:
    def __init__(self, advanced_stroke_sequence_str):
        self.str_ = advanced_stroke_sequence_str
        self.parts = None
        self.simple_stroke_sequences = None

    def parse(self, dictionary, mixin_recursion_chain = []):
        if not self.parts is None:
            return

        part_strs = re.findall(r"""
            \s+                                               # Whitespace (ignored outside of quotes)
            | [*/+\-&\^]                                      # Special characters
            | (?:[A-Z][a-z_]*                                 # Non-quoted mixins
            | \"(?:[^\\\"]|(?:\\\\)*\\[^\"]|(?:\\\\)*\\\")*\" # Double-quoted mixins
            | \'(?:[^\\\']|(?:\\\\)*\\[^\']|(?:\\\\)*\\\')*\' # Single-quoted mixins
            )""",
            self.str_,
            re.VERBOSE)

        # Don't attempt to process if the whole strokes string wasn't parsed
        parts_total_length = 0
        for part_str in part_strs:
            parts_total_length += len(part_str)
        if parts_total_length != len(self.str_):
            raise ParseError("Could not parse mixin definition: " + self.str_)

        self.mixin_parts = []
        action = 0
        side = 0
        for part_str in part_strs:
            if part_str.isspace():
                continue

            if part_str == "&":
                action = 0
            elif part_str == "^":
                action = 1
            else:
                mixin = dictionary.mixin(part_str, side)

                # Mixin contains a circular reference
                if mixin in mixin_recursion_chain:
                    raise CircularReferenceError("Mixin '" + part_str + "' contains mixins that lead back to itself.")

                self.mixin_parts.append(MixinPart(mixin, action))

                if mixin.change_side > 0:
                    side = mixin.change_side - 1

    def to_simple_stroke_sequences(self, dictionary, mixin_recursion_chain = []):
        if self.simple_stroke_sequences is None:
            self.parse(dictionary, mixin_recursion_chain)

            self.simple_stroke_sequences = [StrokeSequence([Stroke(dictionary.key_layout)])]

            for mixin_part in self.mixin_parts:
                stroke_sequences = []

                stroke_sequences_b = mixin_part.mixin.to_simple_stroke_sequences(dictionary, mixin_recursion_chain)
                for stroke_sequence_b in stroke_sequences_b:
                    stroke_sequences_a = copy.deepcopy(self.simple_stroke_sequences);

                    for stroke_sequence_a in stroke_sequences_a:
                        stroke_sequence_a.combine(stroke_sequence_b, mixin_part.action)

                    stroke_sequences += stroke_sequences_a

                self.simple_stroke_sequences = stroke_sequences

        return self.simple_stroke_sequences


class Mixin:
    def __init__(self, advanced_stroke_sequence_strs, change_side = 0):
        self.advanced_stroke_sequences = []
        for str_ in advanced_stroke_sequence_strs:
            self.advanced_stroke_sequences.append(AdvancedStrokeSequence(str_))

        # 0 - none
        # 1 - left
        # 2 - right
        self.change_side = change_side

        self.simple_stroke_sequences = None

    def to_simple_stroke_sequences(self, dictionary, mixin_recursion_chain = []):
        if self.simple_stroke_sequences is None:
            self.simple_stroke_sequences = []
            for advanced_stroke_sequence in self.advanced_stroke_sequences:
                self.simple_stroke_sequences += advanced_stroke_sequence.to_simple_stroke_sequences(dictionary)

        return self.simple_stroke_sequences


class ParseError(Exception):
    pass


class CircularReferenceError(Exception):
    pass


class AdvancedStenoDictionary:
    def __init__(self, key_layout):
        self.key_layout = key_layout
        self.mixins = {}

        self.mixins["-"] = Mixin(["-"], 2)
        self.mixins["+"] = Mixin(["+"], 1)
        self.mixins["/"] = Mixin(["/"], 1)

        self.mixins["-"].simple_stroke_sequences = [StrokeSequence([Stroke(self.key_layout)])]
        self.mixins["+"].simple_stroke_sequences = [StrokeSequence([Stroke(self.key_layout)])]
        self.mixins["/"].simple_stroke_sequences = \
            [StrokeSequence([Stroke(self.key_layout), Stroke(self.key_layout)])]

        self.mixins["--"] = self.mixins["-"]
        self.mixins["-+"] = self.mixins["+"]
        self.mixins["-/"] = self.mixins["/"]

        for i in range(len(self.key_layout.keys)):
            key = self.key_layout.keys[i]
            key_lower = key.lower()

            if i < self.key_layout.break_keys[0]:
                self.mixins[key_lower] = Mixin([key])
                self.mixins[key_lower].simple_stroke_sequences = \
                    [StrokeSequence([Stroke(self.key_layout, key)])]
            elif i >= self.key_layout.break_keys[1]:
                self.mixins["-" + key_lower] = Mixin([key])
                self.mixins["-" + key_lower].simple_stroke_sequences = \
                    [StrokeSequence([Stroke(self.key_layout, "-" + key)])]
            else:
                self.mixins[key_lower] = Mixin(["-" + key], 2)
                self.mixins[key_lower].simple_stroke_sequences = \
                    [StrokeSequence([Stroke(self.key_layout, key)])]
                self.mixins["-" + key_lower] = self.mixins[key_lower]

        self.entries = collections.OrderedDict()

    def add_entries(self, entries):
        for entry, stroke_sequences in entries.items():
            meta_entry = ""
            meta_divider = entry.rfind("|")
            if meta_divider != -1:
                meta_entry = entry[meta_divider+1:]
                entry = entry[:meta_divider]

            # Entry meta information
            mixin_only = meta_entry.find("m") != -1
            entry_only = meta_entry.find("e") != -1
            # 0 - both
            # 1 - left
            # 2 - right
            mixin_side = (meta_entry.find("l") != -1) | ((meta_entry.find("r") != -1)<<1)
            change_side = (meta_entry.find("L") != -1) | ((meta_entry.find("R") != -1)<<1)


            stroke_sequences_ = stroke_sequences
            if not isinstance(stroke_sequences_, list):
                stroke_sequences_ = [stroke_sequences_]

            if not mixin_only:
                if not entry in self.entries:
                    self.entries[entry] = []
                self.entries[entry] += stroke_sequences_

            if not entry_only:
                self.add_mixin(entry, mixin_side, change_side, stroke_sequences_)

    def add_mixin(self, key, side, change_side, entries):
        mixin_keys = [
            "\"" + escape_double_quotes(key) + "\"",
            "'" + escape_single_quotes(key) + "'"]

        # Only add simplified mixin key for keys that don't include
        # special characters and start with a letter.
        if re.match(r"[a-zA-Z][a-zA-Z ]*$", key):
            mixin_keys.append(key.lower().replace(" ", "_"))

        mixin = Mixin(entries, change_side)

        if side == 2:
            for i, key in enumerate(mixin_keys):
                mixin_keys[i] = "-" + key
        elif side != 1:
            add_mixin_keys = []
            for key in mixin_keys:
                add_mixin_keys.append("-" + key)
            mixin_keys += add_mixin_keys

        for key in mixin_keys:
            if key in self.mixins:
                logging.warning("Redefinition of mixin " + key)

            self.mixins[key] = mixin

    def mixin(self, key, side):
        key = ("-" if side == 1 else "") + key[0].lower() + key[1:]

        if not key in self.mixins:
            raise LookupError("Mixin '" + key + "' does not exist.")

        return self.mixins[key]

    def to_simple_dictionary(self):
        simple_dictionary = {}

        for entry, stroke_sequences in self.entries.items():
            for stroke_sequence in stroke_sequences:
                try:
                    simple_stroke_sequences = AdvancedStrokeSequence(stroke_sequence) \
                        .to_simple_stroke_sequences(self)

                    for simple_stroke_sequence in simple_stroke_sequences:
                        strokes_string = simple_stroke_sequence.to_string()
                        if strokes_string in simple_dictionary:
                            logging.warning("Conflict detected with entry: {\""
                                + entry + "\": \"" + stroke_sequence + "\"} and: {\""
                                + simple_dictionary[strokes_string] + "\": \"" + strokes_string + "\"}")

                        simple_dictionary[strokes_string] = entry
                except(ParseError, LookupError, CircularReferenceError), e:
                    logging.warning("Error processing entry: {\"" + entry + "\": \"" + stroke_sequence + "\"}")
                    logging.warning("  " + e.message)

        return simple_dictionary



if len(sys.argv) < 2:
    exit()

layout = KeyLayout()
layout.keys = "STKPWHRAO*EUFRPBLGTSDZ"
layout.break_keys = (7, 12)

with open(sys.argv[1]) as data_file:
    entries = json.load(data_file, object_pairs_hook=collections.OrderedDict)

dictionary = AdvancedStenoDictionary(layout)
dictionary.add_entries(entries)

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

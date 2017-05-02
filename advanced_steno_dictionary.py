import re
import collections
import logging

from stroke import Stroke, StrokeSequence
from advanced_stroke_sequence import \
    AdvancedStrokeSequence, \
    ParseError, \
    CircularReferenceError


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

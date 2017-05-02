import re
import logging
import collections

from advanced_translation import AdvancedTranslation
from stroke_sequence import Stroke, StrokeSequence
from advanced_stroke_sequence import \
    AdvancedStrokeSequence, \
    BoundAdvancedStrokeSequence, \
    ParseError, \
    CircularReferenceError
from permutate import permutate_tree_indices


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
    def __init__(self, change_side = 0):
        self.advanced_stroke_sequences = []

        # 0 - none
        # 1 - left
        # 2 - right
        self.change_side = change_side

        self.simple_stroke_sequences = None

    def add(self, ss):
        self.advanced_stroke_sequences.append(ss)

    def to_simple_stroke_sequences(self, dictionary, mixin_recursion_chain = []):
        if self.simple_stroke_sequences is None:
            self.simple_stroke_sequences = []
            for advanced_stroke_sequence in self.advanced_stroke_sequences:
                self.simple_stroke_sequences += advanced_stroke_sequence \
                    .to_simple_stroke_sequences(dictionary, mixin_recursion_chain)

        return self.simple_stroke_sequences

class AdvancedStenoDictionary:
    def __init__(self, key_layout):
        self.key_layout = key_layout
        self.mixins = {}

        self.mixins["-"] = Mixin(2)
        self.mixins["+"] = Mixin(1)
        self.mixins["/"] = Mixin(1)

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
                self.mixins[key_lower + "-"] = Mixin()
                self.mixins[key_lower + "-"].simple_stroke_sequences = \
                    [StrokeSequence([Stroke(self.key_layout, key)])]
            elif i >= self.key_layout.break_keys[1]:
                self.mixins["-" + key_lower] = Mixin()
                self.mixins["-" + key_lower].simple_stroke_sequences = \
                    [StrokeSequence([Stroke(self.key_layout, "-" + key)])]
            else:
                self.mixins[key_lower + "-"] = Mixin(2)
                self.mixins[key_lower + "-"].simple_stroke_sequences = \
                    [StrokeSequence([Stroke(self.key_layout, key)])]
                self.mixins["-" + key_lower] = self.mixins[key_lower + "-"]

        self.entries = collections.OrderedDict()

    def add_entries(self, entries):
        for translation_str, ss_strs in entries.items():
            translation = AdvancedTranslation(translation_str)

            permutations = permutate_tree_indices(translation)
            if len(permutations) == 0:
                permutations = [()]

            ss_strs = [ss_strs] if isinstance(ss_strs, str) else ss_strs
            for ss_str in ss_strs:
                ss = AdvancedStrokeSequence(ss_str)

                for indices in permutations:
                    simple_translation = translation.lookup(indices)
                    bound_ss = BoundAdvancedStrokeSequence(ss, indices)

                    if translation.is_mixin:
                        self.add_mixin(
                            simple_translation,
                            translation.mixin_side,
                            translation.change_side,
                            bound_ss)

                    if translation.is_entry:
                        if not simple_translation in self.entries:
                            self.entries[simple_translation] = []
                        self.entries[simple_translation].append(bound_ss)

    def add_mixin(self, key, side, change_side, entry):
        mixin_keys = [
            "\"" + escape_double_quotes(key) + "\"",
            "'" + escape_single_quotes(key) + "'"]

        # Only add simplified mixin key for keys that don't include
        # special characters and start with a letter.
        if re.match(r"[a-zA-Z][a-zA-Z ]*$", key):
            mixin_keys.append(key.lower().replace(" ", "_"))

        if side == 0:
            mixin_keys = \
                  [key + "-" for key in mixin_keys] \
                + ["-" + key for key in mixin_keys]
        elif side == 1:
            mixin_keys = [key + "-" for key in mixin_keys]
        elif side == 2:
            mixin_keys = ["-" + key for key in mixin_keys]

        mixin = Mixin(change_side)
        if mixin_keys[0] in self.mixins:
            mixin = self.mixins[mixin_keys[0]]
            if change_side != mixin.change_side:
                logging.warning("Mixin " + key + " definition differs from existing meta data.")
                return
        else:
            for key in mixin_keys:
                self.mixins[key] = mixin

        mixin.add(entry)

    def mixin(self, key, side):
        key = ("-" if side == 1 else "") \
            + key[0].lower() + key[1:] \
            + ("-" if side == 0 else "")

        if not key in self.mixins:
            raise LookupError("Mixin '" + key + "' does not exist.")

        return self.mixins[key]

    def to_simple_dictionary(self):
        simple_dictionary = {}

        for entry, adv_stroke_sequences in self.entries.items():
            for adv_ss in adv_stroke_sequences:
                try:
                    for simple_ss in adv_ss.to_simple_stroke_sequences(self):
                        strokes_string = simple_ss.to_string()
                        if strokes_string in simple_dictionary:
                            logging.warning("Conflict detected with entry: {\""
                                + entry + "\": \""
                                + adv_ss.stroke_sequence.str_ + "\"} and: {\""
                                + simple_dictionary[strokes_string] + "\": \""
                                + strokes_string + "\"}")

                        simple_dictionary[strokes_string] = entry
                except(ParseError, LookupError, CircularReferenceError) as e:
                    logging.warning("Error processing entry: {\""
                        + entry + "\": \""
                        + adv_ss.stroke_sequence.str_ + "\"}")
                    logging.warning("  " + str(e))

        return simple_dictionary

import re
import logging
import collections

from advanced_translation import AdvancedTranslation
from stroke import Stroke, StrokeSequence
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

    def to_simple_stroke_sequences(self, mixin_recursion_chain = []):
        if self.simple_stroke_sequences is None:
            self.simple_stroke_sequences = []
            for advanced_stroke_sequence in self.advanced_stroke_sequences:
                self.simple_stroke_sequences += advanced_stroke_sequence \
                    .to_simple_stroke_sequences(mixin_recursion_chain)

        return self.simple_stroke_sequences

class AdvancedStenoDictionary:
    def __init__(self, key_layout):
        self.key_layout = key_layout
        self.mixins = {}

        self._add_base_mixin("", 0, 0, [StrokeSequence([Stroke(self.key_layout)])])
        self._add_base_mixin("-", 0, 2, [StrokeSequence([Stroke(self.key_layout)])])
        self._add_base_mixin("+", 0, 1, [StrokeSequence([Stroke(self.key_layout)])])
        self._add_base_mixin("/", 0, 1, [StrokeSequence([Stroke(self.key_layout)]*2)])

        for i in range(len(self.key_layout.keys)):
            key = self.key_layout.keys[i]

            key_lower = key.lower()
            if i < self.key_layout.break_keys[0]:
                self._add_base_mixin(key_lower, 1, 0,
                    [StrokeSequence([Stroke(self.key_layout, key)])])
            elif i >= self.key_layout.break_keys[1]:
                self._add_base_mixin(key_lower, 2, 0,
                    [StrokeSequence([Stroke(self.key_layout, "-" + key)])])
            else:
                self._add_base_mixin(key_lower, 0, 2,
                    [StrokeSequence([Stroke(self.key_layout, key)])])

        self.advanced_ss_pattern = re.compile(
            AdvancedStrokeSequence.base_pattern \
                + r"| [" + re.escape("".join(self.key_layout.keys)) + "]"
            , re.VERBOSE)

        self.entries = collections.OrderedDict()

    def add_entries(self, entries):
        for translation_str, ss_strs in entries.items():
            translation = AdvancedTranslation(translation_str)

            permutations = permutate_tree_indices(translation)
            if len(permutations) == 0:
                permutations = [()]

            ss_strs = [ss_strs] if isinstance(ss_strs, str) else ss_strs
            for ss_str in ss_strs:
                ss = AdvancedStrokeSequence(self, ss_str, translation)

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

    def _add_mixin_w_keys(self, keys, side, change_side, entry):
        keys = ([key + "-" for key in keys] if side == 0 or side == 1 else []) \
            + (["-" + key for key in keys] if side == 0 or side == 2 else [])

        mixin = Mixin(change_side)
        if keys[0] in self.mixins:
            mixin = self.mixins[keys[0]]
            if change_side != mixin.change_side:
                logging.warning("Mixin " + keys[0] + " definition differs from existing meta data.")
                return
        else:
            for key in keys:
                self.mixins[key] = mixin

        mixin.add(entry)

    def add_mixin(self, key, side, change_side, entry):
        keys = [
            "\"" + escape_double_quotes(key) + "\"",
            "'" + escape_single_quotes(key) + "'"
        ]

        # Only add simplified mixin key for keys that don't include
        # special characters and start with a letter.
        if re.match(r"[a-zA-Z][a-zA-Z ]*$", key):
            keys.append(key.lower().replace(" ", "_"))

        self._add_mixin_w_keys(keys, side, change_side, entry)

    def _add_base_mixin(self, key, side, change_side, simple_stroke_sequences):
        keys = [
            key,
            "\"" + escape_double_quotes(key) + "\"",
            "'" + escape_single_quotes(key) + "'"
        ]

        self._add_mixin_w_keys(keys, side, change_side, None)

        self.mixin(key, side) \
            .simple_stroke_sequences = simple_stroke_sequences

    def mixin(self, key, side):
        if len(key) > 0:
            key = key[0].lower() + key[1:]
        key = ("-" if side == 2 else "") \
            + key \
            + ("-" if side == 0 or side == 1 else "")

        if not key in self.mixins:
            raise LookupError("Mixin '" + key + "' does not exist.")

        return self.mixins[key]

    def to_simple_dictionary(self):
        simple_dictionary = {}

        for entry, adv_stroke_sequences in self.entries.items():
            for adv_ss in adv_stroke_sequences:
                try:
                    for simple_ss in adv_ss.to_simple_stroke_sequences():
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

import re
import logging

from advanced_translation import AdvancedTranslation
from stroke import Stroke, StrokeSequence
from advanced_stroke_sequence import \
    AdvancedStrokeSequence, \
    ParseError
from permutate import permutate_tree_indices
from util import single_quote_str, double_quote_str, unquote_str


class Mixin:
    def __init__(self, change_side = 0):
        # 0 - none
        # 1 - left
        # 2 - right
        self.change_side = change_side

        self.simple_stroke_sequences = []

    def add(self, stroke_sequences):
        self.simple_stroke_sequences += stroke_sequences

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
            if i < self.key_layout.break_keys[0]:
                self._add_base_mixin(key, 1, 0,
                    [StrokeSequence([Stroke(self.key_layout, key)])])
            elif i >= self.key_layout.break_keys[1]:
                self._add_base_mixin(key, 2, 0,
                    [StrokeSequence([Stroke(self.key_layout, "-" + key)])])
            else:
                self._add_base_mixin(key, 0, 2,
                    [StrokeSequence([Stroke(self.key_layout, key)])])

        self.advanced_ss_pattern = re.compile(
            AdvancedStrokeSequence.base_pattern \
                + r"| [" + re.escape("".join(self.key_layout.keys)) + "]"
            , re.VERBOSE)

        self.entries = {}

    def add_entries(self, entries):
        for translation_str, ss_strs in entries:
            translation = AdvancedTranslation(translation_str)

            permutations = permutate_tree_indices(translation)
            if len(permutations) == 0:
                permutations = [()]

            ss_strs = [ss_strs] if isinstance(ss_strs, str) else ss_strs
            for ss_str in ss_strs:
                try:
                    ss = AdvancedStrokeSequence(self, ss_str, translation)

                    for indices in permutations:
                        simple_translation = translation.lookup(indices)
                        simple_stroke_sequences = ss.to_simple_stroke_sequences(indices)

                        if translation.is_mixin:
                            self.add_mixin(
                                simple_translation,
                                translation.mixin_side,
                                translation.change_side,
                                simple_stroke_sequences)

                        if translation.is_entry:
                            for simple_stroke_sequence in simple_stroke_sequences:
                                key_str = simple_stroke_sequence.to_string()

                                if key_str in self.entries:
                                    logging.warning("Conflict detected with entry: {\""
                                        + translation_str + "\": \""
                                        + ss_str + "\"} and: {\""
                                        + self.entries[key_str] + "\": \""
                                        + key_str + "\"}")

                                self.entries[key_str] = simple_translation
                except(ParseError, LookupError) as e:
                    logging.warning("Error processing entry: {\""
                        + translation_str + "\": \""
                        + ss_str + "\"}")
                    logging.warning("  " + str(e))

    def add_mixin(self, key, side, change_side, entries):
        if side == 0:
            self.add_mixin(key, 1, change_side, entries)
            self.add_mixin(key, 2, change_side, entries)
            return

        key_ = ("-" if side == 2 else "") + double_quote_str(key)
        if key_ in self.mixins:
            mixin = self.mixins[key_]
            if change_side == mixin.change_side:
                mixin.add(entries)
            else:
                logging.warning("Mixin " + keys[0] + " definition differs from existing meta data.")
        else:
            mixin = Mixin(change_side)
            mixin.add(entries)
            self.mixins[key_] = mixin

            # Only add simplified mixin key for keys that don't include
            # special characters and start with a letter.
            if re.match(r"[a-zA-Z][a-zA-Z ]*$", key):
                self.mixins[("-" if side == 2 else "") + key.lower().replace(" ", "_")] = mixin

    def _add_base_mixin(self, key, side, change_side, simple_stroke_sequences):
        mixin = Mixin(change_side)
        mixin.add(simple_stroke_sequences)

        simplified_key = key.lower()
        long_key = double_quote_str(key);

        if side == 0 or side == 1:
            self.mixins[simplified_key] = mixin
            self.mixins[long_key] = mixin
        if side == 0 or side == 2:
            self.mixins["-" + simplified_key] = mixin
            self.mixins["-" + long_key] = mixin

    def mixin(self, key, side):
        key_ = key;
        if len(key) > 0:
            if key[0] == "'":
                key_ = double_quote_str(unquote_str(key))
            elif key[0] != "\"":
                key_ = key.lower()

        key_ = ("-" if side == 2 else "") + key_

        if not key_ in self.mixins:
            raise LookupError("Mixin " + key_ + " does not exist.")

        return self.mixins[key_]

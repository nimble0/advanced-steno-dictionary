import re
import copy

from stroke import Stroke, StrokeSequence


class MixinPart:
    def __init__(self, mixin, action):
        self.mixin = mixin
        self.action = action

class ParseError(Exception):
    pass

class CircularReferenceError(Exception):
    pass

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

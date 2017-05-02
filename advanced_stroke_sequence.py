import copy
import re

from stroke_sequence import Stroke, StrokeSequence
from permutate import PartsList, BuildableOptionGroup, OptionGroupStack


class AdvancedStrokeSequencePart:
    def __init__(self, mixin, action):
        self.mixin = mixin
        self.action = action

    def to_simple_stroke_sequences(self,
        dictionary,
        selection_tree,
        mixin_recursion_chain = []
    ):
        return self.mixin.to_simple_stroke_sequences(
            dictionary,
            mixin_recursion_chain)

#class OptionGroup:
    #def __init__(self, bound_index):
        #self.options = [AdvancedStrokeSequence("")]
        #self.options[0].parts = []
        #self.action = 0
        #self.side = 0
        #self.bound_index = bound_index

    #def add_option(self):
        #self.options.append(AdvancedStrokeSequence(""))
        #self.options[-1].parts = []
        #self.action = 0
        #self.side = 0

    #def to_simple_stroke_sequences(self,
        #dictionary,
        #selection_tree,
        #mixin_recursion_chain = []
    #):
        #selection_indices = selection_tree[self.bound_index]
        #self.simple_stroke_sequences = self.options[selection_indices[0]] \
            #.to_simple_stroke_sequences(
                #dictionary,
                #selection_indices[1],
                #mixin_recursion_chain)

        #return self.simple_stroke_sequences



class AdvancedStrokeSequenceOptionGroup(BuildableOptionGroup):
    def __init__(self, action, bound_index):
        super().__init__(AdvancedStrokeSequence.empty())
        self.action = action
        self.bound_index = bound_index
        self.inner_action = 0
        self.inner_side = 0

    def add_option(self):
        super().add_option()
        self.inner_action = 0
        self.inner_side = 0

    def to_simple_stroke_sequences(self,
        dictionary,
        selection_tree,
        mixin_recursion_chain = []
    ):
        selection_indices = None
        if len(selection_tree) > 0:
            selection_indices = selection_tree[self.bound_index]
            if isinstance(selection_indices, int):
                selection_indices = (selection_indices ,())
        else:
            selection_indices = (0, ())

        self.simple_stroke_sequences = self.options[selection_indices[0]] \
            .to_simple_stroke_sequences(
                dictionary,
                selection_indices[1],
                mixin_recursion_chain)

        return self.simple_stroke_sequences

class AdvancedStrokeSequenceOptionGroupStack(OptionGroupStack):
    def __init__(self):
        super().__init__(AdvancedStrokeSequenceOptionGroup(0, 0))

    def begin_group(self, action, bound_index):
        self.stack.append(AdvancedStrokeSequenceOptionGroup(action, bound_index))

class ParseError(Exception):
    pass

class CircularReferenceError(Exception):
    pass

class AdvancedStrokeSequence(PartsList):
    def __init__(self, advanced_ss_str):
        self.str_ = advanced_ss_str

        self.parts = None
        self.options_tree = []

        self.is_parsed = False

    def __len__(self):
        return len(self.parts)

    def __getitem__(self, i):
        return self.parts[i]

    def empty():
        empty_ss = AdvancedStrokeSequence("")
        empty_ss.parts = []
        return empty_ss

    def add_part(self, part):
        self.parts.append(part)

    def parse(self, dictionary, mixin_recursion_chain = []):
        if not self.parts is None:
            return

        mixin_regex = r"""
            \s+                                               # Whitespace (ignored outside of quotes)
            | [*/+\-&\^\],]                                   # Special single characters
            | \[[0-9]*                                        # Option group
            | [A-Z][a-z_]*                                    # Non-quoted mixins
            | \"(?:[^\\\"]|(?:\\\\)*\\[^\"]|(?:\\\\)*\\\")*\" # Double-quoted mixins
            | \'(?:[^\\\']|(?:\\\\)*\\[^\']|(?:\\\\)*\\\')*\' # Single-quoted mixins
            """

        part_strs = re.findall(
            mixin_regex,
            self.str_,
            re.VERBOSE)

        # Don't attempt to process if the whole strokes string wasn't parsed
        parts_total_length = 0
        for part_str in part_strs:
            parts_total_length += len(part_str)
        if parts_total_length != len(self.str_):
            raise ParseError("Could not parse mixin definition: " + self.str_)

        option_group_stack = AdvancedStrokeSequenceOptionGroupStack()
        for part_str in part_strs:
            if part_str.isspace():
                continue

            if part_str == "&":
                option_group_stack[-1].inner_action = 0
            elif part_str == "^":
                option_group_stack[-1].inner_action = 1
            elif part_str[:1] == "[":
                option_group_stack.begin_group(
                    option_group_stack[-1].inner_action,
                    int(part_str[1:]))
            elif part_str == "]":
                option_group_stack.end_group()
            elif part_str == ",":
                option_group_stack.add_option()
            else:
                mixin = dictionary.mixin(part_str, option_group_stack[-1].inner_side)

                # Mixin contains a circular reference
                if mixin in mixin_recursion_chain:
                    raise CircularReferenceError("Mixin '" + mixin_str + "' contains mixins that lead back to itself.")

                option_group_stack.add_part(AdvancedStrokeSequencePart(
                    mixin,
                    option_group_stack[-1].inner_action))

                if mixin.change_side > 0:
                    option_group_stack[-1].inner_side = mixin.change_side - 1

        self.parts = option_group_stack.root().parts

    def to_simple_stroke_sequences(self,
        dictionary,
        selection_tree = [],
        mixin_recursion_chain = []
    ):
        if not self.is_parsed:
            self.parse(dictionary, mixin_recursion_chain)
            self.is_parsed = True

        simple_stroke_sequences = [StrokeSequence([Stroke(dictionary.key_layout)])]

        for part in self.parts:
            stroke_sequences = []

            stroke_sequences_b = part.to_simple_stroke_sequences(
                dictionary,
                selection_tree,
                mixin_recursion_chain)
            for stroke_sequence_b in stroke_sequences_b:
                stroke_sequences_a = copy.deepcopy(simple_stroke_sequences);

                for stroke_sequence_a in stroke_sequences_a:
                    stroke_sequence_a.combine(stroke_sequence_b, part.action)

                stroke_sequences += stroke_sequences_a

            simple_stroke_sequences = stroke_sequences

        return simple_stroke_sequences

class BoundAdvancedStrokeSequence:
    def __init__(self, stroke_sequence, selection_tree):
        self.stroke_sequence = stroke_sequence
        self.selection_tree = selection_tree

        self.simple_stroke_sequences = None

    def to_simple_stroke_sequences(self, dictionary, mixin_recursion_chain = []):
        if self.simple_stroke_sequences is None:
            self.simple_stroke_sequences = \
                self.stroke_sequence.to_simple_stroke_sequences(
                    dictionary,
                    self.selection_tree,
                    mixin_recursion_chain)

        return self.simple_stroke_sequences

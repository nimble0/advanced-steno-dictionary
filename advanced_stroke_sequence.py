import re
import copy

from stroke import Stroke, StrokeSequence
from permutate import \
    PartsList, \
    OptionGroup, \
    BuildableOptionGroup, \
    OptionGroupStack, \
    permutate_tree_indices
from util import double_quote_str


class AdvancedStrokeSequencePart:
    def __init__(self, dictionary, name, side, action):
        self.mixin = dictionary.mixin(name, side)
        self.action = action

    def to_simple_stroke_sequences(self,
        selection_tree,
        mixin_recursion_chain = []
    ):
        # Mixin contains a circular reference
        #if mixin in mixin_recursion_chain:
            #raise CircularReferenceError("Mixin '" + name + "' contains mixins that lead back to itself.")

        return self.mixin.to_simple_stroke_sequences(
            mixin_recursion_chain)

class AdvancedStrokeSequenceExpandedOptionGroup(OptionGroup):
    def __init__(self, options):
        self.options = options

    def __len__(self):
        return len(self.options)

    def __getitem__(self, i):
        return self.options[i]

    def to_simple_stroke_sequences(self,
        selection_tree = [],
        mixin_recursion_chain = []
    ):
        return self.options[selection_tree].to_simple_stroke_sequences(
            selection_tree,
            mixin_recursion_chain)

class AdvancedStrokeSequenceOptionGroup(BuildableOptionGroup):
    def __init__(self,
        dictionary,
        side,
        action,
        bound_index,
        fill_in_options
    ):
        self.dictionary = dictionary
        self.start_side = side
        self.option_i = -1
        super().__init__(None)
        self.action = action
        self.bound_index = bound_index
        self.sub_option_group_i = 0
        self.fill_in_options = fill_in_options

    def add_option(self):
        self.options.append(AdvancedStrokeSequence.empty(self.dictionary))
        self.inner_side = self.start_side
        self.inner_action = 0
        self.option_i += 1
        self.sub_option_group_i = 0

    def add_part(self, part):
        super().add_part(part)

    def fill_in(self):
        def fill_in_option(i):
            if i < len(self.options) and len(self.options[i].parts) > 0:
                return self.options[i]
            else:
                permutations = permutate_tree_indices(self.fill_in_options[i])
                if len(permutations) == 0:
                    return AdvancedStrokeSequencePart(
                        self.dictionary,
                        double_quote_str(self.fill_in_options[i].lookup(())),
                        self.start_side,
                        0)
                else:
                    return AdvancedStrokeSequenceExpandedOptionGroup({
                        permutation: AdvancedStrokeSequencePart(
                            self.dictionary,
                            double_quote_str(
                                self.fill_in_options[i].lookup(permutation)),
                            self.start_side,
                            0)
                        for permutation in permutations})

        self.options = [fill_in_option(i)
            for i in range(0, len(self.fill_in_options))]

    def to_simple_stroke_sequences(self,
        selection_tree,
        mixin_recursion_chain = []
    ):
        selection_indices = None
        if len(selection_tree) > 0:
            selection_indices = selection_tree[self.bound_index]
            if isinstance(selection_indices, int):
                selection_indices = (selection_indices, ())
        else:
            selection_indices = (0, ())

        return self.options[selection_indices[0]] \
            .to_simple_stroke_sequences(
                selection_indices[1],
                mixin_recursion_chain)

class AdvancedStrokeSequenceOptionGroupStack(OptionGroupStack):
    def __init__(self, dictionary, fill_in_options):
        self.dictionary = dictionary
        self.stack = [AdvancedStrokeSequenceOptionGroup(
            self.dictionary, 0, 0, 1, fill_in_options)]

    def begin_group(self, action, bound_index):
        self.stack[-1].sub_option_group_i += 1
        self.stack.append(AdvancedStrokeSequenceOptionGroup(
            self.dictionary,
            self.stack[-1].inner_side,
            action,
            bound_index,
            self.stack[-1].fill_in_options[self.stack[-1].option_i] \
                .option_group(bound_index)))

    def end_group(self):
        self.stack[-1].fill_in()
        super().end_group()


class ParseError(Exception):
    pass

class CircularReferenceError(Exception):
    pass

class AdvancedStrokeSequence(PartsList):
    base_pattern = r"""
        \s+                                               # Whitespace (ignored outside of quotes)
        | [*/+\-&\^\],]                                   # Special single characters
        | \[[0-9]*                                        # Option group
        | [A-Z][a-z_]*                                    # Non-quoted mixins
        | \"(?:[^\\\"]|(?:\\\\)*\\[^\"]|(?:\\\\)*\\\")*\" # Double-quoted mixins
        | \'(?:[^\\\']|(?:\\\\)*\\[^\']|(?:\\\\)*\\\')*\' # Single-quoted mixins
        """

    def __init__(self, dictionary, advanced_ss_str, fill_in_options):
        self.dictionary = dictionary
        self.str_ = advanced_ss_str
        self.fill_in_options = fill_in_options

        self.parts = None

        self.is_parsed = False

    def __len__(self):
        return len(self.parts)

    def __getitem__(self, i):
        return self.parts[i]

    def empty(dictionary):
        empty_ss = AdvancedStrokeSequence(dictionary, "", None)
        empty_ss.parts = []
        return empty_ss

    def add_part(self, part):
        self.parts.append(part)

    def parse(self, mixin_recursion_chain = []):
        if not self.parts is None:
            return

        part_strs = self.dictionary.advanced_ss_pattern.findall(self.str_)

        # Don't attempt to process if the whole strokes string wasn't parsed
        parts_total_length = 0
        for part_str in part_strs:
            parts_total_length += len(part_str)
        if parts_total_length != len(self.str_):
            raise ParseError("Could not parse mixin definition: " + self.str_)

        option_group_stack = AdvancedStrokeSequenceOptionGroupStack(
            self.dictionary,
            (self.fill_in_options,))
        for part_str in part_strs:
            if part_str.isspace() or part_str == "''" or part_str == '""':
                continue

            if part_str == "&":
                option_group_stack[-1].inner_action = 0
            elif part_str == "^":
                option_group_stack[-1].inner_action = 1
            elif part_str[:1] == "[":
                bound_index = option_group_stack[-1].sub_option_group_i
                if len(part_str) > 1:
                    try:
                        bound_index = int(part_str[1:])
                    except(ValueError) as e:
                        raise ParseError("Bad option group bound index (not an integer)")

                option_group_stack.begin_group(
                    option_group_stack[-1].inner_action,
                    bound_index)
            elif part_str == "]":
                option_group_stack.end_group()
            elif part_str == ",":
                option_group_stack.add_option()
            else:
                part = AdvancedStrokeSequencePart(
                    self.dictionary,
                    part_str,
                    option_group_stack[-1].inner_side,
                    option_group_stack[-1].inner_action)

                option_group_stack.add_part(part)

                if part.mixin.change_side > 0:
                    option_group_stack[-1].inner_side = part.mixin.change_side

        self.parts = option_group_stack.root().parts

    def to_simple_stroke_sequences(self,
        selection_tree = [],
        mixin_recursion_chain = []
    ):
        if not self.is_parsed:
            self.parse(mixin_recursion_chain)
            self.is_parsed = True

        simple_stroke_sequences = [StrokeSequence(
            [Stroke(self.dictionary.key_layout)])]

        for part in self.parts:
            simple_stroke_sequences = [ss_a.copy().combine(ss_b, part.action)
                for ss_b in part.to_simple_stroke_sequences(
                    selection_tree,
                    mixin_recursion_chain)
                for ss_a in simple_stroke_sequences]

        return simple_stroke_sequences

class BoundAdvancedStrokeSequence:
    def __init__(self, stroke_sequence, selection_tree):
        self.stroke_sequence = stroke_sequence
        self.selection_tree = selection_tree

        self.simple_stroke_sequences = None

    def to_simple_stroke_sequences(self, mixin_recursion_chain = []):
        if self.simple_stroke_sequences is None:
            self.simple_stroke_sequences = \
                self.stroke_sequence.to_simple_stroke_sequences(
                    self.selection_tree,
                    mixin_recursion_chain)

        return self.simple_stroke_sequences

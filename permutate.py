import copy
from collections import Sequence
from abc import ABCMeta


class PartsList(Sequence):
    __metaclass__ = ABCMeta

class OptionGroup(Sequence):
    __metaclass__ = ABCMeta

PartsList.register(list)
PartsList.register(tuple)

OptionGroup.register(list)
OptionGroup.register(tuple)


class OptionGroupStack:
    def __init__(self, option_group_object):
        self.option_group_object = option_group_object
        self.stack = [copy.deepcopy(self.option_group_object)]

    def __len__(self):
        return len(self.stack)

    def __getitem__(self, i):
        return self.stack[i]

    def begin_group(self):
        self.stack.append(copy.deepcopy(self.option_group_object))

    def end_group(self):
        complete_group = self.stack.pop()

        self.stack[-1].add_part(complete_group)

    def add_part(self, part):
        self.stack[-1].add_part(part)

    def add_option(self):
        self.stack[-1].add_option()

    def root(self):
        return self.stack[0][0]

class BuildableOptionGroup(OptionGroup):
    def __init__(self, option_object):
        self.option_object = option_object
        self.options = []
        self.add_option()

    def __len__(self):
        return len(self.options)

    def __getitem__(self, i):
        return self.options[i]

    def add_option(self):
        self.options.append(copy.deepcopy(self.option_object))

    def add_part(self, part):
        self.options[-1].add_part(part)


def permutate(container):
    if len(container) == 0:
        return

    indices = [0] * len(container)
    value = [container[i][indices[i]] for i in range(0, len(indices))]

    while True:
        yield tuple(value)

        indices[-1] += 1
        for i in range(len(indices)-1, -1, -1):
            if indices[i] == len(container[i]):
                if i == 0:
                    return

                indices[i] = 0
                indices[i-1] += 1
                value[i] = container[i][indices[i]]
            else:
                value[i] = container[i][indices[i]]
                break

def permutate_recursive(options_tree):
    if not isinstance(options_tree, Sequence):
        return (options_tree,)
    else:
        options_flat = []

        for option_tree in options_tree:
            option_flat = []
            for choice in option_tree:
                option_flat += permutate_recursive(choice)

            options_flat.append(option_flat)

        return [x for x in permutate(options_flat)]

def permutate_indices(container):
    if len(container) == 0:
        return

    indices = [0] * len(container)

    while True:
        yield tuple(indices)

        indices[-1] += 1
        for i in range(len(indices)-1, -1, -1):
            if indices[i] == len(container[i]):
                if i == 0:
                    return

                indices[i] = 0
                indices[i-1] += 1
            else:
                break

def permutate_tree_indices(options_tree):
    options_flat = []
    for option_tree in options_tree:
        if isinstance(option_tree, OptionGroup):
            option_flat = []
            for i in range(0, len(option_tree)):
                if isinstance(option_tree[i], PartsList):
                    option_permutations = permutate_tree_indices(option_tree[i])

                    if len(option_permutations) > 0:
                        option_flat += [(i, sub_i) for sub_i in
                            option_permutations]
                    else:
                        option_flat.append(i)
                else:
                    option_flat.append(i)

            options_flat.append(option_flat)

    return [x for x in permutate(options_flat)]

def lookup_tree_sequence(options_tree, choice_tree):
    value = []
    i = 0
    for option_tree in options_tree:
        choice = choice_tree[i]
        if type(choice) is tuple:
            value.append(lookup_tree_sequence(option_tree[choice[0]], choice[1]))
        else:
            value.append(option_tree[choice])
        i += 1

    return tuple(value)

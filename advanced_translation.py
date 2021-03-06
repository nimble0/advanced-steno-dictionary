import re
from permutate import PartsList, BuildableOptionGroup, OptionGroupStack


class AdvancedTranslation(PartsList):
    translation_pattern = re.compile(
        r"""
            [\[\],]
        | (?:[^\[\],]|\\[\[\],])+
        """,
        re.VERBOSE)

    def __init__(self, translation_str):
        self.str_ = translation_str

        meta_entry = ""
        meta_divider = self.str_.rfind("|")
        translation = self.str_
        if meta_divider != -1:
            meta_entry = self.str_[meta_divider+1:]
            translation = self.str_[:meta_divider]

        # Entry meta information
        self.is_mixin = meta_entry.find("e") == -1
        self.is_entry = meta_entry.find("m") == -1
        # 0 - both
        # 1 - left
        # 2 - right
        self.mixin_side = (meta_entry.find("l") != -1) | ((meta_entry.find("r") != -1)<<1)
        self.change_side = (meta_entry.find("L") != -1) | ((meta_entry.find("R") != -1)<<1)

        if translation == "":
            self.parts = []
            return

        part_strs = AdvancedTranslation.translation_pattern.findall(translation)

        option_group_stack = OptionGroupStack(
            BuildableOptionGroup(AdvancedTranslation("")))
        for part_str in part_strs:
            if part_str == "[":
                option_group_stack.begin_group()
            elif part_str == "]":
                option_group_stack.end_group()
            elif part_str == ",":
                option_group_stack.add_option()
            else:
                option_group_stack.add_part(part_str)

        self.parts = option_group_stack.root().parts

    def __len__(self):
        return len(self.parts)

    def __getitem__(self, i):
        return self.parts[i]

    def add_part(self, part):
        self.parts.append(part)

    def lookup(self, choice_tree):
        value = ""
        i = 0
        for part in self.parts:
            if isinstance(part, BuildableOptionGroup):
                choice = choice_tree[i]
                if isinstance(choice, int):
                    choice = (choice, ())
                value += part[choice[0]].lookup(choice[1])
                i += 1
            else:
                value += part

        return value

    def option_group(self, index):
        i = 0
        for part in self.parts:
            if isinstance(part, BuildableOptionGroup):
                if i == index:
                    return part
                i += 1
        return None

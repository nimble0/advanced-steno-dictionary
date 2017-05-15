import copy

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
        self.keys = [self.keys[i] or stroke.keys[i]
            for i in range(0, len(stroke.keys))]

        return self

    def remove(self, stroke):
        self.keys = [self.keys[i] and not stroke.keys[i]
            for i in range(0, len(stroke.keys))]

        return self

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

        return self

    def remove(self, stroke_sequence):
        self.strokes[-1].remove(stroke_sequence.strokes[0])
        self.strokes += stroke_sequence.strokes[1:]

        return self

    def combine(self, stroke_sequence, action):
        if action == 0:
            self.add(stroke_sequence)
        else:
            self.remove(stroke_sequence)

        return self

    def copy(self):
        return StrokeSequence([copy.copy(stroke) for stroke in self.strokes])

    def to_string(self):
        return "/".join([stroke.to_string() for stroke in self.strokes])

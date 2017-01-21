#!/usr/bin/python

try:
	import simplejson as json
except ImportError:
	import json
import re
import sys


class KeyLayout:
	keys = []
	break_keys = (0, 0)


class Stroke:
	key_layout = None
	keys = []

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
		for i in range(0, len(stroke.keys)):
			self.keys[i] = self.keys[i] or stroke.keys[i]

	def remove(self, stroke):
		for i in range(0, len(stroke.keys)):
			self.keys[i] = self.keys[i] and stroke.keys[i]

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



class StrokesMixin:
	strokes = []
	# 0 - No change
	# 1 - Change to left stroke
	# 2 - Change to right stroke
	change_stroke = 0

	def __init__(self, strokes = [], change_stroke = 0):
		self.strokes = strokes
		self.change_stroke = change_stroke


class AdvancedStenoDictionary:
	key_layout = None

	left_mixins = {}
	right_mixins = {}

	entries = {}


	def __init__(self, key_layout, entries):
		self.key_layout = key_layout

		for i in range(len(self.key_layout.keys)):
			key = self.key_layout.keys[i]

			if i < self.key_layout.break_keys[0]:
				self.left_mixins[key.lower()] = StrokesMixin(
					[Stroke(self.key_layout, key)],
					0)
			elif i >= self.key_layout.break_keys[1]:
				self.right_mixins[key.lower()] = StrokesMixin(
					[Stroke(self.key_layout, "-" + key)],
					0)
			else:
				self.left_mixins[key.lower()] = StrokesMixin(
					[Stroke(self.key_layout, key)],
					2)
				self.right_mixins[key.lower()] = self.left_mixins[key.lower()]

		for entry, strokes in entries.items():
			meta_entry = ""
			meta_divider = entry.rfind("|")
			if meta_divider != -1:
				meta_entry = entry[meta_divider+1:]
				entry = entry[:meta_divider]

			meta_mixin_only = meta_entry.find("m") != -1
			meta_left_mixin = meta_entry.find("r") == -1 or meta_entry.find("l") != -1
			meta_right_mixin = meta_entry.find("l") == -1 or meta_entry.find("r") != -1

			if not meta_mixin_only:
				self.entries[entry] = strokes

			if meta_left_mixin:
				self.left_mixins[entry.lower()] = strokes

			if meta_right_mixin:
				self.right_mixins[entry.lower()] = strokes

	def to_simple_strokes(self, strokes_string):
		parts = re.findall(r"/|-|\^{0,1}-{0,1}(?:[A-Z][a-z]*|\"(?:[^\\\"]|(?:\\\\)*\\\")*\")", strokes_string)

		simple_strokes = [Stroke(self.key_layout)]
		mixins = self.left_mixins
		for part in parts:
			if part == "/":
				simple_strokes.append(Stroke(self.key_layout))
			else:
				mixin = mixins[part.lower()]

				if not isinstance(mixin, StrokesMixin):
					mixins[part.lower()] = StrokesMixin(self.to_simple_strokes(mixin))
					mixin = mixins[part.lower()]

				for stroke in mixin.strokes:
					simple_strokes[-1].add(stroke)
					simple_strokes.append(Stroke(self.key_layout))
				simple_strokes.pop()

				if len(mixin.strokes) > 1:
					mixins = self.left_mixins

				if mixin.change_stroke == 1:
					mixins = self.left_mixins
				elif mixin.change_stroke == 2:
					mixins = self.right_mixins

		return simple_strokes

	def to_simple_dictionary(self):
		simple_dictionary = {}

		for entry, strokes in self.entries.items():
			strokes_string = ""

			for stroke in self.to_simple_strokes(strokes):
				strokes_string += stroke.to_string() + "/"
			strokes_string = strokes_string[:-1]

			simple_dictionary[strokes_string] = entry

		return simple_dictionary




if len(sys.argv) < 2:
	exit()

layout = KeyLayout()
layout.keys = "STKPWHRAOEUFRPBLGTSDZ"
layout.break_keys = (7, 11)

with open(sys.argv[1]) as data_file:
	entries = json.load(data_file)

dictionary = AdvancedStenoDictionary(layout, entries)

simple_dictionary = dictionary.to_simple_dictionary()

if len(sys.argv) >= 3:
	with open(sys.argv[2], 'w') as out_file:
		json.dump(simple_dictionary, out_file, False, True, True, True, None, 2)
else:
	print(json.dumps(simple_dictionary))

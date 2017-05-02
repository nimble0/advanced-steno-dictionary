#!/usr/bin/python

import sys
try:
    import simplejson as json
except ImportError:
    import json
import collections

from stroke_sequence import KeyLayout
from advanced_steno_dictionary import AdvancedStenoDictionary


if len(sys.argv) < 2:
    exit()

layout = KeyLayout()
layout.keys = "STKPWHRAO*EUFRPBLGTSDZ"
layout.break_keys = (7, 12)

with open(sys.argv[1]) as data_file:
    entries = json.load(data_file, object_pairs_hook=collections.OrderedDict)

dictionary = AdvancedStenoDictionary(layout)
dictionary.add_entries(entries)

simple_dictionary = dictionary.to_simple_dictionary()

if len(sys.argv) >= 3:
    with open(sys.argv[2], 'w') as out_file:
        json.dump(simple_dictionary, out_file,
                  ensure_ascii = False, sort_keys = True,
                  indent = 0, separators = (',', ': '))
else:
    print(json.dumps(simple_dictionary,
                     ensure_ascii = False, sort_keys = True,
                     indent = 0, separators = (',', ': ')))

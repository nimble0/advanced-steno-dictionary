#!/usr/bin/python

import sys
try:
    import simplejson as json
except ImportError:
    import json

from stroke import KeyLayout
from advanced_steno_dictionary import AdvancedStenoDictionary


if len(sys.argv) < 2:
    exit()

layout = KeyLayout()
layout.keys = "STKPWHRAO*EUFRPBLGTSDZ"
layout.break_keys = (7, 12)

with open(sys.argv[1]) as data_file:
    entries = json.load(data_file, object_pairs_hook=tuple)

dictionary = AdvancedStenoDictionary(layout)
dictionary.add_entries(entries)

if len(sys.argv) >= 3:
    with open(sys.argv[2], 'w') as out_file:
        json.dump(dictionary.entries, out_file,
                  ensure_ascii = False, sort_keys = True,
                  indent = 0, separators = (',', ': '))
else:
    print(json.dumps(dictionary.entries,
                     ensure_ascii = False, sort_keys = True,
                     indent = 0, separators = (',', ': ')))

# Advanced steno dictionary

A preprocessor that generates a JSON Plover dictionary, which allows the use of dictionary entries as mixins.


## Dictionary format

The dictionary format is a JSON formatted object similar to the JSON Plover dictionary. Entries use the translation as a key and the strokes string as a value (the opposite of the Plover's JSON dictionary format). A list of stroke strings can be used instead of a single string if necessary. Strokes are written in Pascal case; a capital letter starts a new reference to a key or mixin. Quotation marks can also be used to start a new reference (these may need to be escaped) which allows the use of all characters.

### Special characters within strokes

* **/** - Begins a new stroke as in a standard steno dictionary.
* **-** - Changes stroke state to the right, which changes the available keys and mixins. This is similar to its function in a standard steno dictionary.
* **+** - Resets stroke state to the left, reversing the effect of **-** or keys/mixins that behave as a divider.
* **^** - Changes to stroke removal mode, whereby subsequent keys (or keys referred to by mixins) are removed from the given stroke instead of combined. This also resets the stroke state to the left.
* **&** - Resets to stroke addition mode, reversing the effect of **^**. This also resets the stroke state to the left.

### Entry meta options

Meta options are added after the **|** character within the translation string. If a translation includes a **|** then a trailing **|** must be added.

* **m** - Pure mixin, don't create a standalone dictionary entry.
* **e** - Dictionary entry only, don't allow use as a mixin.
* **l** - Left mixin, only allow mixin before divider (-) and keys/mixins that behave as dividers (e.g. voxels).
* **r** - Right mixin, only allow mixin after at least one divider or keys/mixins that behave as dividers.
* **L** - Reset stroke state (similar to a reverse divider).
* **R** - Behave as a divider when used as a mixin.


## Examples

### Simple, single stroke mixin
```
{
"want": "WAPBT",
"wanted": "Want-D"
}
```
Output:
```
{
"WAPBT": "want",
"WAPBTD": "wanted"
}
```

### Pure, left and right mixins
```
{
"N|ml": "TPH",
"N|mr": "-PB",
"nan": "NAN"
}
```
Output:
```
{
"TPHAPB": "nan"
}
```

### Dividing mixin
```
{
"I|mR": "EU",
"pit": "PIT"
}
```
Output:
```
{
"PEUT": "pit"
}
```

### Key removal
```
{
"peek": "PAOEBG",
"peak": "PAOEBG^O"
}
```
Output:
```
{
"PAOEBG": "peek",
"PAEBG": "peak"
}
```

### Multi stroke mixin
```
{
"tragic": "TRAPBLG/EUBG",
"tragically": "Tragic-L"
}
```
Output:
```
{
"TRAPBLG/EUBG": "tragic",
"TRAPBLG/EUBLG": "tragically"
}
```


## Usage

Run from the commandline:

python advanced-steno-dictionary.py <input dictionary file path> <output dictionary file path>

The output dictionary file path can be omitted to output to stdout.

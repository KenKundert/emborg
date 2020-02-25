# Collections
#
# Provides common interface for dictionaries and lists. If a string is passed
# in, it is split and then treated as a list. Optimized for convenience rather
# than for large collections. Sorting versus the key is used to avoid randomness
# in the ordering of the dictionary-based collections.

# License {{{1
# Copyright (C) 2016-2020 Kenneth S. Kundert
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.

# Imports {{{1
from inform import is_collection, is_str

# Globals {{{1
__version__ = "0.3.1"
__released__ = "2020-02-21"


# Utilities {{{1
def split_lines(text, comment=None, strip=False, cull=False):
    """Split lines

    Can be passed as a splitter to Collection. Takes a multiline string,
    converts it to individual lines where each line is stripped (if strip is
    True), comments are removed (if comment string is provided, and empty lines
    are culled (if cull is True).
    """
    lines = text.splitlines()
    if comment:
        lines = (l.partition(comment)[0] for l in lines)
    if strip:
        lines = (l.strip() for l in lines)
    if cull:
        return (l for l in lines if l)
    else:
        return lines


# Collection {{{1
class Collection(object):
    fmt = {}  # default value format
    sep = " "  # default separator
    splitter = "|"  # default format splitter (goes between fmt and sep)

    """Collection

    Takes a list or dictionary and provides both a list like and dictionary like
    API, meaning that it provides the keys, values, and items methods like
    dictionary and you can iterate through the value like a list.  When applying
    keys to a list, the indices are returned as the keys. You can also use an
    index or a key to get a value, you test to see if a value is in the
    collection using the *in* operator, and you can get the length of the
    collection.

    If splitter is a string or None, then you can pass in a string and it will
    be split into a list to form the collection.  You can also pass in a
    splitting function.
    """

    def __init__(self, collection, splitter=None, **kwargs):
        if is_str(collection):
            if callable(splitter):
                self.collection = splitter(collection, **kwargs)
                return
            elif splitter is not False:
                self.collection = collection.split(splitter)
                return
        if is_collection(collection):
            self.collection = collection
            return
        if collection is None:
            self.collection = []
            return
        # is scalar
        self.collection = {None: collection}

    def keys(self):
        try:
            return self.collection.keys()
        except AttributeError:
            return range(len(self.collection))

    def values(self):
        try:
            return [self.collection[k] for k in self.collection.keys()]
        except AttributeError:
            return self.collection

    def items(self):
        try:
            return [(k, self.collection[k]) for k in self.collection.keys()]
        except AttributeError:
            return enumerate(self.collection)

    def render(self, fmt="{v}", sep=", "):
        """Convert the collection into a string

        fmt (str):
            fmt is a format string applied to each of the items in the
            collection where {k} is replaced with the key and {v} replaced with
            the value.
        sep (str):
            The string used to join the formatted items.

        Example:

            >>> from collection import Collection

            >>> dogs = Collection({'collie': 3, 'beagle':1, 'sheppard': 2})
            >>> print('dogs: {}.'.format(dogs.render('{k} ({v})', ', ')))
            dogs: collie (3), beagle (1), sheppard (2).

            >>> print('dogs: {}.'.format(dogs.render(sep=', ')))
            dogs: 3, 1, 2.

        """
        if not fmt:
            fmt = "{}"

        return sep.join(fmt.format(v, k=k, v=v) for k, v in self.items())

    def __format__(self, template):
        """Convert the collection into a string

        The template consists of two components separated by a vertical bar. The
        first component specifies the formatting from each item. The key and
        value are interpolated using {{k}} to represent the key and {{v}} to
        represent the value.  The second component is the separator. Thus:

            >>> dogs = Collection({'collie': 3, 'beagle':1, 'sheppard': 2})
            >>> print('dogs: {:{{k}} ({{v}})|, }.'.format(dogs))
            dogs: collie (3), beagle (1), sheppard (2).

        """
        if template:
            components = template.split(self.splitter)
            if len(components) == 2:
                fmt, sep = components
            else:
                fmt, sep = components[0], " "
        else:
            fmt, sep = self.fmt, self.sep
        if not fmt:
            fmt = "{}"

        if callable(fmt):
            return sep.join(fmt(k, v) for k, v in self.items())
        return sep.join(fmt.format(v, k=k, v=v) for k, v in self.items())

    def __contains__(self, item):
        return item in self.values()

    def __iter__(self):
        return iter(self.values())

    def __len__(self):
        return len(self.collection)

    def __getitem__(self, key):
        return self.collection[key]

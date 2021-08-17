# Collections
#
# Provides common interface for dictionaries and lists. If a string is passed
# in, it is split and then treated as a list. Optimized for convenience rather
# than for large collections.

# License {{{1
# Copyright (C) 2016-2021 Kenneth S. Kundert
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
__version__ = "0.5.0"
__released__ = "2021-01-27"


# Utilities {{{1
def split_lines(text, comment=None, strip=False, cull=False, sep=None):
    """Split lines

    Can be passed as a splitter to Collection. Takes a multi-line string,
    converts it to individual lines where comments are removed (if comment
    string is provided), each line is stripped (if strip is True), and empty
    lines are culled (if cull is True).  If sep is specified, the line is
    partitioned into a key and value (everything before sep is the key,
    everything after is value). In this case a dictionary is returned. Otherwise
    a list is returned.

    """
    lines = text.splitlines()
    if comment:
        lines = list(l.partition(comment)[0] for l in lines)
    if strip:
        lines = list(l.strip() for l in lines)
    if cull:
        lines = list(l for l in lines if l)
    if sep:
        pairs = dict(l.partition(sep)[::2] for l in lines)
        if strip:
            lines = {k.strip(): v.strip() for k, v in pairs.items()}
    return lines


# Collection {{{1
class Collection(object):
    fmt = '{v}'     # default value format
    sep = " "       # default separator
    splitter = "|"  # default format splitter (goes between fmt and sep in template)

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
            return list(self.collection.keys())
        except AttributeError:
            return list(range(len(self.collection)))

    def values(self):
        try:
            return [self.collection[k] for k in self.collection.keys()]
        except AttributeError:
            return list(self.collection)

    def items(self):
        try:
            return [(k, self.collection[k]) for k in self.collection.keys()]
        except AttributeError:
            return list(enumerate(self.collection))

    def render(self, fmt=None, sep=None):
        """Convert the collection into a string

        fmt (str):
            fmt is a format string applied to each of the items in the
            collection where {k} is replaced with the key and {v} replaced with
            the value.
        sep (str):
            The string used to join the formatted items.

        Example:

            >>> from collection import Collection

            >>> dogs = Collection({'collie': 3, 'beagle':1, 'shepherd': 2})
            >>> print('dogs: {}.'.format(dogs.render('{k} ({v})', ', ')))
            dogs: collie (3), beagle (1), shepherd (2).

            >>> print('dogs: {}.'.format(dogs.render(sep=', ')))
            dogs: 3, 1, 2.

        """
        if not fmt:
            fmt = self.fmt
        if not sep:
            sep = self.sep

        if callable(fmt):
            return sep.join(fmt(k, v) for k, v in self.items())
        return sep.join(fmt.format(v, k=k, v=v) for k, v in self.items())

    def __format__(self, template):
        """Convert the collection into a string

        The template consists of two components separated by a vertical bar. The
        first component specifies the formatting from each item. The key and
        value are interpolated using {{k}} to represent the key and {{v}} to
        represent the value.  The second component is the separator. Thus:

            >>> dogs = Collection({'collie': 3, 'beagle':1, 'shepherd': 2})
            >>> print('dogs: {:{{k}} ({{v}})|, }.'.format(dogs))
            dogs: collie (3), beagle (1), shepherd (2).

        """
        if template:
            components = template.split(self.splitter)
            if len(components) == 2:
                fmt, sep = components
            else:
                fmt, sep = components[0], " "
        else:
            fmt, sep = None, None
        if not fmt:
            fmt = self.fmt
        if not sep:
            sep = self.sep

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

    def __repr__(self):
        return f'{self.__class__.__name__}({self.collection!r})'

    def __str__(self):
        return str(self.collection)

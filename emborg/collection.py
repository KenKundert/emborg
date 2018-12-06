# Collections
#
# Provides common interface for dictionaries and lists. If a string is passed
# in, it is split and then treated as a list. Optimized for convenience rather
# than for large collections. Sorting versus the key is used to avoid randomness
# in the ordering of the dictionary-based collections.

# License {{{1
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
# along with this program.  If not, see http://www.gnu.org/licenses/.

# Imports {{{1
from inform import is_str, is_collection

# Collection {{{1
class Collection(object):
    def __init__(self, collection, splitter=None):
        if is_str(collection):
            self.collection = collection.split(splitter)
        elif is_collection(collection):
            self.collection = collection
        elif collection is None:
            self.collection = []
        else:
            # is scalar
            self.collection = {None: collection}

    def keys(self):
        try:
            return self.collection.keys()
        except AttributeError:
            return range(len(self.collection))

    def values(self):
        try:
            return [self.collection[k] for k in sorted(self.collection.keys())]
        except AttributeError:
            return self.collection

    def items(self):
        try:
            return [(k, self.collection[k]) for k in sorted(self.collection.keys())]
        except AttributeError:
            return enumerate(self.collection)

    def __contains__(self, item):
        return item in self.values()

    def __iter__(self):
        return iter(self.values())

    def __len__(self):
        return len(self.collection)

    def __getitem__(self, key):
        return self.collection[key]

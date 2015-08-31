"""
Parse raw* LoC Classification files.

Actually: copies of the DOC files that have been converted to text
files. The PDF versions are wonky, and python doesn't have a way to
easily read DOC files (just DOCX).

NOTE: You are going to get burned if your DOC->TXT conversion does not
preserve record-seporators.
"""
from __future__ import print_function

from argparse import ArgumentParser
from collections import defaultdict
from itertools import chain
import json
import logging
from pathlib import Path
import re

from six import text_type


INPUT_DIRECTORY = Path('files') / 'raw' / 'txt'
OUTPUT_DIRECTORY = Path('files') / 'formatted'

RE_CLASS = re.compile(r'^CLASS ([A-Z])(?:-([A-Z]))? - (.*?)$')

# Class headers will exist if the class was a range
# Subclasses is plural in K, singular everywhere
RE_CLASS_HEADER_OR_SUBCLASS = re.compile(
    r'^(?:'
    r'(?:Class [A-Z])|'
    r'(?:Subclass(?:es)? [A-Z]+(?:-[A-Z]+)?(?:\s+\(obsolete\))?)'
    r')$'
)

# Topic formatting is a nightmare. Topics may be given with no topic
# numbers (in which case I'm assuming it spans the entire subclass), a
# single value may be given, or a range may be given. Topics may be
# surrounded in parentheses (which doesn't seem to signify anything).
# Topics numbers may have narrowing values (which may contain a number,
# a letter, or a letter followed by a number). In one case (which I'm
# skipping, because really Loc? Really?), the alphabetic narrowing is
# given afterward.
# There may be a space after the subclass. This is difficult to
# distinguish from no range given). The class may be repeated in the
# range.
RE_TOPIC = re.compile(
    # g[1] = classification
    # g[2] = subclassification
    r'^\(?([A-Z])([A-Z]{0,2}) ?'

    # g[3] = min topic
    # g[4] = min alphabetic narrowing
    # g[5] = min numeric narrowing
    r'\(?(\d+)(?:\.([A-Z]?)(\d+))?\)?'

    # g[6] = max topic
    # g[7] = max alphabetic narrowing
    # g[8] = max numeric narrowing
    r'(?:(?:-\1?\(?(\d*(?: \d+)?)(?:\.?([A-Z]?)(\d*))?\)?)|(?:\.A-Z))?\)?'

    # g[9] = description
    r'\s+(.*?)\s*$'
)

RE_TOPIC_RANGE = re.compile(
    r'^([A-Z])([A-Z]?)([A-Z])(?:-\1\2([A-Z]))?\s+(.*?)$'
)

RE_MISSPARSED = re.compile(r'^\s*[a-z]+\d+', re.IGNORECASE)

MIN_TOPIC = 1
MAX_TOPIC = 9999

RECORD_SEPARATOR = chr(30)


class State(object):
    """
    Parsing state
    """
    def __init__(self):
        self.classes = {}

        self.classification = None
        self.subclasses = None
        self.min = None
        self.max = None
        self.description = None

    def add_class(self, symbol, description):
        """
        Add a class to the collection of classes
        """
        self.classes[symbol] = {
            u'description': description,
            u'subclasses': defaultdict(list)
        }

    def clear(self):
        """
        Clear any cached topics (adding them to topics as necessary)
        """
        if self.min:  # topic cached
            for subclass in self.subclasses:
                self.classes[self.classification][u'subclasses'][
                    subclass
                ].append(
                    {
                        u'min_topic': self.min[0],
                        u'min_alphabetic': self.min[1],
                        u'min_numeric': self.min[2],
                        u'max_topic': self.max[0],
                        u'max_alphabetic': self.max[1],
                        u'max_numeric': self.max[2],
                        u'description': self.description,
                    }
                )

            self.classification = None
            self.subclasses = None
            self.min = None
            self.max = None
            self.description = None

    def append_description(self, text):
        """
        Append text to the current description
        """
        self.description = u'{} {}'.format(self.description, text)


def parse(directory=INPUT_DIRECTORY):
    """
    Parse raw LoC Classification files

    directory: The Path to the directory containing raw files.
    """
    state = State()

    for filepath in directory.iterdir():
        if filepath.suffix == u'.txt':
            parse_file(filepath, state)

    return state.classes


def parse_file(filepath, state=None):
    """
    Parse a raw LoC Classification file.

    filepath: The Path to the classification file.
    """
    if state is None:
        state = State

    with filepath.open() as fileobj:
        iterator = file_iterator(fileobj)

        # Header
        line = next(iterator)

        if line != u"LIBRARY OF CONGRESS CLASSIFICATION OUTLINE":
            raise ValueError(line)

        # Class
        line = next(iterator)

        match = RE_CLASS.search(line)

        if not match:
            raise ValueError(line)

        start, stop, description = match.groups()

        # class description may be multiline, read into the next line
        line = next(iterator)

        if RE_CLASS_HEADER_OR_SUBCLASS.search(line):
            iterator = chain((line,), iterator)  # oops, not multiline
        else:
            description = u'  '.join((description, line.strip()))

        for num in range(ord(start), ord(stop or start) + 1):
            state.add_class(chr(num), description)

        for line in iterator:
            if RE_CLASS_HEADER_OR_SUBCLASS.search(line):
                state.clear()

                continue

            match = RE_TOPIC.search(line)

            if match:
                state.clear()

                (
                    classification,
                    subclassification,
                    min_topic,
                    min_alphabetic_narrowing,
                    min_numeric_narrowing,
                    max_topic,
                    max_alphabetic_narrowing,
                    max_numeric_narrowing,
                    description
                ) = match.groups()

                # Special case for typo in source file:
                if description == u'Music study abroad':
                    subclassification = u'T'

                if min_numeric_narrowing:
                    min_numeric_narrowing = int(min_numeric_narrowing)

                min_topic = int(min_topic)

                if max_topic:
                    # The space thing is because of a typo in the raw
                    # source :/
                    max_topic = int(max_topic.replace(u' ', u''))

                    if max_numeric_narrowing:
                        max_numeric_narrowing = int(max_numeric_narrowing)
                else:
                    max_topic = min_topic

                    if not (max_alphabetic_narrowing or
                            max_numeric_narrowing):
                        max_alphabetic_narrowing = min_alphabetic_narrowing
                        max_numeric_narrowing = min_numeric_narrowing

                state.classification = classification
                state.subclasses = [subclassification]
                state.min = (
                    min_topic, min_alphabetic_narrowing, min_numeric_narrowing
                )
                state.max = (
                    max_topic, max_alphabetic_narrowing, max_numeric_narrowing
                )
                state.description = description

                continue

            match = RE_TOPIC_RANGE.search(line)

            if match:
                # special case for some absolute bullshit
                if line.startswith(u'DG') and line.endswith(u'City'):
                    state.append_description(u'City')

                    continue

                state.clear()

                (
                    classification,
                    common,
                    start,
                    stop,
                    description,
                ) = match.groups()

                state.classification = classification
                state.subclasses = [
                    u''.join((common, chr(num)))
                    for num in range(ord(start), ord(stop or start) + 1)
                ]
                state.min = (MIN_TOPIC, None, None)
                state.max = (MAX_TOPIC, None, None)
                state.description = description

                continue

            if RE_MISSPARSED.search(line):
                raise ValueError(line)

            if state.description:  # line is additional description
                state.append_description(line.strip())
            else:
                logging.warning('Skipping line: %s', line)

    state.clear()

    return state


def file_iterator(fileobj):
    """
    Iterate over non-blank lines in a file
    """
    for line in fileobj:
        # Sometimes (read: inconsistently within files), LoC uses
        # Record separators instead of hyphens. Even in the best of
        # times, invisible characters in word documents would be
        # ill-advised. In this case, it seems especially ham-fisted,
        # as this replace-hyphens-with-separators mentality extended
        # into hyphenated words in topic descriptions.
        line = line.rstrip().replace(RECORD_SEPARATOR, '-')

        if line:
            # HORRIBLE special case, apparently they forgot a newline
            # once
            if u'  KB3123' in line:
                first, second = line.split(u'  KB3123')

                yield first
                yield u''.join((u'KB3123', second))
            else:
                yield line


def main():
    """
    Run parse from the command line
    """
    parser = ArgumentParser(description="Parse LoC Classification files")
    parser.add_argument('--directory', '-d', default=INPUT_DIRECTORY,
                        type=Path, help="Directory containing raw files.")

    args = parser.parse_args()

    classes = parse(args.directory)

    with (OUTPUT_DIRECTORY / 'lcc.json').open('w') as fileobj:
        # why not json.dump? this is a workaround to get things working
        # on python 2 and 3. TODO: work out why dump isn't working
        fileobj.write(
            json.dumps(classes, indent=2, sort_keys=True, ensure_ascii=False)
        )


if __name__ == '__main__':
    main()

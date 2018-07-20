#!/usr/bin/env python3

# Remove portions of text from annotated files.

# Note: not comprehensively tested, use with caution.

from __future__ import with_statement

import sys
import re

try:
    import argparse
except ImportError:
    from os.path import basename
    from sys import path as sys_path
    # We are most likely on an old Python and need to use our internal version
    sys_path.append(join_path(basename(__file__), '../server/lib'))
    import argparse


class ArgumentError(Exception):
    def __init__(self, s):
        self.errstr = s

    def __str__(self):
        return 'Argument error: %s' % (self.errstr)

def argparser():
    ap=argparse.ArgumentParser(description="Remove portions of text from annotated files.")
    ap.add_argument("--complement", default=False, action="store_true",
                    help="Complement the selected spans of text")
    ap.add_argument("character", metavar="c",
                    help="Split text and annotations on the given character")
    ap.add_argument("file", metavar="FILE", nargs=1, 
                    help="Annotation file")
    return ap


class Annotation(object):
    def __init__(self, id_, type_):
        self.id_ = id_
        self.type_ = type_

    def in_range(self, rs, re):
        # assume not text-bound: in any range
        return True

    def remap(self, _):
        # assume not text-bound: no-op
        pass


class Textbound(Annotation):
    def __init__(self, id_, type_, offsets, text):
        Annotation.__init__(self, id_, type_)
        self.text = text

        self.offsets = []
        if ';' in offsets:
            # not tested w/discont, so better not to try
            raise NotImplementedError('Discontinuous annotations not supported')
        assert len(offsets) == 2, "Data format error"
        self.offsets.append((int(offsets[0]), int(offsets[1])))

    def in_range(self, rs, re):
        for start, end in self.offsets:
            if not (start >= rs and start < re and end >= rs and end < re):
                return False
        return True

    def remap(self, offset):
        remapped = []
        for start, end in self.offsets:
            remapped.append((start-offset, end-offset))
        self.offsets = remapped

    def __str__(self):
        return "%s\t%s %s\t%s" % (self.id_, self.type_, 
                                  ';'.join(['%d %d' % (s, e)
                                            for s, e in self.offsets]),
                                  self.text)


class ArgAnnotation(Annotation):
    def __init__(self, id_, type_, args):
        Annotation.__init__(self, id_, type_)
        self.args = args
        self.textbounds = set()


class Relation(ArgAnnotation):
    def __init__(self, id_, type_, args):
        ArgAnnotation.__init__(self, id_, type_, args)
        for arg in args:
            argtype, argval = arg.split(':')
            if argtype in ['ARG1','ARG2']:
                self.textbounds.add(argval)

    def __str__(self):
        return "%s\t%s %s" % (self.id_, self.type_, ' '.join(self.args))


class Event(ArgAnnotation):
    def __init__(self, id_, type_, trigger, args):
        ArgAnnotation.__init__(self, id_, type_, args)
        self.trigger = trigger
        for arg in args:
            _, argval = arg.split(':')
            self.textbounds.add(argval)

    def __str__(self):
        return "%s\t%s:%s %s" % (self.id_, self.type_, self.trigger, 
                                 ' '.join(self.args))


class Attribute(Annotation):
    def __init__(self, id_, type_, target, value):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.value = value

    def __str__(self):
        return "%s\t%s %s%s" % (self.id_, self.type_, self.target, 
                                '' if self.value is None else ' '+self.value)

class Normalization(Annotation):
    def __init__(self, id_, type_, target, ref, reftext):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.ref = ref
        self.reftext = reftext

    def __str__(self):
        return "%s\t%s %s %s\t%s" % (self.id_, self.type_, self.target,
                                     self.ref, self.reftext)


class Equiv(Annotation):
    def __init__(self, id_, type_, targets):
        Annotation.__init__(self, id_, type_)
        self.targets = targets

    def __str__(self):
        return "%s\t%s %s" % (self.id_, self.type_, ' '.join(self.targets))


class Note(Annotation):
    def __init__(self, id_, type_, target, text):
        Annotation.__init__(self, id_, type_)
        self.target = target
        self.text = text

    def __str__(self):
        return "%s\t%s %s\t%s" % (self.id_, self.type_, self.target, self.text)


def parse_textbound(fields):
    id_, type_offsets, text = fields
    type_offsets = type_offsets.split(' ')
    type_, offsets = type_offsets[0], type_offsets[1:]
    return Textbound(id_, type_, offsets, text)


def parse_relation(fields):
    # allow a variant where the two initial TAB-separated fields are
    # followed by an extra tab
    if len(fields) == 3 and not fields[2]:
        fields = fields[:2]
    id_, type_args = fields
    type_args = type_args.split(' ')
    type_, args = type_args[0], type_args[1:]
    return Relation(id_, type_, args)


def parse_event(fields):
    id_, type_trigger_args = fields
    type_trigger_args = type_trigger_args.split(' ')
    type_trigger, args = type_trigger_args[0], type_trigger_args[1:]
    type_, trigger = type_trigger.split(':')
    return Event(id_, type_, trigger, args)


def parse_attribute(fields):
    id_, type_target_value = fields
    type_target_value = type_target_value.split(' ')
    if len(type_target_value) == 3:
        type_, target, value = type_target_value
    else:
        type_, target = type_target_value
        value = None
    return Attribute(id_, type_, target, value)


def parse_normalization(fields):
    id_, type_target_ref, reftext = fields
    type_, target, ref = type_target_ref.split(' ')
    return Normalization(id_, type_, target, ref, reftext)


def parse_note(fields):
    id_, type_target, text = fields
    type_, target = type_target.split(' ')
    return Note(id_, type_, target, text)


def parse_equiv(fields):
    id_, type_targets = fields
    type_targets = type_targets.split(' ')
    type_, targets = type_targets[0], type_targets[1:]
    return Equiv(id_, type_, targets)


parse_func = {
    'T': parse_textbound,
    'R': parse_relation,
    'E': parse_event,
    'N': parse_normalization,
    'M': parse_attribute,
    'A': parse_attribute,
    '#': parse_note,
    '*': parse_equiv,
    }


def parse(l, ln):
    assert len(l) and l[0] in parse_func, "Error on line %d: %s" % (ln, l)
    try:
        return parse_func[l[0]](l.split('\t'))
    except Exception:
        assert False, "Error on line %d: %s" % (ln, l)


def process(fn, selection, options):
    with open('{}.ann'.format(fn), "rU") as f:
        lines = [l.rstrip('\n') for l in f.readlines()]

        annotations = []
        for i, l in enumerate(lines):
            annotation = parse(l, i+1)
            #sys.stderr.write('annotation: {}\n'.format(annotation))
            annotations.append(annotation)

    i = 0
    for (start,end) in selection.ranges:
        sys.stderr.write('Range is {}-{}\n'.format(start,end))
        i += 1
        fn = options.file[0]
        with open('{}.{}.ann'.format(fn,i), "w", encoding="utf-8") as f:
            kept = set()
            for a in annotations:
                if not a.in_range(start,end):
                    pass
                    # deletes TODO
                    #raise NotImplementedError('Deletion of annotations TODO {}, {}'.format(a,selection))
                    #sys.stderr.write('Deletion of annotations TODO {}, {}\n'.format(a,selection))
                else:
                    a.remap(start)
                    if a.id_[0] == 'T':
                        sys.stderr.write('Adding {} to kept\n'.format(a.id_))
                        kept.add(a.id_)
                        print(a, file=f)
                    elif a.id_[0] in ['R','E']:
                        sys.stderr.write('Textbounds: {}\n'.format(a.textbounds))
                        if not bool(a.textbounds - kept):
                            print(a, file=f)


    #for a in annotations:
        #print a

class Selection(object):
    def __init__(self, options):
        self.complement = options.complement
        self.ranges = []

        fn = options.file[0]
        with open('{}.txt'.format(fn), "r", encoding="utf-8") as f:
            content = f.read()
            positions = [i for i, ltr in enumerate(content) if ltr == options.character]
            previous = 0
            for position in positions:
                self.ranges.append((previous,position))
                previous = position+2
            self.ranges.append((previous,len(content)))
            sys.stderr.write('ranges={}\n'.format(self.ranges))
            i = 0
            for (start,end) in self.ranges:
                i += 1
                with open('{}.{}.txt'.format(fn,i), "w", encoding="utf-8") as subf:
                    subf.write(content[start:end])

        self.ranges.sort()

        # initialize offset map up to end of given ranges
        self.offset_map = {}
        o, m = 0, 0
        if not self.complement:
            for start, end in self.ranges:
                while o < start:
                    self.offset_map[o] = None
                    o += 1
                while o < end:
                    self.offset_map[o] = m
                    o += 1
                    m += 1
        else:
            for start, end in self.ranges:
                while o < start:
                    self.offset_map[o] = m
                    o += 1
                    m += 1
                while o < end:
                    self.offset_map[o] = None
                    o += 1

        self.max_offset = o
        self.max_mapped = m

        # debugging
        # print >> sys.stderr, self.offset_map

    def __str__(self):
        return '({} - {} - {} - {} - {})'.format(self.complement,
                                       self.ranges,
                                       self.offset_map,
                                       self.max_offset,
                                       self.max_mapped)

    def in_range(self, start, end):
        for rs, re in self.ranges:
            if start >= rs and start < re:
                if end >= rs and end < re:
                    return not self.complement
                else:
                    raise NotImplementedError('Annotations partially included in range not supported')
        return self.complement

    def remap_single(self, offset):
        assert offset >= 0, "INTERNAL ERROR"
        if offset < self.max_offset:
            assert offset in self.offset_map, "INTERNAL ERROR"
            o = self.offset_map[offset]
            assert o is not None, "Error: remap for excluded offset %d" % offset
            return o
        else:
            assert self.complement, "Error: remap for excluded offset %d" % offset
            # all after max_offset included, so 1-to-1 mapping past that
            return self.max_mapped + (offset-self.max_offset)

    def remap(self, start, end):
        # end-exclusive to end-inclusive
        end -= 1

        start, end = self.remap_single(start), self.remap_single(end)

        # end-inclusive to end-exclusive
        end += 1

        return (start, end)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    arg = argparser().parse_args(argv[1:])

    try:
        selection = Selection(arg)
    except Exception as e:
        print >> sys.stderr, e
        argparser().print_help()
        return 1        

    fn = arg.file[0]
    process(fn, selection, arg)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

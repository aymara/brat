#!/usr/bin/env python3

"""
Align two IOBES files.

Read both files line by line. 
If two lines begin/end are equal, output the merging of both
If they differ advance to next line in file which begin is before the other 
one and print a warning with both lines
"""

import re
import sys

options = None

EMPTY_LINE_RE = re.compile(r'^\s*$')
IOBES_LINE_RE = re.compile(r'^\S+\t\d+\t\d+\t\S+$')


def read_line(f):
    """Return the first IOBES line in opened file f"""

    while True:
        line = f.readline()
        if not line:
            return None
        if IOBES_LINE_RE.match(line):
            return line.rstrip()



def argparser():
    import argparse
    
    ap=argparse.ArgumentParser(description='Align two IOB files')
    ap.add_argument('-p', '--positions', default=False, action="store_true", 
                    help="Alternate output format with positions: IOBES1<tab>IOBES2<tab>begin<tab>end<tab>token")
    ap.add_argument('files', metavar=['IOBES1', 'IOBES2'], nargs=2, 
                    help='IOB files to align')
    return ap


def process_files(files):
    global options

    with open(files[0], 'r') as  leftfile:
        with open(files[1], 'r') as rightfile:
            leftline = read_line(leftfile)
            rightline = read_line(rightfile)
            while leftline and rightline:
                try:
                    (liobes, lstart, lend, ltok) = leftline.split('\t')
                    (riobes, rstart, rend, rtok) = rightline.split('\t')
                    if lstart == rstart and lend == rend:
                        if options.positions:
                            print('{}\t{}\t{}\t{}\t{}'.format(liobes,riobes,lstart,lend,ltok))
                        else:
                            print('{} {} {}'.format(ltok.replace(' ', '_'),liobes,riobes))
                        leftline = read_line(leftfile)
                        rightline = read_line(rightfile)
                    elif lstart == lend:
                        sys.stderr.write('Same position but different length: {}/{}. Advance both.\n'.format(leftline,rightline))
                        leftline = read_line(leftfile)
                        rightline = read_line(rightfile)
                    elif lstart < lend:
                        sys.stderr.write('Left is before right: {}/{}. Advance left.\n'.format(leftline,rightline))
                        leftline = read_line(leftfile)
                    else:
                        sys.stderr.write('Right is before left: {}/{}. Advance right.\n'.format(leftline,rightline))
                        rightline = read_line(rightfile)
                except ValueError as e:
                    sys.stderr.write('Error spliting one of lines:\n{}\n{}'.format(leftline.split('\t'),rightline.split('\t')))
                    raise


def main(argv=None):
    if argv is None:
        argv = sys.argv

    global options
    options = argparser().parse_args(argv[1:])

    process_files(options.files)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

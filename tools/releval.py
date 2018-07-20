#!/usr/bin/env python3

"""
Evaluate relations
"""

from __future__ import with_statement

import sys
import re
import os

from collections import namedtuple
from os import path
from subprocess import Popen, PIPE

# assume script in brat tools/ directory, extend path to find sentencesplit.py
sys.path.append(os.path.join(os.path.dirname(__file__), '../server/src'))
sys.path.append('.')
from sentencesplit import sentencebreaks_to_newlines

options = None

EMPTY_LINE_RE = re.compile(r'^\s*$')
CONLL_LINE_RE = re.compile(r'^\S+\t\d+\t\d+.')

class FormatError(Exception):
    pass

def argparser():
    import argparse
    
    ap=argparse.ArgumentParser(description='Evaluate relations versus a reference, both in Brat ann format')
    ap.add_argument('files', metavar=['TST','REF'], nargs=2, 
                    help='Test and reference Brat .ann files')
    return ap

def process_file(filename):
  relations = set()
  types = set()
  textbounds = {}
  with open(filename, 'r') as f:
      for line in f:
          line = line.rstrip()
          if line:
              if line[0] == 'T':
                  #T117	COUNTRY 84 90	France
                  tid, features, _ = line.split('\t')
                  ttype, _, tranges = features.partition(' ')
                  tranges = tranges.split(';')
                  if len(tranges) > 1:
                      sys.stderr.write('Warn: discontinuous ranges are not supported while parsing {}\n'.format(line))
                  start, end = tranges[0].split()
                  start, end = int(start), int(end)
                  textbounds[tid] = (start, end, ttype, line)
              elif line[0] == 'R':
                  #R11	birth_date ARG1:T75 ARG2:T176
                  rid, features = line.split('\t')
                  rtype, arg1, arg2 = features.split(' ')
                  types.add(rtype)
                  _, arg1 = arg1.split(':')
                  _, arg2 = arg2.split(':')
                  tb1 = textbounds[arg1]
                  tb2 = textbounds[arg2]
                  relations.add( (rtype, 
                                  tb1[0], tb1[1], tb1[2], 
                                  tb2[0], tb2[1], tb2[2]))
  return (relations, types)


def process_files(testfile,reffile):
    testrelations, testreltypes = process_file(testfile)
    refrelations, refreltypes = process_file(reffile)

    for reltype in refreltypes:
        machingtestrelations = set(rel for rel in testrelations if rel[0] == reltype)
        machingrefrelations = set(rel for rel in refrelations if rel[0] == reltype)
        ok = len(machingtestrelations & machingrefrelations)
        nbtest = len(machingtestrelations)
        nbref = len(machingrefrelations)
        
        P = ok/nbtest if nbtest else float('nan')
        R = ok/nbref if nbref else float('nan')
        F1 = 2 * P * R/(P + R) if P+R > 0 else float('nan')
        
        print('{}:\tP = {:2.2f}; R= {:2.2f} ; F1 = {:2.2f}'.format(reltype,P*100,R*100,F1*100))

    ok = len(testrelations & refrelations)
    nbtest = len(testrelations)
    nbref = len(refrelations)
    
    P = ok/nbtest if nbtest else float('nan')
    R = ok/nbref if nbref else float('nan')
    F1 = 2 * P * R/(P + R) if P+R > 0 else float('nan')
    
    print('ALL:\t\tP = {:2.2f}; R= {:2.2f} ; F1 = {:2.2f}'.format(P*100,R*100,F1*100))
    print


def main(argv=None):
    if argv is None:
        argv = sys.argv

    global options
    options = argparser().parse_args(argv[1:])

    process_files(options.files[0],options.files[1])

if __name__ == "__main__":
    sys.exit(main(sys.argv))

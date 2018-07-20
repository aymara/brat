#!/bin/bash

set -o errexit

TOOLS="/home/gael/Logiciels/brat/tools"
PREFIX="Piste_Audit_CADIF_TEST_1.txt.shuf.test"

# Rebuild full text
ls -1v ${PREFIX}.*.txt | xargs cat > ${PREFIX}.txt
# Group reference annotations in one brat ann file
ls -1v ${PREFIX}.?.ann ${PREFIX}.??.ann | xargs python3 ${TOOLS}/catann.py > ${PREFIX}.ann
# Generate a conll iob file from reference text and reference annotations
python3 ${TOOLS}/anntoconll.py -l fre ${PREFIX}.txt


# Analyze all segments with LIMA
ls -1v ${PREFIX}.*.txt | xargs analyzeText -l fre
# Group LIMA generated annotations in one brat ann file
ls -1v ${PREFIX}.*.txt.ann | xargs python3 ${TOOLS}/catann.py -s > ${PREFIX}.lima.ann
# Generate a conll iob file from reference text and LIMA generated annotations
python3 ${TOOLS}/anntoconll.py  -l fre ${PREFIX}.txt -f ${PREFIX}.lima.ann -o lima.conll

# Align reference and LIMA generated iob files
python3 ${TOOLS}/aligniobes.py ${PREFIX}.conll ${PREFIX}.lima.conll > ${PREFIX}.iob


echo "Entities:"
echo
# Evaluate LIMA generated entities annotations with respect to reference
python3 ${TOOLS}/conlleval.py ${PREFIX}.iob
echo
echo

echo "Relations:"
echo
# Evaluate LIMA generated relations annotations with respect to reference
python3 ${TOOLS}/releval.py ${PREFIX}.lima.ann ${PREFIX}.ann


echo
echo

echo "Events:"
echo
# Evaluate LIMA generated relations annotations with respect to reference
python3 ${TOOLS}/eveval.py ${PREFIX}.lima.ann ${PREFIX}.ann

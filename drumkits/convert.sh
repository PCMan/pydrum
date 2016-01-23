#!/bin/bash
SAVEIFS=$IFS
IFS=$(echo -en "\n\b\0")
for f in `find . -name "*.flac" -print`
do
ogg=`echo "$f" | sed -e s/flac/ogg/`
echo "$f to $ogg"
ffmpeg -y -i $f $ogg
rm $f
done

for f in `find . -name '*.wav' -print`
do
ogg=`echo "$f" | sed -e s/wav/ogg/`
echo "$f to $ogg"
ffmpeg -y -i $f $ogg
rm $f
done


for f in `find . -name '*.xml' -print`
do
sed -i -e 's/\.\(wav\|flac\)/\.ogg/g' $f
done


IFS=$SAVEIFS

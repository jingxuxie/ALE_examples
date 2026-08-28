#!/bin/bash
FILE=$1
COUNTER=0
POSITION=-1
ARR[0]=0
for i in $(cat $FILE);
do
	let POSITION++
	if [ "$i" != "0.0000000000000000e+00" ];
	then
		ARR[$COUNTER]=$POSITION
		let COUNTER++
	fi
	
done
echo Non-zero elements $COUNTER
echo "Elements located at:"

for item in ${ARR[*]}
do
    printf "%s\n" $item
done

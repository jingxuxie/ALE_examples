#!/bin/bash
OLDPWD=$(pwd)
for i in $(cat ./ogg.txt | grep wfc); 
do 
	echo $(if [[ $(basename $(dirname $i))=='images' ]]; 
		then 
			cd $(dirname $i)/../bin;
			TITLE=$(head -n 1 run_params.conf)
			SUMMARY=$(head -n 20 ../result.log)
			cd -
			google youtube post --category Tech $i --title "$TITLE" --summary "$SUMMARY" --access=unlisted $i
		fi);
done


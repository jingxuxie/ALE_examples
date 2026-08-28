#!/bin/bash
for i in $(cat manifest.txt); do 
    echo 'Working on $i'; 
    $HOME/builds/bin/pigz -p 24 -r $i; 
done

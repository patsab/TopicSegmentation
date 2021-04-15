#!/bin/bash

#First: calculate LDA on lectures (IMIP and PA)
for folder in ./gibbslda_training_documents/*; do
    GibbsLDA++-0.2/src/lda -est  -niters 2000 -savestep 2001 -ntopics 8 -twords 10 -dfile $(echo "$folder")/training_data.txt;
done

#calculate TopicTiling
#change directory to execute topictiling jar
cd topictiling_v1.0;
#2 sperate for loops are used, since both courses use a different LDA model.
for folder in ../topictiling_documents/IMIP/*; do
    sh topictiling.sh  -ri 5 -w 5 -tmn "model-final" -tmd ../gibbslda_training_documents/IMIP -fp 'tokens.txt' -fd $(echo "$folder") -out $(echo "$folder")/topictiling.txt;
done
for folder in ../topictiling_documents/PA/*; do
    sh topictiling.sh  -ri 5 -w 5 -tmn "model-final" -tmd ../gibbslda_training_documents/PA -fp 'tokens.txt' -fd $(echo "$folder") -out $(echo "$folder")/topictiling.txt;
done

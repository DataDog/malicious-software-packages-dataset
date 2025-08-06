#!/bin/bash

if [ $# -ne 2 ]; then
    echo "Usage: $0 samples-directory target-directory"
    exit 1
fi

samples=$1
target=$2
mkdir -p $target
find $samples -type f -name '*.zip' | while read sample; do
  unzipDir=$target/$(basename $sample .zip)
  mkdir -p $unzipDir
  unzip -o -P infected $sample -d $unzipDir >/dev/null 2>&1 
done

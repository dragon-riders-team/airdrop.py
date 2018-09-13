#!/bin/bash

echo "["
cat $1 \
	| sed 's/,//g' \
	| sed 's/^R.*;0\.0000.*//' \
	| sed '/^\s*$/d' \
	| perl -lpe 's/(R[\d|\w]+);([\d|\.|\,]+)/  {\n    "addr": "$1",\n    "amount": $2\n  },/' \
	| sed '$ s/.$//'
echo "]"

exit


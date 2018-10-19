#!/bin/bash

addr_array="["
addr_array+=$(cat $1 \
	| sed 's/,//g' \
	| sed 's/^R.*;0\.0000.*//' \
	| sed '/^\s*$/d' \
	| perl -lpe 's/^(R[\d|\w]+);([\d|\,]+(\.\d{4})?)(\d+)?/  {\n    "addr": "$1",\n    "amount": $2\n  },/' \
	| sed '$ s/.$//')
addr_array+="]"

epoch=`date +%s`
output="{\"start_time\": $epoch, \"addresses\": "
output+=$addr_array
output+=',
  "total": 1,
  "average": 1,
  "utxos": 1,
  "total_addresses": 1,
  "ignored_addresses": 0,
  "start_height": 1,
  "ending_height": 1,
  "end_time": 1
}'
echo $output | jq '.'

exit

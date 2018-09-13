#!/usr/bin/env python3
import json
import sys

string = ''
for line in sys.stdin:
    string += line.rstrip()

json_data = json.loads(string)

data_dict = {}
for i in json_data:
    amount = i['amount']
    try:
        amount += data_dict[i['addr']]
        data_dict[i['addr']] = round(amount, 4)
    except:
        data_dict[i['addr']] = amount

new_json_data = []
for key in data_dict.keys():
    new_json_data.append({"addr": key, "amount": data_dict[key]})

new_json = json.dumps(new_json_data)
print(new_json)


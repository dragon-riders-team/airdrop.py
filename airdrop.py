#!/usr/bin/env python3
import sys
import json
import sqlite3
import os.path
import string
import requests


# define function that posts json data to daemons
def post_rpc(url, payload, auth=None):
    try:
        r = requests.post(url, data=json.dumps(payload), auth=auth)
        return(json.loads(r.text))
    except Exception as e:
        raise Exception("Couldn't connect to " + url, e)


def select_all():
    db_query = ("SELECT * FROM addresses;")
    return(db_cursor.execute(db_query).fetchall())


def send_coins(group):
    # convert array to dictionary
    group_array = group
    group_dict = {}
    for e in group_array:
        address = e[0]
        amount = e[1]
        # but first check if we already sent coins to this address
        if issent(address):
            print(
                "Address already processed in a previous session:", address,
                "Skipping...")
        else:
            group_dict[address] = amount
    # abort if everything sent in the past for these addresses
    if not group_dict:
        return
    # define payload for rpc call
    params = ['', group_dict]
    payload = {
        "method": "sendmany",
        "params": params}
    try:
        # make rpc call, send the coins
        rpc_output = post_rpc(daemon_url, payload)
        if rpc_output['result']:
            save_tx(group_dict, rpc_output['result'])
        elif rpc_output['error']:
            raise Exception(rpc_output['error']['message'])
    except Exception as e:
        print("ERROR - Couldn't send coins with payload:\n ", payload)
        print(" ", e)


# function to save transactions to the database
def save_tx(group_dict, tx):
    print("Transaction ID:", tx)
    for a in group_dict.keys():
        db_cursor.execute(
            """UPDATE addresses SET txid = ?, issent = 1 WHERE addr = ?;""",
            (tx, a))
        # yeah, let's make some useful prints in the process
        print(
            "  Address:", a, "Sent:", group_dict[a])
    try:
        db.commit()
    except Exception as e:
        print("  ERROR - Couldn't save transaction:", e)


# check on database if this address was previously processed
def issent(address):
    issent = False
    db_query = 'SELECT issent FROM addresses WHERE addr = "' + address + '";'
    db_cursor.execute(db_query)
    result = db_cursor.fetchone()[0]
    try:
        if result == 1:
            issent = True
    except:
        pass
    return(issent)


# we make sure that multiple entries for the same address
# are summed and made one
def one_entry_per_addr(addresses_data):
    data_dict = {}
    for i in addresses_data:
        amount = i['amount']
        try:
            amount += data_dict[i['addr']]
            data_dict[i['addr']] = round(amount, 4)
        except:
            data_dict[i['addr']] = amount
    new_addresses_data = []
    for key in data_dict.keys():
        new_addresses_data.append({
            "addr": key,
            "amount": data_dict[key]
        })
    new_json = json.dumps(new_addresses_data)
    return(new_json)


# take and process arguments
try:
    sys.argv[1]
except:
    # give hints about usage
    print("You need to specify at least one argument.")
    print(
        "\nUsage (example):\n" +
        "    " + sys.argv[0] + " import COIN_snapshot.json\n" +
        "or:\n" +
        "    " + sys.argv[0] + " <snapshot_timestamp>\n" +
        "(The snapshot name is its creation timestamp.)\n")
    sys.exit(1)
if sys.argv[1] == 'import':
    # we're in import mode, try to read and import data from json file
    try:
        file = sys.argv[2]
        print('Trying to import snapshot file: "' + file + '"...')
        # read from json file
        with open(file) as json_file:
            try:
                # store some data that might be useful
                json_data = json.load(json_file)
                # consolidate multiple entries per address into one per address
                addresses_raw = json_data['addresses']
                addresses = one_entry_per_addr(addresses_raw)
                start_time = json_data['start_time']
                end_time = json_data['end_time']
                start_height = json_data['start_height']
                ending_height = json_data['ending_height']
                # define database name based on snapshot timestamp
                database_name = str(start_time) + '.db'
            except Exception as e:
                print("Couldn't read JSON data from file:", e)
                sys.exit(1)
        # put the data into the database
        try:
            print("Snapshot name: " + str(start_time))
            try:
                # initialize database
                db = sqlite3.connect(database_name)
                db_cursor = db.cursor()
            except Exception as e:
                print("Couldn't initialize database:", e)
                sys.exit(1)
            # create the main table if it does not exist
            createdb_query = (
                "CREATE TABLE IF NOT EXISTS addresses " +
                "(addr text primary key," +
                "amount float," +
                "issent boolean," +
                "txid text)"
            )
            try:
                db.execute(createdb_query)
            except Exception as e:
                print("Couldn't create database: ", e)
                sys.exit(1)
            addresses_tuples = [
                (i['addr'], float(i['amount'])) for i in addresses
            ]
            # import the data, from memory to the database
            db_cursor.executemany(
                "INSERT OR IGNORE INTO addresses " +
                "(addr, amount) VALUES (?, ?);",
                addresses_tuples)
            db.commit()
            # so far so good
            print("JSON data imported successfully.")
        except Exception as e:
            print("Couldn't import data into the database: ", e)
            sys.exit(1)
        finally:
            db.close()
    except:
        print("You need to specify a JSON file to import.")
        sys.exit()
elif len(sys.argv) == 2:
    # we're on database only mode
    snapshot_name = str(sys.argv[1])
    # just in case user confused database name with snapshot name
    snapshot_name = snapshot_name.rstrip('.db')
    # database name is just the snapshot name plus extension
    database_name = snapshot_name + '.db'
    print('Working with snapshot: "' + snapshot_name + '".')
    try:
        # check if database exists first
        if os.path.isfile(database_name) is False:
            print(
                "I couldn't find any database for snapshot " + '"' +
                snapshot_name + '".' + "\n" +
                "If the name is correct, " +
                "please import your snapshot file again.")
            sys.exit()
        elif os.path.isfile(database_name) is True:
            # connect to the database
            db = sqlite3.connect(database_name)
            db_cursor = db.cursor()
            print('Connected to database "' + database_name + '".')
    except Exception as e:
        print("Couldn't connect to the database:", e)
        sys.exit(1)
    # ask some questions to the user first
    try:
        daemon_rpcuser = input(
            "\nWhat is the target network daemon rpc user?: ")
        daemon_rpcpassword = input(
            "\nWhat is the target network daemon rpc password?: ")
        daemon_ip = input(
            "\nWhat is the target network daemon ip? " +
            '(leave empty for default "127.0.0.1"): ')
        daemon_port = input(
            "\nWhat is the target network daemon rpc port?: ")
        if daemon_ip == '':
            daemon_ip = '127.0.0.1'
        daemon_url = (
            'http://' +
            daemon_rpcuser + ':' +
            daemon_rpcpassword + '@' +
            daemon_ip + ':' +
            daemon_port)
        print("\nConnecting to " + daemon_url)
        how_many_at_once = int(input(
            "\nTo how many addresses should I send coins at once " +
            "at each transaction?: "))
        proceed = input(
            "\nAre you sure that you want to proceed " +
            "and send all the corresponding coins? (Yes/No): ")
        if proceed != "Yes" and proceed != "yes":
            print("\nOk, bye.")
            sys.exit(0)
        print("")
    except Exception as e:
        print(e)
        sys.exit(0)
    # bring data from the database
    try:
        database_data = select_all()
    except:
        print("Couldn't select data from the database.")
        sys.exit(1)
    # send coins to target network...
    # grouping to send
    group = []
    for e in database_data:
        # add address and value pair
        group.append((e[0], e[1]))
        # separate in arrays ("groups" of addresses)
        if len(group) == int(how_many_at_once):
            send_coins(group)
            # reset the group list
            group = []
    # treat remaining last group
    if len(group) != 0:
        send_coins(group)
    print("\nSending finished.")
    db.close()
else:
    print("Not sure what you mean by that.")
    sys.exit()

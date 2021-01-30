#!/usr/bin/env python3
import sys 
import argparse
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import time
from RabbitClient import *

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", "-r", help="Remove the messages retrieved from the queue permamently.  Default: Requeue Messages",action="store_true")
    parser.add_argument("--number", "-n", metavar="COUNT", help="Number of messages to retrieve",default=10, type=int)
    parser.add_argument("--timeout", "-t", help="Timeout to stop sonsuming after no new message received",default=3, type=int)
    parser.add_argument("--queue", "-q", default="xrd.wlcg-itb", help="Queue to receive messages")

    return parser.parse_args()



args = parse_args()
load_dotenv()
validation_client = RabbitClient(args.queue, args.timeout)
dict_rec, num_messages = validation_client.get_messages(0, False)
print(num_messages)
print(json.dumps(dict_rec, indent=3, sort_keys=True))

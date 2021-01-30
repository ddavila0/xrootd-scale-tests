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
    parser.add_argument("--timeout", "-t", help="Timeout to stop sonsuming after no new message received",default=3, type=int)
    parser.add_argument("--queue", "-q", default="xrd.wlcg-itb", help="Queue to receive messages")
    parser.add_argument("--print", action="store_true",  help="print removed messages")

    return parser.parse_args()

args = parse_args()

load_dotenv()
rabbit_client = RabbitClient(args.queue, args.timeout)
dict_rec, num_messages = rabbit_client.clean_queue()

if args.print:
    print("Removed: %d, messages", num_messages)
    print(json.dumps(dict_rec, indent=3, sort_keys=True))

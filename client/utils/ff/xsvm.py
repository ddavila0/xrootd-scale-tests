#!/usr/bin/env python3

from XRootD import client
from multiprocessing import Process, Value, Lock
import time
import sys
import json
import argparse
from RabbitClient import *
from Server import *
import logging
import random
import pdb
import pika
import socket

def request_n_files_or_bytes(server, files, num_files, num_bytes, initial_test_id, delay, server_id):
    job_id = initial_test_id
    log.debug("server: %d, started", server_id)
    for i in range(0, num_files):
        # Pick random file
        random_index = random.randint(0,len(files)-1)
        filename = files[random_index][:-1]
        job_id_s = f'{job_id:03}'
        appinfo = job_id_s+"_https://glidein.cern.ch/1-519/0:0:ddavila:crab:TEST:0:0:TEST:TEST-TEST_1"
        if num_bytes > 0:
            log.debug("server: %d, fetching %d bytes, job_id: %d", server_id, num_bytes, job_id)
            byte_array, status = server.fetch_byte_range(filename, 0, num_bytes, appinfo)
        else:
            log.debug("server: %d, fetching file %s, job_id: %d", server_id, filename, job_id)
            byte_array, status = server.fetch_full_file(filename, appinfo)
        if status == -1:
            log.error("Cannot open file: "+ filename +" at server: "+server.get_hostname())
        if delay > 0:
            time.sleep(delay)

        job_id +=1
    log.debug("server: %d, done", server_id)

def run_simple_test(servers, files, num_files, num_bytes, initial_test_id, delay):
    process_list= []
    job_id = initial_test_id
    log.info("Starting servers")
    server_id = 1
    for server in servers:
        p = Process(target=request_n_files_or_bytes, args=(server, files, num_files, num_bytes, initial_test_id, delay, server_id))
        p.start()
        process_list.append(p)
        job_id +=num_files
        server_id +=1
    
    log.info("Waiting for servers")
    for p in process_list:
        p.join()
    
def main():
    #pdb.set_trace()
    #--------------------------------------------------------
    # Args
    #--------------------------------------------------------
    parser = argparse.ArgumentParser(description="Run scale test against multiple XRootD servers")
    parser.add_argument('--logfile', dest='logfile', default=False, required=False, help='file to put the logs (defaults to stdout)')
    parser.add_argument('--num-servers', dest='num_servers', default=1, required=False, help='Number of server from which request files in parallel')
    parser.add_argument('--files-per-server', dest='files_per_server', default=100, required=False, help='Number of files to be requested per server')
    parser.add_argument('--num-bytes', dest='num_bytes', default=0, required=False, help='Number of bytes to request from each file, defualt=0(fetch full file)')
    parser.add_argument('--delay', dest='delay', default=0, required=False, help='Delay between file requests')
    parser.add_argument('--initial-test-id', dest='initial_test_id', default=0, required=False, help='Initial test Id')
    parser.add_argument('--debug', action='store_true', help='Be more verbose')
    parser.add_argument('files_list',   default=None, help='TXT file with the list of files in the servers URLs')
    parser.add_argument('servers_list', default=None, help='TXT file with the list of servers')

    args = parser.parse_args()    
    #--------------------------------------------------------
    # Logging
    #--------------------------------------------------------
    # Avoid getting logs from 'pika' module
    logging.getLogger("pika").setLevel(logging.CRITICAL)
    
    if args.logfile:
        hdlr = logging.FileHandler(args.logfile)
    else:
        hdlr = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s  %(levelname)s - %(message)s', datefmt='%Y%m%d %H:%M:%S')
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    if args.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    #---------------------------------------------------------
    # Rabbit Config
    #---------------------------------------------------------
    queue="xrd.wlcg-itb"
    timeout= 5
    # Load Rabit URL from ENV
    load_dotenv()
    rabbit_q = RabbitClient(queue, timeout)
    #---------------------------------------------------------
    log.info("Reading list of files")
    # Get list of test files
    fd = open(args.files_list)
    files = fd.readlines()
    fd.close()

    log.info("Reading list of servers")
    # Get list of servers
    servers = []
    fd = open(args.servers_list)
    lines = fd.readlines()
    for line in lines:
        hostname = line[:-1]
        ip = socket.gethostbyname(hostname)
        s = Server(hostname, ip)
        servers.append(s)
    fd.close()

    delay = int(args.delay)
    num_files = int(args.files_per_server)
    num_servers = int(args.num_servers)
    num_bytes = int(args.num_bytes)

    initial_test_id = int(args.initial_test_id)
    if num_servers > len(servers):
        log.error("Not enough servers in list. Exiting ...")
        sys.exit(1)
    tic = time.perf_counter() 
    run_simple_test(servers[:num_servers], files, num_files, num_bytes, initial_test_id, delay)
    toc = time.perf_counter()

    log.info(f"Time elapsed {toc - tic:0.4f} seconds") 
log = logging.getLogger()
if __name__ == "__main__":
    main()



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

def request_file(server, filename, appinfo):
    #pdb.set_trace()
    byte_array, status = server.fetch_full_file(filename, appinfo)
    if status == -1:
        log.error("Cannot open file: "+ filename +" at server: "+server.get_hostname())

def run_test(servers, initial_test_id, num_rounds, num_workers, files):
    job_id = initial_test_id
    req_dict = {}
    for i in range(0, num_rounds):
        process_list = []
        for j in range(0, num_workers):
            for server in servers:
                job_id_s = f'{job_id:03}'
                # Pick random file
                random_index = random.randint(0,len(files)-1)
                filename = files[random_index][:-1]
                appinfo = job_id_s+"_https://glidein.cern.ch/1-519/0:0:ddavila:crab:TEST:0:0:TEST:TEST-TEST_1"
                req_dict[job_id_s]={"server":server.get_hostname(), "filename":filename} 
                p = Process(target=request_file, args=(server, filename, appinfo))
                p.start()
                process_list.append(p)
                job_id +=1
    
        for p in process_list:
            p.join()
        time.sleep(1)
    
    return req_dict

def insert_hostnames(dict_rec, servers):
    for key in dict_rec:
        ip = dict_rec[key]["server"]
        hostname =""
        for server in servers:
            if server.get_ip() == ip:
                hostname = server.get_hostname()
                break
        dict_rec[key]["server"]=hostname

def write_dict(my_dict, filename):
    fd = open(filename, 'w')
    log.debug("writting dict to %s", filename)
    json.dump(my_dict, fd, indent=4)
    fd.close() 

def main():
    #pdb.set_trace()
    #--------------------------------------------------------
    # Args
    #--------------------------------------------------------
    parser = argparse.ArgumentParser(description="Run scale test against multiple XRootD servers")
    parser.add_argument('--logfile', dest='logfile', default=False, required=False, help='file to put the logs (defaults to stdout)')
    parser.add_argument('--skip_req', action='store_true', help='skip the tests and go directly to validation')
    parser.add_argument('--skip_validation', action='store_true', help='skip the validation just do the requests')
    parser.add_argument('--dont_remove', action='store_true', help='do not remove records from the queue')
    parser.add_argument('tests_list',   default=None, help='JSON file with the description of the tests to run')
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
    log.setLevel(logging.DEBUG)
    #---------------------------------------------------------
    # Rabbit Config
    #---------------------------------------------------------
    queue="xrd.wlcg-itb"
    timeout= 5
    remove_q = ~args.dont_remove
    # Load Rabit URL from ENV
    load_dotenv()
    rabbit_q = RabbitClient(queue, timeout)
    #---------------------------------------------------------

    # Get list of test files
    fd = open(args.files_list)
    files = fd.readlines()
    fd.close()

    # Get list of servers
    servers = []
    fd = open(args.servers_list)
    lines = fd.readlines()
    for line in lines:
        ip       = line.split()[0]
        hostname = line.split()[1]
        s = Server(hostname, ip)
        servers.append(s)
    fd.close()
    
    # Read tests from JSON 
    fd = open(args.tests_list)
    tests_dict = json.load(fd)
    fd.close()
    
    # Get tests info from header
    test_type  = tests_dict["test_type"]
    rep_id     = int(tests_dict["repetition_id"])
    
    tests_dir  = test_type + "_out"
    test_name  = test_type + "_r" + f'{rep_id:02}' 
    tests_dict = tests_dict["tests"]
    total_jobs = len(tests_dict)

    # Create dir if to store test results
    if not os.path.exists(tests_dir):
        os.makedirs(tests_dir)
    
    log.debug("tests directory: "+tests_dir)
   
    # Remove the rabbit queue before starting:
    rabbit_q.clean_queue() 
    #time.sleep(5)
 
    # For each test in the tests files
    for test in tests_dict:
        total_files         = int(test['num_files'])  
        total_servers       = int(test['num_servers'])  
        files_per_second    = int(test['files_per_second'])
        test_id             = int(test['test_id'])
        test_id_s           = f'{test_id:02}'
        file_out_base       = test_name+"_" + test_id_s 
 
        # Configure the test
        # Name of the file that will have the info of what was requested
        file_out_req = file_out_base+"_req.json"
        log.debug("file_base_req: "+file_out_req)
        num_rounds = int(total_files/files_per_second)
        num_workers = files_per_second 
        
        # Configure Rabbit
        # Name of the file that will have the info of what was recorded
        file_out_rec = file_out_base+"_rec.txt"
        num_messages_expected = total_files * total_servers
        log.info("messages expected: "+str(num_messages_expected)) 
        
        if not args.skip_req:
            # Run test
            log.info("running test: "     + test_name)
            log.info("total servers: "    + str(total_servers))
            log.info("total files: "      + str(total_files))
            log.info("files per second: " + str(files_per_second))
            log.info("file_base: "        + file_out_base)

            dict_req = run_test(servers[:total_servers], test_id, num_rounds, num_workers, files)
            write_dict(dict_req, tests_dir+"/"+file_out_req)
            log.debug("printing dict_req")
            log.debug(json.dumps(dict_req, sort_keys=False, indent=4))
 
            if not args.skip_validation:
                # Wait for the data to be sent to the message bus
                log.info("Sleeping...")
                time.sleep(60)

        if not args.skip_validation:
            dict_rec, num_messages_received = rabbit_q.get_messages(0, remove_q)
            write_dict(dict_rec, tests_dir+"/"+file_out_rec)
            
            if num_messages_expected != num_messages_received:
                if num_messages_received > num_messages_expected:
                    log.error("mesages received(%d) >  expected(%d), Exiting...", num_messages_received, num_messages_expected)
                    sys.exit(0)
                else:
                    log.warning("number of mesages received(%d) <  expected(%d)", num_messages_received, num_messages_expected)
            # Swap IPs by hostnames in the dict_rec 
            insert_hostnames(dict_rec, servers) 
    
            log.debug("Recorded dictionary")
            log.debug(json.dumps(dict_rec, sort_keys=False, indent=4))
    
            # Check Requested vs recorded
            # If we skipped the tests we don't have anything to compare against
            if not args.skip_req:
                num_req_good = num_req_wrong = num_req_missing = 0
                for key in dict_req:
                    req_id          = key 
                    req_filename    = dict_req[key]['filename']
                    req_server      = dict_req[key]['server']
                    if key in dict_rec:
                        rec_filename  = dict_rec[key]['filename']
                        rec_server    = dict_rec[key]['server']
                        if rec_filename == req_filename and rec_server == req_server:
                            num_req_good +=1
                        else:
                            num_req_wrong +=1
                    else:
                        num_req_missing +=1
                if(num_req_good + num_req_wrong +num_req_missing != len(dict_req)):
                   log.error("ERROR: sum(num_req_*) doesn't match total_request")
        
                log.info("validating test: "      +test_name)
                log.info("num good requests: "    +str(num_req_good))
                log.info("num wrong requests: "   +str(num_req_wrong))
                log.info("num missing requests: " +str(num_req_missing))

    sys.exit(0)

log = logging.getLogger()
if __name__ == "__main__":
    main()



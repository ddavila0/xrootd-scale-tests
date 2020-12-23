#!/usr/bin/env python3

from XRootD import client
from multiprocessing import Process, Value, Lock
import time
import sys
import pdb
import json
import argparse
from ValidationClient import *


class Server:
    def __init__(self, url):
        self.server_url = url
    
    def fetch_full_file(self, filename, appinfo=""):
        fd = client.File()
        file_url = self.server_url +"//"+ filename
        #print("opening: "+file_url)
        fd.open(file_url)
        if appinfo:
            c = client.FileSystem(self.server_url)
            c_status, c_response = c.sendinfo(appinfo)
            #print(appinfo)

        int_list = []
        try:
            status, byte_array = fd.read()
        except:
            return None, -1
    
        for one_byte in byte_array:
            int_list.append(one_byte)
        
        fd.close()
        return int_list, status


def request_file(server, filename, appinfo):
    byte_array, status = server.fetch_full_file(filename, appinfo)
    if status == -1:
        print("### ERROR: Cannot open file: "+ filename +" at server: "+server.server_url)
    else:
        assert(len(byte_array) == 256)

def run_test(server, initial_job_id, num_rounds, num_workers, files, file_out):
    job_id = initial_job_id
    my_dict = {}
    for i in range(0, num_rounds):
        process_list = []
        for j in range(0, num_workers):
            filename = files[i*num_workers + j][:-1]
            job_id_s = f'{job_id:03}'
            appinfo = job_id_s+"_https://glidein.cern.ch/1-519/0:0:ddavila:crab:TEST:0:0:TEST:TEST-TEST_1"
            my_dict[job_id_s]=filename
            p = Process(target=request_file, args=(server, filename, appinfo))
            p.start()
            process_list.append(p)
            job_id +=1
    
        for p in process_list:
            p.join()
        time.sleep(1)
    
    #for key in my_dict:
        #print(f'{key:20} : '+ my_dict[key])
    
    with open(file_out, 'w') as outfile:
        json.dump(my_dict, outfile)


def main():
    #--------------------------------------------------------
    # Args
    #--------------------------------------------------------
    if len(sys.argv) == 2:
        tests_file = sys.argv[1]
    else:
        print("expected: xmv <tests_file>")
        print("format of tests_file: <total_files> <files_per_second> <initial_job_id> <file_out>")
        sys.exit(1)
    
    #---------------------------------------------------------
    # Fixed Config
    #---------------------------------------------------------
    server_url="root://fermicloud157.fnal.gov:1094"
    list_of_files = "ff_list_of_files.txt"
    #---------------------------------------------------------
    # Rabbit
    queue="xrd.wlcg-itb"
    remove = True
    timeout= 5
    load_dotenv()
    #---------------------------------------------------------

    # Get list of test files
    fd_list = open(list_of_files)
    files = fd_list.readlines()
    fd_list.close()

    # Create server obj
    server = Server(server_url)

    # Per each test in the file 
    fd_tests = open(tests_file)
    lines = fd_tests.readlines()
    for line in lines:
        total_files = int(line.split()[0]) 
        files_per_second = int(line.split()[1])
        initial_job_id = int(line.split()[2])
        file_base = line.split()[3]
    
        # Configure the test
        file_out = file_base+"_requested.json" 
        num_rounds = int(total_files/files_per_second)
        num_workers = files_per_second 
        
        # Configure Rabbit
        num_messages = total_files
        outfile = file_base+"_recorded.txt"
        
        # Run test
        print("running test: " + str(total_files) +" "+ str(files_per_second)+ " " + str(initial_job_id) + " " + file_base)
        run_test(server, initial_job_id, num_rounds, num_workers, files, file_out)
        
        # Wait for the data to be sent to the message bus
        #print("Sleeping...")
        time.sleep(60)
        
        # Query rabbitMQ
        validation_client = ValidationClient(queue, num_messages, remove, timeout, outfile)
        received_messages = validation_client.start()
        print("*** test: "+file_base + "; num requested: "+str(total_files) + "; num recorded: "+ str(received_messages))
        if remove and num_messages > received_messages and received_messages > 0:
            validation_client = ValidationClient(queue, received_messages, remove, timeout, None)
            received_messages2 = validation_client.start()
            if received_messages > received_messages2:
                print("ERROR while trying to remove shorter queue")



if __name__ == "__main__":
    main()



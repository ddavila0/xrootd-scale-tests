import pika
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import time

class RabbitClient:

    def __init__(self, queue, timeout):
        self.queue = queue
        self.timeout = timeout
        self.receivedMsgs = 0
        self.timer_id = 0
        self.last_messages = 0
        self.my_dict = {}
        self.method = None 
        self.targetMsgs = None
        self.remove = None
    
    def push_in_dict(self, body):
        json_dict = json.loads(body)
        crab_id = file_lfn = ""
        read_bytes = -1

        if "CRAB_Id" in json_dict:
            crab_id = json_dict["CRAB_Id"]
        
        if "file_lfn" in json_dict:
            file_lfn = json_dict["file_lfn"]
        
        if "read_bytes" in json_dict:
            read_bytes = int(json_dict["read_bytes"])

        if "server_host" in json_dict:
            server_host = json_dict["server_host"]

        self.my_dict[crab_id]={"server": server_host, "filename":file_lfn, "read_bytes":read_bytes}
        #self.my_dict[crab_id]=[file_lfn, read_bytes, server_host]

    def pretty_print(self, body, index):
        json_dict = json.loads(body)
        #print(json.dumps(json_dict, indent=4, sort_keys=True))
        ts = json_dict["metadata"]["timestamp"] /1000
        ts_hr = time.strftime("%D %H:%M", time.localtime(ts-3600*7))
        print(f'{"index":20} : '+ str(index))
        print(f'{"timestamp":20} : '+ ts_hr)
        for key in ["CRAB_Id", "file_lfn", "read_bytes", "read_single_bytes", "read_vector_bytes"]:
            value=""
            if key in sorted(json_dict):
                value = str(json_dict[key])
            print(f'{key:20} : '+ value)
        print("====================================================")

    def recvMsg(self, channel: pika.channel, method, properties, body):
        #self.pretty_print(body, self.receivedMsgs)
        #print(body)
        #print(json.dumps(str(body), sort_keys=False, indent=4))
        self.method  = method
        self.push_in_dict(body)
        self.receivedMsgs += 1
    
        # When targetMsgs == 0 we assume that we want all the messages in the queue
        if self.targetMsgs > 0 and self.receivedMsgs == self.targetMsgs:
            if self.remove:
                channel.basic_ack(method.delivery_tag, multiple=True)
            else:
                channel.basic_nack(method.delivery_tag, multiple=True, requeue=True)
            channel.stop_consuming()

    def createConnection(self):
        # Load the credentials into pika
        if 'RABBIT_URL' not in os.environ:
            raise Exception("Unable to find RABBIT_URL in environment file, .env")
        
        parameters = pika.URLParameters(os.environ["RABBIT_URL"])
        self.conn = pika.adapters.blocking_connection.BlockingConnection(parameters)

        # Connect to the queue
        self.channel = self.conn.channel()

        # Consume from the queue
        self.channel.basic_consume(self.queue, self.recvMsg)

    def _checkStatus(self):
        """
        Called every X seconds to check the status of the transfer.
        If nothing has happened lately, then kill the connection.
        """
        if self.last_messages == self.receivedMsgs:
            if self.last_messages > 0:
                if self.remove:
                    self.channel.basic_ack(self.method.delivery_tag, multiple=True)
                else:
                    self.channel.basic_nack(self.method.delivery_tag, multiple=True, requeue=True)
            self.channel.stop_consuming()
        else:
            self.last_messages = self.receivedMsgs
            self.timer_id = self.conn.call_later(self.timeout, self._checkStatus)

    def clean_queue(self):
        self.targetMsgs = 0
        self.remove = True
        num_received_messages = self.start()

        return self.my_dict, num_received_messages

    def get_messages(self, num_messages, remove):
        self.targetMsgs = num_messages
        self.remove = remove
        num_received_messages = self.start()

        return self.my_dict, num_received_messages 

    def start(self):
        self.createConnection()

        # Create a timeout
        self.timer_id = self.conn.call_later(self.timeout, self._checkStatus)

        self.channel.start_consuming()
        self.conn.close()
        # Save value to be returned before reseting the counter
        num_received_messages = self.receivedMsgs
        
        # Reset counters
        self.receivedMsgs = 0
        self.timer_id = 0
        
        return num_received_messages

        



from XRootD import client

class Server:
    def __init__(self, url):
        self.server_url = url
        self.fd = None

    def only_close(self):
        self.fd.close()
    
    def only_open(self, filename, appinfo=""):
        self.fd = client.File()
        file_url = self.server_url +"//"+ filename
        self.fd.open(file_url)
        #print("opening: "+file_url)
        if appinfo:
            c = client.FileSystem(self.server_url)
            c_status, c_response = c.sendinfo(appinfo)
       
    def only_fetch_byte_range(self, start, end):
        chunk_size = end - start
        int_list = []
        try:
            status, byte_array = self.fd.read(start, chunk_size)
        except:
            print("Exception in only_fetch_byte_range()")
            return None
        #print("Status: "+str(status))
        for one_byte in byte_array:
            int_list.append(one_byte)
        
        return int_list, status

    def fetch_byte_range(self, filename, start, end, appinfo=""):
        fd = client.File()
        file_url = self.server_url +"//"+ filename
        #print("opening: "+file_url)
        fd.open(file_url)
        if appinfo:
            c = client.FileSystem(self.server_url)
            c_status, c_response = c.sendinfo(appinfo)
            #print(appinfo)

        chunk_size = end - start
        int_list = []
        try:
            status, byte_array = fd.read(start, chunk_size)
        except:
            return None
    
        for one_byte in byte_array:
            int_list.append(one_byte)
        
        fd.close()
        return int_list, status

    
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



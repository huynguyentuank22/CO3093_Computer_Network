import json
import datetime
FORMAT = 'utf-8'

class Encode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def requestChat(self):
        return json.dumps({
            'type': 'request',
            'flag': 'S',
            'content': f"{self.ip} {self.port}"
        }).encode(FORMAT)
    
if __name__ == '__main__':
    # header = Encode('192.168.137.1', 3000)
    # json_data = header.requestChat()
    # print(json_data)
    print(len('request'.encode()))
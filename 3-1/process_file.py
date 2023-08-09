import process
import utils
import socket
import time





class ProcessHandler(process.ProcessHandler):

    def __init__(self, ip_port_dict, terminate_event):
        super().__init__(ip_port_dict, terminate_event)

    def in_socket(self, retries, delay):
        pass




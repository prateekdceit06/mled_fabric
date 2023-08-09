import process
import utils

class ProcessHandler(process.ProcessHandler):

    def __init__(self, ip_port_dict, terminate_event):
        super().__init__(ip_port_dict, terminate_event)


    def in_socket(self, retries, delay):
        in_socket = utils.create_client_socket(self.own_ip, self.own_port)
        host, port = self.find_host_port()
        super().create_in_socket(in_socket, retries, delay, host, port)

    def find_host_port(self):
        host, port = self.child_ip, self.child_port
        return host, port

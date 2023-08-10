# Process D

import process
import utils


class ProcessHandler(process.ProcessHandler):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)

    def create_route(self, retries, delay):
        in_socket = utils.create_client_socket(self.process_config['ip'], self.process_config['port'])
        host, port = self.find_host_port()
        in_socket = super().connect_in_socket(in_socket, retries, delay, host, port)

    def find_host_port(self):
        if self.process_config['child'] is not None:
            host, port = self.process_config['child_ip'], self.process_config['child_port']
        else:
            host, port = self.process_config['left_neighbor_ip'], self.process_config['left_neighbor_port']
        return host, port


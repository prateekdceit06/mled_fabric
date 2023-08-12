# Process C

from process import ProcessHandlerBase

import utils


class ProcessHandler(ProcessHandlerBase):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)

    def create_data_route(self, retries, delay):
        in_socket = utils.create_client_socket(
            self.process_config['ip'], self.process_config['data_port'])
        host, port = self.find_data_host_port()
        in_socket = super().connect_in_socket(in_socket, retries, delay, host, port)

    def find_data_host_port(self):
        if self.process_config['parent'] is not None:
            host, port = self.process_config['parent_ip'], self.process_config['parent_data_port']
        else:
            host, port = self.process_config['left_neighbor_ip'], self.process_config['left_neighbor_data_port']
        return host, port

    def create_out_data_socket(self, connections, timeout, ip):
        data_port = self.process_config['data_port']
        super().create_out_data_socket(connections, timeout, ip, data_port)

    def create_out_ack_socket(self, connections, timeout, ip):
        ack_port = self.process_config['ack_port']
        super().create_out_ack_socket(connections, timeout, ip, ack_port)

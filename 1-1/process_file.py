# Process C

from process import ProcessHandlerBase

import utils


class ProcessHandler(ProcessHandlerBase):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)
        self.in_data_socket = None
        self.in_ack_socket = None
        self.out_data_socket = None
        self.out_ack_socket = None
        self.out_data_addr = None
        self.out_ack_addr = None
        self.socket_list = [self.in_data_socket, self.in_ack_socket,
                            self.out_data_socket, self.out_ack_socket]

    def create_data_route(self, retries, delay):
        in_data_socket = utils.create_client_socket(
            self.process_config['ip'], 0)
        host, port = self.find_data_host_port()
        in_data_socket_generator = super().connect_in_socket(
            in_data_socket, retries, delay, host, port, "data")
        self.in_data_socket = next(in_data_socket_generator, None)

    def find_data_host_port(self):
        host, port = self.process_config['parent_ip'], self.process_config['parent_data_port']
        return host, port

    def create_ack_route(self, retries, delay):
        in_ack_socket = utils.create_client_socket(
            self.process_config['ip'], self.process_config['ack_port'])
        host, port = self.find_ack_host_port()
        in_ack_socket_generator = super().connect_in_socket(
            in_ack_socket, retries, delay, host, port, "ack")
        self.in_ack_socket = next(in_ack_socket_generator, None)

    def find_ack_host_port(self):
        if self.process_config['child'] is not None:
            host, port = self.process_config['child_ip'], self.process_config['child_ack_port']
        else:
            host, port = self.process_config['right_neighbor_ip'], self.process_config['right_neighbor_ack_port']
        return host, port

    def create_out_data_socket(self, connections, timeout, ip):
        data_port = self.process_config['data_port']
        out_data_socket_generator = super().create_out_data_socket(
            connections, timeout, ip, data_port)
        self.out_data_socket, self.out_data_addr = next(
            out_data_socket_generator, (None, None))

    def create_out_ack_socket(self, connections, timeout, ip):
        ack_port = self.process_config['ack_port']
        out_ack_socket_generator = super().create_out_ack_socket(
            connections, timeout, ip, ack_port)
        self.out_ack_socket, self.out_ack_addr = next(
            out_ack_socket_generator, (None, None))

    def are_sockets_alive(self):
        return super().are_sockets_alive(self.socket_list)

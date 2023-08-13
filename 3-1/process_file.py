# Process A
from process import ProcessHandlerBase
import utils
import time


class ProcessHandler(ProcessHandlerBase):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)
        self.out_data_socket = None
        self.out_data_addr = None
        self.out_ack_addr = None
        self.in_ack_socket = None
        self.socket_list = [
            'out_data_socket',
            'in_ack_socket'
        ]

    def get_socket_by_name(self, name):
        return getattr(self, name)

    def create_out_data_socket(self, connections, timeout, ip):
        if self.process_config['data_port'] is not None:
            data_port = self.process_config['data_port']
            out_data_socket_generator = super().create_out_data_socket(
                connections, timeout, ip, data_port)
            self.out_data_socket, self.out_data_addr = next(
                out_data_socket_generator, (None, None))

    def create_out_ack_socket(self, connections, timeout, ip):
        if self.process_config['ack_port'] is not None:
            ack_port = self.process_config['ack_port']
            out_ack_socket_generator = super().create_out_ack_socket(
                connections, timeout, ip, ack_port)
            self.out_ack_socket, self.out_ack_addr = next(
                out_ack_socket_generator, (None, None))

    def create_ack_route(self, retries, delay):
        in_ack_socket = utils.create_client_socket(
            self.process_config['ip'], 0)
        host, port = self.find_ack_host_port()
        in_ack_socket_generator = super().connect_in_socket(
            in_ack_socket, retries, delay, host, port, "ack")
        self.in_ack_socket = next(in_ack_socket_generator, None)

    def find_ack_host_port(self):
        host, port = self.process_config['child_ip'], self.process_config['child_ack_port']
        return host, port

    def create_out_sockets(self, connections, timeout, ip):
        self.create_out_data_socket(connections, timeout, ip)
        self.create_out_ack_socket(connections, timeout, ip)
        time.sleep(self.process_config['delay_process_socket']+5)
        for sock in self.socket_list:
            print(self.get_socket_by_name(sock))

# Process A
from process import ProcessHandlerBase
from send_receive import SendReceive
import utils
import time
import threading
from circular_buffer import CircularBuffer


class ProcessHandler(ProcessHandlerBase, SendReceive):

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
        self.buffer = CircularBuffer(self.process_config['window_size'])
        self.chunk_size - self.process_config['mtu']

    def read_and_send_data(self):
        seq_num = 0
        with open('astroMLDataTest.csv', 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                seq_num += 1
                seq_num %= (2*self.process_config['window_size'])
                dest = self.process_config['right_neighbor']
                error_detection_method = self.process_config['error_detection_method']['method']
                parameter = self.process_config['error_detection_method']['parameter']
                if not chunk:
                    break
                errors = []
                super().send_data(chunk, self.out_data_socket, self.buffer,
                                  seq_num, self.process_config['name'], dest,
                                  len(chunk), 0, errors, error_detection_method, parameter)
        while True:
            continue

    def receive_ack(self):
        while True:
            received_seq_num, received_src, received_dest, received_check_value, received_chunk, received_ack_byte, received_errors = super(
            ).receive_data(self.in_ack_socket)

            

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

        while True:
            socekts_ready = super().are_sockets_alive(self.socket_list)
            if socekts_ready:
                break
            else:
                time.sleep(self.process_config['delay_process_socket'])

        for sock in self.socket_list:
            print(super().get_socket_by_name(sock))

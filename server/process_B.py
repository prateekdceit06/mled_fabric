# Process B

from process import ProcessHandlerBase
from send_receive import SendReceive

import utils
import time
import threading
from circular_buffer import CircularBuffer
from header import Header
from packet import Packet
from utils import logging_format as logging_format
import os
import print_colour as pc

import logging

logging.basicConfig(format=logging_format, level=logging.INFO)


class ProcessHandler(ProcessHandlerBase, SendReceive):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)
        self.out_ack_socket = None
        self.out_ack_addr = None
        self.in_data_socket = None
        self.socket_list = [
            'out_ack_socket',
            'in_data_socket'
        ]

        self.received_data_buffer = CircularBuffer(
            self.process_config['window_size'])
        self.chunk_size = self.process_config['mtu']

        self.received_data_buffer_lock = threading.Lock()
        self.received_buffer_not_full_condition = threading.Condition(
            self.received_data_buffer_lock)

    def receive_data(self, in_socket, out_ack_socket, received_buffer_not_full_condition, received_data_buffer):
        seq_num = -1

        while True:
            data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data = self.receive_packets(
                in_socket)
            logging.info(pc.PrintColor.print_in_black_back(
                f"Received chunk of size {len(data_to_forward)}"))

            self.handle_data(data_to_forward, packet_to_ack, received_src,
                             received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data)

    def receive_packets(self, in_socket):
        data_to_forward = b''
        packet_to_ack = []
        while True:
            received_seq_num, received_src, received_dest, received_check_value_data, received_chunk_data, received_ack_byte, fixed_data, received_errors_data, received_last_packet = super().receive_data(in_socket)
            packet_to_ack.append(received_seq_num)
            data_to_forward += received_chunk_data
            if received_last_packet:
                break
        return data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data

    def handle_data(self, data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data):
        inner_packet = super().decapsulate(data_to_forward)
        data_to_forward = inner_packet.chunk
        received_check_value_data = inner_packet.header.check_value.encode()
        received_seq_num = inner_packet.header.seq_num
        no_corruption = super().verify_value(data_to_forward, received_check_value_data.decode(),
                                             self.process_config['error_detection_method']['method'], self.process_config['error_detection_method']['parameter'])
        received_src_inner = inner_packet.header.src.encode()
        received_dest_inner = inner_packet.header.dest.encode()
        received_last_packet_inner = inner_packet.header.last_packet
        if no_corruption:
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Positive ACK for seq_num: {received_seq_num} to {received_src_inner} from {received_dest_inner}"))
            for seq_n in packet_to_ack:
                logging.info(pc.PrintColor.print_in_yellow_back(
                    f"Positive ACK for seq_num: {seq_n} to {(self.process_config['child']).encode()} from {(self.process_config['name']).encode()}"))
            self.add_to_buffer(
                data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num, received_last_packet_inner)

    def add_to_buffer(self, data_to_forward, received_buffer_not_full_condition, received_data_buffer, seq_num, last_packet):
        for i in range(0, len(data_to_forward), self.chunk_size):
            chunk = data_to_forward[i:i+self.chunk_size]
            seq_num %= (2*self.process_config['window_size'])
            with received_buffer_not_full_condition:
                while received_data_buffer.is_full():
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"No space in Receiving buffer"))
                    received_buffer_not_full_condition.wait()
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"Received notification that there is space in Receiving buffer"))
                if not chunk:
                    break
                received_data_buffer.add((chunk, last_packet))
                received_buffer_not_full_condition.notify()
                logging.info(pc.PrintColor.print_in_red_back(
                    f"Received chunk {seq_num} of size {len(chunk)} to buffer"))
            seq_num += 1

    def write_to_file(self, received_data_buffer):
        path = os.path.abspath(__file__)
        directory = os.path.dirname(path)
        filename = os.path.join(directory, 'received_data.csv')
        with open(filename, 'wb') as file:
            while True:
                with self.received_buffer_not_full_condition:
                    while received_data_buffer.is_empty():
                        # Wait until there's data in the buffer
                        logging.info(pc.PrintColor.print_in_blue_back(
                            f"Waiting for data in Receiving buffer"))
                        self.received_buffer_not_full_condition.wait()
                        logging.info(pc.PrintColor.print_in_blue_back(
                            f"Received notification that there is data in Receiving buffer"))

                    chunk, last_packet = received_data_buffer.get()
                    file.write(chunk)
                    file.flush()  # Flush the data to the file
                    received_data_buffer.remove()
                    self.received_buffer_not_full_condition.notify()
                    if last_packet:
                        break
        logging.info(pc.PrintColor.print_in_green_back(
            f"Received file successfully"))

    def create_data_route(self, retries, delay):
        in_data_socket = utils.create_client_socket(
            self.process_config['ip'], 0)
        host, port = self.find_data_host_port()
        in_data_socket_generator = super().connect_in_socket(
            in_data_socket, retries, delay, host, port, "data")
        self.in_data_socket = next(in_data_socket_generator, None)

    def find_data_host_port(self):
        host, port = self.process_config['child_ip'], self.process_config['child_data_port']
        return host, port

    def create_out_ack_socket(self, connections, timeout, ip):
        if self.process_config['ack_port'] is not None:
            ack_port = self.process_config['ack_port']
            out_ack_socket_generator = super().create_out_ack_socket(
                connections, timeout, ip, ack_port)
            self.out_ack_socket, self.out_ack_addr = next(
                out_ack_socket_generator, (None, None))

    def create_out_data_socket(self, connections, timeout, ip):
        if self.process_config['data_port'] is not None:
            data_port = self.process_config['data_port']
            out_data_socket_generator = super().create_out_data_socket(
                connections, timeout, ip, data_port)
            self.out_data_socket, self.out_data_addr = next(
                out_data_socket_generator, (None, None))

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

        write_thread = threading.Thread(args=(self.received_data_buffer,),
                                        target=self.write_to_file, name="WriteThread")
        write_thread.start()

        receive_thread = threading.Thread(args=(self.in_data_socket, self.out_ack_socket,
                                                self.received_buffer_not_full_condition, self.received_data_buffer,),
                                          target=self.receive_data, name="ReceiveDataThread")
        receive_thread.start()

        write_thread.join()
        receive_thread.join()

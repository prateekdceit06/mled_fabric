# Process A
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
        self.out_data_socket = None
        self.out_data_addr = None
        self.out_ack_addr = None
        self.in_ack_socket = None
        self.socket_list = [
            'out_data_socket',
            'in_ack_socket'
        ]

        self.sending_data_buffer = CircularBuffer(
            self.process_config['window_size'])
        self.received_data_buffer = CircularBuffer(
            self.process_config['window_size'])
        self.chunk_size = self.process_config['mtu']

        self.received_data_buffer_lock = threading.Lock()
        self.received_buffer_not_full_condition = threading.Condition(
            self.received_data_buffer_lock)

        self.sending_data_buffer_lock = threading.Lock()
        self.sending_data_buffer_condition = threading.Condition(
            self.sending_data_buffer_lock)
        self.sending_buffer_not_full_condition = threading.Condition()

        self.send_lock = threading.Lock()
        self.urgent_send_condition = threading.Condition(
            self.send_lock)
        self.urgent_send_in_progress = False

    def read_file_to_buffer(self):
        path = os.path.abspath(__file__)
        directory = os.path.dirname(path)
        file_path = os.path.join(directory, 'astroMLDataTest.csv')
        with open(file_path, 'rb') as f:
            seq_num = -1
            while True:
                seq_num += 1
                seq_num %= (2*self.process_config['window_size'])
                with self.received_buffer_not_full_condition:
                    while self.received_data_buffer.is_full():
                        # Wait until there's space in the buffer
                        self.received_buffer_not_full_condition.wait()

                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    self.received_data_buffer.add(chunk)

                    logging.info(pc.PrintColor.print_in_red_back(
                        f"Read chunk {seq_num} of size {len(chunk)} to buffer"))
                    logging.info(f"CHUNK: {chunk}")

    def prepare_packet_to_send(self):
        seq_num = -1
        while True:
            chunk = None
            with self.received_buffer_not_full_condition:
                if not self.received_data_buffer.is_empty():
                    chunk = self.received_data_buffer.get()
                    self.received_data_buffer.remove()
                    # Notify read_file_to_buffer that there's space now
                    self.received_buffer_not_full_condition.notify()

            if chunk:
                size_of_chunk = len(chunk)
                seq_num += 1
                seq_num %= (2*self.process_config['window_size'])
                src = self.process_config['name']
                dest = self.process_config['right_neighbor']
                error_detection_method = self.process_config['error_detection_method']['method']
                parameter = self.process_config['error_detection_method']['parameter']
                check_value = super().get_value_to_check(
                    chunk, error_detection_method, parameter)
                errors = []
                if size_of_chunk < self.chunk_size:
                    last_packet = True
                else:
                    last_packet = False
                header = Header(seq_num, src, dest, check_value,
                                size_of_chunk, 0, errors, last_packet)
                packet = Packet(header, chunk)

                with self.sending_buffer_not_full_condition:  # Use the condition for the sending buffer
                    while self.sending_data_buffer.is_full():  # Wait if the sending buffer is full
                        self.sending_buffer_not_full_condition.wait()

                    with self.sending_data_buffer_lock:
                        self.sending_data_buffer.add(packet)
                        logging.info(pc.PrintColor.print_in_green_back(
                            f"Added packet {seq_num} of size {size_of_chunk} to sending buffer"))
                        self.sending_data_buffer_condition.notify()

    def send_packet_from_buffer(self, out_socket, out_addr):
        last_sent_seq_num = -1  # Initialize to an invalid sequence number
        while True:
            with self.sending_data_buffer_condition:
                while self.urgent_send_in_progress or self.sending_data_buffer.is_empty():
                    # Wait until there's a packet to send or an urgent send is needed
                    self.sending_data_buffer_condition.wait()
                seq_num_of_packet_to_send = (
                    last_sent_seq_num + 1) % (2*self.process_config['window_size'])
                packet = self.sending_data_buffer.get_by_sequence(
                    seq_num_of_packet_to_send)
                if packet is None:
                    continue
                with self.send_lock:
                    super().send_data(out_socket, packet)
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"Sent packet {packet.seq_num} of size {packet.header.size_of_data + packet.header.get_size()} (Data: {packet.header.size_of_data} Header: {packet.header.get_size()}) to {out_addr[0]}:{out_addr[1]}"))
                    logging.info(packet)
                    last_sent_seq_num = packet.seq_num

    def receive_ack(self, in_socket, out_socket, out_addr):
        while True:
            received_seq_num, _, _, _, received_chunk_data, received_ack_byte, _, _, _ = super(
            ).receive_data(in_socket)
            ack_string = "ACK" if received_ack_byte == 1 else "NACK" if received_ack_byte == 3 else "UNKNOWN"
            logging.info(pc.PrintColor.print_in_purple_back(
                f"Received {ack_string} for packet {received_seq_num}"))

            with self.sending_data_buffer_condition:

                if received_ack_byte == 1:
                    self.sending_data_buffer.remove_by_sequence(
                        received_seq_num)
                    logging.info(pc.PrintColor.print_in_yellow_back(
                        f"Removed packet {received_seq_num} from sending buffer"))
                    # Notify send_packet_from_buffer that there might be space now
                    self.sending_data_buffer_condition.notify()
                    self.sending_buffer_not_full_condition.notify()

                elif received_ack_byte == 3:
                    packet = self.sending_data_buffer.get_by_sequence(
                        received_seq_num)
                    self.urgent_send_in_progress = True
                    self.urgent_send_condition.notify()
                    super().send_data(out_socket, packet)
                    logging.info(pc.PrintColor.print_in_white_back(
                        f"Re-sent packet {received_seq_num} of size {len(received_chunk_data)} to {out_addr[0]}:{out_addr[1]}"))
                    self.urgent_send_in_progress = False
                    self.urgent_send_condition.notify()

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

        time.sleep(30)
        read_thread = threading.Thread(
            target=self.read_file_to_buffer, name="ReadThread")
        read_thread.start()

        # Thread for prepare_packet_to_send
        prepare_thread = threading.Thread(
            target=self.prepare_packet_to_send, name="PrepareThread")
        prepare_thread.start()

        # Thread for send_packet_from_buffer
        send_thread = threading.Thread(args=(self.out_data_socket, self.out_data_addr,),
                                       target=self.send_packet_from_buffer, name="SendThread")
        send_thread.start()

        # Thread for receive_ack
        receive_thread = threading.Thread(
            target=self.receive_ack, name="ReceiveAckThread", args=(self.in_ack_socket, self.out_data_socket, self.out_data_addr,))
        receive_thread.start()

        # Optionally, if you want the main thread to wait for these threads to finish (though in your case they have infinite loops)
        read_thread.join()
        prepare_thread.join()
        send_thread.join()
        receive_thread.join()

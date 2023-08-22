# Process B

from process import ProcessHandlerBase
from send_receive import SendReceive
import hashlib
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

        self.expected_hash = None

    def receive_data(self, in_socket, out_ack_socket, received_buffer_not_full_condition, received_data_buffer):
        seq_num = -1

        while True:
            data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data = self.receive_packets(
                in_socket, out_ack_socket)
            logging.info(pc.PrintColor.print_in_black_back(
                f"Received chunk of size {len(data_to_forward)}"))

            self.handle_data(out_ack_socket, data_to_forward, packet_to_ack, received_src,
                             received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data)

    def receive_packets(self, in_socket, out_ack_socket):
        data_to_forward = b''
        packet_to_ack = []
        while True:
            received_seq_num, received_src, received_dest, received_check_value_data, received_chunk_data, received_ack_byte, fixed_data, received_errors_data, received_last_packet = super().receive_data(in_socket)
            packet_to_ack.append(received_seq_num)
            data_to_forward += received_chunk_data
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Sending positive ACK for seq_num: {received_seq_num} to {(self.process_config['child']).encode()} from {(self.process_config['name']).encode()}"))
            self.send_ack(
                received_seq_num, (self.process_config['name']).encode(), (self.process_config['child']).encode(), 1, out_ack_socket)
            if received_last_packet:
                break
        return data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data

    def handle_data(self, out_ack_socket, data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data):
        inner_packet = super().decapsulate(data_to_forward)
        data_to_forward = inner_packet.chunk
        received_check_value_data = inner_packet.header.check_value.encode()
        received_seq_num = inner_packet.header.seq_num
        received_src_inner = inner_packet.header.src.encode()
        received_dest_inner = inner_packet.header.dest.encode()
        received_last_packet_inner = inner_packet.header.last_packet

        no_corruption = super().verify_value(data_to_forward, received_check_value_data.decode(),
                                             self.process_config['error_detection_method']['method'],
                                             self.process_config['error_detection_method']['parameter'])
        if no_corruption:
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Sending positive ACK for seq_num: {received_seq_num} to {received_src_inner} from {received_dest_inner}"))

            self.send_ack(received_seq_num, received_dest_inner,
                          received_src_inner, 1, out_ack_socket)

            self.add_to_buffer(
                data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num, received_last_packet_inner)
        else:
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Sending negative ACK for seq_num: {received_seq_num} to {received_src_inner} from {received_dest_inner}"))
            self.send_ack(received_seq_num, received_dest_inner,
                          received_src_inner, 3, out_ack_socket)

    def add_to_buffer(self, data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num, last_packet):
        for i in range(0, len(data_to_forward), self.chunk_size):
            seq_num = received_seq_num
            chunk = data_to_forward[i:i+self.chunk_size]
            # seq_num %= (2*self.process_config['window_size'])
            with received_buffer_not_full_condition:
                while received_data_buffer.is_full():
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"No space in Receiving buffer"))
                    received_buffer_not_full_condition.wait()
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"Received notification that there is space in Receiving buffer"))
                if not chunk:
                    break
                header = Header(seq_num, last_packet=last_packet)
                packet = Packet(header, chunk)
                # logging.info(pc.PrintColor.print_in_cyan_back(
                #     f"Received Data Buffer before adding: {received_data_buffer.print_buffer()}"))
                received_data_buffer.add(packet)
                # logging.info(pc.PrintColor.print_in_blue_back(
                #     f"Received Data Buffer before adding: {received_data_buffer.print_buffer()}"))

                received_buffer_not_full_condition.notify(2)
                logging.info(pc.PrintColor.print_in_red_back(
                    f"Received chunk {seq_num} of size {len(chunk)} to buffer"))
            # seq_num += 1

    def write_to_file(self, file_path, received_data_buffer, expected_hash, hash_method):
        last_written_seq_num = -1
        with open(file_path, 'wb') as file:
            while True:
                while received_data_buffer.is_empty():
                    # Wait until there's data in the buffer
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"No data in receiving buffer"))
                    with self.received_buffer_not_full_condition:
                        self.received_buffer_not_full_condition.wait()
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"Received notification that there is data in receiving buffer"))

                with self.received_buffer_not_full_condition:
                    seq_num_of_packet_to_send = (
                        last_written_seq_num + 1) % (2*self.process_config['window_size'])
                    packet = received_data_buffer.get_by_sequence(
                        seq_num_of_packet_to_send)
                    # logging.info(pc.PrintColor.print_in_purple_back(f"seq_num_of_packet_to_send: {seq_num_of_packet_to_send}"))
                    if packet is None:
                        continue
                    file.write(packet.chunk)
                    logging.info(pc.PrintColor.print_in_red_back(
                        f"Writing chunk {packet.header.seq_num} of size {len(packet.chunk)} to file"))
                    file.flush()  # Flush the data to the file
                    last_written_seq_num = packet.header.seq_num
                    # logging.info(pc.PrintColor.print_in_cyan_back(
                    #     f"Received Data Buffer before removing: {received_data_buffer.print_buffer()}"))

                    received_data_buffer.remove_by_sequence(
                        last_written_seq_num)
                    # logging.info(pc.PrintColor.print_in_blue_back(
                    #     f"Received Data Buffer after removing: {received_data_buffer.print_buffer()}"))

                    self.received_buffer_not_full_condition.notify(2)
                    if packet.header.last_packet:
                        break
        logging.info(pc.PrintColor.print_in_green_back("File Received."))
        is_file_verified = self.verify_file_hash(
            file_path, expected_hash, hash_method)
        if not is_file_verified:
            logging.info(pc.PrintColor.print_in_red_back(
                f"File is corrupted"))
        else:
            logging.info(pc.PrintColor.print_in_green_back(
                f"File is verified successfully"))

    def send_ack(self, seq_num, src, dest, type, out_ack_socket):
        time.sleep(self.process_config['pause_time_before_ack'])
        ack_header = Header(
            seq_num, src.decode(), dest.decode(), "", 0, type, [], True)
        ack_packet = Packet(ack_header, b'')
        super().send_ack(out_ack_socket, ack_packet)

    def verify_file_hash(self, file_path, expected_hash, hash_method):
        try:
            hash_func = getattr(hashlib, hash_method)
        except AttributeError:
            raise ValueError(f"Invalid hash method: {hash_method}")

        with open(file_path, 'rb') as file:
            file_data = file.read()
            calculated_hash = hash_func(file_data).hexdigest()

        return calculated_hash == expected_hash

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

    def check_setup(self):
        _, _, _, received_check_value_data, received_chunk_data, _, _, _, _ = super(
        ).receive_data(self.in_data_socket)

        error_detection_method = self.process_config['error_detection_method']['method']
        parameter = self.process_config['error_detection_method']['parameter']

        is_hash_correct = super().verify_value(received_chunk_data,
                                               received_check_value_data.decode(), error_detection_method, parameter)

        if is_hash_correct:
            self.expected_hash = received_chunk_data.decode()
            logging.info(pc.PrintColor.print_in_green_back(
                f"Hash value received. Hash value is correct. Sending ACK..."))
            self.send_ack(0, self.process_config['name'].encode(
            ), self.process_config['left_neighbor'].encode(), 1, self.out_ack_socket)
            return True
        else:
            logging.info(pc.PrintColor.print_in_red_back(
                f"Hash value received. Hash value is not correct. Sending NACK"))
            self.send_ack(0, self.process_config['name'].encode(
            ), self.process_config['left_neighbor'].encode(), 3, self.out_ack_socket)

            return False

    def create_out_sockets(self, connections, timeout, ip):
        self.create_out_data_socket(connections, timeout, ip)
        self.create_out_ack_socket(connections, timeout, ip)

        while True:
            socekts_ready = super().are_sockets_alive(self.socket_list)
            if socekts_ready:
                break
            else:
                time.sleep(self.process_config['delay_process_socket'])

        is_correct = self.check_setup()

        if is_correct:

            path = os.path.abspath(__file__)
            directory = os.path.dirname(path)
            received_filename = self.process_config['received_filename']
            file_path = os.path.join(directory, received_filename)

            write_thread = threading.Thread(args=(file_path, self.received_data_buffer, self.expected_hash, self.process_config['hash_method']),
                                            target=self.write_to_file, name="WriteToFileThread")
            write_thread.daemon = True
            write_thread.start()

            receive_thread = threading.Thread(args=(self.in_data_socket, self.out_ack_socket,
                                                    self.received_buffer_not_full_condition, self.received_data_buffer,),
                                              target=self.receive_data, name="ReceiveDataThread")
            receive_thread.daemon = True
            receive_thread.start()

            write_thread.join()
            receive_thread.join()

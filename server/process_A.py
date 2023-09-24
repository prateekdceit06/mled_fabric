# Process A
import hashlib
import sys
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
# import subprocess

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

        self.file_transfer_start_time = None
        self.file_transfer_end_time = None
        if self.process_config['packet_error_rate'] > 0:
            self.packet_error_count = int(
                1/self.process_config['packet_error_rate'])
        else:
            self.packet_error_count = 0

        self.last_packet_acked = -1

    def manager_client(self, client_socket):
        control_msg = client_socket.recv(4).decode('utf-8')
        # time.sleep(10)
        logging.info(
            f"Received {control_msg} from manager.")
        # self.terminate_event.set()

    def read_file_to_buffer(self, file_path):

        with open(file_path, 'rb') as f:
            seq_num = -1
            while not self.terminate_event.is_set():
                seq_num += 1
                seq_num %= (2*self.process_config['window_size'])
                with self.received_buffer_not_full_condition:
                    while self.received_data_buffer.is_full() and not self.terminate_event.is_set():
                        # Wait until there's space in the buffer
                        logging.info(pc.PrintColor.print_in_blue_back(
                            f"No space in Receiving buffer"))
                        self.received_buffer_not_full_condition.wait(5)
                        logging.info(pc.PrintColor.print_in_blue_back(
                            f"Received notification that there is space in Receiving buffer"))

                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    self.received_data_buffer.add(chunk)
                    self.received_buffer_not_full_condition.notify(2)
                    logging.info(pc.PrintColor.print_in_yellow_back(
                        f"Send notification that there is chunk in Receiving buffer"))

                    logging.info(pc.PrintColor.print_in_red_back(
                        f"Read chunk {seq_num} of size {len(chunk)} to buffer"))
                    # logging.info(f"CHUNK: {chunk}")

    def prepare_packet_to_send(self):
        seq_num = -1
        while not self.terminate_event.is_set():
            while self.received_data_buffer.is_empty() and not self.terminate_event.is_set():
                # Wait until there's data in the buffer
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"No data in receiving buffer"))
                with self.received_buffer_not_full_condition:
                    self.received_buffer_not_full_condition.wait(5)
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"Received notification that there is data in receiving buffer"))

            if not self.terminate_event.is_set():

                chunk = None
                with self.received_buffer_not_full_condition:
                    chunk = self.received_data_buffer.get()
                    self.received_data_buffer.remove()
                    # Notify read_file_to_buffer that there's space now
                    self.received_buffer_not_full_condition.notify(2)

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

                    # Use the condition for the sending buffer
                    with self.sending_buffer_not_full_condition:
                        # Wait if the sending buffer is full
                        while self.sending_data_buffer.is_full() and not self.terminate_event.is_set():
                            logging.info(pc.PrintColor.print_in_yellow_back(
                                f"No space in sending buffer"))
                            self.sending_buffer_not_full_condition.wait(5)
                            logging.info(pc.PrintColor.print_in_yellow_back(
                                f"Received Notification that there is space in sending buffer"))

                    with self.sending_data_buffer_lock:
                        self.sending_data_buffer.add(packet)
                        logging.info(pc.PrintColor.print_in_green_back(
                            f"Added packet {seq_num} of size {size_of_chunk} to sending buffer"))
                        self.sending_data_buffer_condition.notify()
                        logging.info(pc.PrintColor.print_in_yellow_back(
                            f"Send Notification that there is a packet to send in sending buffer"))

    def send_packet_from_buffer(self, out_socket, out_addr):
        last_sent_seq_num = -1  # Initialize to an invalid sequence number
        packet_number = 0

        while not self.terminate_event.is_set():
            with self.sending_data_buffer_condition:
                while self.sending_data_buffer.is_empty() and not self.terminate_event.is_set():

                    self.file_transfer_end_time = time.time()
                    file_transfer_time = self.file_transfer_end_time - self.file_transfer_start_time
                    logging.info(pc.PrintColor.print_in_green_back(
                        f"Total file transfer time is {file_transfer_time:.4f} seconds"))
                    logging.info(pc.PrintColor.print_in_blue_back(
                        "No packet to send in sending buffer"))

                    self.sending_data_buffer_condition.wait(5)
                    logging.info(pc.PrintColor.print_in_blue_back(
                        "Received notification that there is a packet to send in sending buffer or urgent packet sent successfully."))

                seq_num_of_packet_to_send = (
                    last_sent_seq_num + 1) % (2*self.process_config['window_size'])
                packet = self.sending_data_buffer.get_by_sequence(
                    seq_num_of_packet_to_send)
                accepted_packets_in_flight = [(self.last_packet_acked + 1 + i) % (
                    2 * self.process_config['window_size']) for i in range(self.process_config['window_size'])]
                if packet is None or seq_num_of_packet_to_send not in accepted_packets_in_flight:
                    continue

            if self.packet_error_count > 0 and (packet_number % self.packet_error_count) == 0:
                logging.info(pc.PrintColor.print_in_cyan_back(
                    f"Packet {packet.seq_num} of size {packet.header.size_of_data + packet.header.get_size()} is corrupted"))
                new_chunk = super().add_error(packet.chunk, self.process_config['error_introduction_location'],
                                              self.process_config['error_detection_method']['method'], self.process_config['error_detection_method']['parameter'])
                new_packet = Packet(packet.header, new_chunk)
                packet = new_packet
            packet_number += 1

            with self.urgent_send_condition:
                super().send_data(out_socket, packet)
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"Sent packet {packet.seq_num} of size {packet.header.size_of_data + packet.header.get_size()}" +
                    f" (Data: {packet.header.size_of_data} Header: {packet.header.get_size()}) to {packet.header.dest} from {packet.header.src}"))

                while self.urgent_send_in_progress and packet.header.last_packet:
                    logging.info(pc.PrintColor.print_in_purple_back(
                        "Urgent packet is being sent"))
                    self.urgent_send_condition.wait()
                    logging.info(pc.PrintColor.print_in_purple_back(
                        f"Notification sent that urgent sending completed for {packet.seq_num}"))

                last_sent_seq_num = packet.seq_num

    def receive_ack(self, in_ack_socket, out_data_socket, out_addr):

        positive_ack_seq_num = {}
        expected_ack = -1

        while True:
            # time.sleep(0.1)
            received_seq_num, received_src, received_dest, _, received_size_of_chunk, received_ack_byte, _, _, _ = super(
            ).receive_data(in_ack_socket)

            if received_ack_byte == 5:
                logging.info(pc.PrintColor.print_in_red_back(
                    f"Received DONE signal ({received_ack_byte})"))
                self.terminate_event.set()
                break

            ack_string = "ACK" if received_ack_byte == 1 else "NACK" if received_ack_byte == 3 else "CLOSE"
            logging.info(pc.PrintColor.print_in_purple_back(
                f"Received {ack_string} for packet {received_seq_num} addressed to {received_dest} from {received_src}"))

            with self.sending_buffer_not_full_condition:

                if received_ack_byte == 1:
                    # logging.info(pc.PrintColor.print_in_green_back("Sending data buffer before remove" +
                    #                                                self.sending_data_buffer.print_buffer()))
                    packet = self.sending_data_buffer.remove_by_sequence(
                        received_seq_num)
                    # logging.info(pc.PrintColor.print_in_cyan_back("Sending data buffer after remove" +
                    #                                               self.sending_data_buffer.print_buffer()))
                    if packet:
                        logging.info(pc.PrintColor.print_in_yellow_back(
                            f"Removed packet {packet.seq_num} from sending buffer"))
                    # Notify send_packet_from_buffer that there might be space now
                        self.sending_buffer_not_full_condition.notify()
                        logging.info(pc.PrintColor.print_in_yellow_back(
                            f"Notification sent that sending buffer has space"))
                    else:
                        logging.info(pc.PrintColor.print_in_red_back(
                            f"could not find packet with seq num: {received_seq_num}"))

                    key = received_seq_num

                    while key in positive_ack_seq_num:
                        key += self.process_config['window_size']

                    positive_ack_seq_num[key] = received_seq_num

                    while (expected_ack + 1) in positive_ack_seq_num:
                        expected_ack += 1
                        self.last_packet_acked = positive_ack_seq_num[expected_ack]

                    # logging.info(pc.PrintColor.print_in_green_back(
                    #     f"Last packet acked is {self.last_packet_acked}"))

                    # if len(all_received_ack_seq_num) == self.process_config['window_size']:
                    #     logging.info(pc.PrintColor.print_in_green_back(
                    #         f"All packets in flight have been acked."))
                    #     self.last_packet_acked = max(
                    #         all_received_ack_seq_num)
                    #     all_received_ack_seq_num = []

                elif received_ack_byte == 3:
                    self.urgent_send_in_progress = True
                    # logging.info(pc.PrintColor.print_in_green_back("Sending data buffer before sending" +
                    #                                                self.sending_data_buffer.print_buffer()))
                    logging.info(pc.PrintColor.print_in_purple_back(
                        f"Urgent sending flag set to true for packet {received_seq_num}"))
                    with self.urgent_send_condition:
                        logging.info(pc.PrintColor.print_in_purple_back(
                            f"Requesting the socket to send packet {received_seq_num} again"))
                        packet = self.sending_data_buffer.get_by_sequence(
                            received_seq_num)
                        # logging.info(packet)

                        super().send_data(out_data_socket, packet)
                        logging.info(pc.PrintColor.print_in_purple_back(
                            f"Re-sent packet {received_seq_num} of size {len(packet.chunk)} to {received_src}"))
                        # logging.info(pc.PrintColor.print_in_cyan_back("Sending data buffer after sending" +
                        #                                               self.sending_data_buffer.print_buffer()))
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

    def calculate_file_hash(self, file_path, hash_method):
        try:
            hash_func = getattr(hashlib, hash_method)
        except AttributeError:
            raise ValueError(f"Invalid hash method: {hash_method}")

        with open(file_path, 'rb') as file:
            file_data = file.read()
            file_hash = hash_func(file_data).hexdigest()

        return file_hash

    def create_setup_packet(self, file_hash):
        size_of_chunk = len(file_hash)
        seq_num = 0
        src = self.process_config['name']
        dest = self.process_config['right_neighbor']
        error_detection_method = self.process_config['error_detection_method']['method']
        parameter = self.process_config['error_detection_method']['parameter']
        check_value = super().get_value_to_check(
            file_hash.encode(), error_detection_method, parameter)
        errors = []

        last_packet = True
        header = Header(seq_num, src, dest, check_value,
                        size_of_chunk, 0, errors, last_packet)
        packet = Packet(header, file_hash.encode())
        return packet

    def check_setup(self, file_hash):
        logging.info(pc.PrintColor.print_in_purple_back("Starting setup..."))
        setup_packet = self.create_setup_packet(file_hash)

        super().send_data(self.out_data_socket, setup_packet)

        _, _, _, _, _, received_ack_byte, _, _, _ = super().receive_data(self.in_ack_socket)

        if received_ack_byte == 1:
            logging.info(pc.PrintColor.print_in_green_back(
                "Setup Successful.. Sending File..."))
            return True
        else:
            logging.info(pc.PrintColor.print_in_red_back(
                "Setup Unsuccessful"))
            return False

    def create_out_sockets(self, connections, timeout, ip, client_socket):
        self.create_out_data_socket(connections, timeout, ip)
        self.create_out_ack_socket(connections, timeout, ip)

        while True:
            socekts_ready = super().are_sockets_alive(self.socket_list)
            if socekts_ready:
                break
            else:
                time.sleep(self.process_config['delay_process_socket'])

        path = os.path.abspath(__file__)
        directory = os.path.dirname(path)
        # command = [
        #     "scp",
        #     "-o", "StrictHostKeyChecking=no",
        #     "-i", "/home/ubuntu/mledASU",
        #     "asarabi3@192.168.1.1:/home/collection_*",
        #     "/home/ubuntu/file1"
        # ]

        # result = subprocess.run(command, capture_output=True, text=True)

        # # Check if the command was successful
        # if result.returncode == 0:
        #     print("Command executed successfully!")
        # else:
        #     print("Command failed!")
        #     print("Output:", result.stdout)
        #     print("Error:", result.stderr)

        filename = self.process_config['filename']
        file_path = os.path.join(directory, filename)

        file_hash = self.calculate_file_hash(
            file_path, self.process_config['hash_method'])

        setup_start_time = time.time()
        is_correct = self.check_setup(file_hash)
        setup_end_time = time.time()  # Get the current time after executing the function

        # Calculate the difference between the start and end times
        setup_time = setup_end_time - setup_start_time
        logging.info(pc.PrintColor.print_in_yellow_back(
            f"Network setup time is {setup_time:.4f} seconds"))
        time.sleep(self.process_config['delay_process_socket'])

        if is_correct:

            manager_client_thread = threading.Thread(
                args=(client_socket,), target=self.manager_client, name="ManagerlientThread")
            manager_client_thread.daemon = True
            manager_client_thread.start()

            self.file_transfer_start_time = time.time()

            read_thread = threading.Thread(args=(file_path,),
                                           target=self.read_file_to_buffer, name="ReadFromFileThread")
            read_thread.daemon = True
            read_thread.start()

            # Thread for prepare_packet_to_send
            prepare_thread = threading.Thread(
                target=self.prepare_packet_to_send, name="PreparePacketThread")
            prepare_thread.daemon = True
            prepare_thread.start()

            # Thread for send_packet_from_buffer
            send_thread = threading.Thread(args=(self.out_data_socket, self.out_data_addr,),
                                           target=self.send_packet_from_buffer, name="SendPacketThread")
            send_thread.daemon = True
            send_thread.start()

            # Thread for receive_ack
            receive_thread = threading.Thread(
                target=self.receive_ack, name="ReceiveAckThread", args=(self.in_ack_socket, self.out_data_socket, self.out_data_addr,))
            receive_thread.daemon = True
            receive_thread.start()

            manager_client_thread.join()
            logging.info(pc.PrintColor.print_in_red_back(
                "Manager client thread ended execution"))
            read_thread.join()
            logging.info(pc.PrintColor.print_in_red_back(
                "Read thread ended execution."))
            prepare_thread.join()
            logging.info(pc.PrintColor.print_in_red_back(
                "Prepare thread ended execution."))
            send_thread.join()
            logging.info(pc.PrintColor.print_in_red_back(
                "Send thread ended execution."))
            receive_thread.join()
            logging.info(pc.PrintColor.print_in_red_back(
                "Receive thread ended execution."))

            done_msg = ("DONE").encode('utf-8')

            size_of_chunk = len(done_msg)
            seq_num = 0
            src = self.process_config['name']
            dest = self.process_config['right_neighbor']
            error_detection_method = self.process_config['error_detection_method']['method']
            parameter = self.process_config['error_detection_method']['parameter']
            check_value = super().get_value_to_check(
                done_msg, error_detection_method, parameter)
            errors = []
            last_packet = True
            header = Header(seq_num, src, dest, check_value,
                            size_of_chunk, 0, errors, last_packet)
            packet = Packet(header, done_msg)

            self.urgent_send_in_progress = True
            # with self.urgent_send_condition:
            super().send_data(self.out_data_socket, packet)
            # self.urgent_send_in_progress = False
            # self.urgent_send_condition.notify()

            logging.info(pc.PrintColor.print_in_red_back(
                "Sending DONE."))

            time.sleep(10)

            for sock in self.socket_list:
                getattr(self, sock).close()

        else:
            sys.exit(1)

# Process E

from process import ProcessHandlerBase
from send_receive import SendReceive

import utils
import logging
import threading
import time
from circular_buffer import CircularBuffer

from header import Header
from packet import Packet
from utils import logging_format as logging_format
import print_colour as pc
import logging

logging.basicConfig(format=logging_format, level=logging.INFO)


class ProcessHandler(ProcessHandlerBase, SendReceive):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)
        self.terminate_event = terminate_event
        self.out_data_socket_up = None
        self.out_data_addr_up = None
        self.out_data_socket_down = None
        self.out_data_addr_down = None
        self.out_ack_socket_up = None
        self.out_ack_addr_up = None
        self.out_ack_socket_down = None
        self.out_ack_addr_down = None
        self.in_data_socket_up = None
        self.in_data_socket_down = None
        self.in_ack_socket_up = None
        self.in_ack_socket_down = None
        self.socket_list = [
            'out_data_socket_up',
            'out_data_socket_down',
            'out_ack_socket_up',
            'out_ack_socket_down',
            'in_data_socket_up',
            'in_data_socket_down',
            'in_ack_socket_up',
            'in_ack_socket_down'
        ]
        self.chunk_size = self.process_config['mtu']

        if self.process_config['parent'] is not None:
            self.sending_data_up_buffer = CircularBuffer(
                self.process_config['window_size'])
            self.received_data_up_buffer = CircularBuffer(
                self.process_config['window_size'])

            self.received_data_up_buffer_lock = threading.Lock()
            self.received_up_buffer_not_full_condition = threading.Condition(
                self.received_data_up_buffer_lock)

            self.sending_data_up_buffer_lock = threading.Lock()
            self.sending_data_up_buffer_condition = threading.Condition(
                self.sending_data_up_buffer_lock)
            self.sending_up_buffer_not_full_condition = threading.Condition(
                self.sending_data_up_buffer_lock
            )

        self.send_lock = threading.Lock()
        self.urgent_send_condition = threading.Condition(
            self.send_lock)
        self.urgent_send_in_progress = False

        self.sending_data_down_buffer = CircularBuffer(
            self.process_config['window_size'])
        self.received_data_down_buffer = CircularBuffer(
            self.process_config['window_size'])

        self.received_data_down_buffer_lock = threading.Lock()
        self.received_down_buffer_not_full_condition = threading.Condition(
            self.received_data_down_buffer_lock)

        self.sending_data_down_buffer_lock = threading.Lock()
        self.sending_data_down_buffer_condition = threading.Condition(
            self.sending_data_down_buffer_lock)
        self.sending_down_buffer_not_full_condition = threading.Condition(
            self.sending_data_down_buffer_lock
        )

        if self.process_config['packet_error_rate'] > 0:
            self.packet_error_count = int(
                1/self.process_config['packet_error_rate'])
        else:
            self.packet_error_count = 0

        self.last_seq_num = -1
        self.last_packet_acked = -1

    def manager_client(self, client_socket):
        control_msg = client_socket.recv(4).decode('utf-8')
        time.sleep(10)
        logging.info(
            f"Received {control_msg} from manager.")

    def receive_data(self, in_socket, out_ack_socket, received_buffer_not_full_condition, received_data_buffer):
        # seq_num = -1

        while True:
            data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data = self.receive_packets(
                in_socket, out_ack_socket)

            try:
                if data_to_forward.decode('utf-8') == 'DONE':
                    self.terminate_event.set()
                    break
            except:
                pass

            logging.info(pc.PrintColor.print_in_black_back(
                f"Received chunk of size {len(data_to_forward)}"))

            if received_src.decode() != self.process_config['parent']:
                if self.process_config['child'] is not None:
                    self.handle_process_with_child(out_ack_socket, data_to_forward, packet_to_ack, received_src, received_dest,
                                                   received_seq_num, received_buffer_not_full_condition, received_data_buffer)
                else:
                    self.handle_process_with_no_child(out_ack_socket, data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num,
                                                      received_buffer_not_full_condition, received_data_buffer, received_check_value_data)
            else:
                self.add_to_buffer(
                    data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num, received_src)

    def receive_packets(self, in_socket, out_ack_socket):
        data_to_forward = b''
        packet_to_ack = []
        while True:
            received_seq_num, received_src, received_dest, received_check_value_data, received_chunk_data, received_ack_byte, fixed_data, received_errors_data, received_last_packet = super().receive_data(in_socket)
            packet_to_ack.append(received_seq_num)

            try:
                if received_chunk_data.decode() == 'DONE':
                    return received_chunk_data, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data
            except:
                pass

            if received_src.decode() == self.process_config['parent']:
                data_to_forward += (fixed_data + received_check_value_data +
                                    received_errors_data + received_chunk_data)
                if len(data_to_forward) >= self.chunk_size or received_last_packet:
                    break
            elif received_src.decode() == self.process_config['left_neighbor']:

                data_to_forward += received_chunk_data
                if len(data_to_forward) >= self.chunk_size or received_last_packet:
                    break
            else:
                logging.info(pc.PrintColor.print_in_yellow_back(
                    f"Sending positive ACK for seq_num: {received_seq_num} to {self.process_config['child']} from {self.process_config['name']}"))
                self.send_ack(received_seq_num, (self.process_config['name'].encode()),
                              (self.process_config['child'].encode()), 1, out_ack_socket)
                data_to_forward += received_chunk_data
                if received_last_packet:
                    break

        return data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data

    def handle_process_with_child(self, out_ack_socket, data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer):
        inner_packet = super().decapsulate(data_to_forward)
        data_to_forward = inner_packet.chunk
        received_check_value_data = inner_packet.header.check_value.encode()
        received_seq_num = inner_packet.header.seq_num
        received_src_inner = inner_packet.header.src.encode()
        received_dest_inner = inner_packet.header.dest.encode()

        no_corruption = super().verify_value(data_to_forward, received_check_value_data.decode(),
                                             self.process_config['error_detection_method']['method'],
                                             self.process_config['error_detection_method']['parameter'])

        if no_corruption:
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Sending positive ACK for seq_num: {received_seq_num} to {received_src_inner} from {received_dest_inner}"))

            self.send_ack(received_seq_num, received_dest_inner,
                          received_src_inner, 1, out_ack_socket)

            self.add_to_buffer(
                data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num, received_src)
        else:
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Sending negative ACK for seq_num: {received_seq_num} to {received_src_inner} from {received_dest_inner}"))
            self.send_ack(received_seq_num, received_dest_inner,
                          received_src_inner, 3, out_ack_socket)

    def handle_process_with_no_child(self, out_ack_socket, data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data):
        no_corruption = super().verify_value(data_to_forward, received_check_value_data.decode(),
                                             self.process_config['error_detection_method']['method'],
                                             self.process_config['error_detection_method']['parameter'])
        if no_corruption:

            # for seq_num in packet_to_ack:
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Sending positive ACK for seq_num: {received_seq_num} to {received_src} from {received_dest}"))
            self.send_ack(
                received_seq_num, received_dest, received_src, 1, out_ack_socket)

            self.add_to_buffer(
                data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num, received_src)
        else:
            # for seq_num in packet_to_ack:
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Sending negative ACK for seq_num: {received_seq_num} to {received_src} from {received_dest}"))
            self.send_ack(
                received_seq_num, received_dest, received_src, 3, out_ack_socket)

    def add_to_buffer(self, data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num, received_src):

        for i in range(0, len(data_to_forward), self.chunk_size):

            if received_src.decode() == self.process_config['parent']:
                seq_num = self.last_seq_num
                seq_num += 1
                seq_num %= (2*self.process_config['window_size'])
                self.last_seq_num = seq_num
            else:
                seq_num = received_seq_num

            chunk = data_to_forward[i:i+self.chunk_size]

            with received_buffer_not_full_condition:
                while received_data_buffer.is_full():
                    # Wait until there's space in the buffer
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"No space in Receiveing buffer"))
                    received_buffer_not_full_condition.wait()
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"Received notification that there is space in Receiving buffer"))

                if not chunk:
                    break
                header = Header(seq_num)
                packet = Packet(header, chunk)
                received_data_buffer.add(packet)
                received_buffer_not_full_condition.notify(2)
                logging.info(pc.PrintColor.print_in_yellow_back(
                    f"Send notification that there is chunk in Receiving buffer"))
                logging.info(pc.PrintColor.print_in_red_back(
                    f"Received chunk {seq_num} of size {len(chunk)} to buffer"))

    def prepare_packet_to_send(self, received_buffer_not_full_condition, received_data_buffer, sending_buffer_not_full_condition,
                               sending_data_buffer, sending_data_buffer_lock, sending_data_buffer_condition):
        # seq_num = -1
        index = -1
        while not self.terminate_event.is_set():
            while received_data_buffer.is_empty() and not self.terminate_event.is_set():
                # Wait until there's data in the buffer
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"No data in receiving buffer"))
                with received_buffer_not_full_condition:
                    received_buffer_not_full_condition.wait(5)
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"Received notification that there is data in receiving buffer"))

            received_packet = None
            with received_buffer_not_full_condition:
                while True:
                    accepted_packets_in_flight = [(self.last_packet_acked + 1 + i) % (
                        2 * self.process_config['window_size']) for i in range(self.process_config['window_size'])]
                    # logging.info(pc.PrintColor.print_in_red_back(
                    #     f"\nlast acked packet: {self.last_packet_acked}\naccepted packets in flight: {accepted_packets_in_flight}\n"))

                    index += 1
                    recieved_seq_num = accepted_packets_in_flight[index % len(
                        accepted_packets_in_flight)]
                    received_packet = received_data_buffer.get_by_sequence(
                        recieved_seq_num)
                    if received_packet is not None or self.terminate_event.is_set():
                        break
                index = -1
                # logging.info(pc.PrintColor.print_in_cyan_back(
                #     f"Received Buffer before removing: {received_data_buffer.print_buffer()}"))
                packet = received_data_buffer.remove_by_sequence(
                    recieved_seq_num)
                # logging.info(f"PAcket: {packet}")
                # logging.info(pc.PrintColor.print_in_cyan_back(
                #     f"Received Buffer after removing: {received_data_buffer.print_buffer()}"))

                # Notify read_file_to_buffer that there's space now
                received_buffer_not_full_condition.notify(2)
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"Notified that there is space in receiving buffer"))

            if received_packet:
                chunk = received_packet.chunk
                seq_num = received_packet.header.seq_num
                size_of_chunk = len(chunk)
                # seq_num += 1
                # seq_num %= (2*self.process_config['window_size'])
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

                with sending_buffer_not_full_condition:  # Use the condition for the sending buffer
                    while sending_data_buffer.is_full() and not self.terminate_event.is_set():  # Wait if the sending buffer is full
                        logging.info(pc.PrintColor.print_in_yellow_back(
                            f"No space in sending buffer"))
                        sending_buffer_not_full_condition.wait(5)
                        logging.info(pc.PrintColor.print_in_yellow_back(
                            f"Received Notification that there is space in sending buffer"))

                with sending_data_buffer_lock:
                    sending_data_buffer.add(packet)
                    logging.info(pc.PrintColor.print_in_green_back(
                        f"Added packet {seq_num} of size {size_of_chunk} to sending buffer"))
                    sending_data_buffer_condition.notify()
                    logging.info(pc.PrintColor.print_in_yellow_back(
                        f"Send Notification that there is a packet to send in sending buffer"))

    def send_packet_from_buffer(self, out_socket, out_addr, sending_data_buffer_condition, sending_data_buffer):
        last_sent_seq_num = -1  # Initialize to an invalid sequence number
        packet_number = 0
        while not self.terminate_event.is_set():

            with sending_data_buffer_condition:
                while self.urgent_send_in_progress or (sending_data_buffer.is_empty() and not self.terminate_event.is_set()):
                    # Wait until there's a packet to send or an urgent send is needed
                    if self.urgent_send_in_progress:
                        logging.info(pc.PrintColor.print_in_blue_back(
                            "Urgent packet is being sent"))
                    elif sending_data_buffer.is_empty():
                        logging.info(pc.PrintColor.print_in_blue_back(
                            "No packet to send in sending buffer"))
                    sending_data_buffer_condition.wait(5)
                    logging.info(pc.PrintColor.print_in_blue_back(
                        "Received notification that there is a packet to send in sending buffer or urgent packet sent successfully."))
                seq_num_of_packet_to_send = (
                    last_sent_seq_num + 1) % (2*self.process_config['window_size'])
                packet = sending_data_buffer.get_by_sequence(
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

    def receive_ack(self, in_data_socket, out_data_socket, out_ack_socket, out_addr,
                    sending_data_buffer_condition, sending_data_buffer, sending_buffer_not_full_condition):
        while True:
            # time.sleep(0.1)
            received_seq_num, received_src, received_dest, _, received_size_of_chunk, received_ack_byte, _, _, _ = super(
            ).receive_data(in_data_socket)

            ack_string = "ACK" if received_ack_byte == 1 else "NACK" if received_ack_byte == 3 else "CLOSE"
            logging.info(pc.PrintColor.print_in_purple_back(
                f"Received {ack_string} for packet {received_seq_num} addressed to {received_dest} from {received_src}"))

            if received_dest.decode() == self.process_config['name']:
                with sending_buffer_not_full_condition:

                    if received_ack_byte == 1:
                        # logging.info(pc.PrintColor.print_in_green_back("Sending data buffer before remove" +
                        #                                                sending_data_buffer.print_buffer()))
                        packet = sending_data_buffer.remove_by_sequence(
                            received_seq_num)
                        # logging.info(pc.PrintColor.print_in_cyan_back("Sending data buffer after remove" +
                        #                                               sending_data_buffer.print_buffer()))
                        if packet:
                            logging.info(pc.PrintColor.print_in_yellow_back(
                                f"Removed packet {packet.seq_num} from sending buffer"))
                        # Notify send_packet_from_buffer that there might be space now

                            sending_buffer_not_full_condition.notify()
                            logging.info(pc.PrintColor.print_in_yellow_back(
                                f"Notification sent that sending buffer has space"))
                        else:
                            logging.info(pc.PrintColor.print_in_red_back(
                                f"could not find packet with seq num: {received_seq_num}"))

                        self.last_packet_acked = received_seq_num

                    elif received_ack_byte == 3:
                        self.urgent_send_in_progress = True
                    # logging.info(pc.PrintColor.print_in_green_back("Sending data buffer before sending" +
                    #                                                self.sending_data_buffer.print_buffer()))
                        logging.info(pc.PrintColor.print_in_purple_back(
                            f"Urgent sending flag set to true for packet {received_seq_num}"))
                        with self.urgent_send_condition:
                            logging.info(pc.PrintColor.print_in_purple_back(
                                f"Requesting the socket to send packet {received_seq_num} again"))
                            packet = sending_data_buffer.get_by_sequence(
                                received_seq_num)
                            # logging.info(packet)

                            super().send_data(out_data_socket, packet)
                            logging.info(pc.PrintColor.print_in_purple_back(
                                f"Re-sent packet {received_seq_num} of size {len(packet.chunk)} to {received_src}"))
                            # logging.info(pc.PrintColor.print_in_cyan_back("Sending data buffer after sending" +
                            #                                               self.sending_data_buffer.print_buffer()))
                            self.urgent_send_in_progress = False
                            self.urgent_send_condition.notify()
            else:
                # send ack to its out ack socket
                logging.info(pc.PrintColor.print_in_purple_back(
                    f"Forwarding {ack_string} for packet {received_seq_num} addressed to {received_dest} from {received_src}"))
                self.send_ack(received_seq_num, received_src,
                              received_dest, received_ack_byte, out_ack_socket)
                if received_ack_byte == 5:
                    break

    def send_ack(self, seq_num, src, dest, type, out_ack_socket):
        time.sleep(self.process_config['pause_time_before_ack'])
        ack_header = Header(
            seq_num, src.decode(), dest.decode(), "", 0, type, [], True)
        ack_packet = Packet(ack_header, b'')
        super().send_ack(out_ack_socket, ack_packet)

    def in_socket_up_handler(self, in_socket_up, retries, delay, up_host, up_port, socket_type):
        if socket_type == "data":
            in_data_socket_up_generator = super().connect_in_socket(
                in_socket_up, retries, delay, up_host, up_port, socket_type)
            self.in_data_socket_up = next(in_data_socket_up_generator, None)
        elif socket_type == "ack":
            in_ack_socket_up_generator = super().connect_in_socket(
                in_socket_up, retries, delay, up_host, up_port, socket_type)
            self.in_ack_socket_up = next(in_ack_socket_up_generator, None)

    def in_socket_down_handler(self, in_socket_down, retries, delay, down_host, down_port, socket_type):
        if socket_type == "data":
            in_data_socket_down_generator = super().connect_in_socket(
                in_socket_down, retries, delay, down_host, down_port, socket_type)
            self.in_data_socket_down = next(
                in_data_socket_down_generator, None)
        elif socket_type == "ack":
            in_ack_socket_down_generator = super().connect_in_socket(
                in_socket_down, retries, delay, down_host, down_port, socket_type)
            self.in_ack_socket_down = next(in_ack_socket_down_generator, None)

    def create_data_route(self, retries, delay):
        in_socket_up = None
        if self.process_config['parent'] is not None:
            in_socket_up = utils.create_client_socket(
                self.process_config['ip'], 0)
            up_host, up_port = self.find_data_host_port_up()
            self.in_socket_up_handler(
                in_socket_up, retries, delay, up_host, up_port, "data")

        in_socket_down = utils.create_client_socket(
            self.process_config['ip'], 0)
        down_host, down_port = self.find_data_host_port_down()
        self.in_socket_down_handler(
            in_socket_down, retries, delay, down_host, down_port, "data")

    def find_data_host_port_down(self):
        if self.process_config['child'] is not None:
            host, port = self.process_config['child_ip'], self.process_config['child_data_port'] + 100
        else:
            host, port = self.process_config['left_neighbor_ip'], self.process_config['left_neighbor_data_port']
        return host, port

    def find_data_host_port_up(self):
        host, port = self.process_config['parent_ip'], self.process_config['parent_data_port']
        return host, port

    def create_ack_route(self, retries, delay):
        in_socket_up = None
        if self.process_config['parent'] is not None:
            in_socket_up = utils.create_client_socket(
                self.process_config['ip'], 0)
            up_host, up_port = self.find_ack_host_port_up()
            self.in_socket_up_handler(
                in_socket_up, retries, delay, up_host, up_port, "ack")

        in_socket_down = utils.create_client_socket(
            self.process_config['ip'], 0)
        down_host, down_port = self.find_ack_host_port_down()
        self.in_socket_down_handler(
            in_socket_down, retries, delay, down_host, down_port, "ack")

    def find_ack_host_port_down(self):
        if self.process_config['child'] is not None:
            host, port = self.process_config['child_ip'], self.process_config['child_ack_port'] + 100
        else:
            host, port = self.process_config['right_neighbor_ip'], self.process_config['right_neighbor_ack_port']
        return host, port

    def find_ack_host_port_up(self):
        host, port = self.process_config['parent_ip'], self.process_config['parent_ack_port']
        return host, port

    def create_out_socket(self, connections, timeout, ip, port, socket_type):

        if socket_type == "data":
            out_data_socket_down_generator = super().create_out_socket(
                connections, timeout, ip, port, socket_type)
            self.out_data_socket_down, self.out_data_addr_down = next(
                out_data_socket_down_generator, (None, None))
        elif socket_type == "ack":
            out_ack_socket_down_generator = super().create_out_socket(
                connections, timeout, ip, port, socket_type)
            self.out_ack_socket_down, self.out_ack_addr_down = next(
                out_ack_socket_down_generator, (None, None))

        if self.process_config['parent'] is not None:
            port = port + 100
            if socket_type == "data":
                out_data_socket_up_generator = super().create_out_socket(
                    connections, timeout, ip, port, socket_type)
                self.out_data_socket_up, self.out_data_addr_up = next(
                    out_data_socket_up_generator, (None, None))
            elif socket_type == "ack":
                out_ack_socket_up_generator = super().create_out_socket(
                    connections, timeout, ip, port, socket_type)
                self.out_ack_socket_up, self.out_ack_addr_up = next(
                    out_ack_socket_up_generator, (None, None))

    def check_setup(self):
        if self.process_config['parent'] is None:
            _, _, _, received_check_value_data, received_chunk_data, _, fixed_data, received_errors_data, _ = super(
            ).receive_data(self.in_data_socket_down)
            data_to_forward = fixed_data + received_check_value_data + \
                received_errors_data + received_chunk_data
            packet_to_forward = super().decapsulate(data_to_forward)
            super().send_data(self.out_data_socket_down, packet_to_forward)

            _, received_src, received_dest, _, _, received_ack_byte, _, _, _ = super(
            ).receive_data(self.in_ack_socket_down)

            if received_ack_byte == 1:
                self.send_ack(0, received_src,
                              received_dest, 1, self.out_ack_socket_down)
                return True

            return False
        else:
            _, _, _, received_check_value_data, received_chunk_data, _, fixed_data, received_errors_data, _ = super(
            ).receive_data(self.in_data_socket_down)
            data_to_forward = fixed_data + received_check_value_data + \
                received_errors_data + received_chunk_data
            packet_to_forward = super().decapsulate(data_to_forward)
            super().send_data(self.out_data_socket_up, packet_to_forward)

            _, _, _, received_check_value_data, received_chunk_data, _, fixed_data, received_errors_data, _ = super(
            ).receive_data(self.in_data_socket_up)
            data_to_forward = fixed_data + received_check_value_data + \
                received_errors_data + received_chunk_data
            packet_to_forward = super().decapsulate(data_to_forward)
            super().send_data(self.out_data_socket_down, packet_to_forward)

            _, received_src, received_dest, _, _, received_ack_byte, _, _, _ = super(
            ).receive_data(self.in_ack_socket_down)

            if received_ack_byte == 1:
                self.send_ack(0, received_src,
                              received_dest, 1, self.out_ack_socket_up)

            _, received_src, received_dest, _, _, received_ack_byte, _, _, _ = super(
            ).receive_data(self.in_ack_socket_up)

            if received_ack_byte == 1:
                self.send_ack(0, received_src,
                              received_dest, 1, self.out_ack_socket_down)
                return True

            return False

    def create_out_sockets(self, connections, timeout, ip, client_socket):
        port = self.process_config['data_port']
        self.create_out_socket(connections, timeout, ip, port, "data")
        port = self.process_config['ack_port']
        self.create_out_socket(connections, timeout, ip, port, "ack")

        if self.process_config['parent'] is None:
            self.socket_list = [
                'out_data_socket_down',
                'out_ack_socket_down',
                'in_data_socket_down',
                'in_ack_socket_down'
            ]

        while True:
            socekts_ready = super().are_sockets_alive(self.socket_list)
            if socekts_ready:
                break
            else:
                time.sleep(self.process_config['delay_process_socket'])

        is_correct = self.check_setup()

        if is_correct:

            if self.process_config['parent'] is None:

                # manager_client_thread = threading.Thread(
                #     args=(client_socket,), target=self.manager_client, name="ManagerlientThread")
                # manager_client_thread.daemon = True
                # manager_client_thread.start()

                receive_down_data_thread = threading.Thread(args=(self.in_data_socket_down, self.out_ack_socket_down,
                                                                  self.received_down_buffer_not_full_condition,
                                                                  self.received_data_down_buffer,),
                                                            target=self.receive_data, name="ReceiveDataDownThread")
                receive_down_data_thread.start()

                # Thread for prepare_packet_to_send
                prepare_down_thread = threading.Thread(args=(self.received_down_buffer_not_full_condition, self.received_data_down_buffer,
                                                             self.sending_down_buffer_not_full_condition, self.sending_data_down_buffer,
                                                             self.sending_data_down_buffer_lock, self.sending_data_down_buffer_condition,),
                                                       target=self.prepare_packet_to_send, name="PreparePacketDownThread")
                prepare_down_thread.start()

                # Thread for send_packet_from_buffer
                send_down_thread = threading.Thread(args=(self.out_data_socket_down, self.out_data_addr_down,
                                                          self.sending_data_down_buffer_condition, self.sending_data_down_buffer,),
                                                    target=self.send_packet_from_buffer, name="SendPacketDownThread")
                send_down_thread.start()

                # Thread for receive_ack
                receive_ack_down_thread = threading.Thread(args=(self.in_ack_socket_down, self.out_data_socket_down, self.out_ack_socket_down,
                                                                 self.out_data_addr_down,
                                                                 self.sending_data_down_buffer_condition, self.sending_data_down_buffer,
                                                                 self.sending_down_buffer_not_full_condition,),
                                                           target=self.receive_ack, name="ReceiveAckDownThread")
                receive_ack_down_thread.start()

                # send_ack_thread = threading.Thread(args=(self.out_ack_socket_down,),
                #                                    target=self.receive_ack, name="SendAckThread")
                # send_ack_thread.start()

                receive_down_data_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Receive down data thread ended execution"))
                prepare_down_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Prepare down thread ended execution"))
                send_down_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Send down thread ended execution"))
                receive_ack_down_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Receive ack down thread ended execution"))
                # send_ack_thread.join()

                done_msg = ("DONE").encode('utf-8')

                size_of_chunk = len(done_msg)
                seq_num = 0
                src = self.process_config['name']

                if self.process_config['child'] is None:
                    dest = self.process_config['right_neighbor']
                else:
                    dest = self.process_config['child']

                error_detection_method = self.process_config['error_detection_method']['method']
                parameter = self.process_config['error_detection_method']['parameter']
                check_value = super().get_value_to_check(
                    done_msg, error_detection_method, parameter)
                errors = []
                last_packet = True
                header = Header(seq_num, src, dest, check_value,
                                size_of_chunk, 0, errors, last_packet)
                packet = Packet(header, done_msg)
                super().send_data(self.out_data_socket_down, packet)

                time.sleep(10)

                for sock in self.socket_list:
                    getattr(self, sock).close()

            else:

                # manager_client_thread = threading.Thread(
                #     args=(client_socket,), target=self.manager_client, name="ManagerlientThread")
                # manager_client_thread.daemon = True
                # manager_client_thread.start()

                receive_down_data_thread = threading.Thread(args=(self.in_data_socket_down, self.out_ack_socket_down,
                                                                  self.received_down_buffer_not_full_condition,
                                                                  self.received_data_down_buffer,),
                                                            target=self.receive_data, name="ReceiveDataDownThread")
                receive_down_data_thread.start()

                prepare_up_thread = threading.Thread(args=(self.received_down_buffer_not_full_condition, self.received_data_down_buffer,
                                                           self.sending_down_buffer_not_full_condition, self.sending_data_down_buffer,
                                                           self.sending_data_down_buffer_lock, self.sending_data_down_buffer_condition,),
                                                     target=self.prepare_packet_to_send, name="PreparePacketUpThread")
                prepare_up_thread.start()

                send_up_thread = threading.Thread(args=(self.out_data_socket_up, self.out_data_addr_up,
                                                        self.sending_data_down_buffer_condition, self.sending_data_down_buffer,),
                                                  target=self.send_packet_from_buffer, name="SendPacketUpThread")
                send_up_thread.start()

                receive_up_data_thread = threading.Thread(args=(self.in_data_socket_up, self.out_ack_socket_up,
                                                                self.received_up_buffer_not_full_condition,
                                                                self.received_data_up_buffer,),
                                                          target=self.receive_data, name="ReceiveDataUpThread")
                receive_up_data_thread.start()

                prepare_down_thread = threading.Thread(args=(self.received_up_buffer_not_full_condition, self.received_data_up_buffer,
                                                             self.sending_up_buffer_not_full_condition, self.sending_data_up_buffer,
                                                             self.sending_data_up_buffer_lock, self.sending_data_up_buffer_condition,),
                                                       target=self.prepare_packet_to_send, name="PreparePacketDownThread")
                prepare_down_thread.start()

                send_down_thread = threading.Thread(args=(self.out_data_socket_down, self.out_data_addr_down,
                                                          self.sending_data_up_buffer_condition, self.sending_data_up_buffer,),
                                                    target=self.send_packet_from_buffer, name="SendPacketDownThread")
                send_down_thread.start()

                receive_ack_down_thread = threading.Thread(args=(self.in_ack_socket_down, self.out_data_socket_down, self.out_ack_socket_up,
                                                                 self.out_data_addr_down,
                                                                 self.sending_data_up_buffer_condition, self.sending_data_up_buffer,
                                                                 self.sending_up_buffer_not_full_condition,),
                                                           target=self.receive_ack, name="ReceiveAckDownThread")
                receive_ack_down_thread.start()

                receive_ack_up_thread = threading.Thread(args=(self.in_ack_socket_up, self.out_data_socket_up, self.out_ack_socket_down,
                                                               self.out_data_addr_up,
                                                               self.sending_data_down_buffer_condition, self.sending_data_down_buffer,
                                                               self.sending_down_buffer_not_full_condition,),
                                                         target=self.receive_ack, name="ReceiveAckUpThread")
                receive_ack_up_thread.start()

                receive_down_data_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Receive down data thread ended execution"))
                prepare_up_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Prepare up thread ended execution"))
                send_up_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Send up thread ended execution"))

                receive_ack_down_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Receive ack down thread ended execution"))

                done_msg = ("DONE").encode('utf-8')

                size_of_chunk = len(done_msg)
                seq_num = 0
                src = self.process_config['name']
                dest = self.process_config['parent']
                error_detection_method = self.process_config['error_detection_method']['method']
                parameter = self.process_config['error_detection_method']['parameter']
                check_value = super().get_value_to_check(
                    done_msg, error_detection_method, parameter)
                errors = []
                last_packet = True
                header = Header(seq_num, src, dest, check_value,
                                size_of_chunk, 0, errors, last_packet)
                packet = Packet(header, done_msg)
                super().send_data(self.out_data_socket_up, packet)

                receive_up_data_thread.join()

                logging.info(pc.PrintColor.print_in_red_back(
                    "Receive up data thread ended execution"))
                prepare_down_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Prepare down thread ended execution"))
                send_down_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Send down thread ended execution"))
                receive_ack_up_thread.join()
                logging.info(pc.PrintColor.print_in_red_back(
                    "Receive ack up thread ended execution"))

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
                super().send_data(self.out_data_socket_down, packet)

                time.sleep(10)

                for sock in self.socket_list:
                    getattr(self, sock).close()

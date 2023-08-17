# Process D

from process import ProcessHandlerBase
from send_receive import SendReceive

import utils
import time
import threading
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
        self.out_data_socket = None
        self.out_ack_socket = None
        self.out_data_addr = None
        self.out_ack_addr = None
        self.in_data_socket = None
        self.in_ack_socket = None
        self.socket_list = [
            'out_data_socket',
            'out_ack_socket',
            'in_data_socket',
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

    def receive_data(self, in_socket, out_ack_socket, received_buffer_not_full_condition, received_data_buffer):
        seq_num = -1

        while True:
            data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data = self.receive_packets(
                in_socket)
            logging.info(pc.PrintColor.print_in_black_back(
                f"Received chunk of size {len(data_to_forward)}"))

            if self.process_config['child'] is not None:
                self.handle_child(data_to_forward, packet_to_ack, received_src,
                                  received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data)
            elif self.process_config['child'] is None:
                self.handle_no_child(data_to_forward, packet_to_ack, received_src, received_dest,
                                     received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data)
            else:
                self.add_to_buffer(
                    data_to_forward, received_buffer_not_full_condition, received_data_buffer, seq_num)

    def receive_packets(self, in_socket):
        data_to_forward = b''
        packet_to_ack = []
        while True:
            received_seq_num, received_src, received_dest, received_check_value_data, received_chunk_data, received_ack_byte, fixed_data, received_errors_data, received_last_packet = super().receive_data(in_socket)
            packet_to_ack.append(received_seq_num)
            if self.process_config['child'] is None:
                data_to_forward += received_chunk_data
                if len(data_to_forward) >= self.chunk_size or received_last_packet:
                    break
            else:
                data_to_forward += received_chunk_data
                if received_last_packet:
                    break
        return data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_check_value_data

    def handle_child(self, data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data):
        inner_packet = super().decapsulate(data_to_forward)
        data_to_forward = inner_packet.chunk
        received_check_value_data = inner_packet.header.check_value.encode()
        received_seq_num = inner_packet.header.seq_num
        no_corruption = super().verify_value(data_to_forward, received_check_value_data.decode(),
                                             self.process_config['error_detection_method']['method'], self.process_config['error_detection_method']['parameter'])
        received_src_inner = inner_packet.header.src.encode()
        received_dest_inner = inner_packet.header.dest.encode()
        if no_corruption:
            logging.info(pc.PrintColor.print_in_yellow_back(
                f"Positive ACK for seq_num: {received_seq_num} to {received_src_inner} from {received_dest_inner}"))
            for seq_n in packet_to_ack:
                logging.info(pc.PrintColor.print_in_yellow_back(
                    f"Positive ACK for seq_num: {seq_n} to {(self.process_config['child']).encode()} from {(self.process_config['name']).encode()}"))
            self.add_to_buffer(
                data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num)

    def handle_no_child(self, data_to_forward, packet_to_ack, received_src, received_dest, received_seq_num, received_buffer_not_full_condition, received_data_buffer, received_check_value_data):
        no_corruption = super().verify_value(data_to_forward, received_check_value_data.decode(),
                                             self.process_config['error_detection_method']['method'], self.process_config['error_detection_method']['parameter'])
        if no_corruption:
            if received_src.decode() != self.process_config['child']:
                for seq_n in packet_to_ack:
                    logging.info(pc.PrintColor.print_in_yellow_back(
                        f"Positive ACK for seq_num: {seq_n} to {received_src} from {received_dest}"))
            self.add_to_buffer(
                data_to_forward, received_buffer_not_full_condition, received_data_buffer, received_seq_num)
        else:
            for seq_num in packet_to_ack:
                logging.info(pc.PrintColor.print_in_yellow_back(
                    f"Negative ACK for seq_num: {seq_num}"))

    def add_to_buffer(self, data_to_forward, received_buffer_not_full_condition, received_data_buffer, seq_num):
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
                received_data_buffer.add(chunk)
                received_buffer_not_full_condition.notify()
                logging.info(pc.PrintColor.print_in_red_back(
                    f"Received chunk {seq_num} of size {len(chunk)} to buffer"))
            seq_num += 1

    def prepare_packet_to_send(self, received_buffer_not_full_condition, received_data_buffer, sending_buffer_not_full_condition,
                               sending_data_buffer, sending_data_buffer_lock, sending_data_buffer_condition):
        seq_num = -1
        while True:
            chunk = None
            with received_buffer_not_full_condition:
                if not received_data_buffer.is_empty():
                    chunk = received_data_buffer.get()
                    received_data_buffer.remove()
                    # Notify read_file_to_buffer that there's space now
                    received_buffer_not_full_condition.notify()

            if chunk:
                size_of_chunk = len(chunk)
                seq_num += 1
                seq_num %= (2*self.process_config['window_size'])
                src = self.process_config['name']
                dest = self.process_config['parent']
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
                    while sending_data_buffer.is_full():  # Wait if the sending buffer is full
                        logging.info(pc.PrintColor.print_in_yellow_back(
                            f"No space in sending buffer"))
                        sending_buffer_not_full_condition.wait()
                        logging.info(pc.PrintColor.print_in_yellow_back(
                            f"Received Notification that htere is space in sending buffer"))

                    with sending_data_buffer_lock:
                        sending_data_buffer.add(packet)
                        logging.info(pc.PrintColor.print_in_green_back(
                            f"Added packet {seq_num} of size {size_of_chunk} to sending buffer"))
                        sending_data_buffer_condition.notify()

    def send_packet_from_buffer(self, out_socket, out_addr, sending_data_buffer_condition, sending_data_buffer):
        last_sent_seq_num = -1  # Initialize to an invalid sequence number
        while True:
            with sending_data_buffer_condition:
                while self.urgent_send_in_progress or sending_data_buffer.is_empty():
                    # Wait until there's a packet to send or an urgent send is needed
                    sending_data_buffer_condition.wait()
                seq_num_of_packet_to_send = (
                    last_sent_seq_num + 1) % (2*self.process_config['window_size'])
                packet = sending_data_buffer.get_by_sequence(
                    seq_num_of_packet_to_send)
                if packet is None:
                    continue

                with self.send_lock:

                    super().send_data(out_socket, packet)
                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"Sent packet {packet.seq_num} of size {packet.header.size_of_data + packet.header.get_size()} (Data: {packet.header.size_of_data} Header: {packet.header.get_size()}) to {out_addr[0]}:{out_addr[1]}"))
                    # logging.info(packet)
                    last_sent_seq_num = packet.seq_num

    def receive_ack(self, in_socket, out_socket, out_addr,
                    sending_data_buffer_condition, sending_data_buffer, sending_buffer_not_full_condition):
        while True:
            # time.sleep(0.1)
            received_seq_num, received_src, _, _, received_size_of_chunk, received_ack_byte, _, _, _ = super(
            ).receive_data(in_socket)

            ack_string = "ACK" if received_ack_byte == 1 else "NACK" if received_ack_byte == 3 else "UNKNOWN"
            logging.info(pc.PrintColor.print_in_purple_back(
                f"Received {ack_string} for packet {received_seq_num}"))
            if received_src.decode() == self.process_config['name']:
                with sending_buffer_not_full_condition:

                    if received_ack_byte == 1:
                        logging.info(pc.PrintColor.print_in_green_back("Sending data buffer before remove" +
                                                                       sending_data_buffer.print_buffer()))
                        packet = sending_data_buffer.remove_by_sequence(
                            received_seq_num)
                        logging.info(pc.PrintColor.print_in_cyan_back("Sending data buffer after remove" +
                                                                      sending_data_buffer.print_buffer()))
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

                    elif received_ack_byte == 3:
                        packet = self.sending_data_buffer.get_by_sequence(
                            received_seq_num)
                        self.urgent_send_in_progress = True
                        self.urgent_send_condition.notify()
                        super().send_data(out_socket, packet)
                        logging.info(pc.PrintColor.print_in_white_back(
                            f"Re-sent packet {received_seq_num} of size {received_size_of_chunk} to {out_addr[0]}:{out_addr[1]}"))
                        self.urgent_send_in_progress = False
                        self.urgent_send_condition.notify()
            else:
                # send ack to its out ack socket
                pass

    def create_data_route(self, retries, delay):
        in_data_socket = utils.create_client_socket(
            self.process_config['ip'], 0)
        host, port = self.find_data_host_port()
        in_data_socket_generator = super().connect_in_socket(
            in_data_socket, retries, delay, host, port, "data")
        self.in_data_socket = next(in_data_socket_generator, None)

    def find_data_host_port(self):
        if self.process_config['child'] is not None:
            host, port = self.process_config['child_ip'], self.process_config['child_data_port']
        else:
            host, port = self.process_config['left_neighbor_ip'], self.process_config['left_neighbor_data_port']
        return host, port

    def create_ack_route(self, retries, delay):
        in_ack_socket = utils.create_client_socket(
            self.process_config['ip'], 0)
        host, port = self.find_ack_host_port()
        in_ack_socket_generator = super().connect_in_socket(
            in_ack_socket, retries, delay, host, port, "ack")
        self.in_ack_socket = next(in_ack_socket_generator, None)

    def find_ack_host_port(self):
        host, port = self.process_config['parent_ip'], self.process_config['parent_ack_port']
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

        receive_data_thread = threading.Thread(args=(self.in_data_socket, self.out_ack_socket, self.received_buffer_not_full_condition, self.received_data_buffer,),
                                               target=self.receive_data, name="ReceiveThread")
        receive_data_thread.start()

        # Thread for prepare_packet_to_send
        prepare_thread = threading.Thread(args=(self.received_buffer_not_full_condition, self.received_data_buffer, self.sending_buffer_not_full_condition,
                                                self.sending_data_buffer, self.sending_data_buffer_lock, self.sending_data_buffer_condition,),
                                          target=self.prepare_packet_to_send, name="PrepareThread")
        prepare_thread.start()

        # Thread for send_packet_from_buffer
        send_thread = threading.Thread(args=(self.out_data_socket, self.out_data_addr, self.sending_data_buffer_condition, self.sending_data_buffer,),
                                       target=self.send_packet_from_buffer, name="SendThread")
        send_thread.start()

        # Thread for receive_ack
        receive_ack_thread = threading.Thread(args=(self.in_ack_socket, self.out_data_socket, self.out_data_addr,
                                                    self.sending_data_buffer_condition, self.sending_data_buffer, self.sending_buffer_not_full_condition,),
                                              target=self.receive_ack, name="ReceiveAckThread")
        receive_ack_thread.start()

        # Optionally, if you want the main thread to wait for these threads to finish (though in your case they have infinite loops)
        receive_data_thread.join()
        prepare_thread.join()
        send_thread.join()
        receive_ack_thread.join()

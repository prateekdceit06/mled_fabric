# Process C

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
        self.in_data_socket = None
        self.in_ack_socket = None
        self.out_data_socket = None
        self.out_ack_socket = None
        self.out_data_addr = None
        self.out_ack_addr = None
        self.socket_list = ['in_data_socket', 'in_ack_socket',
                            'out_data_socket', 'out_ack_socket']
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

    def receive_data(self, in_socket):
        seq_num = -1
        while True:
            _, _, _, received_check_value_data, received_chunk_data, _, fixed_data, received_errors_data, _ = super(
            ).receive_data(in_socket)
            data_to_forward = (fixed_data + received_check_value_data +
                               received_errors_data + received_chunk_data)
            logging.info(pc.PrintColor.print_in_black_back(
                f"Received chunk of size {len(data_to_forward)}"))

            # Split the chunk into smaller chunks
            for i in range(0, len(data_to_forward), self.chunk_size):
                chunk = data_to_forward[i:i+self.chunk_size]

                seq_num += 1
                seq_num %= (2*self.process_config['window_size'])

                with self.received_buffer_not_full_condition:
                    while self.received_data_buffer.is_full():
                        # Wait until there's space in the buffer
                        logging.info(pc.PrintColor.print_in_blue_back(
                            f"No space in Receiving buffer"))
                        self.received_buffer_not_full_condition.wait()
                        logging.info(pc.PrintColor.print_in_blue_back(
                            f"Received notification that there is space in Receiving buffer"))

                    if not chunk:
                        break
                    self.received_data_buffer.add(chunk)
                    self.received_buffer_not_full_condition.notify(2)
                    logging.info(pc.PrintColor.print_in_yellow_back(
                        f"Send notification that there is chunk in Receiving buffer"))
                    logging.info(pc.PrintColor.print_in_red_back(
                        f"Received chunk {seq_num} of size {len(chunk)} to buffer"))
                    # logging.info(f"CHUNK: {chunk}")

    def prepare_packet_to_send(self):
        seq_num = -1
        while True:
            while self.received_data_buffer.is_empty():
                # Wait until there's data in the buffer
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"No data in receiving buffer"))
                with self.received_buffer_not_full_condition:
                    self.received_buffer_not_full_condition.wait()
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"Received notification that there is data in receiving buffer"))
            chunk = None
            with self.received_buffer_not_full_condition:
                chunk = self.received_data_buffer.get()
                self.received_data_buffer.remove()
                # Notify read_file_to_buffer that there's space now
                self.received_buffer_not_full_condition.notify(2)
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"Notified that there is space in receiving buffer"))

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
                        logging.info(pc.PrintColor.print_in_yellow_back(
                            f"No space in sending buffer"))
                        self.sending_buffer_not_full_condition.wait()
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
        while True:
            with self.sending_data_buffer_condition:
                while self.urgent_send_in_progress or self.sending_data_buffer.is_empty():
                    # Wait until there's a packet to send or an urgent send is needed
                    if self.urgent_send_in_progress:
                        logging.info(pc.PrintColor.print_in_blue_back(
                            "Urgent packet is being sent"))
                    elif self.sending_data_buffer.is_empty():
                        logging.info(pc.PrintColor.print_in_blue_back(
                            "No packet to send in sending buffer"))
                    self.sending_data_buffer_condition.wait()
                    logging.info(pc.PrintColor.print_in_blue_back(
                        "Received notification that there is a packet to send in sending buffer or urgent packet sent successfully."))
                seq_num_of_packet_to_send = (
                    last_sent_seq_num + 1) % (2*self.process_config['window_size'])
                packet = self.sending_data_buffer.get_by_sequence(
                    seq_num_of_packet_to_send)
                if packet is None:
                    continue

            with self.send_lock:
                super().send_data(out_socket, packet)
                logging.info(pc.PrintColor.print_in_blue_back(
                    f"Sent packet {packet.seq_num} of size {packet.header.size_of_data + packet.header.get_size()}" +
                    f" (Data: {packet.header.size_of_data} Header: {packet.header.get_size()}) to {packet.header.dest} from {packet.header.src}"))
                # logging.info(packet)

                last_sent_seq_num = packet.seq_num

    def receive_ack(self, in_data_socket, out_data_socket, out_ack_socket, out_addr):
        while True:
            # time.sleep(0.1)
            received_seq_num, received_src, received_dest, _, received_size_of_chunk, received_ack_byte, _, _, _ = super(
            ).receive_data(in_data_socket)

            ack_string = "ACK" if received_ack_byte == 1 else "NACK" if received_ack_byte == 3 else "UNKNOWN"
            logging.info(pc.PrintColor.print_in_purple_back(
                f"Received {ack_string} for packet {received_seq_num} addressed to {received_dest} from {received_src}"))

            if received_dest.decode() == self.process_config['name']:
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

                    elif received_ack_byte == 3:
                        packet = self.sending_data_buffer.get_by_sequence(
                            received_seq_num)
                        self.urgent_send_in_progress = True
                        self.urgent_send_condition.notify()
                        logging.info(pc.PrintColor.print_in_red_back(
                            f"Notification sent that urgent sending required for {received_seq_num}"))
                        super().send_data(out_data_socket, packet)
                        logging.info(pc.PrintColor.print_in_white_back(
                            f"Re-sent packet {received_seq_num} of size {received_size_of_chunk} to {out_addr[0]}:{out_addr[1]}"))
                        self.urgent_send_in_progress = False
                        self.urgent_send_condition.notify()
                        logging.info(pc.PrintColor.print_in_red_back(
                            f"Notification sent that urgent sending completed for {received_seq_num}"))
            else:
                # send ack to its out ack socket
                logging.info(pc.PrintColor.print_in_purple_back(
                    f"Forwarding {ack_string} for packet {received_seq_num} addressed to {received_dest} from {received_src}"))
                self.send_ack(received_seq_num, received_src,
                              received_dest, received_ack_byte, out_ack_socket)

    def send_ack(self, seq_num, src, dest, type, out_ack_socket):
        time.sleep(0.1)
        ack_header = Header(
            seq_num, src.decode(), dest.decode(), "", 0, type, [], True)
        ack_packet = Packet(ack_header, b'')
        super().send_ack(out_ack_socket, ack_packet)

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
            self.process_config['ip'], 0)
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

        receive_data_thread = threading.Thread(args=(self.in_data_socket,),
                                               target=self.receive_data, name="ReceiveDataThread")
        receive_data_thread.start()

        # Thread for prepare_packet_to_send
        prepare_thread = threading.Thread(
            target=self.prepare_packet_to_send, name="PreparePacketThread")
        prepare_thread.start()

        # Thread for send_packet_from_buffer
        send_thread = threading.Thread(args=(self.out_data_socket, self.out_data_addr,),
                                       target=self.send_packet_from_buffer, name="SendPacketThread")
        send_thread.start()

        # Thread for receive_ack
        receive_ack_thread = threading.Thread(args=(self.in_ack_socket, self.out_data_socket, self.out_ack_socket, self.out_data_addr,),
                                              target=self.receive_ack, name="ReceiveAckThread")
        receive_ack_thread.start()

        receive_data_thread.join()
        prepare_thread.join()
        send_thread.join()
        receive_ack_thread.join()

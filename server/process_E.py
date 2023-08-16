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
import struct
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
            self.sending_up_buffer_not_full_condition = threading.Condition()

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
        self.sending_down_buffer_not_full_condition = threading.Condition()

    def receive_data(self, in_socket, received_buffer_not_full_condition, received_data_buffer):
        seq_num = -1
        while True:
            data_to_forward = b''
            while True:
                received_seq_num, received_src, received_dest, received_check_value_data, received_chunk_data, received_ack_byte, fixed_data, received_errors_data, received_last_packet = super(
                ).receive_data(in_socket)
                if received_dest.decode() == self.process_config['name']:

                    data_to_forward += received_chunk_data
                    if len(data_to_forward) >= self.chunk_size or received_last_packet:
                        break
                elif received_dest.decode() is not self.process_config['name'] and received_src.decode() == self.process_config['child']:
                    data_to_forward += received_chunk_data
                    if received_last_packet:
                        break
                else:
                    data_to_forward += (fixed_data + received_check_value_data +
                                        received_errors_data + received_chunk_data)

                    if len(data_to_forward) >= self.chunk_size or received_last_packet:
                        break
            if received_dest.decode() is not self.process_config['name'] and received_src.decode() == self.process_config['child']:
                inner_packet = super().decapsulate(data_to_forward)
                data_to_forward = inner_packet.chunk
                received_check_value_data = inner_packet.header.check_value.encode()

            if received_src.decode() != self.process_config['parent']:
                no_corruption = super().verify_value(data_to_forward, received_check_value_data.decode(),
                                                     self.process_config['error_detection_method']['method'],
                                                     self.process_config['error_detection_method']['parameter'])
                if no_corruption:
                    logging.info(pc.PrintColor.print_in_green_back(
                        "Positive ACK for seq_num: "))
                else:
                    logging.info(
                        pc.PrintColor.print_in_red_back("Negative ACK"))

            logging.info(pc.PrintColor.print_in_black_back(
                f"Received chunk of size {len(data_to_forward)}"))

            # Split the chunk into smaller chunks
            for i in range(0, len(data_to_forward), self.chunk_size):
                chunk = data_to_forward[i:i+self.chunk_size]

                seq_num += 1
                seq_num %= (2*self.process_config['window_size'])

                with received_buffer_not_full_condition:
                    while received_data_buffer.is_full():
                        # Wait until there's space in the buffer
                        received_buffer_not_full_condition.wait()

                    if not chunk:
                        break
                    received_data_buffer.add(chunk)
                    logging.info(pc.PrintColor.print_in_red_back(
                        f"Read chunk {seq_num} of size {len(chunk)} to buffer"))
                    logging.info(f"CHUNK: {chunk}")

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
                    while sending_data_buffer.is_full():  # Wait if the sending buffer is full
                        sending_buffer_not_full_condition.wait()

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
                # if out_socket == self.out_data_socket_up:
                #     logging.info(f"Packet CHUNK: {packet.chunk}")
                #     packet = super().decapsulate(packet.header.pack + packet.chunk)

                with self.send_lock:

                    super().send_data(out_socket, packet)

                    logging.info(pc.PrintColor.print_in_blue_back(
                        f"Sent packet {packet.seq_num} of size {packet.header.size_of_data + packet.header.get_size()} (Data: {packet.header.size_of_data} Header: {packet.header.get_size()}) to {out_addr[0]}:{out_addr[1]}"))
                    logging.info(packet)
                    last_sent_seq_num = packet.seq_num

    def receive_ack(self, in_socket, out_socket, out_addr,
                    sending_data_buffer_condition, sending_data_buffer, sending_buffer_not_full_condition):
        while True:
            received_seq_num, _, _, _, received_size_of_chunk, _, received_ack_byte, _, _ = super(
            ).receive_data(in_socket)
            ack_string = "ACK" if received_ack_byte == 1 else "NACK" if received_ack_byte == 3 else "UNKNOWN"
            logging.info(pc.PrintColor.print_in_purple_back(
                f"Received {ack_string} for packet {received_seq_num}"))

            with sending_data_buffer_condition:

                if received_ack_byte == 1:
                    sending_data_buffer.remove_by_sequence(
                        received_seq_num)
                    logging.info(pc.PrintColor.print_in_yellow_back(
                        f"Removed packet {received_seq_num} from sending buffer"))
                    # Notify send_packet_from_buffer that there might be space now
                    sending_data_buffer_condition.notify()
                    sending_buffer_not_full_condition.notify()

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

    def send_ack(self, in_socket, out_socket, out_addr):
        pass

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

    def create_out_sockets(self, connections, timeout, ip):
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

        for sock in self.socket_list:
            print(super().get_socket_by_name(sock))

        if self.process_config['parent'] is None:

            receive_down_data_thread = threading.Thread(args=(self.in_data_socket_down, self.received_down_buffer_not_full_condition,
                                                              self.received_data_down_buffer,),
                                                        target=self.receive_data, name="ReceiveDownThread")
            receive_down_data_thread.start()

            # Thread for prepare_packet_to_send
            prepare_down_thread = threading.Thread(args=(self.received_down_buffer_not_full_condition, self.received_data_down_buffer,
                                                         self.sending_down_buffer_not_full_condition, self.sending_data_down_buffer,
                                                         self.sending_data_down_buffer_lock, self.sending_data_down_buffer_condition,),
                                                   target=self.prepare_packet_to_send, name="PrepareDownThread")
            prepare_down_thread.start()

            # Thread for send_packet_from_buffer
            send_down_thread = threading.Thread(args=(self.out_data_socket_down, self.out_data_addr_down,
                                                      self.sending_data_down_buffer_condition, self.sending_data_down_buffer,),
                                                target=self.send_packet_from_buffer, name="SendDownThread")
            send_down_thread.start()

            # Thread for receive_ack
            receive_ack_down_thread = threading.Thread(args=(self.in_ack_socket_down, self.out_data_socket_down, self.out_data_addr_down,
                                                             self.sending_data_down_buffer_condition, self.sending_data_down_buffer,
                                                             self.sending_down_buffer_not_full_condition,),
                                                       target=self.receive_ack, name="ReceiveAckDownThread")
            receive_ack_down_thread.start()

            # send_ack_thread = threading.Thread(args=(self.out_ack_socket_down,),
            #                                    target=self.receive_ack, name="SendAckThread")
            # send_ack_thread.start()

            receive_down_data_thread.join()
            prepare_down_thread.join()
            send_down_thread.join()
            receive_ack_down_thread.join()
            # send_ack_thread.join()

        else:

            receive_down_data_thread = threading.Thread(args=(self.in_data_socket_down, self.received_down_buffer_not_full_condition,
                                                              self.received_data_down_buffer,),
                                                        target=self.receive_data, name="ReceiveDownThread")
            receive_down_data_thread.start()

            prepare_up_thread = threading.Thread(args=(self.received_down_buffer_not_full_condition, self.received_data_down_buffer,
                                                       self.sending_down_buffer_not_full_condition, self.sending_data_down_buffer,
                                                       self.sending_data_down_buffer_lock, self.sending_data_down_buffer_condition,),
                                                 target=self.prepare_packet_to_send, name="PrepareUpThread")
            prepare_up_thread.start()

            send_up_thread = threading.Thread(args=(self.out_data_socket_up, self.out_data_addr_up,
                                                    self.sending_data_down_buffer_condition, self.sending_data_down_buffer,),
                                              target=self.send_packet_from_buffer, name="SendUpThread")
            send_up_thread.start()

            receive_up_data_thread = threading.Thread(args=(self.in_data_socket_up, self.received_up_buffer_not_full_condition,
                                                            self.received_data_up_buffer,),
                                                      target=self.receive_data, name="ReceiveUpThread")
            receive_up_data_thread.start()

            prepare_down_thread = threading.Thread(args=(self.received_up_buffer_not_full_condition, self.received_data_up_buffer,
                                                         self.sending_up_buffer_not_full_condition, self.sending_data_up_buffer,
                                                         self.sending_data_up_buffer_lock, self.sending_data_up_buffer_condition,),
                                                   target=self.prepare_packet_to_send, name="PrepareDownThread")
            prepare_down_thread.start()

            send_down_thread = threading.Thread(args=(self.out_data_socket_down, self.out_data_addr_down,
                                                      self.sending_data_up_buffer_condition, self.sending_data_up_buffer,),
                                                target=self.send_packet_from_buffer, name="SendDownThread")
            send_down_thread.start()

            receive_ack_down_thread = threading.Thread(args=(self.in_ack_socket_down, self.out_data_socket_down, self.out_data_addr_down,
                                                             self.sending_data_up_buffer_condition, self.sending_data_up_buffer,
                                                             self.sending_up_buffer_not_full_condition,),
                                                       target=self.receive_ack, name="ReceiveAckDownThread")
            receive_ack_down_thread.start()

            receive_ack_up_thread = threading.Thread(args=(self.in_ack_socket_up, self.out_data_socket_up, self.out_data_addr_up,
                                                           self.sending_data_down_buffer_condition, self.sending_data_down_buffer,
                                                           self.sending_down_buffer_not_full_condition,),
                                                     target=self.receive_ack, name="ReceiveAckUpThread")
            receive_ack_up_thread.start()

            receive_down_data_thread.join
            prepare_up_thread.join()
            send_up_thread.join()
            receive_up_data_thread.join()
            prepare_down_thread.join()
            send_down_thread.join()
            receive_ack_down_thread.join()
            receive_ack_up_thread.join()

    # def receive_data(self, in_socket, received_buffer_not_full_condition, received_data_buffer, out_socket):
    #     seq_num = -1
    #     while True:
    #         chunk = None
    #         received_seq_num, received_src, received_dest, received_check_value_data, received_chunk_data, received_ack_byte, fixed_data, received_errors_data = super(
    #         ).receive_data(in_socket)
    #         data_to_forward = (fixed_data + received_check_value_data +
    #                            received_errors_data + received_chunk_data)
    #         logging.info(pc.PrintColor.print_in_black_back(
    #             f"Received chunk of size {len(data_to_forward)}"))
    #         if received_dest == self.process_config['name']:
    #             received_check_value = received_check_value_data.decode(
    #                 'utf-8')
    #             received_chunk = received_chunk_data.decode('utf-8')

    #             error_detection_method = self.process_config['error_detection_method']['method']
    #             parameter = self.process_config['error_detection_method']['parameter']
    #             correct = super().verify_value(
    #                 received_chunk, received_check_value, error_detection_method, parameter)

    #             if correct:

    #                 size_of_chunk = 0
    #                 seq_num = received_seq_num
    #                 src = self.process_config['name']
    #                 dest = self.process_config['left_neighbor']

    #                 check_value = ""
    #                 errors = []
    #                 header = Header(seq_num, src, dest, check_value,
    #                                 size_of_chunk, 1, errors)
    #                 packet = Packet(header, received_chunk)

    #                 self.send_ack(out_socket, packet)

    #                 for i in range(0, len(received_chunk), self.chunk_size):
    #                     chunk = received_chunk[i:i+self.chunk_size]

    #                     seq_num += 1
    #                     seq_num %= (2*self.process_config['window_size'])

    #                     with received_buffer_not_full_condition:
    #                         while received_data_buffer.is_full():
    #                             # Wait until there's space in the buffer
    #                             received_buffer_not_full_condition.wait()

    #                         if not chunk:
    #                             break
    #                         received_data_buffer.add(chunk)
    #                         logging.info(pc.PrintColor.print_in_red_back(
    #                             f"Wrote chunk {seq_num} of size {len(chunk)} to buffer"))

    #             else:
    #                 size_of_chunk = 0
    #                 seq_num = received_seq_num
    #                 src = self.process_config['name']
    #                 dest = self.process_config['left_neighbor']

    #                 check_value = ""
    #                 errors = []
    #                 header = Header(seq_num, src, dest, check_value,
    #                                 size_of_chunk, 3, errors)
    #                 packet = Packet(header, received_chunk)

    #                 self.send_ack(out_socket, packet)
    #         else:

    #             # Split the chunk into smaller chunks
    #             for i in range(0, len(data_to_forward), self.chunk_size):
    #                 chunk = data_to_forward[i:i+self.chunk_size]

    #                 seq_num += 1
    #                 seq_num %= (2*self.process_config['window_size'])

    #                 with received_buffer_not_full_condition:
    #                     while received_data_buffer.is_full():
    #                         # Wait until there's space in the buffer
    #                         received_buffer_not_full_condition.wait()

    #                     if not chunk:
    #                         break
    #                     received_data_buffer.add(chunk)
    #                     logging.info(pc.PrintColor.print_in_red_back(
    #                         f"Wrote chunk {seq_num} of size {len(chunk)} to buffer"))

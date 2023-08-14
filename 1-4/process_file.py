# Process E

from process import ProcessHandlerBase
import utils
import logging
import threading
import time

logging_format = utils.logging_format+" %(threadName)s"

logging.basicConfig(format=logging_format, level=logging.INFO)


class ProcessHandler(ProcessHandlerBase):

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
        alive_threads = threading.enumerate()
        print("Alive threads: ", alive_threads)
        for sock in self.socket_list:
            print(super().get_socket_by_name(sock))

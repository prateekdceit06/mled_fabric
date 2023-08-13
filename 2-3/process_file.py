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
            self.out_data_socket_up,
            self.out_data_socket_down,
            self.out_ack_socket_up,
            self.out_ack_socket_down,
            self.in_data_socket_up,
            self.in_data_socket_down,
            self.in_ack_socket_up,
            self.in_ack_socket_down
        ]

    def out_socket_up_handler(self, connections, timeout, ip, port, socket_type):
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

    def out_socket_down_handler(self, connections, timeout, ip, port, socket_type):
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
            in_socket_up_thread = threading.Thread(target=self.in_socket_up_handler,
                                                   args=(in_socket_up, retries, delay, up_host, up_port, "data",))
            # in_socket_up_thread.daemon = True
            in_socket_up_thread.start()
            logging.info("Process E: up Data route created")

        in_socket_down = utils.create_client_socket(
            self.process_config['ip'], 0)
        down_host, down_port = self.find_data_host_port_down()
        in_socket_down_thread = threading.Thread(target=self.in_socket_down_handler,
                                                 args=(in_socket_down,
                                                       retries, delay, down_host, down_port, "data",))
        # in_socket_down_thread.daemon = True
        in_socket_down_thread.start()
        logging.info("Process E: down Data route created")

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
            in_socket_up_thread = threading.Thread(target=self.in_socket_up_handler,
                                                   args=(in_socket_up, retries, delay, up_host, up_port, "ack"))
            # in_socket_up_thread.daemon = True
            in_socket_up_thread.start()

        # parent_thread_id = threading.currentThread().ident

        in_socket_down = utils.create_client_socket(
            self.process_config['ip'], 0)
        down_host, down_port = self.find_ack_host_port_down()
        in_socket_down_thread = threading.Thread(target=self.in_socket_down_handler,
                                                 args=(in_socket_down,
                                                       retries, delay, down_host, down_port, "ack"))
        # in_socket_down_thread.daemon = True
        in_socket_down_thread.start()

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

        out_server_socket_down_thread = threading.Thread(target=self.out_socket_down_handler,
                                                         args=(connections, timeout, ip, port, socket_type,))
        # out_server_socket_down_thread.daemon = True
        out_server_socket_down_thread.start()

        if self.process_config['parent'] is not None:
            port = port + 100
            out_server_socket_up_thread = threading.Thread(target=self.out_socket_up_handler,
                                                           args=(connections, timeout,
                                                                 ip, port, socket_type,))
            # out_server_socket_up_thread.daemon = True
            out_server_socket_up_thread.start()
            out_server_socket_up_thread.join()
        out_server_socket_down_thread.join()

        logging.info("COMPLETED THREAD EXECUTION")

    def create_out_data_socket(self, connections, timeout, ip):
        port = self.process_config['data_port']
        self.create_out_socket(connections, timeout, ip, port, "data")

    def create_out_ack_socket(self, connections, timeout, ip):
        port = self.process_config['ack_port']
        self.create_out_socket(connections, timeout, ip, port, "ack")

    def create_out_sockets(self, connections, timeout, ip):
        self.create_out_data_socket(connections, timeout, ip)
        self.create_out_ack_socket(connections, timeout, ip)

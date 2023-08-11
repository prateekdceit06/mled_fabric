# Process E

import process
import utils
import logging
import threading

logging.basicConfig(format=utils.logging_format, level=logging.INFO)


class ProcessHandler(process.ProcessHandler):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)
        self.terminate_event = terminate_event

    def out_socket_up_handler_thread(self, connections, timeout, ip, port):
        super().create_out_socket(connections, timeout, ip, port)

    def out_socket_down_handler_thread(self, connections, timeout, ip, port):
        super().create_out_socket(connections, timeout, ip, port)

    def in_socket_up_handler_thread(self, in_socket_up, retries, delay, up_host, up_port):
        in_socket_up = super().connect_in_socket(in_socket_up, retries, delay, up_host, up_port)

    def in_socket_down_handler_thread(self, in_socket_down, retries, delay, down_host, down_port):
        in_socket_down = super().connect_in_socket(in_socket_down, retries, delay, down_host, down_port)

    def create_out_socket(self, connections, timeout, ip=None, port=None):
        if ip is None:
            ip = self.process_config['ip']
        if port is None:
            port = self.process_config['port']

        out_server_socket_down_thread = threading.Thread(target=self.out_socket_down_handler_thread,
                                                         args=(connections, timeout, ip, port,))
        # out_server_socket_down_thread.daemon = True
        out_server_socket_down_thread.start()


        if self.process_config['parent'] is not None:
            port = port + 100
            out_server_socket_up_thread = threading.Thread(target=self.out_socket_up_handler_thread,
                                                           args=(connections, timeout,
                                                                 ip, port,))
            # out_server_socket_up_thread.daemon = True
            out_server_socket_up_thread.start()
        out_server_socket_down_thread.join()
        logging.info("COMPLETED THREAD EXECUTION")

    def create_route(self, retries, delay):
        in_socket_up = None
        if self.process_config['parent'] is not None:
            in_socket_up = utils.create_client_socket(self.process_config['ip'], self.process_config['port'])
            up_host, up_port = self.find_host_port_up()
            in_socket_up_thread = threading.Thread(target=self.in_socket_up_handler_thread,
                                                   args=(in_socket_up, retries, delay, up_host, up_port,))
            # in_socket_up_thread.daemon = True
            in_socket_up_thread.start()

        # parent_thread_id = threading.currentThread().ident

        in_socket_down = utils.create_client_socket(self.process_config['ip'], 0)
        down_host, down_port = self.find_host_port_down()
        in_socket_down_thread = threading.Thread(target=self.in_socket_down_handler_thread,
                                                 args=(in_socket_down,
                                                       retries, delay, down_host, down_port,))
        # in_socket_down_thread.daemon = True
        in_socket_down_thread.start()


    def find_host_port_down(self):
        if self.process_config['child'] is not None:
            host, port = self.process_config['child_ip'], self.process_config['child_port'] + 100
        else:
            host, port = self.process_config['left_neighbor_ip'], self.process_config['left_neighbor_port']
        return host, port

    def find_host_port_up(self):
        host, port = self.process_config['parent_ip'], self.process_config['parent_port']
        return host, port

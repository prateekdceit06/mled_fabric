import utils
import logging
import socket
import time

logging.basicConfig(format=utils.logging_format, level=logging.INFO)


class ProcessHandler:

    def __init__(self, ip_port_dict, terminate_event):
        def get_value(key, default=None):
            return ip_port_dict.get(key, default)

        self.own_ip = get_value('ip')
        self.own_port = get_value('port')
        self.parent_ip = get_value('parent_ip')
        self.parent_port = get_value('parent_port')
        self.child_ip = get_value('child_ip')
        self.child_port = get_value('child_port')
        self.right_neighbor_ip = get_value('right_neighbor_ip')
        self.right_neighbor_port = get_value('right_neighbor_port')
        self.left_neighbor_ip = get_value('left_neighbor_ip')
        self.left_neighbor_port = get_value('left_neighbor_port')
        self.terminate_event = terminate_event

    def create_out_socket(self, connections, timeout):
        logging.info(f"Creating socket on {self.own_ip}:{self.own_port}")

        out_server_socket = utils.create_server_socket(self.own_ip, self.own_port, connections, timeout)

        while not self.terminate_event.is_set():
            try:
                out_socket, addr = out_server_socket.accept()
                logging.info(f"Accepted connection from {addr[0]}")
            except socket.timeout:
                # logging.info("Server is idle.")
                pass
            except socket.error as e:
                if self.terminate_event.is_set():
                    logging.info("Terminating due to signal.")
                    out_server_socket.close()
                logging.error(f"Error on socket accept: {e}")

    def connect_in_socket(self, in_socket, retries, delay, host, port):
        while retries > 0:
            try:
                in_socket.connect((host, port))
                logging.info(f"Connected to the server {host}:{port}!")
                return in_socket
            except socket.error as e:
                if e.errno == 111:  # Connection refused error
                    logging.error(f"Connection refused. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    retries -= 1
                else:
                    logging.error(f"Error on socket connect: {e}")
                    raise e
        print("Failed to connect after multiple attempts.")
        return None

    def create_route(self, retries, delay):
        pass

import utils
import logging
import socket
import time
import print_colour

logging.basicConfig(format=utils.logging_format, level=logging.INFO)


class ProcessHandlerBase:

    def __init__(self, process_config, terminate_event):
        self.process_config = process_config
        self.terminate_event = terminate_event

    def create_out_socket(self, connections, timeout, ip, port, socket_type):

        logging.info(print_colour.PrintColor.print_in_purple_back(
            f"Creating {socket_type} socket on {ip}:{port}"))
        out_server_socket = utils.create_server_socket(
            ip, port, socket_type, connections, timeout)

        while not self.terminate_event.is_set():
            try:

                out_socket, addr = out_server_socket.accept()
                host_relation = self.get_host_relation(addr[0])
                host_relation_name = self.process_config[host_relation]
                if socket_type == "data":
                    logging.info(print_colour
                                 .PrintColor
                                 .print_in_green_back(f"Accepted connection from {addr[0]}. "
                                                      f"Process {self.process_config['name']} is ready to send data to "
                                                      f"{host_relation_name} on {addr[0]}:{addr[1]}."))
                elif socket_type == "ack":
                    logging.info(print_colour
                                 .PrintColor
                                 .print_in_green_back(f"Accepted connection from {addr[0]}. "
                                                      f"Process {self.process_config['name']} is ready to send "
                                                      f"acknowledgements to {host_relation_name} on {addr[0]}:{addr[1]}."))
            except socket.timeout:
                # logging.info("Server is idle.")
                pass
            except socket.error as e:
                if self.terminate_event.is_set():
                    logging.info("Terminating due to signal.")
                    out_server_socket.close()
                logging.error(f"Error on socket accept: {e}")

    def connect_in_socket(self, in_socket, retries, delay, host, port, socket_type):
        host_relation = None
        while retries > 0:
            try:
                in_socket.connect((host, port))
                host_relation = self.get_host_relation(host)
                logging.info(print_colour.PrintColor.print_in_red_back(f"{self.process_config['name']} is connected "
                             f"on {host}:{port} and ready to receive {socket_type} from {self.process_config[host_relation]} ."))
                yield in_socket
                while True:
                    try:
                        in_socket.getpeername()
                        time.sleep(delay)
                    except socket.error as e:
                        if e.errno == 107:
                            logging.info(print_colour.PrintColor.print_in_yellow_back(
                                f"Connection closed by {host}:{port}."))
                            break

            except socket.error as e:
                if e.errno == 111:  # Connection refused error
                    logging.error(f"Connection refused to {self.process_config.get(host_relation)} "
                                  f"on {host}:{port}."
                                  f" Retrying in {delay} seconds...")
                    time.sleep(delay)
                    retries -= 1
                else:
                    logging.error(f"Error on socket connect: {e}")
                    raise e
        print("Failed to connect after multiple attempts.")

    def create_data_route(self, retries, delay):
        pass

    def create_ack_route(self, retries, delay):
        pass

    def get_host_relation(self, host):
        host_relation_ip = utils.get_key_for_value(self.process_config, host)
        host_relation = host_relation_ip[0].rsplit("_", 1)[0]
        return host_relation

    def create_out_data_socket(self, connections, timeout, ip, port):
        self.create_out_socket(connections, timeout, ip, port, "data")

    def create_out_ack_socket(self, connections, timeout, ip, port):
        self.create_out_socket(connections, timeout, ip, port, "ack")

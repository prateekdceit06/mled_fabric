import process
import utils
import logging
import socket

logging.basicConfig(format=utils.logging_format, level=logging.INFO)


class ProcessHandler(process.ProcessHandler):

    def __init__(self, ip_port_dict, terminate_event):
        super().__init__(ip_port_dict, terminate_event)

    def create_out_socket(self, connections, timeout):
        logging.info(f"Creating socket on {self.own_ip}:{self.own_port}")

        out_server_socket = utils.create_server_socket(self.own_ip, self.own_port, connections, timeout)

        while not self.terminate_event.is_set():
            try:
                out_socket, addr = out_server_socket.accept()
                logging.info(f"Accepted connection from {addr[0]}")
            except socket.timeout:
                logging.info("Server is idle.")
            except socket.error as e:
                if self.terminate_event.is_set():
                    logging.info("Terminating due to signal.")
                    out_server_socket.close()
                logging.error(f"Error on socket accept: {e}")
    def create_route(self, retries, delay):
        in_socket_down = utils.create_client_socket(self.own_ip, self.own_port)
        port2 = self.own_port + 100
        in_socket_up = utils.create_client_socket(self.own_ip, port2)
        host_down, port_down = self.find_host_port_down()
        host_up, port_up = self.find_host_port_up()
        if host_down is not None:
            in_socket_down = super().connect_in_socket(in_socket_down, retries, delay, host_down, port_down)
        if host_up is not None:
            in_socket_up = super().connect_in_socket(in_socket_up, retries, delay, host_up, port_up)

    def find_host_port_down(self):
        if self.child_ip is not None:
            host, port = self.child_ip, self.child_port
        else:
            host, port = self.left_neighbor_ip, self.left_neighbor_port
        return host, port

    def find_host_port_up(self):
        return None, None

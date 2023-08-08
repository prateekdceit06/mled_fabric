
from utils import read_json_file

import socket
import sys
import signal
import threading
import logging
import os

lock = threading.Lock()
logging.basicConfig(level=logging.INFO)





def send_file_to_client(client_socket, file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    client_socket.sendall(len(data).to_bytes(4, byteorder='big'))
    client_socket.sendall(data)
    filename = os.path.basename(file_path)
    logging.info(f"File {filename} sent to client {client_socket.getpeername()[0]}")


def signal_handler(sig, frame):
    logging.info("Gracefully shutting down")
    sys.exit(0)


class Server:

    def __init__(self, directory):
        self.path = directory

    def handle_client(self, server_socket, client_socket, addr, connected_clients, client_ips):
        process_type = client_socket.recv(2)
        received_char = process_type.decode('utf-8')
        logging.info(f"Received {received_char} from client {addr[0]}")
        process_tarfile_path = os.path.join(self.path, f'process_{received_char}.tar.gz')
        send_file_to_client(client_socket, process_tarfile_path)
        # with lock:
        #     if connected_clients == client_ips:
        #         logging.info("All clients connected. Closing server socket")
        #         server_socket.close()

    def client_handler(self, server_socket, client_socket, addr, client_ips, connected_clients):
        if addr[0] in client_ips:
            logging.info(f"Connected with {addr[0]}")
            connected_clients.add(addr[0])
            master_config_path = os.path.join(self.path, 'master_config.json')
            send_file_to_client(client_socket, master_config_path)
            self.handle_client(server_socket, client_socket, addr, connected_clients, client_ips)
        else:
            client_socket.close()

    def start_server(self):
        signal.signal(signal.SIGINT, signal_handler)
        ip_list_path = os.path.join(self.path, 'ip_list.json')
        ip_list = read_json_file(ip_list_path)
        server_ip = ip_list['server_ip']
        server_port = ip_list['server_port']
        client_ips = set(ip_list['client'])

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.settimeout(1)  # Set a timeout on accept()
        try:
            server_socket.bind((server_ip, server_port))
        except socket.error as e:
            logging.error(f"Error on socket bind: {e}")
            sys.exit(1)

        try:
            server_socket.listen(10)
            logging.info(f"Listening on {server_ip}:{server_port}")
        except socket.error as e:
            logging.error(f"Error on socket listen: {e}")
            sys.exit(1)

        connected_clients = set()

        try:
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    logging.info(f"Accepted connection from {addr[0]}")
                    client_thread = threading.Thread(target=self.client_handler,
                                                     args=(server_socket, client_socket, addr,
                                                           client_ips, connected_clients))
                    client_thread.start()
                except socket.timeout:
                    with lock:
                        if connected_clients == client_ips:
                            logging.info("All clients served. Closing server socket (Timeout)")
                            break
                        else:
                            continue
                except socket.error as e:
                    if e.errno == 9:  # Bad file descriptor
                        with lock:
                            if connected_clients == client_ips:
                                logging.info("All clients served. Closing server socket (Bad file descriptor)")
                                break
                    else:
                        raise
        except socket.error as e:
            logging.error(f"Error on socket accept: {e}")
            sys.exit(1)

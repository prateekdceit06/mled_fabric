import utils

import socket
import sys
import threading
import logging
import os

lock = threading.Lock()
logging.basicConfig(format=utils.logging_format, level=logging.INFO)


def send_file_to_client(client_socket, file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    client_socket.sendall(len(data).to_bytes(4, byteorder='big'))
    client_socket.sendall(data)
    filename = os.path.basename(file_path)
    logging.info(
        f"File {filename} sent to client {client_socket.getpeername()[0]}")


class Server:

    def __init__(self, directory):
        self.path = directory

    def handle_client(self, server_socket, client_socket, addr, connected_clients, client_ips):
        process_type = client_socket.recv(2)
        received_char = process_type.decode('utf-8')
        logging.info(
            f"Received process type {received_char} from client {addr[0]}")
        # tar_name = f"process_{received_char}.tar.gz"
        routing_file_name = f"process_{received_char}.py"
        routing_file = os.path.join(self.path, routing_file_name)
        # process_tarfile_path = os.path.join(self.path, tar_name)
        # utils.create_tarfile(process_tarfile_path, routing_file1)
        # logging.info(f"Created tar file {tar_name}")
        send_file_to_client(client_socket, routing_file)
        # with lock:
        #     if connected_clients == client_ips:
        #         logging.info("All clients connected. Closing server socket")
        #         server_socket.close()

    def client_handler(self, server_socket, client_socket, addr, client_ips, connected_clients, master_config_file):
        if addr[0] in client_ips:
            logging.info(f"Connected with {addr[0]}")
            connected_clients.add(addr[0])
            master_config_path = os.path.join(self.path, master_config_file)
            ip_list_config_path = os.path.join(self.path, 'ip_list.json')
            send_file_to_client(client_socket, ip_list_config_path)
            send_file_to_client(client_socket, master_config_path)
            self.handle_client(server_socket, client_socket,
                               addr, connected_clients, client_ips)
        else:
            client_socket.close()

    def start_server(self, terminate_event, ip_list):
        
        server_ip = ip_list['server_ip']
        server_port = ip_list['server_port']
        connections = ip_list['connections_manager_process']
        timeout = ip_list['timeout_manager_process']
        client_ips = [client["ip"] for client in ip_list["clients"]]
        master_config_file = ip_list['master_config_file']

        server_socket = utils.create_server_socket(
            server_ip, server_port, "manager", connections, timeout)
        connected_clients = set()

        try:
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    logging.info(f"Accepted connection from {addr[0]}")
                    client_thread = threading.Thread(target=self.client_handler, name="ClientHandlerThread",
                                                     args=(server_socket, client_socket, addr,
                                                           client_ips, connected_clients, master_config_file,))
                    client_thread.start()
                except socket.timeout:

                    if terminate_event.is_set():
                        logging.info("Terminating server")
                        break

                    # with lock:
                    #     if connected_clients == client_ips:
                    #         logging.info("All clients served. Closing server socket (Timeout)")
                    #         break
                    #     else:
                    #         continue
                except socket.error as e:
                    if e.errno == 9:  # Bad file descriptor
                        with lock:
                            if connected_clients == client_ips:
                                logging.info(
                                    "All clients served. Closing server socket (Bad file descriptor)")
                                break
                    else:
                        raise
        except socket.error as e:
            logging.error(f"Error on socket accept: {e}")
            sys.exit(1)

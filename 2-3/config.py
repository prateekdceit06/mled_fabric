from node_config import NodeConfigHandler
from master_config import MasterConfigHandler
import socket
import sys
import os
import logging
import tarfile

logging.basicConfig(format='%(filename)s - %(funcName)s - %(levelname)s - %(message)s', level=logging.INFO)


def delete_file(file_path):
    if os.path.exists(file_path):
        filename = os.path.basename(file_path)
        os.remove(file_path)
        logging.info(f"Deleted file: {filename}")


class ConfigClient:

    def __init__(self, server_ip, server_port, client_ip, client_port, directory):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port
        self.directory = directory

    def get_config(self):
        try:
            # Create a socket object
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as e:
            logging.error(f"Error creating socket: {e}")
            sys.exit(1)

        # Bind the socket to the client IP and port
        try:
            client_socket.bind((self.client_ip, self.client_port))
        except socket.error as e:
            logging.error(f"Error on socket bind: {e}")
            sys.exit(1)

        try:
            # Connect to the server
            client_socket.connect((self.server_ip, self.server_port))
        except socket.gaierror as e:
            logging.info(f"Address-related error connecting to server: {e}")
            sys.exit(1)
        except socket.error as e:
            logging.error(f"Connection error: {e}")
            sys.exit(1)

        logging.info(f"Connected to server at {self.server_ip}:{self.server_port}")

        master_config, master_config_file_path = self.get_master_config(client_socket)

        node_config = self.create_node_config(master_config, master_config_file_path)

        char_to_send = node_config['node_type']

        self.get_node_file(client_socket, char_to_send)

        # Close the connection
        try:
            client_socket.close()
        except socket.error as e:
            logging.error(f"Error closing socket: {e}")
            sys.exit(1)

    def get_master_config(self, client_socket):
        master_config_file_path = os.path.join(self.directory, 'master_config.json')
        master_config_handler = MasterConfigHandler(master_config_file_path)
        master_config_handler.get_master_config(client_socket)
        logging.info("Received master config from server")
        master_config = master_config_handler.read_master_config()
        return master_config, master_config_file_path

    def create_node_config(self, master_config, master_config_file_path):
        node_config_file_path = os.path.join(self.directory, 'node_config.json')
        node_config_handler = NodeConfigHandler(node_config_file_path)
        node_config = node_config_handler.create_node_config(master_config, self.client_ip)
        node_config_handler.write_node_config(node_config)
        logging.info("Created node config")
        delete_file(master_config_file_path)
        return node_config

    def get_node_file(self, client_socket, char_to_send):
        filename = 'node_' + char_to_send + '.tar.gz'
        node_A_path = os.path.join(self.directory, filename)
        client_socket.sendall(char_to_send.encode('utf-8'))
        length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = client_socket.recv(length)
        with open(node_A_path, 'wb') as f:
            f.write(data)
        logging.info(f"Received node file from server: {filename}")
        self.extract_tar_gz(node_A_path)
        logging.info(f"Extracted node tar file: {filename}")
        delete_file(node_A_path)
        logging.info(f"Deleted node tar file: {filename}")

    def extract_tar_gz(self, file_path):
        with tarfile.open(file_path, 'r:gz') as tar:
            tar.extractall(path=self.directory)

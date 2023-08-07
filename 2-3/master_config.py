from node_config import NodeConfig
import socket
import sys
import json
import os


class MasterConfigClient:

    def __init__(self, server_ip, server_port, client_ip, client_port, master_config_file):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port
        self.master_config_file = master_config_file

    def read_master_config(self):
        with open(self.master_config_file, 'r') as file:
            data = json.load(file)
        return data

    def get_master_config(self):
        try:
            # Create a socket object
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as e:
            print(f"Error creating socket: {e}")
            sys.exit(1)

        # Bind the socket to the client IP and port
        try:
            client_socket.bind((self.client_ip, self.client_port))
        except socket.error as e:
            print(f"Error on socket bind: {e}")
            sys.exit(1)

        try:
            # Connect to the server
            client_socket.connect((self.server_ip, self.server_port))
        except socket.gaierror as e:
            print(f"Address-related error connecting to server: {e}")
            sys.exit(1)
        except socket.error as e:
            print(f"Connection error: {e}")
            sys.exit(1)

        print(f"Connected to server at {self.server_ip}:{self.server_port}")

        length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = client_socket.recv(length)
        with open(self.master_config_file, 'wb') as f:
            f.write(data)

        path = os.path.abspath(__file__)
        directory = os.path.dirname(path)
        node_config_file_path = os.path.join(directory, 'node_config.json')
        config = self.read_master_config()
        node_config = NodeConfig()
        node_config_to_write = node_config.get_node_config(config, self.client_ip)
        node_config.write_node_config(node_config_file_path, node_config_to_write)
        char_to_send = node_config_to_write['node_type']

        # Send byte to server
        client_socket.sendall(char_to_send.encode('utf-8'))

        # Receive "node_A.py" file from the server
        length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = client_socket.recv(length)
        filename = 'node_' + char_to_send + '.py'
        node_A_path = os.path.join(directory, filename)
        with open(node_A_path, 'wb') as f:
            f.write(data)

        # Close the connection
        try:
            client_socket.close()
        except socket.error as e:
            print(f"Error closing socket: {e}")
            sys.exit(1)

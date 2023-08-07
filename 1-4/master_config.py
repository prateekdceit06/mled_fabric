import socket
import sys


class MasterConfigClient:

    def __init__(self, server_ip, server_port, client_ip, client_port, master_config_file):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port
        self.master_config_file = master_config_file

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

        transfer_complete = False

        # Receive file from the server
        with open(self.master_config_file, 'wb') as f:
            while True:
                data = client_socket.recv(1024)  # Adjust the size based on the checksum length
                if not data:
                    transfer_complete = True
                    break
                f.write(data)

        if transfer_complete:
            print("Transfer completed.")
        # Close the connection
        try:
            client_socket.close()
        except socket.error as e:
            print(f"Error closing socket: {e}")
            sys.exit(1)

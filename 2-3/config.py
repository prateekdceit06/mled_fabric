from process_config import ProcessConfigHandler
from master_config import MasterConfigHandler
import utils
import socket
import sys
import os
import logging
import time
import threading

logging.basicConfig(format='%(filename)s - %(funcName)s - %(levelname)s - %(message)s', level=logging.INFO)


def terminate_process_thread(terminate_event, client_socket):
    while not terminate_event.is_set():
        time.sleep(10)
    logging.info("Terminating process thread")
    client_socket.close()


def delete_file(file_path):
    success = utils.delete_file(file_path)
    if success:
        filename = os.path.basename(file_path)
        logging.info(f"Deleted file: {filename}")


class ConfigClient:

    def __init__(self, server_ip, server_port, client_ip, client_port, directory):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_ip = client_ip
        self.client_port = client_port
        self.directory = directory

    def get_config(self, terminate_event):

        client_socket = utils.create_client_socket(self.client_ip, self.client_port)
        terminate_thread = threading.Thread(target=terminate_process_thread, args=(terminate_event, client_socket))
        terminate_thread.daemon = True
        terminate_thread.start()

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

        process_config = self.create_process_config(master_config, master_config_file_path)

        char_to_send = process_config['process_type']

        self.get_process_file(client_socket, char_to_send)

        # Close the connection
        try:
            client_socket.close()
        except socket.error as e:
            logging.error(f"Error closing socket: {e}")
            sys.exit(1)
        return master_config, process_config

    def get_master_config(self, client_socket):
        master_config_file_path = os.path.join(self.directory, 'master_config.json')
        master_config_handler = MasterConfigHandler(master_config_file_path)
        master_config_handler.get_master_config(client_socket)
        logging.info("Received master config from server")
        master_config = utils.read_json_file(master_config_file_path)
        return master_config, master_config_file_path

    def create_process_config(self, master_config, master_config_file_path):
        process_config_file_path = os.path.join(self.directory, 'process_config.json')
        process_config_handler = ProcessConfigHandler(process_config_file_path)
        process_config = process_config_handler.create_process_config(master_config, self.client_ip)
        utils.write_json_file(process_config, process_config_file_path)
        logging.info("Created process config")
        delete_file(master_config_file_path)
        return process_config

    def get_process_file(self, client_socket, char_to_send):
        filename = 'process_' + char_to_send + '.tar.gz'
        process_project_file_path = os.path.join(self.directory, filename)
        client_socket.sendall(char_to_send.encode('utf-8'))
        length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = client_socket.recv(length)
        with open(process_project_file_path, 'wb') as f:
            f.write(data)
        logging.info(f"Received process file from server: {filename}")
        utils.extract_tar_gz(self.directory, process_project_file_path)
        logging.info(f"Extracted process tar file: {filename}")
        delete_file(process_project_file_path)

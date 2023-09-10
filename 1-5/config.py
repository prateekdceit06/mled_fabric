from process_config import ProcessConfigHandler
from master_config import MasterConfigHandler
from ip_list_config import IPListConfigHandler
import utils
import socket
import sys
import os
import logging


logging.basicConfig(format=utils.logging_format, level=logging.INFO)


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

    def get_config(self):

        client_socket = utils.create_client_socket(
            self.client_ip, self.client_port)

        try:
            # Connect to the server
            client_socket.connect((self.server_ip, self.server_port))
        except socket.gaierror as e:
            logging.info(f"Address-related error connecting to server: {e}")
            sys.exit(1)
        except socket.error as e:
            logging.error(f"Connection error: {e}")
            sys.exit(1)

        logging.info(
            f"Connected to server at {self.server_ip}:{self.server_port}")

        ip_list_config = self.get_ip_list_config(client_socket)

        master_config, master_config_file_path = self.get_master_config(
            client_socket, ip_list_config['master_config_file'])

        process_config = self.create_process_config(
            master_config, master_config_file_path, ip_list_config)

        char_to_send = process_config['process_type']

        self.get_process_file(client_socket, char_to_send)

        # Close the connection
        # try:
        #     client_socket.close()
        # except socket.error as e:
        #     logging.error(f"Error closing socket: {e}")
        #     sys.exit(1)
        return process_config, client_socket

    def get_master_config(self, client_socket, master_config_file_name):
        master_config_file_path = os.path.join(
            self.directory, master_config_file_name)
        master_config_handler = MasterConfigHandler(master_config_file_path)
        master_config_handler.get_master_config(client_socket)
        logging.info("Received master config from server")
        master_config = utils.read_json_file(master_config_file_path)
        return master_config, master_config_file_path

    def get_ip_list_config(self, client_socket):
        ip_list_config_file_path = os.path.join(self.directory, 'ip_list.json')
        ip_list_config_handler = IPListConfigHandler(ip_list_config_file_path)
        ip_list_config_handler.get_ip_list_config(client_socket)
        logging.info("Received Ip list config from server")
        ip_list_config = utils.read_json_file(ip_list_config_file_path)
        return ip_list_config

    def create_process_config(self, master_config, master_config_file_path, ip_list_config):
        process_config_file_path = os.path.join(
            self.directory, 'process_config.json')
        process_config_handler = ProcessConfigHandler(process_config_file_path)
        process_config = process_config_handler.create_process_config(
            master_config, ip_list_config, self.client_ip)
        utils.write_json_file(process_config, process_config_file_path)
        logging.info("Created process config")
        delete_file(master_config_file_path)
        return process_config

    def get_process_file(self, client_socket, char_to_send):
        filename = 'process_' + char_to_send + '.tar.gz'
        process_file_path = os.path.join(self.directory, filename)
        client_socket.sendall(char_to_send.encode('utf-8'))
        length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = bytearray()
        while len(data) < length:
            packet = client_socket.recv(length - len(data))
            if not packet:
                raise Exception("Socket connection broken")
            data.extend(packet)
        with open(process_file_path, 'wb') as f:
            f.write(data)
        logging.info(f"Received process file from server: {filename}")
        utils.extract_tar_gz(self.directory, process_file_path)
        logging.info(f"Extracted process tar file: {filename}")
        new_filename = "process_file.py"
        new_filename_path = os.path.join(self.directory, new_filename)
        old_filename = 'process_' + char_to_send + '.py'
        old_filename_path = os.path.join(self.directory, old_filename)
        success = utils.rename_file(old_filename_path, new_filename_path)
        if success:
            logging.info(f"Renamed process file to: {new_filename}")
        delete_file(process_file_path)

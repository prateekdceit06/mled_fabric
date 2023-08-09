import json


class MasterConfigHandler:

    def __init__(self, master_config_file_path):
        self.master_config_file_path = master_config_file_path

    def get_master_config(self, client_socket):
        length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = client_socket.recv(length)
        with open(self.master_config_file_path, 'wb') as f:
            f.write(data)

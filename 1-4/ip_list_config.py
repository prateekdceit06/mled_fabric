class IPListConfigHandler:

    def __init__(self, ip_list_config_file_path):
        self.ip_list_config_file_path = ip_list_config_file_path

    def get_ip_list_config(self, client_socket):
        length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = client_socket.recv(length)
        with open(self.ip_list_config_file_path, 'wb') as f:
            f.write(data)


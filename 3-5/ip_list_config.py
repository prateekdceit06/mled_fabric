class IPListConfigHandler:

    def __init__(self, ip_list_config_file_path):
        self.ip_list_config_file_path = ip_list_config_file_path

    def get_ip_list_config(self, client_socket):
        length = int.from_bytes(client_socket.recv(4), byteorder='big')
        data = bytearray()
        while len(data) < length:
            packet = client_socket.recv(length - len(data))
            if not packet:
                raise Exception("Socket connection broken")
            data.extend(packet)
        with open(self.ip_list_config_file_path, 'wb') as f:
            f.write(data)


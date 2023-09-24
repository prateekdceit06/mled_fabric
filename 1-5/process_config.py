

class ProcessConfigHandler:
    layer = dict()
    process = dict()

    def __init__(self, config_file_path):
        self.config_file_path = config_file_path

    def create_process_config(self, master_config, ip_list_config, client_ip):

        ip_port_dict = dict()

        ip_port_dict['connections_process_socket'] = master_config['connections_process_socket']
        ip_port_dict['timeout_process_socket'] = master_config['timeout_process_socket']
        ip_port_dict['retries_process_socket'] = master_config['retries_process_socket']
        ip_port_dict['delay_process_socket'] = master_config['delay_process_socket']
        ip_port_dict['pause_time_before_ack'] = master_config['pause_time_before_ack']

        for layer in master_config['layers']:
            for process in layer['processes']:
                if process['ip'] == client_ip:
                    self.process = process
                    self.layer = layer
                    break
            if self.process:
                break

        clients = ip_list_config['clients']

        keys = ["child", "parent", "right_neighbor", "left_neighbor"]

        for key in keys:
            if self.process[key] is not None:
                for client in clients:
                    if client['name'] == self.process[key]:
                        ip_port_dict[f"{key}_ip"] = client['ip']
                        ip_port_dict[f"{key}_data_port"] = client['data_port']
                        ip_port_dict[f"{key}_ack_port"] = client['ack_port']
                        break
            else:
                ip_port_dict[f"{key}_ip"] = None
                ip_port_dict[f"{key}_data_port"] = None
                ip_port_dict[f"{key}_ack_port"] = None

        data_port = None
        for client in clients:
            if client['name'] == self.process['name']:
                data_port = client['data_port']
                ack_port = client['ack_port']
                break

        process_config_to_write = {
            "connections_process_socket": ip_port_dict['connections_process_socket'],
            "timeout_process_socket": ip_port_dict['timeout_process_socket'],
            "retries_process_socket": ip_port_dict['retries_process_socket'],
            "delay_process_socket": ip_port_dict['delay_process_socket'],
            "window_size": self.layer['window_size'],
            "name": self.process['name'],
            "ip": self.process['ip'],
            "data_port": data_port,
            "ack_port": ack_port,
            "layer_id": self.layer['layer_id'],
            "process_id": self.process['process_id'],
            "child": self.process['child'],
            "parent": self.process['parent'],
            "right_neighbor": self.process['right_neighbor'],
            "left_neighbor": self.process['left_neighbor'],
            "child_ip": ip_port_dict['child_ip'],
            "parent_ip": ip_port_dict['parent_ip'],
            "right_neighbor_ip": ip_port_dict['right_neighbor_ip'],
            "left_neighbor_ip": ip_port_dict['left_neighbor_ip'],
            "child_data_port": ip_port_dict['child_data_port'],
            "parent_data_port": ip_port_dict['parent_data_port'],
            "right_neighbor_data_port": ip_port_dict['right_neighbor_data_port'],
            "left_neighbor_data_port": ip_port_dict['left_neighbor_data_port'],
            "child_ack_port": ip_port_dict['child_ack_port'],
            "parent_ack_port": ip_port_dict['parent_ack_port'],
            "right_neighbor_ack_port": ip_port_dict['right_neighbor_ack_port'],
            "left_neighbor_ack_port": ip_port_dict['left_neighbor_ack_port'],
            "mtu": self.layer['layer_mtu'],
            "error_model": self.layer['error_model'],
            "error_detection_method": self.layer['error_detection_method'],
            "process_type": self.process['process_type'],
            "pause_time_before_ack": ip_port_dict['pause_time_before_ack'],
            "master_config_file": ip_list_config['master_config_file'],
        }

        if self.process['process_type'] == 'A':
            process_config_to_write["hash_method"] = master_config['hash_method']
            process_config_to_write["filename"] = master_config['filename']
            process_config_to_write["asu_server_ip"] = master_config['asu_server_ip']
            process_config_to_write["asu_server_username"] = master_config['asu_server_username']
            process_config_to_write["asu_server_full_filename"] = master_config['asu_server_full_filename']
            process_config_to_write["asu_server_private_key_name"] = master_config['asu_server_private_key_name']

        if self.process['process_type'] == 'B':
            process_config_to_write["hash_method"] = master_config['hash_method']
            process_config_to_write["received_filename"] = master_config['received_filename']

        if self.process['process_type'] in ['A', 'C', 'E']:
            process_config_to_write["packet_error_rate"] = self.process['packet_error_rate']
            process_config_to_write["error_introduction_location"] = master_config['error_introduction_location']

        return process_config_to_write

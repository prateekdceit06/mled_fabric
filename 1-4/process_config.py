

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
                        ip_port_dict[f"{key}_port"] = client['port']
                        break
            else:
                ip_port_dict[f"{key}_ip"] = None
                ip_port_dict[f"{key}_port"] = None

        port = None
        for client in clients:
            if client['name'] == self.process['name']:
                port = client['port']
                break

        process_config_to_write = {
            "connections_process_socket": ip_port_dict['connections_process_socket'],
            "timeout_process_socket": ip_port_dict['timeout_process_socket'],
            "retries_process_socket": ip_port_dict['retries_process_socket'],
            "delay_process_socket": ip_port_dict['delay_process_socket'],
            "name": self.process['name'],
            "ip": self.process['ip'],
            "port": port,
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
            "child_port": ip_port_dict['child_port'],
            "parent_port": ip_port_dict['parent_port'],
            "right_neighbor_port": ip_port_dict['right_neighbor_port'],
            "left_neighbor_port": ip_port_dict['left_neighbor_port'],
            "mtu": self.layer['layer_mtu'],
            "error_model": self.layer['error_model'],
            "error_detection_method": self.layer['error_detection_method'],
            "process_type": self.process['process_type']
        }

        return process_config_to_write

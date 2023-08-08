import json


class ProcessConfigHandler:
    layer = dict()
    process = dict()

    def __init__(self, config_file_path):
        self.config_file_path = config_file_path

    def write_process_config(self, config):
        with open(self.config_file_path, 'w') as file:
            json.dump(config, file)

    def create_process_config(self, config, client_ip):

        for layer in config['layers']:
            for process in layer['processes']:
                if process['ip'] == client_ip:
                    self.process = process
                    self.layer = layer
                    break
            if self.process:
                break

        process_config_to_write = {
            "name": self.process['name'],
            "ip": self.process['ip'],
            "layer_id": self.layer['layer_id'],
            "process_id": self.process['process_id'],
            "child": self.process['child'],
            "parent": self.process['parent'],
            "right_neighbor": self.process['right_neighbor'],
            "left_neighbor": self.process['left_neighbor'],
            "child_ip": self.process['child_ip'],
            "parent_ip": self.process['parent_ip'],
            "right_neighbor_ip": self.process['right_neighbor_ip'],
            "left_neighbor_ip": self.process['left_neighbor_ip'],
            "mtu": self.layer['layer_mtu'],
            "error_model": self.layer['error_model'],
            "error_detection_method": self.layer['error_detection_method'],
            "process_type": self.process['process_type']
        }

        return process_config_to_write

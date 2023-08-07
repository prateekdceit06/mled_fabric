
import json


class NodeConfig:
    layer = dict()
    node = dict()

    def write_node_config(self, config_file_path, config):
        with open(config_file_path, 'w') as file:
            json.dump(config, file)
        print("Node config file created.")

    def get_node_config(self, config, client_ip):

        for layer in config['layers']:
            for node in layer['nodes']:
                if node['ip'] == client_ip:
                    self.node = node
                    self.layer = layer
                    break
            if self.node:
                break

        node_config_to_write = {
            "name": self.node['name'],
            "ip": self.node['ip'],
            "layer_id":self.layer['layer_id'],
            "node_id": self.node['node_id'],
            "child": self.node['child'],
            "parent": self.node['parent'],
            "neighbor": self.node['neighbor'],
            "mtu": self.layer['layer_mtu'],
            "error_model": self.layer['error_model'],
            "error_detection_method": self.layer['error_detection_method'],
            "node_type": self.node['node_type']
        }

        return node_config_to_write


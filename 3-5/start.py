from master_config import MasterConfigClient
from node_config import NodeConfig
import os

if __name__ == '__main__':
    client_ip = '10.0.0.109'
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)
    master_config_file_path = os.path.join(directory, 'master_config.json')
    node_config_file_path = os.path.join(directory, 'node_config.json')

    master_config_client = MasterConfigClient('10.0.0.100', 50000,
                                              client_ip, 0, master_config_file_path)
    master_config_client.get_master_config()






from config import ConfigClient

import os

if __name__ == '__main__':
    client_ip = '10.0.0.103'
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)

    config_handler = ConfigClient('10.0.0.100', 50000, client_ip, 0, directory)
    master_config, node_config = config_handler.get_config()



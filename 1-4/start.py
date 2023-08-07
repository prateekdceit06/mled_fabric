from config import ConfigClient

import os

if __name__ == '__main__':
    client_ip = '10.0.0.104'
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)

    master_config_client = ConfigClient('10.0.0.100', 50000, client_ip, 0, directory)
    master_config_client.get_config()

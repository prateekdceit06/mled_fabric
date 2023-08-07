from master_config import MasterConfigClient
import os

if __name__ == '__main__':
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)
    config_file_path = os.path.join(directory, 'master_config.json')

    client = MasterConfigClient('10.0.0.100', 50000,
                                '10.0.0.102', 0, config_file_path)
    client.get_master_config()

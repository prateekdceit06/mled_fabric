from server import Server
from tree import build_tree, find_root_node, print_tree
import os
import json


# def read_master_config(master_config_file_path):
#     with open(master_config_file_path, 'r') as file:
#         data = json.load(file)
#     return data


if __name__ == "__main__":
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)
    # master_config_file_path = os.path.join(directory, 'master_config.json')
    # master_config = read_master_config(master_config_file_path)
    # tree = build_tree(master_config)
    # root_node = find_root_node(tree)
    # print_tree(root_node, tree)
    server = Server(directory)
    server.start_server()
    print("Setup Completed.")

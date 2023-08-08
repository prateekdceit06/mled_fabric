from server import Server
from print_network import PrintNetwork
import os



if __name__ == "__main__":
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)
    master_config_file_path = os.path.join(directory, 'master_config.json')
    print_network = PrintNetwork(master_config_file_path)
    print_network.print_network()
    server = Server(directory)
    server.start_server()
    print("Setup Completed.")

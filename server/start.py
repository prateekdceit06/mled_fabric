from server import Server
from print_network import PrintNetwork
from utils import logging_format as logging_format
import os
import threading
import signal
import logging
import utils

logging.basicConfig(format=logging_format, level=logging.INFO)

terminate_event = threading.Event()


def signal_handler(sig, frame):
    logging.info("Gracefully shutting down")
    terminate_event.set()  # Signal all threads to terminate


def start_server_in_thread(master_process, ip_list):
    master_process.start_server(terminate_event, ip_list)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)
    ip_list_path = os.path.join(directory, 'ip_list.json')
    ip_list = utils.read_json_file(ip_list_path)

    master_config_file = ip_list['master_config_file']
    master_config_file_path = os.path.join(directory, master_config_file)

    print_network = PrintNetwork(master_config_file_path)
    print_network.print_network()

    master_process = Server(directory)

    server_thread = threading.Thread(
        target=start_server_in_thread, name='ServerThread', args=(master_process, ip_list,))
    server_thread.start()

    logging.info("Setup Completed.")

from server import Server
from print_network import PrintNetwork

import os
import threading
import signal
import logging

logging.basicConfig(format='%(filename)s - %(funcName)s - %(levelname)s - %(message)s', level=logging.INFO)

terminate_event = threading.Event()


def signal_handler(sig, frame):
    logging.info("Gracefully shutting down")
    terminate_event.set()  # Signal all threads to terminate


def start_server_in_thread(master_process):
    master_process.start_server(terminate_event)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)
    master_config_file_path = os.path.join(directory, 'master_config.json')

    print_network = PrintNetwork(master_config_file_path)
    print_network.print_network()

    master_process = Server(directory)

    server_thread = threading.Thread(target=start_server_in_thread, args=(master_process,))
    server_thread.start()

    print("Setup Completed.")

from config import ConfigClient
import os
import threading
import logging
import signal
from utils import logging_format as logging_format
import importlib
import time


logging.basicConfig(format=logging_format, level=logging.INFO)

terminate_event = threading.Event()


def fetch_config(config_handler, results):
    process_config = config_handler.get_config()
    results['process_config'] = process_config


def process_create_out_socket(process_handler, connections, timeout, client_ip):
    process_handler.create_out_sockets(connections, timeout, client_ip)


def process_create_route(process_handler, retries, delay):
    process_handler.create_data_route(retries, delay)
    process_handler.create_ack_route(retries, delay)


def signal_handler(sig, frame):
    logging.info("Gracefully shutting down")
    terminate_event.set()


if __name__ == '__main__':
    terminate_event = threading.Event()
    signal.signal(signal.SIGINT, signal_handler)

    client_ip = '10.0.0.108'
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)

    config_handler = ConfigClient('10.0.0.100', 50000, client_ip, 0, directory)

    results = {}

    config_thread = threading.Thread(
        target=fetch_config, args=(config_handler, results,))
    config_thread.start()
    config_thread.join()

    process_config = results.get('process_config')
    logging.info("Process Setup Completed.")

    connections = process_config['connections_process_socket']
    timeout = process_config['timeout_process_socket']
    retries = process_config['retries_process_socket']
    delay = process_config['delay_process_socket']

    process_file = importlib.import_module('process_file')

    process_handler = process_file.ProcessHandler(
        process_config, terminate_event)

    process_start_in_socket_thread = threading.Thread(target=process_create_route, name='process_create_routes',
                                                      args=(process_handler, retries, delay,))
    process_start_in_socket_thread.daemon = True
    process_start_in_socket_thread.start()

    process_create_out_socket_thread = threading.Thread(target=process_create_out_socket, name='process_create_out_sockets',
                                                        args=(process_handler, connections, timeout, client_ip))
    process_create_out_socket_thread.daemon = True
    process_create_out_socket_thread.start()

    process_create_out_socket_thread.join()

    # while not process_handler.are_sockets_alive():
    #     time.sleep(5)

    while True:
        pass

    logging.info("Process Ended.")

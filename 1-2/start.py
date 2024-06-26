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

    client_ip = '10.0.0.102'
    server_ip = '10.0.0.100'
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)

    config_handler = ConfigClient(server_ip, 50000, client_ip, 0, directory)

    results = {}

    config_thread = threading.Thread(name='ConfigThread',
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

    create_routes_thread = threading.Thread(target=process_create_route, name='CreateRoutesThread',
                                            args=(process_handler, retries, delay,))
    create_routes_thread.daemon = True
    create_routes_thread.start()

    create_out_socket_thread = threading.Thread(target=process_create_out_socket, name='CreateOutSocketThread',
                                                args=(process_handler, connections, timeout, client_ip,))
    create_out_socket_thread.daemon = True
    create_out_socket_thread.start()

    create_out_socket_thread.join()

    while True:
        pass

    logging.info("Process Ended.")

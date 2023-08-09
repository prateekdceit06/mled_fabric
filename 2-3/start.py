from config import ConfigClient
from process_file import ProcessHandler
import os
import threading
import logging
import signal
from utils import logging_format as logging_format


logging.basicConfig(format=logging_format, level=logging.INFO)

terminate_event = threading.Event()


def fetch_config(config_handler, results):
    process_config = config_handler.get_config()
    results['process_config'] = process_config


def process_start_out_socket(process_handler, connections, timeout):
    process_handler.create_out_socket(connections, timeout)


def process_create_route(process_handler, retries, delay):
    process_handler.create_route(retries, delay)


def signal_handler(sig, frame):
    logging.info("Gracefully shutting down")
    terminate_event.set()


if __name__ == '__main__':
    terminate_event = threading.Event()
    signal.signal(signal.SIGINT, signal_handler)

    client_ip = '10.0.0.107'
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)

    config_handler = ConfigClient('10.0.0.100', 50000, client_ip, 0, directory)

    results = {}

    config_thread = threading.Thread(target=fetch_config, args=(config_handler, results,))
    config_thread.start()
    config_thread.join()

    process_config = results.get('process_config')
    print("Process Setup Completed.")

    connections = process_config['connections_process_socket']
    timeout = process_config['timeout_process_socket']
    retries = process_config['retries_process_socket']
    delay = process_config['delay_process_socket']

    process_handler = ProcessHandler(process_config, terminate_event)

    process_start_in_socket_thread = threading.Thread(target=process_create_route,
                                                      args=(process_handler, retries, delay,))
    process_start_in_socket_thread.daemon = True
    process_start_in_socket_thread.start()

    process_start_out_socket_thread = threading.Thread(target=process_start_out_socket,
                                                       args=(process_handler, connections, timeout,))
    process_start_out_socket_thread.daemon = True
    process_start_out_socket_thread.start()

    process_start_out_socket_thread.join()

    logging.info("Process Ended.")

from config import ConfigClient
import os
import threading
import logging
import signal
from utils import logging_format as logging_format
import importlib


logging.basicConfig(format=logging_format, level=logging.INFO)

terminate_event = threading.Event()


def fetch_config(config_handler, results):
    process_config, client_socket = config_handler.get_config()
    results['process_config'] = process_config
    results['client_socket'] = client_socket


def process_create_out_socket(process_handler, connections, timeout, client_ip, client_socket):
    process_handler.create_out_sockets(
        connections, timeout, client_ip, client_socket)


def process_create_route(process_handler, retries, delay):
    process_handler.create_data_route(retries, delay)
    process_handler.create_ack_route(retries, delay)


def signal_handler(sig, frame):
    logging.info("Gracefully shutting down")
    terminate_event.set()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    while True:

        try:
            choice = int(input("Enter 1 to start sending file or 2 to exit: "))
        except ValueError:
            print("Please enter a valid number!")
            continue

        if choice in [1, 2]:
            if choice == 1:
                client_ip = '10.0.0.108'
                server_ip = '10.0.0.100'
                path = os.path.abspath(__file__)
                directory = os.path.dirname(path)

                config_handler = ConfigClient(
                    server_ip, 50000, client_ip, 0, directory)

                results = {}

                config_thread = threading.Thread(name='ConfigThread',
                                                 target=fetch_config, args=(config_handler, results,))
                config_thread.start()
                config_thread.join()

                process_config = results.get('process_config')
                client_socket = results.get('client_socket')
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
                                                            args=(process_handler, connections, timeout, client_ip, client_socket, ))
                create_out_socket_thread.daemon = True
                create_out_socket_thread.start()

                create_out_socket_thread.join()

                logging.info("Process Ended.")
            else:
                print("Exiting...")
                break
        else:
            print("Invalid choice!")
            continue

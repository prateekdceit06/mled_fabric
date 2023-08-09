from config import ConfigClient
import os
import threading
import logging
import signal

logging.basicConfig(format='%(filename)s - %(funcName)s - %(levelname)s - %(message)s', level=logging.INFO)



def fetch_config(config_handler, results, terminate_event):
    master_config, process_config = config_handler.get_config(terminate_event)
    results['master_config'] = master_config
    results['process_config'] = process_config


def signal_handler(sig, frame):
    logging.info("Gracefully shutting down")
    terminate_event.set()  # Signal all threads to terminate


if __name__ == '__main__':
    terminate_event = threading.Event()
    signal.signal(signal.SIGINT, signal_handler)

    client_ip = '10.0.0.107'
    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)

    config_handler = ConfigClient('10.0.0.100', 50000, client_ip, 0, directory)

    results = {}

    config_thread = threading.Thread(target=fetch_config, args=(config_handler, results, terminate_event))
    config_thread.start()
    config_thread.join()

    master_config = results.get('master_config')
    process_config = results.get('process_config')

    print("Process Setup Completed.")

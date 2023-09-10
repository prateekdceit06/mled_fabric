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


def start_server_in_thread(master_process, ip_list, master_config_file):
    master_process.start_server(terminate_event, ip_list, master_config_file)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    path = os.path.abspath(__file__)
    directory = os.path.dirname(path)

    config_path = os.path.join(directory, 'config')

    flag = True

    while (flag):
        try:
            all_items = os.listdir(config_path)
            files_only = [item for item in all_items if os.path.isfile(
                os.path.join(config_path, item))]

            print("Select a master config file:\n")

            for index, file in enumerate(files_only, 1):
                print(f"[{index}] {file}")

            try:
                choice = int(input("\nSelect a file by entering its number: "))
            except ValueError:
                flag = False
                print("Please enter a valid number!")
                continue

            if 1 <= choice <= len(files_only):
                master_config_file = files_only[choice - 1]
                print(f"You selected: {master_config_file}")
                flag = True

                ip_list_path = os.path.join(directory, 'ip_list.json')
                ip_list = utils.read_json_file(ip_list_path)

                ip_list['master_config_file'] = master_config_file

                utils.write_json_file(ip_list, ip_list_path)
            else:
                flag = False
                print("Invalid choice!")
                continue
            master_config_file_path = os.path.join(
                config_path, master_config_file)

            print_network = PrintNetwork(master_config_file_path)
            print_network.print_network()

            master_process = Server(directory)

            server_thread = threading.Thread(
                target=start_server_in_thread, name='ServerThread', args=(master_process, ip_list, master_config_file,))

            server_thread.daemon = True
            server_thread.start()
            server_thread.join()
        except:
            flag = False
            print("Something went wrong...")

    logging.info("Exiting MLED.")

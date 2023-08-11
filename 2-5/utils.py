import json
import os
import socket
import logging
import sys
import tarfile


logging_format = '%(pathname)s:%(lineno)d - %(funcName)s - %(levelname)s - %(message)s'

logging.basicConfig(format=logging_format, level=logging.INFO)

def read_json_file(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data


def write_json_file(data, filename):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)


def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)
        return True


def create_client_socket(client_ip, client_port):
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        logging.error(f"Error creating socket: {e}")
    if client_socket is not None:
        try:
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_socket.bind((client_ip, client_port))
        except socket.error as err:
            if err.errno == 98:
                pass
            else:
                logging.error(f"Error on socket bind: {err}")
    return client_socket


def create_server_socket(server_ip, server_port, connections=10, timeout=5):
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        logging.error(f"Error creating socket: {e}")

    if server_socket is not None:
        server_socket.settimeout(timeout)  # Set a timeout on accept()

        try:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((server_ip, server_port))
        except socket.error as err:
            if err.errno == 98:
                pass
            else:
                logging.error(f"Error on socket bind: {err}")

        try:
            server_socket.listen(connections)
            logging.info(f"Listening on {server_ip}:{server_port}")
        except socket.error as e:
            logging.error(f"Error on socket listen: {e}")

    return server_socket



def create_tarfile(filename, *files):
    with tarfile.open(filename, "w:gz") as tar:
        for file in files:
            tar.add(file, arcname=os.path.basename(file))


def extract_tar_gz(directory, file_path):
    with tarfile.open(file_path, 'r:gz') as tar:
        tar.extractall(path=directory)


def rename_file(old_path, new_path):
    try:
        os.rename(old_path, new_path)
        return True
    except Exception as e:
        return False

def get_key_for_value(dict, value_to_find):
    return [key for key, value in dict.items() if value == value_to_find]

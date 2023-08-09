import json
import os
import socket
import logging
import sys
import tarfile

logging.basicConfig(format='%(filename)s - %(funcName)s - %(levelname)s - %(message)s', level=logging.INFO)


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
    try:
        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        logging.error(f"Error creating socket: {e}")
        sys.exit(1)

    try:
        client_socket.bind((client_ip, client_port))
    except socket.error as e:
        logging.error(f"Error on socket bind: {e}")
        sys.exit(1)

    return client_socket


def create_server_socket(server_ip, server_port):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        logging.error(f"Error creating socket: {e}")
        sys.exit(1)
    server_socket.settimeout(5)  # Set a timeout on accept()
    try:
        server_socket.bind((server_ip, server_port))
    except socket.error as e:
        logging.error(f"Error on socket bind: {e}")
        sys.exit(1)

    try:
        server_socket.listen(10)
        logging.info(f"Listening on {server_ip}:{server_port}")
    except socket.error as e:
        logging.error(f"Error on socket listen: {e}")
        sys.exit(1)

    return server_socket


def create_tarfile(filename, *files):
    with tarfile.open(filename, "w:gz") as tar:
        for file in files:
            tar.add(file, arcname=os.path.basename(file))


def extract_tar_gz(directory, file_path):
    with tarfile.open(file_path, 'r:gz') as tar:
        tar.extractall(path=directory)

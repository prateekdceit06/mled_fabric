import socket
import json
import sys
import signal
import threading
import logging

lock = threading.Lock()
logging.basicConfig(level=logging.INFO)


def read_json_file(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data


def send_file_to_client(client_socket, filename):
    with open(filename, 'rb') as file:
        data = file.read()
    client_socket.sendall(len(data).to_bytes(4, byteorder='big'))
    client_socket.sendall(data)
    logging.info(f"File {filename} sent to client {client_socket.getpeername()[0]}")


def handle_client(server_socket, client_socket, addr, connected_clients, client_ips):
    node_type = client_socket.recv(2)
    received_char = node_type.decode('utf-8')
    logging.info(f"Received {received_char} from client {addr[0]}")
    filename = f"./server/node_{received_char}.py"
    send_file_to_client(client_socket, filename)
    with lock:
        if connected_clients == client_ips:
            logging.info("All clients connected. Closing server socket")
            server_socket.close()


def signal_handler(sig, frame):
    logging.info("Gracefully shutting down")
    sys.exit(0)


def client_handler(server_socket, client_socket, addr, client_ips, connected_clients):
    if addr[0] in client_ips:
        logging.info(f"Connected with {addr[0]}")
        connected_clients.add(addr[0])
        send_file_to_client(client_socket, './server/master_config.json')
        handle_client(server_socket, client_socket, addr, connected_clients, client_ips)
    else:
        client_socket.close()


class Server:

    def start_server(self):
        signal.signal(signal.SIGINT, signal_handler)
        ip_list = read_json_file('./server/ip_list.json')
        server_ip = ip_list['server_ip']
        server_port = ip_list['server_port']
        client_ips = set(ip_list['client'])

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.settimeout(1)  # Set a timeout on accept()
        try:
            server_socket.bind((server_ip, server_port))
        except socket.error as e:
            logging.info(f"Error on socket bind: {e}")
            sys.exit(1)

        try:
            server_socket.listen(10)
            logging.info(f"Listening on {server_ip}:{server_port}")
        except socket.error as e:
            logging.info(f"Error on socket listen: {e}")
            sys.exit(1)

        connected_clients = set()

        try:
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    logging.info(f"Accepted connection from {addr[0]}")
                    client_thread = threading.Thread(target=client_handler,
                                                     args=(server_socket, client_socket, addr,
                                                           client_ips, connected_clients))
                    client_thread.start()
                except socket.timeout:
                    with lock:
                        if connected_clients == client_ips:
                            logging.info("Closing after timeout.")
                            break
                        else:
                            continue
                except socket.error as e:
                    if e.errno == 9:  # Bad file descriptor
                        logging.info("Server socket closed. Exiting accept loop.")
                        break
                    else:
                        raise
        except socket.error as e:
            logging.info(f"Error on socket accept: {e}")
            sys.exit(1)

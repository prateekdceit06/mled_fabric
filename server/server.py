import socket
import json
import sys
import signal
import threading


def read_json_file(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data


def send_file_to_client(client_socket, filename):
    file_sent = False
    with open(filename, 'rb') as file:
        while True:
            data = file.read(1024)
            if not data:
                file_sent = True
                break
            client_socket.sendall(data)
    client_socket.close()
    if file_sent:
        print(f"File {filename} sent to client {client_socket.getpeername()[0]}")


def signal_handler(sig, frame):
    print("Gracefully shutting down")
    sys.exit(0)


def client_handler(client_socket, addr, client_ips, connected_clients):
    if addr[0] in client_ips:
        print(f"Connected with {addr[0]}")
        send_file_to_client(client_socket, './server/master_config.json')
        connected_clients.add(addr[0])
    else:
        client_socket.close()


def start_server():
    signal.signal(signal.SIGINT, signal_handler)
    ip_list = read_json_file('./server/ip_list.json')
    server_ip = ip_list['server_ip']
    server_port = ip_list['server_port']
    client_ips = set(ip_list['client'])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((server_ip, server_port))
    except socket.error as e:
        print(f"Error on socket bind: {e}")
        sys.exit(1)

    try:
        server_socket.listen(5)
        print(f"Listening on {server_ip}:{server_port}")
    except socket.error as e:
        print(f"Error on socket listen: {e}")
        sys.exit(1)

    connected_clients = set()

    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Accepted connection from {addr[0]}")
            client_thread = threading.Thread(target=client_handler,
                                             args=(client_socket, addr, client_ips, connected_clients))
            client_thread.start()

    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()

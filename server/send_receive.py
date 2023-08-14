from crc import CRC
from checksum import Checksum
from header import fixed_format

import struct


class SendReceive:

    def get_value_to_check(chunk, method, parameter):
        if method == "crc":
            crc_obj = CRC(parameter)
            value = crc_obj.calculate(chunk)
        elif method == "checksum":
            checksum_obj = Checksum(parameter)
            value = checksum_obj.calculate(chunk)
        return value

    def send_data(self, sending_socket, packet):
        header = packet.header
        packed_header = header.pack()
        chunk = packet.chunk
        sending_socket.sendall(packed_header)
        sending_socket.send(header.check_value.encode())
        sending_socket.sendall(struct.pack(
            f"{header.size_of_errors}i", *header.errors))

        sending_socket.sendall(chunk.encode())

    def receive_data(self, receiving_sock):
        fixed_data = receiving_sock.recv(struct.calcsize(fixed_format))
        received_seq_num, received_src, received_dest, received_size_of_check_value, received_size_of_chunk, received_ack_byte, received_size_of_errors = struct.unpack(
            fixed_format, fixed_data)

        received_check_value = receiving_sock.recv(
            received_size_of_check_value).decode()

        received_errors_format = f"{received_size_of_errors}i"
        received_errors_data = receiving_sock.recv(
            struct.calcsize(received_errors_format))
        received_errors = list(struct.unpack(
            received_errors_format, received_errors_data))
        received_chunk = receiving_sock.recv(received_size_of_chunk).decode()

        return received_seq_num, received_src, received_dest, received_check_value, received_chunk, received_ack_byte, received_errors

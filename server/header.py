import struct

fixed_format = "i 3s 3s i i B i ?"


class Header:
    def __init__(self, seq_num, src=None, dest=None, check_value=None, size_of_data=None, ack_byte=None, errors=None, last_packet=None):

        self.seq_num = seq_num
        self.src = src
        self.dest = dest
        self.size_of_check_value = len(check_value)
        self.check_value = check_value
        self.size_of_data = size_of_data
        self.ack_byte = ack_byte
        self.size_of_errors = len(errors)
        self.errors = errors
        self.last_packet = last_packet

    def __str__(self):
        return (f"Header(\n"
                f"Size of Data: {self.size_of_data},\n"
                f"Sequence Number: {self.seq_num},\n"
                f"Acknowledgment Byte: {self.ack_byte},\n"
                f"Size of Errors: {self.size_of_errors},\n"
                f"Errors: {self.errors},\n"
                f"Size of Check Value: {self.size_of_check_value},\n"
                f"Check Value: {self.check_value},\n"
                f"Source: {self.src},\n"
                f"Destination: {self.dest}\n"
                f")")

    def pack(self):
        packed_header = struct.pack(fixed_format, self.seq_num, self.src.encode(), self.dest.encode(
        ), self.size_of_check_value, self.size_of_data, self.ack_byte, self.size_of_errors, self.last_packet)
        return packed_header

    def unpack(packed_header):
        unpacked_data = struct.unpack(fixed_format, packed_header)
        seq_num = unpacked_data[0]
        src = unpacked_data[1].decode().strip('\x00')
        dest = unpacked_data[2].decode().strip('\x00')
        size_of_check_value = unpacked_data[3]
        size_of_data = unpacked_data[4]
        ack_byte = unpacked_data[5]
        size_of_errors = unpacked_data[6]
        last_packet = unpacked_data[7]
        header = Header(seq_num, src, dest, b'\x00' * size_of_check_value,
                        size_of_data, ack_byte, [], last_packet)
        return header

    def get_size(self):
        fixed_size = struct.calcsize(fixed_format)
        check_value_size = len(self.check_value.encode())
        errors_size = struct.calcsize(f"{self.size_of_errors}i")
        return fixed_size + check_value_size + errors_size

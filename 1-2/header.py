import struct

fixed_format = "i 3s 3s i i B i"


class Header:
    def __init__(self, seq_num, src, dest, check_value, size_of_data, ack_byte, errors):

        self.seq_num = seq_num
        self.src = src
        self.dest = dest
        self.size_of_check_value = len(check_value)
        self.check_value = check_value
        self.size_of_data = size_of_data
        self.ack_byte = ack_byte
        self.size_of_errors = len(errors)
        self.errors = errors

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
        ), self.size_of_check_value, self.size_of_data, self.ack_byte, self.size_of_errors)
        return packed_header

class Header:
    def __init__(self, seq_num, src, dest, size_of_data=0, ack_byte=0, size_of_errors=0, errors=None, check_value=0):
        self.size_of_data = size_of_data
        self.seq_num = seq_num
        self.ack_byte = ack_byte
        self.size_of_errors = size_of_errors
        self.errors = errors if size_of_errors != 0 and errors is not None else []
        self.check_value = check_value
        self.src = src
        self.dest = dest

    def __str__(self):
        return (f"Header(\n"
                f"Size of Data: {self.size_of_data},\n"
                f"Sequence Number: {self.seq_num},\n"
                f"Acknowledgment Byte: {self.ack_byte},\n"
                f"Size of Errors: {self.size_of_errors},\n"
                f"Errors: {self.errors},\n"
                f"Check Value: {self.check_value},\n"
                f"Source: {self.src},\n"
                f"Destination: {self.dest}\n"
                f")")

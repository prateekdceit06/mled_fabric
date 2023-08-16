from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from header import Header


class Packet:
    def __init__(self, header: 'Header', chunk: bytes):
        self.header = header
        self.chunk = chunk
        self.seq_num = header.seq_num

    def __str__(self):
        return f"Packet({self.seq_num}, {self.header}, {self.chunk})"
    
    def get_size(self):
        return len(self.chunk) + self.header.get_size()

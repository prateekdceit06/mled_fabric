from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from header import Header


class Packet:
    def __init__(self, header: 'Header', data: bytes):
        self.header = header
        self.data = data

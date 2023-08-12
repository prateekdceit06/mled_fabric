# Process A
from process import ProcessHandlerBase


class ProcessHandler(ProcessHandlerBase):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)

    def create_out_data_socket(self, connections, timeout, ip):
        data_port = self.process_config['data_port']
        super().create_out_data_socket(connections, timeout, ip, data_port)

    def create_out_ack_socket(self, connections, timeout, ip):
        ack_port = self.process_config['ack_port']
        super().create_out_ack_socket(connections, timeout, ip, ack_port)

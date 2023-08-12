# Process B

from process import ProcessHandlerBase
import utils


class ProcessHandler(ProcessHandlerBase):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)

    def create_data_route(self, retries, delay):
        in_data_socket = utils.create_client_socket(
            self.process_config['ip'], 0)
        host, port = self.find_data_host_port()
        in_data_socket = super().connect_in_socket(
            in_data_socket, retries, delay, host, port, "data")

    def find_data_host_port(self):
        host, port = self.process_config['child_ip'], self.process_config['child_data_port']
        return host, port

    def create_out_ack_socket(self, connections, timeout, ip):
        if self.process_config['ack_port'] is not None:
            ack_port = self.process_config['ack_port']
            super().create_out_ack_socket(connections, timeout, ip, ack_port)

    def create_out_data_socket(self, connections, timeout, ip):
        data_port = self.process_config['data_port']
        super().create_out_data_socket(connections, timeout, ip, data_port)

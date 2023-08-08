from print_colour import PrintColor
import json


def read_master_config(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def center_string(s):
    return s.center(17, ' ')


class PrintNetwork:

    def __init__(self, file_path):
        self.file_path = file_path
        self.data = read_master_config(self.file_path)
        self.arrange_processes()
        self.layer_wise_processes = [layer['processes'] for layer in self.data['layers']]
        self.last_layer_length = len(self.data['layers'][-1]['processes'])
        self.printing_length = 2 * self.last_layer_length - 1


    def _print_line(self, processes_in_layer, connection_block_number, content_func, last_layer=False):
        for index, process in enumerate(processes_in_layer):
            print(content_func(process), end="")
            if index != len(processes_in_layer) - 1:
                if last_layer:
                    print(PrintColor.print_in_red(center_string("\u2190" + "\u2500" * 13 + "\u2192")), end="")
                else:
                    print(center_string(" ") * int(connection_block_number), end="")
        print()

    def print_network(self):
        print(PrintColor.print_in_green(PrintColor.divider()))

        for out_index, processes_in_layer in enumerate(self.layer_wise_processes):
            connection_block_number = (self.printing_length - len(processes_in_layer)) / (len(processes_in_layer) - 1)

            last_layer = out_index == len(self.layer_wise_processes) - 1

            self._print_line(processes_in_layer, connection_block_number,
                             lambda process: PrintColor.print_in_green_back(center_string(process["name"])), last_layer)
            self._print_line(processes_in_layer, connection_block_number,
                             lambda process: PrintColor.print_in_green_back(center_string(process["ip"])))

            if not last_layer:
                self._print_line(processes_in_layer, connection_block_number,
                                 lambda process: PrintColor.print_in_red(center_string("\u2191")))
                self._print_line(processes_in_layer, connection_block_number,
                                 lambda process: PrintColor.print_in_red(center_string("|")))
                self._print_line(processes_in_layer, connection_block_number,
                                 lambda process: PrintColor.print_in_red(center_string("\u2193")))

        print(PrintColor.print_in_green(PrintColor.divider()))

    def arrange_processes(self):
        self.data['layers'] = sorted(self.data['layers'], key=lambda layer: len(layer['processes']))
        for layer in self.data['layers']:
            layer['processes'] = sorted(layer['processes'], key=lambda process: process['process_id'])


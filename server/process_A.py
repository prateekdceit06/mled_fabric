# Process A
import process


class ProcessHandler(process.ProcessHandler):

    def __init__(self, process_config, terminate_event):
        super().__init__(process_config, terminate_event)

class PrintColor:
    RESET = "\u001B[0m"
    BLACK = "\u001B[30m"
    BLACK_BACKGROUND = "\u001B[40m"
    RED = "\u001B[31m"
    RED_BACKGROUND = "\033[41m"
    GREEN = "\u001B[32m"
    BRIGHT_GREEN = "\u001B[32;1m"
    GREEN_BACKGROUND = "\u001B[42m"
    YELLOW = "\u001B[33m"
    YELLOW_BACKGROUND = "\u001B[43m"
    BLUE = "\u001B[34m"
    BLUE_BACKGROUND = "\u001B[44m"
    PURPLE = "\u001B[35m"
    PURPLE_BACKGROUND = "\u001B[45m"
    CYAN = "\u001B[36m"
    CYAN_BACKGROUND = "\u001B[46m"
    WHITE = "\u001B[37m"
    WHITE_BACKGROUND = "\u001B[47m"
    RED_BACKGROUND_BRIGHT = "\033[0;101m"

    @staticmethod
    def print_in_bright_red_back(s):
        return PrintColor.RED_BACKGROUND_BRIGHT + s + PrintColor.RESET

    @staticmethod
    def print_in_black(s):
        return PrintColor.BLACK + s + PrintColor.RESET

    @staticmethod
    def print_in_black_back(s):
        return PrintColor.BLACK_BACKGROUND + s + PrintColor.RESET

    @staticmethod
    def print_in_red(s):
        return PrintColor.RED + s + PrintColor.RESET

    @staticmethod
    def print_in_red_back(s):
        return PrintColor.RED_BACKGROUND + s + PrintColor.RESET

    @staticmethod
    def print_in_green(s):
        return PrintColor.GREEN + s + PrintColor.RESET

    @staticmethod
    def print_in_green_back(s):
        return PrintColor.GREEN_BACKGROUND + s + PrintColor.RESET

    @staticmethod
    def print_in_yellow(s):
        return PrintColor.YELLOW + s + PrintColor.RESET

    @staticmethod
    def print_in_yellow_back(s):
        return PrintColor.YELLOW_BACKGROUND + s + PrintColor.RESET

    @staticmethod
    def print_in_blue(s):
        return PrintColor.BLUE + s + PrintColor.RESET

    @staticmethod
    def print_in_blue_back(s):
        return PrintColor.BLUE_BACKGROUND + s + PrintColor.RESET

    @staticmethod
    def print_in_purple(s):
        return PrintColor.PURPLE + s + PrintColor.RESET

    @staticmethod
    def print_in_purple_back(s):
        return PrintColor.PURPLE_BACKGROUND + s + PrintColor.RESET

    @staticmethod
    def print_in_cyan(s):
        return PrintColor.CYAN + s + PrintColor.RESET

    @staticmethod
    def print_in_cyan_back(s):
        return PrintColor.CYAN_BACKGROUND + s + PrintColor.RESET

    @staticmethod
    def print_in_white(s):
        return PrintColor.WHITE + s + PrintColor.RESET

    @staticmethod
    def print_in_white_back(s):
        return PrintColor.WHITE_BACKGROUND + s + PrintColor.RESET

    @staticmethod
    def divider():
        return "=" * 153

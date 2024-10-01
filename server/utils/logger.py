import logging
import os


LOG_FORMAT = "%(asctime)s %(message)s"
DEFAULT_LEVEL = logging.DEBUG


class Logger:

    PATH = "./logs"

    def __init__(self, name, mode="w"):
        self.create_directory()
        self.filename = f"{Logger.PATH}/{name}.log"
        self.logger = logging.getLogger(name)
        self.logger.setLevel(DEFAULT_LEVEL)

        # File handler
        file_handler = logging.FileHandler(self.filename, mode=mode)
        file_handler.setFormatter(
            logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
        )
        self.logger.addHandler(file_handler)

        # Stream handler (console)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(
            logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
        )
        self.logger.addHandler(stream_handler)

        self.logger.info(f"Logger init() {self.filename}")

    def create_directory(self):
        if not os.path.exists(Logger.PATH):
            os.makedirs(Logger.PATH)

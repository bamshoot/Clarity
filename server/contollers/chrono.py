import time
import threading
from utils.logger import Logger


class Chrono:
    def __init__(self, interval=10):
        self.interval = interval
        self.logger = Logger("chrono")
        self._stop_event = threading.Event()
        self.thread = None

    def _run(self):
        while not self._stop_event.is_set():
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.logger.logger.info(f"Current time: {current_time}")
            time.sleep(self.interval)

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run)
            self.thread.start()
        else:
            self.logger.logger.warning("Chrono is already running")

    def stop(self):
        if self.thread and self.thread.is_alive():
            self._stop_event.set()
            self.thread.join()
        else:
            self.logger.logger.warning("Chrono is not running")

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

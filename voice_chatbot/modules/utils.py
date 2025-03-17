import time
from functools import wraps
from contextlib import contextmanager

class TimingStats:
    def __init__(self):
        self.startup_time = None
        self.last_response_time = None
        self.response_times = []  # Keep track of all response times
        
    def get_average_response_time(self):
        if not self.response_times:
            return 0
        return sum(self.response_times) / len(self.response_times)
    
    def format_time(self, seconds):
        """Format seconds into minutes and seconds"""
        minutes = int(seconds // 60)
        seconds = seconds % 60
        if minutes > 0:
            return f"{minutes}m {seconds:.2f}s"
        return f"{seconds:.2f}s"

@contextmanager
def measure_time():
    """Context manager to measure execution time"""
    start_time = time.time()
    yield lambda: time.time() - start_time
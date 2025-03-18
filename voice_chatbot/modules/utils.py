import time
from functools import wraps
from contextlib import contextmanager

class TimingStats:
    def __init__(self):
        self.startup_time = None
        self.last_response_time = None
        self.response_times = []
        # Add new timing attributes
        self.last_audio_time = None
        self.audio_times = []
        self.last_total_time = None
        self.total_times = []
    
    def get_average_response_time(self):
        if not self.response_times:
            return 0
        return sum(self.response_times) / len(self.response_times)
    
    # Add new methods
    def get_average_audio_time(self):
        if not self.audio_times:
            return 0
        return sum(self.audio_times) / len(self.audio_times)
    
    def get_average_total_time(self):
        if not self.total_times:
            return 0
        return sum(self.total_times) / len(self.total_times)
    
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
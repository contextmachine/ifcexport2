
import os, psutil
from typing import TypedDict
from dataclasses import dataclass
class ConsumerProcessMemoryInfo(TypedDict):
    rss:int

class ConsumerProcessCpuTimes(TypedDict):
    user:float
    system:float
    children_user:float
    children_system:float

@dataclass
class ConsumerProcessStats:
    pid:int
    is_running:int
    cpu_times:ConsumerProcessCpuTimes
    cpu_percent:float
    memory_info:ConsumerProcessMemoryInfo
    memory_percent: float

def get_process(pid=None):
    if pid is None:
        pid = os.getpid()
    proc = psutil.Process(pid)
    return proc
def process_stats(pid=None)->ConsumerProcessStats:

    proc = get_process(pid)
    stats=ConsumerProcessStats(proc.pid,proc.is_running(),proc.cpu_times()._asdict(), proc.cpu_percent(), proc.memory_full_info()._asdict(),     proc.memory_percent())
    return stats
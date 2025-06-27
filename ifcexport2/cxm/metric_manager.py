import json
import logging
import os
import threading
import time
import uuid
import warnings
from contextlib import contextmanager
from dataclasses import dataclass, asdict, fields
from typing import TypedDict, Literal, Optional

import psutil
import ujson
import redis

from ifcexport2.api.settings import DEPLOYMENT_NAME


class ProcessMemoryInfo(TypedDict):
    rss:int

class ProcessCpuTimes(TypedDict):
    user:float
    system:float
    children_user:float
    children_system:float

@dataclass
class ProcessStats:
    pid:int
    cpu_times:ProcessCpuTimes
    cpu_percent:float
    memory_info:ProcessMemoryInfo
    memory_percent: float
@dataclass
class ApplicationMetrics:
    process_stats:ProcessStats
    app_message:str


def get_process(pid=None):
    if pid is None:
        pid = os.getpid()
    proc = psutil.Process(pid)
    return proc
import struct
import traceback
class ExceptionData(TypedDict):
    type:str
    args:list[Optional[str]]
    traceback:str
    attempts:int

def exception_data(exc:Exception)->ExceptionData:


    full_error = traceback.format_exc()
    print("Captured traceback:\n", full_error)

    return {'type':exc.__class__.__name__,'args':[str(arg) for arg in exc.args],'traceback':full_error}
    # full_error is now a normal str — log it, send it, test it, etc.
def get_process_stats(pid=None)->ProcessStats:

    proc = get_process(pid)
    stats=ProcessStats(proc.pid,
                       proc.cpu_times()._asdict(),
                       proc.cpu_percent(),
                       proc.memory_full_info()._asdict(),
                       proc.memory_percent())
    return stats

class MetricManager:
    __allowed_key_types=bytes , memoryview , str , int , float
    __allowed_val_types = bytes, memoryview, str, int, float
    
    def __init__(self,redis_client:redis.Redis, stream_name:str, app_instance_id:str=None, delay:float=1.):
        self.delay=delay
        self._stop_signal=False
        self._redis_client=redis_client
        self.logger=logging.getLogger(DEPLOYMENT_NAME)
        self._app_context_stream=stream_name


        self._proc_thread=threading.Thread(target=self._proc)
        if app_instance_id is None:
            self.app_instance_id=uuid.uuid4().__str__()


        self._app_context:dict={"status":"idle", "app_instance":self.app_instance_id}

    def _update_process_stats(self):
        proc_stats=asdict(get_process_stats())
        self._normalize_nested(proc_stats)
        self._app_context.update(proc_stats)
        self._app_context['time']=time.time()


    def set_app_status(self, status:Literal['idle','work']):
        self._app_context['status']=status


    def update_app_context(self, msg:dict):
        _msg=dict(**msg)
        if 'app_instance' in msg.keys():
            
            warnings.warn(f'The "app_instance" key is reserved and will be removed!')
            del _msg['app_instance']
        for f in fields(ProcessStats):
            if f.name in msg:
                warnings.warn(f'The "{f.name}" key is reserved and will be removed!')
                del _msg[f.name]

        self._normalize_nested(_msg)
        self._app_context.update(_msg)

    def _normalize_nested(self,dct:dict):
        for k in list(dct.keys()):
            if not isinstance(k, self.__allowed_key_types):
                raise TypeError(f"keys with {type(k).__name__} type is not allowed! Use: {self.__allowed_key_types}")
            if not isinstance(dct[k], self.__allowed_val_types):
                v = dct[k]
                dct[k] = ujson.dumps(
                    v, ensure_ascii=False
                )


    def _stop(self):
        self._stop_signal=True

    def _proc(self):
        while True:

            self._update_process_stats()
            print(self._app_context)
            self.logger.info(json.dumps(self._app_context))
            if self._stop_signal:


                self._redis_client.xadd(self._app_context_stream, self._app_context)
                self._app_context['status']='stopping'
                self.logger.info(json.dumps(self._app_context))
                break


            self._redis_client.xadd(self._app_context_stream, self._app_context)

            time.sleep(self.delay)
        
        self.logger.info(json.dumps(self._app_context))
        

    def __enter__(self):
        self._proc_thread.start()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self._app_context['status']='error'
            self._app_context['error']:ujson.dumps(exception_data(exc_val))
            self._stop()
            self._proc_thread.join(self.delay)
            self.logger.info(json.dumps(self._app_context))
            raise exc_val
        if self._proc_thread.is_alive():
            self._app_context['status'] = 'complete'
            self._stop()
          
            self._proc_thread.join(self.delay)
            self.logger.info(json.dumps(self._app_context))



import json
import os, psutil
import threading
import time
import traceback
from typing import TypedDict, Optional, Literal
from dataclasses import dataclass, asdict


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
    stats=ConsumerProcessStats(proc.pid,proc.cpu_times()._asdict(), proc.cpu_percent(), proc.memory_full_info()._asdict(),     proc.memory_percent())
    return stats

class ExceptionData(TypedDict):
        type: str
        args: list[Optional[str]]
        traceback: str
        attempts: int

def exception_data(exc:Exception) -> ExceptionData:

    full_error = traceback.format_exc()
    print("Captured traceback:\n", full_error)

    return {'type': exc.__class__.__name__, 'args': [str(arg) for arg in exc.args], 'traceback': full_error}
from contextlib import AbstractContextManager
import redis
class MetricsManagerAppInstanceContextException(BaseException):
    ...
def _process_str(val):
    if isinstance(val,bytes):
        return val.decode('utf-8')
    else:
        return str(val)

_tp_map={b'int':int,b'float':float,b'str':_process_str,b'bytes':lambda x:x,b'json':lambda x:json.loads(x.decode('utf-8') if isinstance(x,bytes) else x) if x is not None else None }


def _get_app_instance_stats_key_types(app_instance_stats_key,redis_conn:redis.Redis):
    return redis_conn.hgetall(app_instance_stats_key)
def _get_app_instance_stats_key(app_instance_name:str, redis_conn:redis.Redis):
        return app_instance_name+'-key-type'


def get_app_instance_stats_dict(app_instance_name:str,redis_conn:redis.Redis):

    types =     _get_app_instance_stats_key_types(app_instance_name,redis_conn)
    stats = {}
    for k, v in redis_conn.hgetall(app_instance_name).items():
        k = _tp_map[b'str'](k)
        cast_func = _tp_map.get(types.get(k), lambda x: x)

        stats[k] = cast_func(v)
    return stats

def set_app_instance_stats(app_instance_stats_key, key, value,redis_conn:redis.Redis):
        if isinstance(value, (int, str, bytes, float)):
            redis_conn.hset(_get_app_instance_stats_key(app_instance_stats_key, redis_conn) + '-types', key,
                            type(value).__name__)

            redis_conn.hset(app_instance_stats_key, key, value)

        else:
            redis_conn.hset(_get_app_instance_stats_key(app_instance_stats_key, redis_conn), key, "json")
            redis_conn.hset(app_instance_stats_key, key, json.dumps(value))



def get_app_instance_stats(app_instance_stats_key, key,redis_conn:redis.Redis):
        tp=redis_conn.hget(_get_app_instance_stats_key(app_instance_stats_key, redis_conn), key)
        val = redis_conn.hget(app_instance_stats_key, key)
        cast_func = _tp_map.get(tp, lambda x: x)
        return cast_func(val)


import rich
class MetricsManager(AbstractContextManager):


    __app_instance_key_types__={
        'last_stats':b'json',
        'last_task':b'str',
        "last_update": b'float',
        "status":b'str',
        "exception":b'json'
    }
    __status_color__={
        'idle':'blue',
               'error':'red',
                       'work':'cyan',
        'stop':'gray'
    }







    _status:Literal['idle','work','error','stop']
    def __init__(self, redis_conn:redis.Redis, app_name:str, delay:float = 1.0,verbose:bool=None):
        self.delay=delay
        self._stop_signal=False
        self.last_stats=None
        self.last_task = None
        self._status='idle'
        self.redis_conn=redis_conn
        self.verbose=verbose if verbose is not None else bool(int(os.getenv('METRIC_MANAGER_VERBOSE', '0')))
        self.app_name=app_name
        self._redis_app_metrics_key=f'{self.app_name}-metrics'
        self._redis_app_running_set_key=f'{self.app_name}-running'
        self._num = None
        self._current_task = None
        self._redis_app_instance_stats_key=None
        self._th=threading.Thread(target=self._thread)

    def _get_redis_app_instance_stats_key(self):
        return _get_app_instance_stats_key(self._redis_app_instance_stats_key,self.redis_conn)

    @property
    def success_tasks_count(self):
        return self.redis_conn.zscore(self._redis_app_running_set_key, self._redis_app_instance_stats_key)
    def _init_app_running_set(self):
        self._check()

        self.redis_conn.zadd(self._redis_app_running_set_key, {self._redis_app_instance_stats_key: 0})

    def _add_success_task(self):

        self.redis_conn.zincrby(self._redis_app_running_set_key, 1, self._redis_app_instance_stats_key)

    def _set_num(self,num):
        self._num=num
        self._redis_app_instance_stats_key = f'{self.app_name}-{self._num}'

    def _remove_from_app_running_set(self):
        self.redis_conn.zrem(self._redis_app_running_set_key, self._redis_app_instance_stats_key)

    def _init_app_instance_metrics(self):

        if not self.redis_conn.hexists(self._redis_app_metrics_key, 'num'):

           self._set_num(0)

        else:

            self._set_num(int(self.redis_conn.hget(self._redis_app_metrics_key, "num")) + 1)


        self.redis_conn.hset(self._redis_app_metrics_key, mapping={"num": self._num,"running":self._redis_app_running_set_key})


        self.redis_conn.hset(self._get_redis_app_instance_stats_key(), mapping=self.__class__.__app_instance_key_types__)


    def _join(self, timeout=None):
        self._th.join(timeout)
    def update_process_stats(self):

        self.last_stats=  process_stats()

    def end_task(self, success:bool=True):
        if success:
            self._add_success_task()

        self._status = 'idle'




    def set_status(self,status:Literal['idle','work','error','stop']):


        self._status=status




    def set_stop(self):
        self._status='stop'

        self._stop_signal=True

    def set_error(self, exc):
        self._status = 'error'
        self.set_stats("exception", exception_data(exc))
        self._stop_signal = True

    @property
    def app_instance_stats_dict(self):

        return get_app_instance_stats_dict(self._redis_app_instance_stats_key,self.redis_conn)




    def __enter__(self):

        self._init_app_instance_metrics()
        self._init_app_running_set()
        self._th.start()
        return self




    def _check(self):
        if self._redis_app_running_set_key is None or        self._redis_app_metrics_key is None :
            raise MetricsManagerAppInstanceContextException(
                f"MetricsManager app data is missing: app_metrics_key: {self._redis_app_metrics_key },app_running_set_key: {self._redis_app_running_set_key }")

        if self._num is None or self._redis_app_instance_stats_key is None:
            raise MetricsManagerAppInstanceContextException(f"MetricsManager app instance data is missing: num: {self._num}, app_metrics_key: {self._redis_app_metrics_key} ")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_from_app_running_set()
        if exc_val is not None:
            self.set_error(exc_val)



        else:
            self.set_stop()
        self._join(self.delay*2
                   )








    def _update_app_instance_info(self
                            ):
        self._check()
        self.update_process_stats()
        self.redis_conn.hset(self._redis_app_instance_stats_key,

               mapping={'status': self._status,
                        'stats': json.dumps(asdict(self.last_stats)),
                        'last_update': time.time()

                       }
                             )

        self.set_stats('last_task', str(self.last_task))



    def start_task(self,task_id:str):
        self._current_task=task_id
        self._status='work'






    def set_stats(self, key, value):
        set_app_instance_stats(self._redis_app_instance_stats_key,key,value,redis_conn=self.redis_conn)

    def get_stats(self, key):
       return get_app_instance_stats(self._redis_app_instance_stats_key,key,redis_conn=self.redis_conn)

    @property
    def app_instance_name(self):
        return self._redis_app_instance_stats_key


    def _thread(self):


            while True:

                try:
                    if self.verbose:
                        tag = self.__status_color__[self._status]
                        rich.print(f'app status: [bold][[{tag}]{self._status}[/{tag}]][/bold]            ', end='\r',
                                   flush=True)

                    if self._stop_signal:

                        break

                    self._update_app_instance_info()

                    time.sleep(self.delay)

                except KeyboardInterrupt as err:
                    raise err
                except Exception as err:

                    raise err













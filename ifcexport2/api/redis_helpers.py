from ifcexport2.api.settings import redis_client
import pickle

class Hset:
    def __init__(self, name, client=redis_client):
        self.name=name
        self.client=client
    def set(self, k,v):
        return self.client.hset(self.name,k,pickle.dumps(v,protocol=pickle.HIGHEST_PROTOCOL))
    def _get(self, k):

        return pickle.loads(self.client.hget(self.name, k) )
    def get(self,key,default=None):
        if self.has(key):
            return self._get(key)
        return default
    def has(self,k):
        return bool(self.client.hexists(self.name,k))
    def delete(self,*keys):
        return self.client.hdel(self.name,*keys)

    def keys(self):
        return self.client.hkeys(self.name)
    def __getitem__(self, item):
        return self._get(item)

    def __setitem__(self, key, value):
        return self.set(key,value)

    def __delitem__(self, key):
        return self.delete(key)

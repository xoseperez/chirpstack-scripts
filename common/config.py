import os

import yaml
import flatdict

class Config():

    _data = flatdict.FlatDict({})
    _args = None

    def __init__(self, file=None, args={}):
        
        try:
            with open(file or "config.yml", "r") as f:
                _data =  yaml.load(f, Loader=yaml.loader.SafeLoader)
        except FileNotFoundError:
            _data = {'logging': {'level' : logging.INFO}}
        
        self._data = flatdict.FlatDict(_data, delimiter='.')

        # filter out "None" values
        for key in self._data:
            if self._data[key] == None:
                del self._data[key]

        self._args = args

    def get(self, key, default=None):
        
        # External name
        env_name = key.upper().replace('.', '_').replace('-', '_')

        # Arguments have precedence over `config.yml` but do not get persisted
        value = self._args.get(env_name, None)
        
        # Environment variables have precedence over `config.yml` but do not get persisted
        if value is None:
            value = os.environ.get(env_name, None)
        
        # Get the value from `config.yml` or the default
        if value is None:
            value = self._data.get(key)

        if value is None:
            value = default

        return value

    def set(self, key, value):
        if self._data.get(key) != value:
            self._data[key] = value


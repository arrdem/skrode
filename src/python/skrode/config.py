"""
The BBDB config
"""

from __future__ import absolute_import

import json
import types

from skrode.redis.workqueue import WorkQueue
from skrode.sql import make_uri as make_sql_uri, make_engine_session_factory

import yaml
import redis
from twitter import Api


def make_proxy_ctor(ctor, **more):
  def _from_yaml(loader, node):
    return ctor(**loader.construct_mapping(node), **more)

  return _from_yaml


def _make_sql_session(**kwargs):
  engine, sessionmaker = make_engine_session_factory(uri=make_sql_uri(**kwargs))
  return sessionmaker()


yaml.SafeLoader.add_constructor('!skrode/redis', make_proxy_ctor(redis.StrictRedis))
yaml.SafeLoader.add_constructor('!skrode/queue', make_proxy_ctor(WorkQueue,
                                                               encoder=json.dumps,
                                                               decoder=json.loads))
yaml.SafeLoader.add_constructor('!skrode/twitter', make_proxy_ctor(Api))
yaml.SafeLoader.add_constructor('!skrode/sql', make_proxy_ctor(_make_sql_session))


DEFAULTS = {
  "twitter": {
    "timeout": 30,
  },
  "sql": {
    "dialect": "postgresql+psycopg2",
    "username": "postgres",
    "password": "",
    "hostname": "localhost",
    "port": "5432",
    "database": "skrode",
    "uri": make_sql_uri,
  }
}

class BBDBConfig(object):
  """An object structure which proxies pretty thinly over a loaded dictionary of data, and a
  dictionary of either default values or default-calculating functions.

  """

  def __init__(self, config=None, data=None, defaults=DEFAULTS):
    if data is None:
      self._filename = config or "config.yml"
      with open(self._filename) as f:
        self._config = yaml.safe_load(f)
    else:
      self._config = data

    self._defaults = defaults

  def get(self, key, default=None):
     if key in self._config:
       val = self._config[key]
       if isinstance(val, dict):
         return BBDBConfig(None, val, self._defaults.get(key))
       elif isinstance(val, types.FunctionType):
         return val(self)
       else:
         return val
     else:
       return default

  def dict(self):
    return self._config

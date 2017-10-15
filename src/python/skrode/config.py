"""
The BBDB config
"""

from __future__ import absolute_import

import json
import types

from skrode.redis.workqueue import WorkQueue
from skrode.sql import make_engine_session_factory
from skrode.sql import make_uri as make_sql_uri

from imapclient import IMAPClient
from lazy_object_proxy import Proxy
import redis
from twitter import Api
import yaml


def make_proxy_ctor(ctor, **more):
  """
  Wraps a constructor with keyword arguments and the machinery to load more from a YAML mapping.

  Returns a function which will actually generate instances via the wrapped constructor.

  Uses lazy_object_proxy.Proxy to delay construction as long as possible.

  """
  def _from_yaml(loader, node):
    d = loader.construct_mapping(node)
    d.update(more)

    return Proxy(lambda: ctor(**d))

  return _from_yaml


def _make_sql_session(**kwargs):
  engine, sessionmaker = make_engine_session_factory(uri=make_sql_uri(**kwargs))
  return sessionmaker()


def _make_imap_server(hostname=None,
                      port=None,
                      username=None,
                      password=None,
                      **kwargs):
  server = IMAPClient(hostname, port,
                      **kwargs)
  if username and password:
    server.login(username, password)
  return server


def _decode_and_load(text):
  if isinstance(text, bytes):
    text = text.decode("utf-8")
  return json.loads(text)


yaml.SafeLoader.add_constructor('!skrode/redis', make_proxy_ctor(redis.StrictRedis))
yaml.SafeLoader.add_constructor('!skrode/queue', make_proxy_ctor(WorkQueue,
                                                                 encoder=json.dumps,
                                                                 decoder=_decode_and_load))
yaml.SafeLoader.add_constructor('!skrode/twitter', make_proxy_ctor(Api))
yaml.SafeLoader.add_constructor('!skrode/sql', make_proxy_ctor(_make_sql_session))
yaml.SafeLoader.add_constructor('!skrode/imap', make_proxy_ctor(_make_imap_server))


class Config(object):
  """An object structure which proxies pretty thinly over a loaded dictionary of data, and a
  dictionary of either default values or default-calculating functions.

  """

  def __init__(self, config=None, data=None, defaults=None):
    if data is None:
      self._filename = config or "config.yml"
      with open(self._filename) as f:
        self._config = yaml.safe_load(f)
    else:
      self._config = data

    self._defaults = defaults or {}

  def get(self, key, default=None):
     if key in self._config:
       val = self._config[key]
       if isinstance(val, dict):
         return Config(None, val, self._defaults.get(key))
       elif isinstance(val, types.FunctionType):
         return val(self)
       else:
         return val
     else:
       return default

  def __getattribute__(self, name):
    if name not in ["_filename", "_config", "_defaults", "get", "dict", "__repr__"]:
      return self.get(name)
    else:
      return super(Config, self).__getattribute__(name)

  def __repr__(self):
    return "<Config %r, %r>" % (self._config, self._defaults)

  def dict(self):
    return self._config

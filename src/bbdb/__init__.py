"""
The heart of bbdb. Session & DB state stuff.
"""

from detritus import once
from bbdb import schema
from bbdb.config import BBDBConfig

from redis import StrictRedis

def rds_for_config(config=None):
  """A redis config constructor."""
  if config is None:
    config = BBDBConfig()

  return StrictRedis(host=config.redis.hostname,
                     port=config.redis.port,
                     db=int(config.redis.db))

@once
def rds():
  """A constructor for the \"default\" Redis connection."""

  return rds_for_config(BBDBConfig("config.yml"))

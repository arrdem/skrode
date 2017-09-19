"""
The heart of bbdb. Session & DB state stuff.
"""

from detritus import once
from bbdb.config import BBDBConfig


@once
def cfg():
  """A constructor for the \"default\" BBDB config."""

  return BBDBConfig("config.yml")


@once
def rds():
  """A constructor for the \"default\" Redis connection."""

  return cfg().get("redis")

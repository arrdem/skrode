"""
The heart of skrode. Session & DB state stuff.
"""

from detritus import once
from skrode.config import Config


@once
def cfg():
  """A constructor for the \"default\" Skrode config."""

  return Config("config.yml")


@once
def rds():
  """A constructor for the \"default\" Redis connection."""

  return cfg().get("redis")

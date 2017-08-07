"""
The BBDB config
"""

import yaml


class BBDBConfig(object):
  """
  A session-like object, derived from loading a configuration file.
  """

  def __init__(self, config="config.yml"):
    self._filename = config
    with open(config) as f:
      self._config = yaml.safe_load(f)

  @property
  def _twitter(self):
    return self._config["twitter"]

  @property
  def twitter_api_key(self):
    return self._twitter["api_key"]

  @property
  def twitter_api_secret(self):
    return self._twitter["api_secret"]

  @property
  def twitter_access_token(self):
    return self._twitter["access_token"]

  @property
  def twitter_access_secret(self):
    return self._twitter["access_secret"]

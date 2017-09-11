"""
The BBDB config
"""

from hashlib import md5

import yaml


class BBDBConfig(object):
  """
  A session-like object, derived from loading a configuration file.
  """

  def __init__(self, config=None):
    self._filename = config or "config.yml"
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

  @property
  def twitter_cache_dir(self):
    return self._twitter.get("cache_dir", ".twitter-cache")

  @property
  def twitter_cache_timeout(self):
    return int(self._twitter.get("cache_ttl", 24 * 60 * 60))

  @property
  def _sql(self):
    return self._config["sql"]

  @property
  def sql_dialect(self):
    return self._sql["dialect"]

  @property
  def sql_username(self):
    return self._sql["username"]

  @property
  def sql_password(self):
    return self._sql["password"]

  @property
  def sql_port(self):
    return self._sql["port"]

  @property
  def sql_database(self):
    return self._sql["database"]

  @property
  def sql_hostname(self):
    return self._sql["hostname"]

  @property
  def sql_uri(self):
    return "{dialect}://{username}:{password}@{hostname}:{port}/{database}"\
        .format(dialect=self.sql_dialect,
                username=self.sql_username,
                password=self.sql_password,
                hostname=self.sql_hostname,
                port=self.sql_port,
                database=self.sql_database)

  @property
  def _rds(self):
    return self._config["redis"]

  @property
  def rds_hostname(self):
    return self._rds.get("hostname", "localhost")

  @property
  def rds_port(self):
    return self._rds.get("port", 6379)

  @property
  def rds_db(self):
    return self._rds.get("db", 0)

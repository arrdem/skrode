"""
A wrapper around imaplib.* for convenience.

Primarily written because imapclient is crap (under-documented/under-exampled) and I'm still
learning the mechanics of the protocol so no better time to write an excessively thin wrapper.
"""

import logging as log
import re

from arrow import utcnow


LIST_RESPONSE_PATTERN = re.compile(
  r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)'
)

QUOTED_PATTERN = re.compile(
  r'^"[^"]*"$'
)

FOLDER_STATUS_RESPONSE_PATTERN = re.compile(
  r'(?P<name>(([^"]\S*)|"[^"]*")) \((?P<kvs>[^\)]*)\)'
)

FOLDER_STATUS_K_V_PATTERN = re.compile(
  r'(?P<condition>\w+) (?P<value>\d+)'
)


def _ensure_quoted(text):
  if not re.match(QUOTED_PATTERN, text):
    return '"%s"' % text
  else:
    return text


class IMAPException(Exception):
  pass


class IMAPFolder(object):
  def __init__(self, client, name, flags, delimeter, status=None):
    self.name = name
    self.flags = flags
    self.delimeter = delimeter
    self._client = client
    self._recursion = 0
    self._status = None

  def __repr__(self):
    return "<IMAPFolder {0.name!r} status={0._status}>".format(self)

  def __enter__(self):
    self._client.select(self.name)
    self._recursion += 1

  def __exit__(self, *args, **kwargs):
    if self._recursion == 1:
      self._client.close()
    else:
      self._recursion -= 1

  def search(self, *args, **kwargs):
    with self:
      return self._client.search(*args, **kwargs)

  def status(self):
    return self._client.status(self.name)


class IMAPFolderStatus(object):
  def __init__(self, client, folder,
               messages=None,
               recent=None,
               uidnext=None,
               uidvalidity=None,
               unseen=None):
    self._client = client
    self.folder = folder
    self.messages = messages
    self.recent = recent
    self.uidnext = uidnext
    self.uidvalidity = uidvalidity
    self.unseen = unseen

  def __repr__(self):
    return "<IMAPFolderStatus messages={0.messages}, recent={0.recent}, uidnext={0.uidnext}, uidvalidity={0.uidvalidity}, unseen={0.unseen}>".format(self)  # noqa


class IMAPWrapper(object):
  """
  A wrapper around an imaplib.IMAP4* instance which provides some nicer error behavior and proxies
  most of its methods. Provides some conveniences around searching and soforth.
  """

  def __init__(self, client):
    self._client = client
    self._folders = {}
    self._folder_ttl = utcnow().replace(years=-1)

  def login(self, *args, **kwargs):
    """
    Try to authenticate as a user to the IMAP server.
    """

    return self._client.login(*args, **kwargs)

  def logout(self, *args, **kwargs):
    """
    Log out of the server.
    """

    return self._client.logout(*args, **kwargs)

  def select(self, *args, **kwargs):
    """
    Open a folder for searching, fetching and other operations.
    """

    err, results = self._client.select(*args, **kwargs)
    if err == "OK":
      return results
    else:
      raise IMAPException(results)

  def close(self, *args, **kwargs):
    """
    Close the open folder.
    """

    err, results = self._client.close(*args, **kwargs)
    if err == "OK":
      return results
    else:
      raise IMAPException(results)

  def status(self, folder_name, fields=None):
    """
    Returns a IMAPFolderStatus record.

    By default, fetches all standard-defined fields.

    Supported fields:
    - 'MESSAGES',
    - 'RECENT',
    - 'UIDNEXT',
    - 'UIDVALIDITY',
    - 'UNSEEN'
    """

    # For side-effects. Refresh the folder cache.
    self.list()

    # And ask the server...
    err, results = self._client.status(_ensure_quoted(folder_name),
                                       (("(%s)" % " ".join(fields)) if fields
                                        else "(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)"))
    if err == "OK":
      result = results[0].decode("utf-8")

      match = re.match(FOLDER_STATUS_RESPONSE_PATTERN, result)
      kvs = match.group("kvs")
      folder = self._folders.get(folder_name)
      status = folder._status or IMAPFolderStatus(self, folder)
      folder._status = status

      # Update whatever attributes we just loaded & return the updated status record.
      for m in re.finditer(FOLDER_STATUS_K_V_PATTERN, kvs):
        k = m.group("condition").lower()
        v = int(m.group("value"))
        setattr(status, k, v)

      return status

    else:
      raise IMAPException(results)

  def search(self, *args, **kwargs):
    """

    """

    err, results = self._client.search(*args, **kwargs)
    if err == "OK":
      for result in results:
        if result == ")":
          break

        for msgid in result.split(" "):
          if msgid:
            yield int(msgid)

    else:
      raise IMAPException(results)

  def fetch(self, *args, **kwargs):
    """
    Fetch messages.
    """

    err, results = self._client.fetch(*args, **kwargs)
    if err == "OK":
      return results
    else:
      raise IMAPException(results)

  def list(self, *args, **kwargs):
    """
    List out the folders in the connected server.
    """

    if utcnow() < self._folder_ttl:
      return self._folders.values()

    else:
      err, results = self._client.list(*args, **kwargs)
      if err == "OK":
        acc = []
        for result in results:
          result = result.decode("utf-8")
          for match in re.finditer(LIST_RESPONSE_PATTERN, result):
            flags, delimeter, name = match.groups()
            folder = self._folders.get(name, IMAPFolder(self, name, flags, delimeter))
            folder.flags = flags
            folder.delimeter = delimeter
            self._folders[name] = folder
            acc.append(folder)
        self._folder_ttl = utcnow().replace(seconds=5)
        return acc

      else:
        raise IMAPException(results)

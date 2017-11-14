"""
An imap driver that actually makes some attempt to provide a structured access model.
"""

from email import message_from_string
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

K_PATTERN = re.compile(r"(?P<msg_id>\d+)?\s\(?(?P<data_item>.*) \{\d+\}")

def _ensure_quoted(text):
  if not re.match(QUOTED_PATTERN, text):
    return '"%s"' % text
  else:
    return text


class IMAPException(Exception):
  pass


class IMAPMessage(object):
  def __init__(self, client, folder):
    self._client = client
    self._folder = folder

  def fetch(self, items):
    pass


class IMAPFolder(object):
  def __init__(self, client, name, flags, delimeter, status=None):
    self._client = client
    self._recursion = 0
    self._status = None

    self.name = name
    self.flags = flags
    self.delimeter = delimeter

  def __repr__(self):
    return "<IMAPFolder {0.name!r} status={0._status}>".format(self)

  def __enter__(self):
    self._client.select(self.name)
    self._recursion += 1

  def __exit__(self, *args, **kwargs):
    self._recursion = max(0, self._recursion - 1)

    if self._recursion == 0:
      self._client.close()

  def search(self, *args, **kwargs):
    with self:
      return self._client.search(*args, **kwargs)

  def status(self):
    return self._client.status(self.name)

  def fetch(self, *args, **kwargs):
    with self:
      return self._client.fetch(*args, **kwargs)


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

  def fetch(self, sequence_set, data_items):
    """Fetch messages.

    https://tools.ietf.org/html/rfc3501#section-6.4.5

    Accepts a "sequence set", being either the ID, ID range(s) or UUID of a message in the current
    mailbox, and a string being either an atom naming a datom to fetch, or a parenthesized list of
    datoms to fetch or a macro representing a list of datoms.

    Returns a map from message IDs (as strings) to maps of datom (as named by the server) to values
    as returned by the server.

    .. code-block:: python

       >>> with inbox:
       ...   server.fetch(18, '(BODY[HEADER.FIELDS (MESSAGE-ID)] BODY[])')
       ...
       {'18': {'BODY[HEADER.FIELDS (MESSAGE-ID)]': 'Message-ID: <....>\r\n\r\n',
               'BODY[]': '....\r\n\r\n'}}
    """

    def fake_defaultdict(m, k):
      if k not in m:
        m[k] = {}
      return m[k]

    def parse_multi_kv_response(result_tuples):
      """Implementation detail.

      RFC350 6.4.5. defines the FETCH command to return a sequence of untagged (* prefixed)
      responses, of the form `* <msgid> FETCH ....`, followed by a tagged terminating response ala
      `OK ...`. Each individual `FETCH` response is itself is an ordered association list of datom
      name to data, for each datom requested from the server in the request's data items.

      The Python API driver can sort of figure out the association list pairs, but doesn't do a good
      job of it. What the user gets back is a sequence of (k, v) tuples and the string ")". The
      first k has as a prefix the ID of the message. The ")" denotes the end of a single email's
      sequence of k/v pairs. For instance...

      .. code-block:: python

         >>> server.fetch(18, '(BODY[HEADER.FIELDS (MESSAGE-ID)] BODY[])')
         [('18 (BODY[HEADER.FIELDS (MESSAGE-ID)] {84}',
           'Message-ID: <....>\r\n\r\n'),
          (' BODY[] {4690}',
           '....\r\n'),
          ')']

      This data structure isn't completely wrong, but it also isn't directly useful at all.

      This function eats the incompletely processed sequence of k/vs and delimiters, returning a map
      of message IDs to response k/vs.
      """

      result = {}
      message_id = None

      for line in result_tuples:
        if line == ")":
          continue
        else:
          k, v = line
          m = re.match(K_PATTERN, k)
          message_id = m.group("msg_id") or message_id
          fake_defaultdict(result, message_id)[m.group("data_item")] = v

      return result

    err, results = self._client.fetch(sequence_set, data_items)
    if err == "OK":
      # At this point results is a rather complicated thing.
      return parse_multi_kv_response(results)
    else:
      raise IMAPException(results)

  def fetch_as_emails(self, sequence_set):
    """
    Fetches a sequence set of emails as email.message.Message objects.

    Returns a map of message ID to Message object.
    """

    err, results = self._client.fetch(sequence_set, "(BODY[])")
    if err != "OK":
      raise IMAPException(results)

    actual_results = {}

    for line in results:
      if line == ")":
        continue

      k, v = line
      m = re.match(K_PATTERN, k)
      actual_results[m.group("msg_id")] = message_from_string(v)

    return actual_results

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

"""
Ingest mail from one or more configured IMAP accounts.
"""

from __future__ import print_function

from traceback import format_exc
import argparse
import logging as log
import sys

from skrode.config import Config
from skrode.imap import IMAPWrapper

import html2text

args = argparse.ArgumentParser()
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")
args.add_argument("-a", "--account",
                  dest="account")


def message_parts_and_types(message):
  """Converts a MIME (potentially multipart) message to a sequence of pairs (type, \ -> str)

  The functions are 0-argument delays returning the decoded text of message parts.
  """

  def normalize(text):
    return text.decode("utf-8").replace(u"\xa0", " ")  # Fuck your non-breaking spaces

  if message.is_multipart():
    for part in message.walk():
      yield part.get_content_type(), lambda: normalize(part.get_payload(decode=True))

  else:
    yield message.get_content_type(), lambda: normalize(message.get_payload(decode=True))


def message_to_text(message):
  """Does its damndest to convert a message to plain text.

  So far I've only really seen two "kinds" of email - text/plain encoded mail, and text/html email
  with a bunch more stuff to it. This function attempts to normalize to text/plain, using html2text
  to flatten the HTML to "plain" text if a text/plain rendering isn't available.

  Returns None of it can't find a "normalization" of the email.
  """

  for type, part in message_parts_and_types(message):
    if type == "text/plain":
      return part()

  h = html2text.HTML2Text()
  h.ignore_links = False
  h.ignore_tables = True

  for type, part in message_parts_and_types(message):
    if type == "text/html":
      return h.handle(part())


def main(opts):
  """

  """

  config = Config(config=opts.config)
  imap_server = None

  try:
    imap_server = IMAPWrapper(config.get(opts.account))

    for folder in imap_server.list():
      with folder:
        message_ids = list(folder.search(None, 'ALL'))

        example = []
        # Find the shortest example message from each folder
        for message_id in message_ids:
          data = imap_server.fetch(message_id, '(BODY[HEADER.FIELDS (MESSAGE-ID)] BODY[])')

          if sys.getsizeof(repr(data)) < sys.getsizeof(repr(example)):
            example = data
          elif not example:
            example = data

        log.info("%s", example)
        sys.exit(0)

  finally:
    if imap_server:
      imap_server.logout()


if __name__ == "__main__":
  _root_logger = log.getLogger()
  _root_logger.setLevel(log.DEBUG)

  main(args.parse_args(sys.argv[1:]))

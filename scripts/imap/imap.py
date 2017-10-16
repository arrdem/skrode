"""
Ingest mail from one or more configured IMAP accounts.
"""

from __future__ import print_function

import StringIO
from traceback import format_exc
import argparse
import logging as log
from email.message import Message
import sys

from skrode.config import Config
from skrode.imap import IMAPWrapper

args = argparse.ArgumentParser()
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")
args.add_argument("-a", "--account",
                  dest="account")


def main(opts):
  """

  """

  config = Config(config=opts.config)
  imap_server = None

  try:
    imap_server = IMAPWrapper(config.get(opts.account))

    for folder in imap_server.list():
      with folder:
        log.info("%r", folder)
        log.info("%r", folder.status())
        message_ids = folder.search(None, 'ALL')
        log.info("%r", list(message_ids))

        _blob = None
        continue

        for message_id in message_ids:
          err, data = imap_server.fetch(message_id, '(RFC822)')
          blob = 'Message %s\n%s\n%s\n' % (message_id, err, data)
          if not _blob or len(_blob) > len(blob):
            _blob = blob

        log.info(_blob)
  finally:
    if imap_server:
      imap_server.logout()


if __name__ == "__main__":
  _root_logger = log.getLogger()
  _root_logger.setLevel(log.DEBUG)

  main(args.parse_args(sys.argv[1:]))

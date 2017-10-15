"""
Ingest mail from one or more configured IMAP accounts.
"""

import argparse
import logging as log
import sys

from skrode.config import Config


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

  imap_server = config.get(opts.account)

  folders = imap_server.list_folders()

  # This gives a sequence of folder descriptor structures.
  # My inbox looks something like....
  #
  # [(('\\HasNoChildren',), '/', u'INBOX'),
  #  (('\\HasNoChildren', '\\Archive'), '/', u'Archive'),
  #  (('\\HasNoChildren', '\\Drafts'), '/', u'Drafts'),
  #  (('\\HasChildren',), '/', u'Forums'),
  #  (('\\HasNoChildren',), '/', u'Forums/Lobsters'),
  #  ...
  #  (('\HasNoChildren', '\\Junk'), '/', u'Junk Mail'),
  #  (('\\HasNoChildren', '\\XNotes'), '/', u'Notes'),
  #  (('\\HasNoChildren', '\\Sent'), '/', u'Sent Items'),
  #  (('\\HasChildren',), '/', u'Services'),
  #  (('\\HasNoChildren',), '/', u'Services/Github'),
  #  ...
  #  (('\\HasNoChildren',), '/', u'Starred'),
  #  (('\\HasNoChildren', '\\Trash'), '/', u'Trash'),
  #  ]

  for _flags, _delimeter, folder_name in folders:
    imap_server.select_folder(folder_name)
    
  
if __name__ == "__main__":
  main(args.parse_args(sys.argv[1:]))

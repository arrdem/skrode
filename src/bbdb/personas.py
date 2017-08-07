"""
Helpers for working with (merging/splitting) personas.
"""

from bbdb import names
from bbdb.schema import Person

def merge_left(session, l, r):
  """
  Merge the right profile into the left profile, destroying the right. 
  """

  for name in r.names:
    names.insert_name(session, l, name.name)
    session.delete(name)

  for twitter_account in r.twitter_account:
    twitter_account.persona = l
    session.add(twitter_account)

  for email_account in r.email_accounts:
    email_account.persona = l
    session.add(email_account)

  for github_account in r.github_accounts:
    github_account.persona = l
    session.add(github_account)

  for keybase_account in r.keybase_accounts:
    keybase_account.persona = l
    session.add(keybase_account)

  for website in r.websites:
    website.persona = l
    session.add(website)

  session.commit()


def link_personas_by_owner(session, *ps):
  """
  Given a list of personas, link then to the same owner.
  """

  person = None
  for p in ps:
    person = person or p.owner
    if person:
      break

  person = person or Person()
  session.add(person)

  for p in ps:
    p.owner = person
    session.add(p)

  session.commit()

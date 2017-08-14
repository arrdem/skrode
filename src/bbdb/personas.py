"""
Helpers for working with (merging/splitting) personas.
"""

from bbdb import schema
from bbdb.schema import get_or_create
from bbdb.twitter import insert_user

from sqlalchemy import func
from sqlalchemy import or_

from phonenumbers import format_number as format_phonenumber, parse as parse_phonenumber, PhoneNumberFormat


def insert_name(session, persona, name):
  return get_or_create(session, schema.Name, name=name, persona=persona)


def insert_phone_number(session, persona, number):
  _number = format_phonenumber(parse_phonenumber(number), PhoneNumberFormat.RFC3966)
  _number = schema.PhoneNumber(handle=_number, persona=persona)
  session.add(_number)
  session.commit()
  return _number


def personas_by_name(session, name, one=False):
  q = session.query(schema.Persona)\
                .join(schema.Persona.names)\
                .filter(schema.Name.name.contains(name))\
                .order_by(func.length(schema.Name.name))\
                .distinct()
  if one:
    return q.first()
  else:
    return q.all()


def merge_left(session, l, r):
  """
  Merge the right profile into the left profile, destroying the right. 
  """

  if l.id == r.id:
    # We're merging a record onto itself
    return

  for name in r.names:
    insert_name(session, l, name.name)
    session.delete(name)

  for twitter_account in r.twitter_accounts:
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

  for reddit_account in r.reddit_accounts:
    reddit_account.persona = l
    session.add(reddit_account)

  for lobsters_account in r.lobsters_accounts:
    lobsters_account.persona = l
    session.add(lobsters_account)

  for hn_account in r.hn_accounts:
    hn_account.persona = l
    session.add(l)

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

  person = person or schema.Person()
  session.add(person)

  for p in ps:
    p.owner = person
    session.add(p)

  session.commit()


def create_persona(session, twitter_api,
                   names=None, links=None, emails=None, phones=None, twitter_handles=None):
  persona = schema.Persona()
  session.add(persona)
  if names:
    for name in names:
      get_or_create(session, schema.Name, name=name, persona=persona)

  if links:
    for link in links:
      get_or_create(session, schema.Website, handle=link, persona=persona)

  if emails:
    for email in emails:
      get_or_create(session, schema.EmailHandle, handle=email, persona=persona)

  if phones:
    for phone in phones:
      insert_phone_number(session, persona, phone)

  if twitter_handles and twitter_api:
    for handle in twitter_handles:
      user = twitter_api.GetUser(screen_name=handle)
      handle = session.query(schema.TwitterHandle).filter_by(id=user.id).first()
      if handle:
        merge_left(session, persona, handle.persona)
      else:
        insert_user(session, user, persona)

  session.commit()

  return persona

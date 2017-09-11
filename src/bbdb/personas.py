"""
Helpers for working with (merging/splitting) personas.
"""

from bbdb import schema
from bbdb.schema import get_or_create
from bbdb.telephones import insert_phone_number

from sqlalchemy import func


def insert_name(session, persona, name):
  return get_or_create(session, schema.Name, name=name, persona=persona)


def personas_by_name(session, name, one=False, exact=False):
  _cmp = lambda: schema.Name.name.contains(name) if not exact else schema.Name.name == name

  p = session.query(schema.Persona)\
                .join(schema.Account)\
                .filter(schema.Persona.id == schema.Account.persona_id)\
                .join(schema.Name)\
                .filter(schema.Name.account_id == schema.Account.id)\
                .filter(_cmp())\
                .order_by(func.length(schema.Name.name))\
                .distinct()

  q = session.query(schema.Persona)\
                .join(schema.Name)\
                .filter(_cmp())\
                .order_by(func.length(schema.Name.name))\
                .distinct()

  if one:
    return p.first() or q.first()
  else:
    return set(p.all() + q.all())


def merge_left(session, l, r):
  """
  Merge the right profile into the left profile, destroying the right. 
  """

  if l.id == r.id:
    # We're merging a record onto itself
    return

  for account in r.accounts:
    account.persona_id = l.id
    session.add(account)
  session.commit()

  for name in r.linked_names:
    name.persona_id = l.id
    session.add(name)
  session.commit()

  # This is now safe, and if it isn't because there are orphans then it'll explode
  session.delete(r)

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
        from bbdb.twitter import insert_user
        insert_user(session, user, persona)

  session.commit()

  return persona

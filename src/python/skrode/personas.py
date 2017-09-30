"""
Helpers for working with (merging/splitting) personas.
"""

from sqlalchemy import asc, func, inspect, join, or_, select, union

from skrode import schema
from skrode.schema import get_or_create
from skrode.services import mk_insert_user, mk_service
from skrode.telephones import insert_phone_number

null_service = mk_service("namesvc", [])

def _nullsvc_fk(id):
  return "namesvc+user:%s" % id

insert_user = mk_insert_user(null_service, _nullsvc_fk)


def insert_name(session, persona, name):
  """Add a name to the given persona by linking it through a null service."""

  nullsvc = null_service(session)
  nullact = session.query(schema.Account)\
                   .filter_by(service=nullsvc,
                              persona=persona)\
                   .first()
  if not nullact:
    nullact = schema.Account(service=nullsvc,
                             external_id=_nullsvc_fk(persona.id),
                             persona=persona)
    session.add(nullact)
    session.commit()

  return get_or_create(session, schema.Name,
                       name=name,
                       account=nullact)


def personas_by_name(session, name, one=False, exact=False, limit=None):
  _filter = lambda: schema.Name.name.contains(name) if not exact else schema.Name.name == name
  _score = lambda: func.abs(func.length(schema.Name.name) - len(name))

  p = session.query(schema.Persona)\
             .join(schema.Account)\
             .filter(schema.Persona.id == schema.Account.persona_id)\
             .join(schema.Name)\
             .filter(schema.Name.account_id == schema.Account.id)\
             .filter(_filter())\
             .order_by(_score())\
             .distinct()

  if limit:
    p = p.limit(limit)

  if one:
    return p.first()
  else:
    return p.all()


def merge_left(session, l, r):
  """
  Merge the right profile into the left profile, destroying the right. 
  """

  if l.id == r.id:
    # We're merging a record onto itself
    return

  for account in r.accounts:
    if not inspect(account).deleted:
      account.persona_id = l.id
      session.add(account)

  session.commit()

  for name in r.linked_names:
    if not inspect(name).deleted:
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

  person = person or schema.Human()
  session.add(person)

  for p in ps:
    p.owner = person
    session.add(p)

  session.commit()

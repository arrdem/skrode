"""
A module to help interacting with the names model.

Ensures that names on a persona are a set.
"""

from bbdb.schema import Name, Persona, get_or_create

from sqlalchemy import func
from sqlalchemy import or_


def insert_name(session, persona, name):
  return get_or_create(session, Name, name=name, persona=persona)


def personas_by_name(session, name, one=False):
  q = session.query(Persona)\
                .join(Persona.names)\
                .filter(Name.name.contains(name))\
                .order_by(func.length(Name.name))\
                .distinct()
  if one:
    return q.first()
  else:
    return q.all()

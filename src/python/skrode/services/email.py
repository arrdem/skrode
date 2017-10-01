"""
An email service for Skrode.
"""

from skrode.services import mk_service as _mk_service, mk_insert_user as _mk_insert_user


insert_email = _mk_service("Email", [])


def external_id(username):
  """
  Some thoughts:

  - Normalizing email addresses is gonna be insanely hard
  - Normalizing / qualifying addresses by provider is gonna be equally obnoxious
  - Modeling the complexities of email hosting is probably out of scope, so do the dumb thing.
  """

  return u"email+user:{}".format(username.lower())


insert_user = _mk_insert_user(insert_email, external_id)

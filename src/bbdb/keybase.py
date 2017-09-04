"""
A BBDB module for trying to find keybase identities related to a profile
"""

from keybase import Api, NoSuchUserException
from bbdb import schema
from bbdb.services import mk_service, normalize_url
from bbdb.twitter import insert_twitter


_proof_types = set()


insert_keybase = mk_service("Keybase", ["http://keybase.io"])


def insert_kb_user(session, persona, kb_user):
  schema.get_or_create(session, schema.Account,
                       external_id="kekybase:" + kb_user.id,
                       service=insert_keybase(session),
                       persona=persona)

  for proof in kb_user.proofs:
    if proof.proof_type == "generic_web_site":
      continue

    proved_service = schema.get_or_create(session, schema.Service,
                                          name=proof.proof_type)
    schema.get_or_create(session, schema.ServiceURL,
                         service=proved_service,
                         url=normalize_url())

    _proof_types.add(proof.proof_type)


def link_keybases(session, kb=None):
  """
  Traverse tall known Twitter handles, searching for linked Keybase accounts and attempting to
  populate existing Twitter-linked personas with more information from Keybase.
  """

  kb = kb or Api()
  _twitter = insert_twitter(session)

  for screenname in session.query(schema.Name)\
                           .join(schema.Account)\
                           .filter(schema.Account.service == _twitter)\
                           .all():
    account = screenname.account
    persona = account.persona or account.persona

    if persona.keybase_accounts:
      print("Skipping handle %s already linked to %s"
            % (screenname.handle, persona.keybase_accounts))
      continue

    try:
      name = screenname.handle
      print("Trying twitter handle", name)
      kb_user = kb.get_users(twitter=name, one=True)
      print("Got keybase user", kb_user.username, kb_user.id)
      insert_kb_user(session, persona, kb_user)
    except NoSuchUserException:
        pass

  session.commit()

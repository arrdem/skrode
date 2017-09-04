"""
A BBDB module for trying to find keybase identities related to a profile
"""

from keybase import Api, Proof, NoSuchUserException
from bbdb import schema
from bbdb.services import mk_service, normalize_url
from bbdb.twitter import insert_twitter


_proof_types = set()


insert_keybase = mk_service("Keybase", ["http://keybase.io"])


def insert_kb_user(session, persona, kb_user, kb=None):
  if kb is None:
    kb = insert_keybase(session)

  user = schema.get_or_create(session, schema.Account,
                              external_id="keybase:" + kb_user.id,
                              service=kb,
                              persona=persona)
  session.add(user)

  name = schema.get_or_create(session, schema.Name,
                              name=kb_user.username,
                              account=user)
  name.persona_id = persona.id
  session.add(name)

  for proof in kb_user.proofs:
    if proof.proof_type == "generic_web_site":
      continue

    proved_service = schema.get_or_create(session, schema.Service,
                                          name=proof.proof_type)
    service_url = schema.get_or_create(session, schema.ServiceURL,
                                       service=proved_service,
                                       url=normalize_url(proof.service_url))
    proved_account = schema.get_or_create(session, schema.Account,
                                          service=proved_service,
                                          persona=persona,
                                          external_id=("%s:%s" % (proof.proof_type,
                                                                  proof.nametag)))
    schema.get_or_create(session, schema.Name,
                         name=proof.nametag,
                         account=proved_account)

    print("User", user, "proved for service", proved_service)

  return user


def link_keybases(session, kb=None):
  """
  Traverse tall known Twitter handles, searching for linked Keybase accounts and attempting to
  populate existing Twitter-linked personas with more information from Keybase.
  """

  kb = kb or Api()
  _twitter = insert_twitter(session)

  for screenname in session.query(schema.Name)\
                           .join(schema.Account)\
                           .filter(schema.Account.service_id == _twitter.id)\
                           .filter(schema.Name.name.like("@%"))\
                           .all():
    account = screenname.account
    persona = account.persona or account.persona

    keybase_account = session.query(schema.Account)\
                             .filter(schema.Account.service_id == insert_keybase(session).id)\
                             .filter(schema.Account.persona_id == persona.id)\
                             .first()

    if keybase_account:
      print("Skipping handle %s already linked to %s"
            % (screenname.name, keybase_account))
      continue

    try:
      name = screenname.name.replace("@", "")
      print("Trying twitter handle %r" % name)
      kb_user = kb.get_users(twitter=name, one=True)
      print("Got keybase user", kb_user.username, kb_user.id)
      insert_kb_user(session, persona, kb_user)
    except NoSuchUserException:
        pass

  session.commit()

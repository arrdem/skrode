"""
A BBDB module for trying to find keybase identities related to a profile
"""

from keybase import Api, NoSuchUserException
from bbdb import schema


proof_types = set()


def insert_kb_user(session, persona, kb_user):
  schema.get_or_create(session, schema.KeybaseHandle, handle=kb_user.username, persona=persona)

  tags_to_types = {"hackernews": schema.HNHandle,
                   "github": schema.GithubHandle,
                   "reddit": schema.RedditHandle,
                   "generic_web_site": schema.Website}

  for proof in kb_user.proofs:
    ctor = tags_to_types.get(proof.proof_type)
    if ctor:
      schema.get_or_create(session, ctor, handle=proof.nametag, persona=persona)

    proof_types.add(proof.proof_type)


def link_keybases(session, kb=None):
  """
  Traverse tall known Twitter handles, searching for linked Keybase accounts and attempting to
  populate existing Twitter-linked personas with more information from Keybase.
  """

  kb = kb or Api()

  for screenname in session.query(schema.TwitterScreenName).all():
    persona = screenname.persona
    try:
      name = screenname.name
      print("Trying twitter handle", name)
      kb_user = kb.get_users(twitter=name, one=True)
      print("Got keybase user", kb_user.username, kb_user.id)
      insert_kb_user(session, persona, kb_user)
    except NoSuchUserException:
        pass

  session.commit()

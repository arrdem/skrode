"""
A BBDB module for trying to find keybase identities related to a profile
"""

from keybase import Api, NoSuchUserException, Proof
from skrode import schema
from skrode.personas import merge_left
from skrode.services import mk_insert_user, mk_service, normalize_url
from skrode.twitter import insert_twitter
from skrode.twitter import insert_user as twitter_insert_user


insert_keybase = mk_service("Keybase", ["http://keybase.io"])

def keybase_external_id(user_id):
  return "keybase+user:{}".format(user_id)


_insert_user = mk_insert_user(insert_keybase, keybase_external_id)


def insert_user(session, kb_user, persona=None, when=None, twitter_api=None):
  kb_account = _insert_user(session, kb_user.id,
                            persona=persona, when=when)

  name = schema.get_or_create(session, schema.Name,
                              name=kb_user.username,
                              account=kb_account)

  for proof in kb_user.proofs:
    if proof.proof_type == "generic_web_site":
      # FIXME: do something with this.
      continue

    elif proof.proof_type == "twitter":
      # FIXME: Try to find (or create) a Twitter user.
      #
      # It happens to be safe just to search by @-handle since we drive keybase from Twitter for
      # now. But that may not be safe in the future. Really this should push to a Twitter user
      # ingesting queue or something somewhere.
      proved_service = insert_twitter(session)
      twitter_account = session.query(schema.Account)\
                               .filter_by(service=proved_service)\
                               .join(schema.Name)\
                               .filter(schema.Name.name=="@{}".format(proof.nametag))\
                               .first()
      if not twitter_account and twitter_api:
        twitter_insert_user(session, twitter_api.GetUser(screen_name=proof.nametag),
                            persona=kb_account.persona)

      elif twitter_account:
        merge_left(session, kb_account.persona, twitter_account.persona)

      else:
        print("[WARN] Unable to link proved Twitter identity @{}".format(proof.nametag))
        continue

    else:
      # We make a bunch of assumptions about other services...
      proved_service = schema.get_or_create(session, schema.Service,
                                            name=proof.proof_type)

      # Insert the service's URL
      schema.get_or_create(session, schema.ServiceURL,
                           service=proved_service,
                           url=normalize_url(proof.service_url))

      external_id = ("%s:%s" % (proof.proof_type, proof.nametag))

      proved_account = session.query(schema.Account)\
                              .filter_by(service=proved_service,
                                         external_id=external_id)\
                              .first()

      if not proved_account:
        proved_account = schema.Account(service=proved_service,
                                        external_id=external_id,
                                        persona=kb_account.persona)

      elif proved_account.persona_id is not None:
        merge_left(session, kb_account.persona, proved_account.persona)
      else:
        proved_account.persona_id = persona.id

      session.add(proved_account)

      nametag = schema.get_or_create(session, schema.Name,
                                     name=proof.nametag,
                                     account=proved_account)
      nametag.persona = persona
      session.add(nametag)
      session.commit()

    print("User", kb_account, "proved for service", proved_service)

  return kb_account

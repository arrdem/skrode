"""
Helpers for working with services.
"""

from urllib.parse import urlparse

from bbdb import schema

from detritus import once
from arrow import utcnow as now


def normalize_url(url):
  """Normalizes a URL down to the netloc with a HTTP scheme."""

  parse_result = urlparse(url)
  return "http://{0.netloc}".format(parse_result)


def mk_service(name, urls, normalize=True):
  """Returns a partial function for getting/creating a Service record for a name and a domain."""

  @once
  def helper(session):
    service = session.query(schema.Service).filter(schema.Service.name == name.lower()).first()
    if not service:
      service = schema.get_or_create(session, schema.Service,
                                     name=name.lower())

    if service.more and  "pretty_name" not in service.more:
      service.more["pretty_name"] = name

    elif not service.more:
      service.more = {"pretty_name": name}

    for url in urls:
      schema.get_or_create(session, schema.ServiceURL, service=service,
                           url=normalize_url(url) if normalize else url)
    return service

  return helper


def mk_insert_user(service_ctor, external_id_fn):

  def helper(session, external_id, persona=None, when=None):
    when = when or now()
    _svc = service_ctor(session)
    _extid = external_id_fn(external_id)

    account = session.query(schema.Account)\
                     .filter_by(service=_svc,
                                external_id=_extid)\
                     .first()
    if not account:
      account = schema.Account(service=_svc, external_id=_extid)
      session.add(account)

    account.when = when
    if account.persona and persona:
      from bbdb.personas import merge_left
      merge_left(session, persona, account.persona)

    else:
      account.persona = persona = persona or schema.Persona()

    schema.get_or_create(session, schema.Name,
                         name=external_id,
                         account=account,
                         persona=persona)

    session.commit()
    session.refresh(account)
    return account

  return helper

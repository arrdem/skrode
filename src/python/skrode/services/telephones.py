"""
Helpers for working with telephone numbers.
"""

from __future__ import absolute_import

from skrode import schema
from skrode.services import mk_service

from phonenumbers import PhoneNumberFormat
from phonenumbers import format_number as format_phonenumber
from phonenumbers import parse as parse_phonenumber


insert_phone_service = mk_service("telephone", [])


def insert_phone_number(session, persona, number):
  """
  Parses a phone number, inserting a new Account record for the given persona's telephone number.
  """

  parsed_number = format_phonenumber(parse_phonenumber(number), PhoneNumberFormat.RFC3966)
  phone_account = schema.Account(external_id=parsed_number,
                                 persona=persona,
                                 service=insert_phone_service(session))
  session.add(phone_account)
  session.commit()
  return phone_account

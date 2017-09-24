<p align="center">
  <a href="http://www.imgrum.org/media/978947310038702323_34982965"><img src="https://github.com/arrdem/skrode/raw/master/etc/skroderider.jpg" alt="The Skrode and its rider"/></a>
</p>

# Skrode

Because not everything fits in my endocortex.

## What

**TL;DR** A database that records everything I read, everyone I talk to or interact with, and makes
information such as this searchable to the best of my ability.

This project is inspired by the [Emacs BBDB](https://www.emacswiki.org/emacs/BbdbMode), a tool for
building and maintaining a contacts list by automatically analyzing various sources such as email
and IRC.

I never got BBDB to work for me for a number of reasons...

- I simply don't run long-lived Emacs instances (for long-lived meaning n > 12h)
- BBDB doesn't support Twitter
- I don't use Emacs as my mail client

The goal of this project is to develop a multi-worker queue architecture capable of processing many
source streams from services such as Twitter, IRC, Slack and soforth as well as traditional BBDB
sources such as Atom feeds and email, aggregating user profiles, link data and full text for search.

## Architecture

Skrode is a Postgres backed collection of Python tools written using the SQLAlchemy ORM toolkit.

Skrode is primarily concerned with the concepts of Humans, Personas, Services and Accounts. A Human is
a biological entity. Unfortunately, they're rather fluid things about which few assumptions are
actually safe. Humans present Personas to the world - professional or otherwise - which consist of
presences as Accounts on Services.

For instance I have a presence which is the "arrdem" brand. Some people may maintain multiple such
"brands" for various purposes across various services. However none of those presences can really
safely be confused with the person themselves, as the person may self-revise or abandon a persona at
any time.

In keeping with the "big brother" nature of the project, we also warehouse posts made by accounts to
services, recording posts relationships to each-other (reply-to, quotes, etc.) as well as to the
service on which it appears, its distribution (only sent directly to a few Accounts vs anycast etc.)
and other information.

In order to support a multi-process, multi-host worker architecture, Redis is used as a simple
durable-enough job queue primarily for ingesting services such as Twitter which best fit a streaming
rather than batch model.

### SQL Schema

![Database schema](./etc/dbschema.png)

## Configuration

Skrode and its affiliated CLI scripts all rely on a config file (by default `./config.yml`) which
provides configuration values for the various required services.

### Example config

```yaml
---
twitter:
  api_key: ...
  api_secret: ...
  access_token: ...
  access_secret: ...
  timeout: 30

sql:
  dialect: postgresql+psycopg2
  hostname: localhost
  port: 5432
  username: ...
  password: ...
  database: skrode

redis:
  hostname: localhost
  port: 6379
  db: 0
```

## Usage

The `whois.py` script which honestly relates more to the traditional `finger` command, searches the
configured database for personas with names matching the given pattern, and pretty-prints the
results as mostly-YAML.

```
$ ./whois.py "arrdem"
---
persona: f6dde3c9-aed5-4bf0-a2f3-e2411ae143b0
names:
  - @arrdemsays
  - ArrdemSays

accounts:
  - service: <Service 'twitter'>
    foreign key: twitter+user:883521901670178818
    names:
      - @arrdemsays
      - ArrdemSays


---
human: 62cef37c-e9fd-4f18-8f90-6d0500296037
personas:
  - persona: 1ac45ba0-d0f5-484f-8d6b-fa10ac1bd688
    names:
      - arrdem
      - 33e1116b6ef2d7431684ae11c7f91200
      - rdmckenzie
      - @arrdem
      - Reid McKenzie

    accounts:
      - service: <Service 'hackernews'>
        foreign key: hackernews+user:rdmckenzie
        names:
          - rdmckenzie

      - service: <Service 'keybase'>
        foreign key: keybase+user:33e1116b6ef2d7431684ae11c7f91200
        names:
          - 33e1116b6ef2d7431684ae11c7f91200
          - arrdem

      - service: <Service 'lobsters'>
        foreign key: lobsters+user:arrdem
        names:
          - arrdem

      - service: <Service 'github'>
        foreign key: github+user:arrdem
        names:
          - arrdem

      - service: <Service 'twitter'>
        foreign key: twitter+user:389468789
        names:
          - @arrdem
          - Reid McKenzie

      ...
```

The `ingest_twitter.py` script connects to the Twitter streaming API, the configured SQL database
and a Redis instance, establishing a small three-worker process topology for ingesting Twitter
posts, as well as home timeline events such as deletes, follows, favorites replies and soforth.

The `crawl_$SERVICE.py` family of scripts traverse various services, trying to create or populate
Account records. The precise mechanics of the scripts varies, but most are written with respect to
trying to relate Twitter accounts to other services.

## License

Copyright Reid 'arrdem' McKenzie. All rights reserved.

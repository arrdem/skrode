python_library(
  name="config",
  sources=["config.py"],
  dependencies=[
    # direct deps
    ":sql",
    
    # source deps
    "//src/python:detritus",
    "//src/python/skrode/redis",

    # 3rdparty deps
    "//3rdparty/python:arrow",
    "//3rdparty/python:redis",
    "//3rdparty/python:sqlalchemy",
    "//3rdparty/python:psycopg2",
    "//3rdparty/python:PyYAML",
    "//vendored/python/twitter",
  ]
)

python_library(
  name="personas",
  sources=["personas.py"],
  dependencies=[
    ":schema",
  ]
)

python_library(
  name="schema",
  sources=["schema.py"],
  dependencies=[
    # source deps
    "//src/python:detritus",

    # 3rdparty deps
    "//3rdparty/python:sqlalchemy",
    "//3rdparty/python:sqlalchemy-utils",
  ]
)

python_library(
  name="sql",
  sources=["sql.py"],
  dependencies=[
    # direct deps
    ":schema",

    # 3rdparty dependencies
    "//3rdparty/python:sqlalchemy",
  ]
)

python_library(
  name="skrode",
  sources=["__init__.py"],
  dependencies=[
    ":config",
    ":personas",
    ":schema",
  ]
)

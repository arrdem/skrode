python_library(
  name="twitter",
  sources=["twitter.py"],
  dependencies=[
    "//src/python/skrode:schema",
    "//src/python/skrode/services:twitter",

    "//3rdparty/python:arrow",
    "//vendored/python/twitter",
    "//3rdparty/python:sqlalchemy",
    "//3rdparty/python:requests",
  ]
)

####################################################################################################
python_library(
  name="ingesters",
  dependencies=[
    ":twitter",
  ]
)

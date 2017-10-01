python_library(
  name="lib",
  sources=["__init__.py"],
  dependencies=[
    "//src/python/skrode:schema",
  ]
)

python_library(
  name="facebook",
  sources=["facebook.py"],
  dependencies=[
    ":lib",
  ]
)

python_library(
  name="github",
  sources=["github.py"],
  dependencies=[
    ":lib",
  ]
)

python_library(
  name="hackernews",
  sources=["hackernews.py"],
  dependencies=[
    ":lib",

    "//src/python/skrode:schema",
  ]
)

python_library(
  name="keybase",
  sources=["keybase.py"],
  dependencies=[
    ":lib",

    "//src/python/skrode:schema",
  ]
)

python_library(
  name="lobsters",
  sources=["lobsters.py"],
  dependencies=[
    ":lib",

    "//src/python/skrode:schema",
  ]
)

python_library(
  name="reddit",
  sources=["reddit.py"],
  dependencies=[
    ":lib",

    "//src/python/skrode:schema",
  ]
)

python_library(
  name="telephones",
  sources=["telephones.py"],
  dependencies=[
    ":lib",

    "//src/python/skrode:schema",
  ]
)

python_library(
  name="twitter",
  sources=["twitter.py"],
  dependencies=[
    ":lib",

    "//src/python/skrode:schema",
  ]
)

####################################################################################################
python_library(
  name="services",
  dependencies=[
    ":facebook",
    ":github",
    ":hackernews",
    ":keybase",
    ":lobsters",
    ":reddit",
    ":telephones",
    ":twitter",
  ]
)

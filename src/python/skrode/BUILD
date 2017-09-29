python_library(
  name="config",
  sources=["config.py"],
  dependencies=[
    "//src/python:detritus",
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

  ]
)

python_library(
  name="skrode",
  sources=["__init__.py"]
  dependencies=[
    ":config",
    ":personas",
    ":schema",
  ]
)

python_library(
  name='skrode',
  dependencies=[
    ':schema',
    'src/python/skrode/services',
  ]
)

python_library(
  name='schema',
  sources=['schema.py'],
  dependencies=[
    'src/python/detritus',

    '3rdparty/python:sqlalchemy',
    '3rdparty/python:sqlalchemy-utils',
  ]
)

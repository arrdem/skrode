#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='bbdb',
    version='0.0.0',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    dependencies=[
      'six==1.10.0',
      'sqlalchemy==1.1.12',
      'requests==2.18.2',
      'beautifulsoup4==4.6.0',
      'phonenumbers==8.7.1',
      'python-twitter==1.7.1',
      'arrow=0.10.0',
    ]
)

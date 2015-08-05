"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path, walk
import sys
import shutil

here = path.abspath(path.dirname(__file__))

shutil.move("%s/bin/vcycle" % here, "/etc/init.d/vcycle")

# Add contextualization dir files
install_path = '/etc/vcycle/'
datafiles = [(path.join(install_path, root), [path.join(root, f) for f in files])
    for root, dirs, files in walk("contextualization")]

if not hasattr(sys, 'version_info') or sys.version_info < (2, 7):
    raise SystemExit("Vcycle requires Python version 2.7 or above.")

# Get the long description from the relevant file
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='Vcycle',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.6.0',

    description='Vcycle',
    #long_description=long_description,

    # The project's main homepage.
    #url='https://github.com/pypa/sampleproject',

    # Author details
    author='Luis Villazon Esteban',
    author_email='luis.villazon.esteban@cern.ch',

    # Choose your license
    license='GPL',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development',

        # Pick your license as you wish (should match "license" above)
        'License :: GPL License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
    ],

    # What does your project relate to?
    keywords='development',

    scripts=['vcycle/main.py'],

    packages=['vcycle', 'vcycle.conditions', 'vcycle.connectors', 'vcycle.db'],

    install_requires=[
        'requests',
        'pyMongo',
        'jinja2',
        'pyYAML',
        'moment',
        'python-novaclient',
        'azure'
    ],


)

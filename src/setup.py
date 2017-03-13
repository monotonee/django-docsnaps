"""
Note that include_package_data enables MANIFEST.in consumption.

See:
    https://setuptools.readthedocs.io/en/latest/setuptools.html#including-data-files

Using semantic verisioning.

See:
    https://www.python.org/dev/peps/pep-0440/#public-version-identifiers
    http://semver.org/

"""

import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

setup(
    name='django-docsnaps',
    version='0.0.1',

    author='monotonee',
    author_email='monotonee@tuta.io',
    include_package_data=True,
    install_requires=[
        'aiodns',
        'aiohttp',
        'django',
        'django-forcedfields',
        'mysqlclient'
    ],
    license='MIT',
    packages=find_packages(exclude=('tests',)),
    url='https://github.com/monotonee/django-docsnaps',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
    description=(
        'Monitors remote documents and saves snapshots when changes are '
        'detected.'),
    keywords='change django document snapshots',
    long_description=README
)

"""
Note that include_package_data enables MANIFEST.in consumption.

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
        'django',
    ],
    license='MIT',
    packages=find_packages(),
    # url='<url here>',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
    description='Monitors documents and saves snapshots on change.',
    keywords='change django document snapshots',
    long_description=README
)
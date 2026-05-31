#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:authors: python273, aaxnet
:license: Apache License, Version 2.0, see LICENSE file
:copyright: (c) 2019 python273, 2024 aaxnet
"""

from io import open
from setuptools import setup, find_packages

version = '12.0.0'

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='vk_api',
    version=version,

    author='python273',
    author_email='vk_api@python273.pw',

    description=(
        'Python модуль для создания скриптов для социальной сети '
        'Вконтакте (vk.com API wrapper)'
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',

    url='https://github.com/aaxnet/vk_api',
    download_url='https://github.com/aaxnet/vk_api/archive/v{}.zip'.format(
        version
    ),

    license='Apache License, Version 2.0, see LICENSE file',

    packages=find_packages(exclude=['tests*', 'examples*', 'docs*']),
    python_requires='>=3.8',

    install_requires=[
        'requests>=2.28.0',
    ],
    extras_require={
        'vkstreaming': ['websocket-client>=1.0.0'],
        'vkaudio': ['beautifulsoup4>=4.11.0'],
        'dev': [
            'pytest>=7.0',
            'pytest-cov',
            'flake8',
            'mypy',
            'black',
        ],
    },

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    keywords='vk vkontakte api wrapper social network bot',

    project_urls={
        'Bug Reports': 'https://github.com/aaxnet/vk_api/issues',
        'Source': 'https://github.com/aaxnet/vk_api',
        'Documentation': 'https://vk-api.readthedocs.io/',
    },
)

#!/usr/bin/env python

import codecs
from setuptools import setup, find_packages

setup(
    name="wxagent",
    version="0.1",
    license='http://www.apache.org/licenses/LICENSE-2.0',
    description="A weixin agent daemon and client",
    author='kitech',
    author_email='yatseni@gmail.com',
    url='http://contrix.tk/',
    packages=find_packages(),
    package_data={
        'wxagent': ['readme.md']
    },
    install_requires=[],
    entry_points="""
    [console_scripts]
    wxagent = wxagent.wxagent:main
    wxaui = wxagent.lwwx:main
    """,
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    # long_description=long_description,
)


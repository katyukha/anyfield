#!/usr/bin/env python
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

_doc = open('README.rst', 'rt').read()

setup(
    name='anyfield',
    version='0.1.2',
    description='Simplifies structured data processing',
    author='Dmytro Katyukha',
    author_email='firemage.dima@gmail.com',
    url='https://github.com/katyukha/anyfield',
    long_description=_doc,
    #packages=[],
    #scripts=[],
    install_requires=[
        'six>=1.10',
    ],
    license="GPL",
    py_modules=['anyfield'],
    classifiers=[
        # 'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
        'Development Status :: 3 - Alpha',
        # 'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords=[],
)

# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = (
    'statsd',
    )
extra_requires = {
    'standalone': ('waitress', 'PasteDeploy',),
    }
description = "An interface for logging client-side metrics and messages."


setup(
    name='cnx-logging',
    version='0.0',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-logging",
    license='AGPL, See also LICENSE.txt',
    description=description,
    packages=['cnxlogging'],
    include_package_data=False,
    install_requires=install_requires,
    extra_requires=extra_requires,
    entry_points="""\
    [paste.app_factory]
    main = cnxlogging:paste_app_factory
    """,
    test_suite='tests'
    )

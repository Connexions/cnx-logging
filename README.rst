Connexions Logging Application / Utility
========================================

This is a simple interface for logging client-side metrics and messages.

The application/utility is used to proxy client-side metrics and messages
to a running ``statsd`` service and logging service, respectively.
If a statsd service has not been configured,
the metrics will default to logging.

There are two ways to use this codebase:

1) As a standalone application which accepts and incoming request.
2) Within an existing application (recommended).

Security is handled via an HTTP header ``X-cnx-logging-key``,
which a shared key to be configured on both sides.
This is useful in the case where two or more applications share the service,
whicha also enables the applications to handle authnz in their own way.


Getting started
---------------

This is built as a Python WSGI application as well as an importable utility.

Installing
~~~~~~~~~~

To install the application itself::

    pip install .

Running the standalone application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reinstall the application with the following::

    pip install .[standalone]

To run the application, use the ``paste`` script with the ``serve`` command.
(The paste script and serve command come from ``PasteScript`` and
``PasteDeploy``, respectively.)

This example uses the ``development.ini``, which has been supplied with the
package.  If you changed any of the database setup values, you'll also need to
change them in the configuration file.::

    paster serve development.ini

You can then surf to the address printed out by the above command.

Running tests
-------------

.. image:: https://travis-ci.org/Connexions/cnx-logging.png?branch=master
   :target: https://travis-ci.org/Connexions/cnx-logging

The tests use the standard library ``unittest`` package
and can therefore be run with minimal effort.
::

    $ python -m unittest discover

Or::

    $ python setup.py test

API
---

:/metric: Accepts a JSON formatted POST containing
	  the metric ``type``, ``label`` and ``value``.

	  For example::

	      {"type": "incr", "label": "i.haz.clikd.cheezburgr"}

:/log: Accepts a JSON formatted POST contains a ``message``.

       For example::

	   {"message": "Smoo clikd on a cheezburgr"}

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2013 Rice University

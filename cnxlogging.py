# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""This is a simple interface for logging client-side metrics and messages."""
import logging
import json
import statsd


__all__ = ('Application', 'make_statist', 'paste_app_factory',)


STATS_LOGGER_NAME = 'stats'
SETTINGS_KEY__STATSD_HOST = 'statsd.host'
SETTINGS_KEY__STATSD_PORT = 'statsd.port'
SETTINGS_KEY__STATSD_PREFIX = 'statsd.prefix'


class _StatsLoggingClient(statsd.StatsClient):
    """This provides the same interface as statsd.StatsClient to make
    a logging compatible version of the statistics capturing methods.
    """

    def __init__(self, host=None, port=None, prefix=None, maxudpsize=512):
        """Keep the same parameters for easy instantiation."""
        self._addr = (host, port,)
        self._logger = logging.getLogger(STATS_LOGGER_NAME)
        self._prefix = prefix
        self._maxudpsize = maxudpsize

    def _send(self, data):
        """Send data to statsd."""
        self._logger.info(data.encode('ascii'))


def make_statist(settings):
    """Factory to create a statist object that will use statsd when
    configured or default to logging.
    """
    host = settings.get(SETTINGS_KEY__STATSD_HOST, None)
    port = settings.get(SETTINGS_KEY__STATSD_PORT, 8125)
    prefix = settings.get(SETTINGS_KEY__STATSD_PREFIX, None)

    # Is statsd configured?
    if host is not None:
        # Use statsd client.
        klass = statsd.StatsClient
    else:
        # Use statsd logging clone.
        klass = _StatsLoggingClient
    statist = klass(host, port, prefix)
    return statist


class Application:
    """Metric and message logging application.
    The given ``statist`` should be a ``statsd.StatsClient``
    or object with a compatible interface.
    The ``logger`` is a stand python logger from ``logging.getLogger``.
    The ``path`` is an optional path to listen on.
    If ``path`` is ``None``, the application will handle
    requests coming in to any path.
    """

    def __init__(self, statist, logger, path=None):
        self.statist = statist
        self.logger = logger
        self._message_type_handlers = {
            'log': self.handle_log,
            'metric': self.handle_metric,
            }

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] != 'POST':
            return self.not_found(environ, start_response)

        payload = self._parse(environ)
        # ??? Why are we smashing the type in the data
        #     rather than using a path based routing mechanism?
        handler = self._message_type_handlers[payload['message-type']]

        try:
            handler(payload)
        except Exception as exc:
            start_response('500 Internal Server Error',
                           [('Content-type', 'text/plain')])
            resp = ["{}: {}".format(exc.__class__.__name__, exc.message)]
        else:
            start_response('200 OK', [])
            resp = []
        return resp

    def not_found(self, environ, start_response):
        start_response('404 Not Found', [])
        return []

    def _parse(self, environ):
        return json.load(environ['wsgi.input'])

    def handle_log(self, payload):
        self.logger.info(payload['log-message'])

    def handle_metric(self, payload):
        # FIXME Only accepting `incr` metric,
        #       because that's all the original implemenation accepted.
        if payload['metric-type'] != 'incr':
            raise NotImplementedError("Only accepting `incr' request.")
        self.statist.incr(payload['metric-label'])


def paste_app_factory(global_config, **local_config):
    """Makes a WSGI application using the ``PasteDeploy`` interface."""
    statist = make_statist(local_config)
    logger = logging.getLogger(__name__)
    return Application(statist, logger)

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

ACCEPTED_METRIC_TYPES = ('incr', 'gauge', 'timing',)

logger = logging.getLogger(__name__)


class BaseHandlingError(Exception):
    """Base exception for exceptions that happen inside
    the log and metric handlers.
    """


class InvalidMetricType(BaseHandlingError):

    def __init__(self, type_):
        message = 'Invalid metric type: {}'.format(type_)
        super(InvalidMetricType, self).__init__(message)


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

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] != 'POST':
            return self.not_found(environ, start_response)

        # Routing (poorly, but simply done).
        if environ['PATH_INFO'] == '/metric':
            handler = self.handle_metric
        elif environ['PATH_INFO'] == '/log':
            handler = self.handle_log
        else:
            return self.not_found(environ, start_response)

        # Handle errors and don't send the entire traceback.
        try:
            handler(self._parse_message_body(environ))
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

    def _parse_message_body(self, environ):
        return json.load(environ['wsgi.input'])

    def handle_log(self, payload):
        self.logger.info(payload['message'])

    def handle_metric(self, payload):
        metric_type = payload['type']
        if metric_type not in ACCEPTED_METRIC_TYPES:
            raise InvalidMetricType(metric_type)
        method = getattr(self.statist, metric_type)

        label = payload['label']
        value = payload.get('value', None)
        value = value is None and 1 or value
        method(label, value)
        

def paste_app_factory(global_config, **local_config):
    """Makes a WSGI application using the ``PasteDeploy`` interface."""
    statist = make_statist(local_config)
    logger = logging.getLogger(__name__)
    return Application(statist, logger)

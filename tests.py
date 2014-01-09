# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import unittest
import logging
import json
from wsgiref.util import setup_testing_defaults

import statsd


class MockStatist(statsd.StatsClient):

    def __init__(self, test_case):
        self._prefix = None
        self.test_case = test_case

    def _send(self, data):
        if not hasattr(self.test_case, 'stats'):
            self.test_case.stats = []
        self.test_case.stats.append(data)


class LogCapturingHandler(logging.Handler):

    def __init__(self, test_case, level=logging.NOTSET):
        self.test_case = test_case
        super(LogCapturingHandler, self).__init__(level)

    def emit(self, record):
        if not hasattr(self.test_case, 'logged'):
            self.test_case.logged = []
        self.test_case.logged.append(record)


class StatistCase(unittest.TestCase):

    def test_creation_of_statsd_client(self):
        settings = {
            'statsd.host': 'example.com',
            'statsd.port': '8125',
            'statsd.prefix': '',
            }
        from cnxlogging import make_statist
        statist = make_statist(settings)
        import statsd
        self.assertTrue(isinstance(statist, statsd.StatsClient))

    def test_creation_degrades_to_logging(self):
        settings = {}
        from cnxlogging import make_statist
        statist = make_statist(settings)
        from cnxlogging import _StatsLoggingClient
        self.assertTrue(isinstance(statist, _StatsLoggingClient))


class ApplicationTestCase(unittest.TestCase):

    def setUp(self):
        self.statist = MockStatist(self)
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        self.log_handler = LogCapturingHandler(self)
        logger.addHandler(self.log_handler)
        from cnxlogging import Application
        self.app = Application(self.statist, logger)

    def start_response(self, *args, **kwargs):
        self.resp_args = args
        self.resp_kwargs = kwargs

    def test_metric_acceptance(self):
        metric_data = {
            'message-type': 'metric',
            'metric-type': 'incr',
            'metric-label': 'i.haz.clikd.cheezburgr',
            'metric-value': None,  # Also tests that `None' becomes 1.
            }
        environ = {'REQUEST_METHOD': 'POST'}
        setup_testing_defaults(environ)
        # Assign the posted message.
        environ['wsgi.input'].write(json.dumps(metric_data))
        environ['wsgi.input'].seek(0)

        resp_body = self.app(environ, self.start_response)

        # Check response, smoke test.
        self.assertEqual(resp_body, [])
        self.assertEqual(self.resp_args[0].upper(), '200 OK')
        self.assertEqual(self.resp_args[1], [])

        # Check the metric was accepted.
        self.assertEqual(self.stats, [u'i.haz.clikd.cheezburgr:1|c'])

    def test_log_acceptance(self):
        message = 'Smoo clikd on a cheezburgr'
        metric_data = {
            'message-type': 'log',
            'log-message': message,
            }
        environ = {'REQUEST_METHOD': 'POST'}
        setup_testing_defaults(environ)
        # Assign the posted message.
        environ['wsgi.input'].write(json.dumps(metric_data))
        environ['wsgi.input'].seek(0)

        resp_body = self.app(environ, self.start_response)

        # Check response, smoke test.
        self.assertEqual(resp_body, [])
        self.assertEqual(self.resp_args[0], '200 OK')
        self.assertEqual(self.resp_args[1], [])

        # Check the metric was accepted.
        self.assertEqual([x.msg for x in self.logged], [message])

    def test_only_accepts_post(self):
        environ = {'REQUEST_METHOD': 'GET'}
        setup_testing_defaults(environ)

        resp_body = self.app(environ, self.start_response)

        # Check response, smoke test.
        self.assertEqual(resp_body, [])
        self.assertEqual(self.resp_args[0].upper(), '404 NOT FOUND')
        self.assertEqual(self.resp_args[1], [])

    def test_invalid_metric_type(self):
        metric_data = {
            'message-type': 'metric',
            'metric-type': 'smudge',
            'metric-label': 'doo.be.doo.be.do',
            'metric-value': None,
            }
        environ = {'REQUEST_METHOD': 'POST'}
        setup_testing_defaults(environ)
        # Assign the posted message.
        environ['wsgi.input'].write(json.dumps(metric_data))
        environ['wsgi.input'].seek(0)

        from cnxlogging import InvalidMetricType
        with self.assertRaises(InvalidMetricType):
            resp_body = self.app.handle_metric(metric_data)

        resp_body = self.app(environ, self.start_response)
        self.assertEqual(self.resp_args[0], '500 Internal Server Error')
        self.assertEqual(self.resp_args[1], [('Content-type', 'text/plain')])
        self.assertEqual(resp_body,
                         ['InvalidMetricType: Invalid metric type: smudge'])


class StatsApplicationTestCase(unittest.TestCase):

    def setUp(self):
        self.log_handler = LogCapturingHandler(self)

        from cnxlogging import _StatsLoggingClient
        self.statist = _StatsLoggingClient()
        self.statist._logger.setLevel(logging.INFO)
        self.statist._logger.addHandler(self.log_handler)

        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        logger.addHandler(self.log_handler)

        from cnxlogging import Application
        self.app = Application(self.statist, logger)

    def start_response(self, *args, **kwargs):
        self.resp_args = args
        self.resp_kwargs = kwargs

    def test_stats_w_logging_client(self):
        # In the case where a statsd server has not been configured,
        #   stats info is sent to a log using a custom class that provides
        #   the same interface as the statsd.StatsClient.
        metric_data = {
            'message-type': 'metric',
            'metric-type': 'timing',
            'metric-label': 'i.haz.thunkd.cheezburgr',
            'metric-value': 300,
            }
        environ = {'REQUEST_METHOD': 'POST'}
        setup_testing_defaults(environ)
        # Assign the posted message.
        environ['wsgi.input'].write(json.dumps(metric_data))
        environ['wsgi.input'].seek(0)

        resp_body = self.app(environ, self.start_response)

        # Check response, smoke test.
        self.assertEqual(resp_body, [])
        self.assertEqual(self.resp_args[0].upper(), '200 OK')
        self.assertEqual(self.resp_args[1], [])

        # Check the metric was accepted.
        self.assertEqual([x.msg for x in self.logged],
                         ['i.haz.thunkd.cheezburgr:300|ms'])

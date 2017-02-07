"""
Tests the selection of job data from the database.

These tests create tight coupling to the aiohttp library. The other alternative
to mocking aiohttp objects is to use a Docker web server container to serve
bare-bones pages to test HTTP response codes, timeouts, etc.

Alternative is possibly to use the http.server module to start and stop a web
server here in this test file, defining handlers for the GET method.

"""

import asyncio
import io
import sys
import unittest.mock

import aiohttp
from django.test import SimpleTestCase
import yarl

# Preemptively replace settings module. Python will believe that the module has
# already been imported. The module's settings file imports the Django project
# settings module which, when running these tests outside of a Django project,
# obviously raises an exception. This must be done before the Command is
# imported.
sys.modules['docsnaps.settings'] = unittest.mock.NonCallableMock()

from .. import utils as test_utils
from docsnaps.management.commands._run import Command


patch_attributes = {'DOCSNAPS_REQUEST_TIMEOUT': 0.5}
@unittest.mock.patch('docsnaps.settings', create=True, **patch_attributes)
class TestRequestDocument(SimpleTestCase):
    """
    Patch the module settings into every test case. The sys.modules manipulation
    ensures the import statements never actually hit the import system and the
    patch ensures that the replacement value occupies the correct name within
    the test subject module's namespace.

    """

    def setUp(self):
        """
        Capture stdout output to string buffer instead of allowing it to be
        sent to actual terminal stdout.

        """
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._test_url = 'http://url.test'

    def test_error_code(self, docsnaps_settings_mock):
        """
        Test unsuccessful HTTP response code.

        I'm not happy with this test as I'm not sure it actually serves a
        purpose given the way it's implemented.

        """
        async def _mock_get(*args, **kwargs):
            response = aiohttp.ClientResponse(
                aiohttp.hdrs.METH_GET,
                yarl.URL(self._test_url))
            response.status = 404
            return response
        client_session = unittest.mock.Mock(get=_mock_get)
        loop = asyncio.get_event_loop()

        self.assertRaises(
            aiohttp.errors.HttpProcessingError,
            loop.run_until_complete,
            self._command._request_document(client_session, self._test_url))

    def test_request_timeout(self, docsnaps_settings_mock):
        """
        Test request timing out.

        Timeout should be logged with moderate to high severity.

        Nested coroutine function defined because aiohttp complains when
        ClientSession is not instantiated from within coroutine. Additionally,
        I prefer to at least attempt to test the instance's creation in a
        context similar to that of production.

        """
        async def _client_session_creation_coroutine(**kwargs):
            async with aiohttp.ClientSession(**kwargs) as session:
                await self._command._request_document(
                    session,
                    self._test_url)

        async def _mock_connect_coroutine(self, *args, **kwargs):
            await asyncio.sleep(
                patch_attributes['DOCSNAPS_REQUEST_TIMEOUT'] + 0.1)

        loop = asyncio.get_event_loop()
        connector = aiohttp.TCPConnector(loop=loop)
        connector.connect = _mock_connect_coroutine

        self.assertRaises(
            aiohttp.errors.TimeoutError,
            loop.run_until_complete,
            _client_session_creation_coroutine(connector=connector))

    def test_successful_request(self, docsnaps_settings_mock):
        """
        Test normal, successful HTTP request.

        I'm not sure nested function definitions are good practice here. Review.

        """
        # Define awaitable response mock.
        document_text = 'Documents snapshot.'
        async def mock_text_coroutine(*args, **kwargs):
            return document_text
        response_mock = unittest.mock.NonCallableMock()
        response_mock.text = mock_text_coroutine

        # Define awaitable get() mock.
        async def mock_get_coroutine(*args, **kwargs):
            return response_mock
        client_session_mock = unittest.mock.NonCallableMock(
            get=mock_get_coroutine)

        loop = asyncio.get_event_loop()
        text = loop.run_until_complete(
            self._command._request_document(
                client_session_mock,
                self._test_url))

        self.assertEqual(text, document_text)
        self.assertTrue(response_mock.close.called)

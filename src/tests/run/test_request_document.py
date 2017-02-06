"""
Tests the selection of job data from the database.

"""

import asyncio
import io
import sys
import unittest.mock

import aiohttp
import aiohttp.errors
from django.test import SimpleTestCase

# Preemptively replace settings module. Python will believe that the module has
# already been imported. The module's settings file imports the Django project
# settings module which, when running these tests outside of a Django project,
# obviously raises an exception. This must be done before the Command is
# imported.
sys.modules['docsnaps.settings'] = unittest.mock.NonCallableMock()

from .. import utils as test_utils
from docsnaps.management.commands._run import Command


patch_attributes = {'DOCSNAPS_REQUEST_TIMEOUT': 0.1}
@unittest.mock.patch('docsnaps.settings', create=True, **patch_attributes)
class TestRequestDocument(SimpleTestCase):

    def setUp(self):
        """
        Capture stdout output to string buffer instead of allowing it to be
        sent to actual terminal stdout.

        """
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._client_session_mock = unittest.mock.NonCallableMock()

    def test_error_code(self, docsnaps_settings_mock):
        """
        Test unsuccessful HTTP response code.

        """
        raise NotImplementedError('Complete this test.')

    def test_no_response(self, docsnaps_settings_mock):
        """
        Test no response from remote host, testing timeout.

        """
        raise NotImplementedError('Complete this test.')

    def test_redirect_code(self, docsnaps_settings_mock):
        """
        Test redirects in request.

        Redirect should be logged.

        """
        raise NotImplementedError('Complete this test.')

    def test_request_timeout(self, docsnaps_settings_mock):
        """
        Test request timing out.

        Timeout should be logged with moderate to high severity.

        """
        # Construct a real connector and mock its connect() method.
        # See: https://github.com/KeepSafe/aiohttp/blob/master/aiohttp/client.py
        # See the __init__ and _request methods.
        async def mock_connect_coroutine(*args, **kwargs):
            await asyncio.sleep(
                docsnaps_settings_mock.DOCSNAPS_REQUEST_TIMEOUT + 0.1)
        loop = asyncio.get_event_loop()
        connector = aiohttp.TCPConnector(loop=loop)
        connector.connect = mock_connect_coroutine

        async def client_session_coroutine(connector):
            async with aiohttp.ClientSession(connector=connector) as session:
                await self._command._request_document(
                    session,
                    'http://url.test')

        self.assertRaises(
            aiohttp.errors.TimeoutError,
            loop.run_until_complete,
            client_session_coroutine(connector))

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
        self._client_session_mock.get = mock_get_coroutine

        loop = asyncio.get_event_loop()
        text = loop.run_until_complete(
            self._command._request_document(
                self._client_session_mock,
                'http://url.test'))

        self.assertEqual(text, document_text)
        self.assertTrue(response_mock.close.called)

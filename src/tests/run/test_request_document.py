"""
Tests the selection of job data from the database.

"""

import asyncio
import io
import unittest.mock

from django.test import SimpleTestCase

from .. import utils as test_utils
from docsnaps.management.commands._run import Command


class TestRequestDocument(SimpleTestCase):

    def setUp(self):
        """
        Capture stdout output to string buffer instead of allowing it to be
        sent to actual terminal stdout.

        """
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._client_session_mock = unittest.mock.NonCallableMock()

    def test_error_code(self):
        """
        Test unsuccessful HTTP response code.

        """
        raise NotImplementedError('Complete this test.')

    def test_no_response(self):
        """
        Test no response from remote host, testing timeout.

        """
        raise NotImplementedError('Complete this test.')

    def test_redirect_code(self):
        """
        Test redirects in request.

        Redirect should be logged.

        """
        raise NotImplementedError('Complete this test.')

    def test_request_timeout(self):
        """
        Test request timing out.

        Timeout should be logged with moderate to high severity.

        """
        raise NotImplementedError('Complete this test.')

    def test_successful_request(self):
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
                'test.tset'))

        self.assertEqual(text, document_text)
        self.assertTrue(response_mock.close.called)

"""
Tests for the utility module in the management command package.

"""

import django.test

import django_docsnaps.management.commands._utils as command_utils
from . import utils as test_utils


class TestModelRelationFlattening(django.test.SimpleTestCase):
    """
    Test the model relationship graph flattener.

    """

    def test_normal_graph(self):
        """
        Given a normal model relationship graph, test for expected output.

        """
        docs_langs = test_utils.get_test_models()[0]
        expected = [
            docs_langs,
            docs_langs.document_id,
            docs_langs.language_id
        ]
        flattened = list(command_utils.flatten_model_graph(docs_langs))

        # List equality also compares order.
        self.assertEqual(flattened, expected)

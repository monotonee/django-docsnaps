"""
Tests for the utility module in the management command package.

"""

from django.test import SimpleTestCase

from . import utils as test_utils
import docsnaps.management.commands._utils as command_utils


class TestModelRelationFlattening(SimpleTestCase):
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

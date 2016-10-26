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
            docs_langs.language_id,
            docs_langs.document_id.service_id,
            docs_langs.document_id.service_id.company_id]
        flattened = list(
            command_utils.flatten_model_graph(docs_langs))

        # List equality also compares order.
        self.assertEqual(flattened, expected)

    def test_incorrect_argument(self):
        """
        Test that the function only accepts instance of the correct model.

        Because the subject of the tests is a generator, no code is executed
        until next() has been called at least once. We need to execute all
        iterations of the function until StopIteration is raised.

        """
        document = test_utils.get_test_models()[0].document_id

        self.assertRaises(
            ValueError,
            list,
            command_utils.flatten_model_graph(document))

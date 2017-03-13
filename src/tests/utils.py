"""
Utility and common functions used in testing.

"""

import docsnaps.models


def get_test_models(omit=None):
        """
        Construct a valid model graph with relationship attributes assigned.

        No parts of the data need to be real nor do URLs need to point to real
        resources. This is simply to test valid module structure and values.

        Note the explicit primary key values. This is done to facilitate
        comparison of QuerySet results. Without these explicit primary key
        values, attempts to compare these model instances with query result sets
        fails. To overcome this comparison failure would increase complexity of
        test assertions to an untenable level given the composite keys and
        foreign key constraints.

        Args:
            omit (string): The name of a model to omit from graph. The value
                in the graph will be set to None. If the omitted model is
                DocumentsLanguages, an iterable containing which is normally
                returned, the return value will be an empty iterable.

        Returns:
            sequence: Sequence of DocumentsLanguages model instances. If
                DocumentsLanguages were omitted using the optional keyword
                argument, then the iterable will be empty.

        Raises:
            ValueError: If value for "omit" argument is provided but the
                specified model name is not used inside this function.

        """
        model_name = None
        model_dict = {}

        # Assign models
        model_name = docsnaps.models.Language.__name__
        model_dict[model_name] = docsnaps.models.Language(
            language_id=1,
            name='English',
            code_iso_639_1='en') \
            if omit != model_name else None

        model_name = docsnaps.models.Document.__name__
        model_dict[model_name] = docsnaps.models.Document(
            document_id=1,
            module='fake.module',
            name='Terms of Use') \
            if omit != model_name else None

        model_name = docsnaps.models.DocumentsLanguages.__name__
        model_dict[model_name] = docsnaps.models.DocumentsLanguages(
            documents_languages_id=1,
            document_id=model_dict[docsnaps.models.Document.__name__],
            language_id=model_dict[docsnaps.models.Language.__name__],
            url='help.test.tset/legal/termsofuse?locale=en') \
            if omit != model_name else None

        # If "omit" argument was passed and yet no models were omitted from the
        # hierarchy, then value of "omit" must not correspond to a model name.
        if omit and omit not in list(model_dict.keys()):
            raise ValueError(
                'Cannot omit model "' + omit + '". '
                'No such model is returned by this function.')

        # Define return iterable.
        # model_name will be the DocumentsLanguages class name or None.
        return_iterable = ()
        if model_dict[model_name]:
            return_iterable = (model_dict[model_name],)

        return return_iterable

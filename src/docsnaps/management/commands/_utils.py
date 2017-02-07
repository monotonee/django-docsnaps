"""
A module that provides a few utility functions and/or classes.

"""

from collections import deque

from django.core.management.base import CommandError
from django.core.management.color import color_style
from django.db.models.fields.related import ForeignKey

from docsnaps.models import DocumentsLanguages


def flatten_model_graph(model):
    """
    Recursively yield related model instances in a relationship graph.

    Technically, a ForeignKey relationship is always going to be a tree rather
    than a generic graph, but this name keeps things more flexible for future
    changes to entity relationshisps and isn't technically inaccurate.

    The chain of relationship fields in a model form a graph structure.
    The plugin modules' get_models() function returns an iterable of what
    equates to the deepest nodes in their respective, logical "graphs." By this
    metric, this method yields each model in the relationship graph in a
    reverse breadth-first/level-order manner. However, if one considers the
    passed model class the root node, then this method would be yield each model
    in the graph in a standard breadth-first manner.

    For instance, the DocumentsLanguages models have two parent (ForeignKey)
    fields: a Document and a Language. This generator will first yield the
    child DocumentsLanguages instance before yielding the parent Document
    and Language instances.

    Since this method yields depth first, it tests for instances of
    relationship fields, not reverse relationship fields.

    Args:
        model (models.DocumentsLanguages): A "child" model instance, the
            relationship fields of which will be traversed up the graph.

    Yields:
        models.*: Each model instance of each relationship field in the model
            graph, depth-first.

    See:
        https://github.com/django/django/blob/master/django/db/models/fields/related.py
        https://github.com/django/django/blob/master/django/db/models/fields/reverse_related.py

    """
    model_queue = deque([model])
    while model_queue:
        current_model = model_queue.popleft()
        for field in current_model._meta.get_fields():
            if (isinstance(field, ForeignKey)
                and hasattr(current_model, field.name)):
                model_queue.append(getattr(current_model, field.name))
        yield current_model

def raise_command_error(stdout, message):
    """
    Raise a CommandError and writes a failure string to stdout.

    This function is designed specifically to be used inside a Command
    class. In this module, the custom Command classes often begin status
    messages in stdout without ending them with a newline. Success or
    failure messages are later appended to the stdout line along with with the
    newline. This function closes one of these open-ended stdout lines with a
    failure.

    In addition, it raises the CommandError that Django's management command
    framework expects and will handle.

    Args:
        stdout: An IO stream. Used to output
        message (string or Exception): The message to pass to the exception
            constructor. Whatever is passed to an Exception constructor
            seems to be implicitly converted to a string. All Exception
            subclasses appear to output their message when converted.

    Raises:
        django.core.management.base.CommandError

    """
    style = color_style()
    stdout.write(style.ERROR('failed'))
    raise CommandError(message)


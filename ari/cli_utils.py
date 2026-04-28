from typing import Any, Callable

from prompt_toolkit.validation import Validator
from prompt_toolkit.shortcuts import prompt


def is_number(text):
    # If you expect None to be passed:
    if text is None:
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


number_validator = Validator.from_callable(
    is_number,
    error_message="Deze invoer bevat niet-numerieke tekens",
    move_cursor_to_end=True,
)


def is_bool(text):
    if text == "true":
        return True
    if text == "True":
        return True
    if text == "false":
        return True
    if text == "False":
        return True
    return False


bool_validator = Validator.from_callable(
    is_bool, error_message="Deze invoer is geen boolean waarde", move_cursor_to_end=True
)


def is_yes_or_no(text):
    # If you expect None to be passed:
    if text is None:
        return False
    if text == "":
        return True  # to handle default value
    if text == "y" or text == "Y":
        return True
    if text == "n" or text == "N":
        return True
    return False


yes_no_validator = Validator.from_callable(
    is_yes_or_no,
    error_message="De invoer moet ja (y) of nee (n) zijn",
    move_cursor_to_end=True,
)

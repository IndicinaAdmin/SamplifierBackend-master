import os
from datetime import date
from decimal import Decimal
from enum import Enum
from json import JSONEncoder
from typing import Union
from uuid import UUID, uuid4


def get_today():
    """ This method allows mocking the current date in tests. """
    return date.today()


def get_today_str():
    return str(get_today())


def empty_list():
    return []


def empty_set():
    return set([])


def empty_dict():
    return {}


def new_uuid():
    """ Returns a unique id version 4. """
    return str(uuid4())


def get_boolean_env_var(name: str):
    value = os.environ.get(name, False)
    return True if str(value).lower() == "true" else False


def parse_boolean(value: Union[int, str]) -> bool:
    """
    Parses a str or int value to bool.
    For str values, the result is True if it starts with '1', 't', 'T', 'y', 'Y'.
    Otherwise, the result is false.

    Args:
        value(int or str): the value to be parsed

    Returns:
        A bool with the value parsed, default is False
    """
    if isinstance(value, int):
        return value > 0
    elif isinstance(value, str):
        # Find the first alphanumeric char
        for char in value:
            if char.isalnum():
                # Values that represent True
                if char in ["1", "t", "T", "y", "Y"]:
                    return True
                else:
                    return False
        # False is the default
        return False
    else:
        raise TypeError("The value provided should be an int or str.")


class EnumWithDescription(Enum):
    def __new__(cls, *args, **kwds):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, description: str = None):
        self._description_ = description

    # this makes sure that the description is read-only
    @property
    def description(self):
        return self._description_

    @classmethod
    def has_value(cls, value):
        """ Check if value is a value in enum. """
        if type(value) == cls:
            return value in cls.__members__.values()
        elif type(value) == int:
            return value in cls._value2member_map_
        else:
            return False


class CustomEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Enum):
            return o.value
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, Decimal):
            if o % 1 == 0:
                return int(o)
            return float(o)
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, o)


class ConfigFileType(Enum):
    """
    Enum with the names of the config sub-folders
    """

    REFERENCE_ARRAY = "reference_array"
    MEASURES_PER_YEAR = "measures_per_year"
    MEASURES_PER_PRODUCT = "measures_per_product"
    SINGLE_RATE_MEASURES = "single_rate_measures"
    MULTI_RATE_MEASURES = "multi_rate_measures"


class FileStatus(Enum):
    """
    Enum to represent the possible file status
    DO NOT CHANGE THE VALUES OF EACH ENTRY. THEY ARE HTTP CODES
    """

    NOT_FOUND = 404
    INVALID = 422
    VALID = 200
    WRONG_TIMESTAMP = 409
    CALCULATED = 202
    EXPORTED = 201
    UNEXPECTED_ERROR = 500


def find_and_parse_int(buffer: str) -> int:
    """
    Converts the first sequence of numerals in a string to an integer
    Args:
        buffer(str): a string to parse
    Returns:
        int: The integer.
    """
    i = 0
    while i < len(buffer) and not (buffer[i].isnumeric()):
        i += 1
    j = i
    while j < len(buffer) and buffer[j].isnumeric():
        j += 1
    return int(buffer[i:j])

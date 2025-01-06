import os
from dataclasses import is_dataclass, fields
from datetime import datetime
from dataclasses import is_dataclass, fields
from typing import Any, Type, Dict, get_origin, get_args, Union


def dict_to_dataclass(cls: Type, data: Dict[str, Any]) -> Any:
    """
    Recursively converts a dictionary into a dataclass instance, handling Union types.

    Args:
        cls: The dataclass type (or Union of types) to convert to.
        data: The dictionary to convert.

    Returns:
        An instance of the dataclass `cls` populated with values from `data`.
    """

    if not is_dataclass(cls) and not (get_origin(cls) is Union):
        raise ValueError(f"Provided class {cls} is not a dataclass or Union.")

    # If it's a Union, find the first matching dataclass
    if get_origin(cls) is Union:
        for sub_cls in get_args(cls):
            if is_dataclass(sub_cls):
                if all(key in [f.name for f in fields(sub_cls)] for key in data.keys()):
                    cls = sub_cls
                    break
        else:
            raise ValueError(f"No matching dataclass found for the given data: {data}")

    # Prepare a dictionary to hold the field values for the dataclass instance
    init_values = {}

    # Iterate through the fields of the dataclass
    for field in fields(cls):
        field_name = field.name
        field_type = field.type

        if field_name not in data:
            # If the field is not in the input dictionary, skip it (optional fields)
            continue

        value = data[field_name]

        # Handle lists, assuming that they are lists of dataclasses or primitives
        if isinstance(value, list):
            if hasattr(field_type, '__origin__') and field_type.__origin__ == list:
                # Get the type of the list elements
                list_type = field_type.__args__[0]

                if is_dataclass(list_type):
                    # Recursively convert each item in the list if it's a dataclass
                    init_values[field_name] = [dict_to_dataclass(list_type, item) if isinstance(item, dict) else item
                                               for item in value]
                else:
                    # If the list contains primitives, assign it directly
                    init_values[field_name] = value
            else:
                init_values[field_name] = value

        # Handle nested dataclasses (if the field type is another dataclass)
        elif is_dataclass(field_type) and isinstance(value, dict):
            init_values[field_name] = dict_to_dataclass(field_type, value)

        # Handle Union types in nested fields
        elif get_origin(field_type) is Union:
            init_values[field_name] = dict_to_dataclass(field_type, value)

        # For everything else (primitives, enums, etc.)
        else:
            init_values[field_name] = value

    # Instantiate the dataclass with the initialized values
    return cls(**init_values)
import urllib.parse
def unquote(encoded_url):

    """

    :param encoded_url:
    :return:
    encoded_url = '/files/ptcloud%2Bmesg.json'
    decoded_url=unquote(encoded_url)
    print(decoded_url)

    '/files/ptcloud+mesg.json'
    """
    decoded_url = urllib.parse.unquote(encoded_url)
    return decoded_url
def now(sep="T", domain="hours"):
    return datetime.now().isoformat(sep=sep, timespec=domain)

def remove_none_values(d):
    """
    Recursively remove keys with None values from a dictionary or list.
    Parameters:
    d (dict or list): The input dictionary or list to clean.
    Returns:
    dict or list: The cleaned dictionary or list.
    """
    if isinstance(d, dict):
        return {k: remove_none_values(v) for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        return [remove_none_values(v) for v in d if v is not None]
    else:
        return d

def on_shutdown():
    return True


def hostname():
    return os.getenv("HOSTNAME", "localhost")


class Host:
    @classmethod
    @property
    def name(cls):
        return hostname()

    @classmethod
    def format(cls, key, sep=":"):
        return f"{cls.name}{sep}{key}"


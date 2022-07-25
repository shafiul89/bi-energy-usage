import copy
import enum
import json


def is_safe_json(obj) -> bool:
    """
    Can the specified object be safely converted to JSON?

    Parameters
    ----------
    obj : any
        The object to be tested.

    Returns
    -------
    bool
        True if the specified object can be converted to JSON, False otherwise.
    """
    try:
        json.dumps(obj)
        return True
    except Exception:  # noqa
        return False


def get_safe_json(obj, max_length: int = -1, deep_copy: bool = True):
    """
    Convert the specified object to JSON for inclusion in logging output.

    Various methods are attempted in order to convert the object to JSON:

    - If the object is a string, return the string directly.
    - If the object is an enum value, return the string representation of the value.
    - A direct conversion using json.dumps(obj)
    - An indirect conversion using ~ json.dumps(vars(obj))
    - A poor fallback using str(obj) that may provide no more than a class/type name

    Values in lists/dicts (inc. nested lists/dicts) are converted where possible.

    Parameters
    ----------
    obj : any
        The object to be converted to JSON
    max_length : int
        The maximum length of the resulting string.  Default -1 = no limit.
    deep_copy : bool
        True to make a deep copy of the object (if it is a list or dict) prior to converting to JSON in order
        to avoid making changes to the object

    Returns
    -------
    str
        A JSON representation of the object.

    """
    s = None

    # is the object a string, return the string
    if type(obj) is str:
        s = obj

    # if the object is an enum value, return the string representation of the value
    if s is None:
        try:
            if issubclass(type(obj), enum.Enum):
                s = str(obj)
        except Exception as e:  # noqa
            pass

    # try direct conversion
    if s is None:
        try:
            s = json.dumps(obj)
        except Exception:  # noqa
            pass

    # if the object is a list or dict, try making a deep copy of the list/dict JSON-safe and converting that to JSON
    if s is None and ((type(obj) is list) or type(obj) is dict):
        try:
            if deep_copy:
                obj = copy.deepcopy(obj)
            if type(obj) is list:
                make_safe_list(obj, max_length)  # noqa
            elif type(obj) is dict:
                make_safe_dict(obj, max_length)  # noqa
            s = json.dumps(obj)
        except Exception:  # noqa
            pass

    # if the object is a class
    if s is None:
        try:
            if hasattr(obj, '__dict__'):
                x = copy.deepcopy(vars(obj))  # deep copy to avoid changing the object itself
                make_safe_dict(x, max_length)
                s = json.dumps(x)
        except Exception:  # noqa
            pass

    # string fallback
    if s is None:
        try:
            s = str(obj)
        except Exception:  # noqa
            pass
    if s is not None and -1 < max_length < len(s):
        return s[0:max_length]
    return s


def get_object_safe_for_json(obj, max_length: int, deep_copy: bool = True):
    """
    Replace values in the specified object that cannot be converted to JSON with JSON-safe values.

    Beware:  This method modifies the object passed to it.
    A deep conversion is performed - i.e. nested lists/dicts are also processed.

    In comparison to get_safe_json(), this function does not actually return JSON, but a modified version of the
    specified object that is JSON-safe (i.e. can be converted to JSON).

    Parameters
    ----------
    obj : any
        The object to process.
    max_length : int
        The maximum length of converted values.  Default -1 = no limit.
    deep_copy : bool
        True to make a deep copy of the object in order to avoid making changes to the object.

    Returns
    -------
    any
        Either the original value (if JSON-safe) or a modified value that is JSON-safe.
    """
    if is_safe_json(obj):
        return obj
    if deep_copy:
        obj = copy.deepcopy(obj)
    if type(obj) is list:
        make_safe_list(obj, max_length)   # noqa
    elif type(obj) is dict:
        make_safe_dict(obj, max_length)   # noqa
    elif type(obj) is str:
        if len(obj) > max_length:         # noqa
            return obj[0:max_length]
    else:
        obj = get_safe_json(obj, max_length)
    return obj


def make_safe_list(obj: list, max_length: int = -1):
    """
    Replace values in the specified list that cannot be converted to JSON with JSON-safe values.

    Beware:  This method modifies the list passed to it.
    A deep conversion is performed - i.e. nested lists/dicts are also processed.

    Parameters
    ----------
    obj : list
        The list to process.
    max_length : int
        The maximum length of converted values within the list.  Default -1 = no limit.

    Returns
    -------
    None
        No return value - the values are directly updated inside the specified list.
    """
    updates = {}
    for idx, child in enumerate(obj):
        if type(child) is list:
            make_safe_list(child, max_length)
        elif type(child) is dict:
            make_safe_dict(child, max_length)
        elif type(child) is str:
            if len(child) > max_length:
                updates[idx] = child[0:max_length]
        else:
            if not is_safe_json(child):
                s = get_safe_json(obj[idx], max_length, False)
                updates[idx] = s
    for idx in updates:
        obj[idx] = updates[idx]


def make_safe_dict(obj, max_length: int = -1):
    """
    Replace values in the specified dict that cannot be converted to JSON with JSON-safe values.

    Beware:  This method modifies the list passed to it.
    A deep conversion is performed - i.e. nested lists/dicts are also processed.

    Parameters
    ----------
    obj : dict
        The dict to process.
    max_length : int
        The maximum length of converted values within the dict.  Default -1 = no limit.

    Returns
    -------
    None
        No return value - the values are directly updated inside the specified dict.
    """
    updates = {}
    for key in obj:
        if type(obj[key]) is list:
            make_safe_list(obj[key], max_length)
        elif type(obj[key]) is dict:
            make_safe_dict(obj[key], max_length)
        elif type(obj[key]) is str:
            if len(obj[key]) > max_length:
                updates[key] = obj[key][0:max_length]
        else:
            if not is_safe_json(obj[key]):
                s = get_safe_json(obj[key], max_length, False)
                updates[key] = s
    for key in updates:
        obj[key] = updates[key]

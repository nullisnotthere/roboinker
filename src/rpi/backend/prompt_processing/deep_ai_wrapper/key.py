"""
Source: https://github.com/5eroo/DeepAI-Wrapper
"""

import js2py
from .api_typing import MyRandomString


def get_random_str() -> MyRandomString:

    """
    This function returns a random string in the hardcoded JS
    """

    _random_str = """
const myrandomstr = function () {
    return Math.round(Math.random() * 100000000000) + '';
};

"""

    return js2py.eval_js(_random_str + "myrandomstr()")


__all__ = [
    'get_random_str',
]

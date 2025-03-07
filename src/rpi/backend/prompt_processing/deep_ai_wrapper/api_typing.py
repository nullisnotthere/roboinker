"""
Source: https://github.com/5eroo/DeepAI-Wrapper
"""

import typing


MyRandomString = typing.NewType('MyRandomString', str)
Messages = typing.List[typing.Dict[str, str]]
CompletionsGenerator = typing.Generator[str, None, None]

__all__ = [
    'MyRandomString',
    'Messages',
    'CompletionsGenerator'
]

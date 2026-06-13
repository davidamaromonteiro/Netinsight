"""
Shared rate-limiter instance.

Placed in its own module so that both ``main.py`` (middleware setup) and
endpoint modules (decorators) can import the same ``Limiter`` object
without circular dependencies.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

import shutil
import os

_cache = {}


def check_binary(name):
    if name not in _cache:
        found = shutil.which(name) is not None
        _cache[name] = found
        if not found:
            print(f"  [SKIP] {name} not found on PATH")
    return _cache[name]


def check_env(var):
    if os.getenv(var):
        return True
    print(f"  [SKIP] {var} not set")
    return False

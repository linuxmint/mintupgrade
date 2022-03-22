#!/usr/bin/python3
import gi
import threading
from gi.repository import GObject

# Used as a decorator to run things in the background
def async_function(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

# Used as a decorator to run things in the main loop, from another thread
def idle_function(func):
    def wrapper(*args):
        GObject.idle_add(func, *args)
    return wrapper


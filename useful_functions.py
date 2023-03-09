"""Useful functions to use in Go4Schools_API_Access.py"""

from os import system
from subprocess import check_call


def clear():
    """Clears the console."""
    system("cls")


def install(package):
    """Uses pip to install a package. This will error if 'pip' is not on %PATH%."""
    check_call(["pip", "install", package])

"""A Lennard-Jones potential in PyTorch, as a template atomforge model plugin.

Everything in this package except ``executor.py`` is imported on the host, where
torch is not installed. Only ``executor.py`` may import torch, and only inside
functions and methods, so that loading the module on the host stays cheap.
"""

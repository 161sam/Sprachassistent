"""
Integration package for binary audio backend support
"""

from .compatibility_layer import CompatibilityWrapper, MockSTTProcessor, MockTTSProcessor, MockConfig

__all__ = ['CompatibilityWrapper', 'MockSTTProcessor', 'MockTTSProcessor', 'MockConfig']

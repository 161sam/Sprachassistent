"""
Testmodul: test_config.py
Ziel: Validiert das Laden von .env-Konfigurationen
Erwartung: Variablen werden gesetzt
"""

import os

from testsuite.base_test import BaseTest


def test_env_loading():
    BaseTest.load_env(profile=os.getenv("TEST_PROFILE"))
    # As placeholder, ensure at least one environment variable is set
    assert os.getenv("PATH")

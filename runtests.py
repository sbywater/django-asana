#!/usr/bin/env python
# coding: utf-8

import os
import sys
import django


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    django.setup()
    from django.test.runner import DiscoverRunner

    test_runner = DiscoverRunner(verbosity=2)
    failures = test_runner.run_tests(["djasana.tests"])
    if failures:
        sys.exit(failures)

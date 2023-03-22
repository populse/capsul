# -*- coding: utf-8 -*-
from pathlib import Path
import subprocess
import sys

capsul_module_dir = Path(__file__).parent.parent
pytest_command = [sys.executable, '-m', 'coverage', 'run', '--source=.',
                  '-m', 'pytest', '--junit-xml=junit.xml', '--html=tests.html']
coverage_command = [sys.executable, '-m', 'coverage', 'html', '-d', 'coverage']
print(' '.join("'{}'".format(i) for i in pytest_command))
subprocess.check_call(pytest_command)
print(' '.join("'{}'".format(i) for i in coverage_command))
subprocess.check_call(coverage_command)

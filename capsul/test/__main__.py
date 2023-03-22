# -*- coding: utf-8 -*-
import argparse
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(
    prog='Test capsul module',
    description='Run Capsul test suite')
parser.add_argument('--html',
                    action='store',
                    default=None,
                    metavar='DIRECTORY',
                    help='Create tests and coverage HTML reports in given '
                    'directory. Entrypoints are test.html and index.html')
args = parser.parse_args()
if args.html:
    Path(args.html).mkdir(exist_ok=True)
    pytest_command = [sys.executable, '-m', 'coverage', 'run', '--source=.',
                    '-m', 'pytest', '--junit-xml={}/junit.xml'.format(args.html),
                    '--html={}/tests.html'.format(args.html)]
    coverage_command = [sys.executable, '-m', 'coverage', 'html', '-d', args.html]
    print(' '.join("'{}'".format(i) for i in pytest_command))
    subprocess.check_call(pytest_command)
    print(' '.join("'{}'".format(i) for i in coverage_command))
    subprocess.check_call(coverage_command)
else:
    pytest_command = [sys.executable, '-m', 'pytest']
    coverage_command = [sys.executable, '-m', 'coverage', 'html', '-d', 'coverage']
    print(' '.join("'{}'".format(i) for i in pytest_command))
    subprocess.check_call(pytest_command)

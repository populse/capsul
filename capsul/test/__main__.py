import argparse
import os
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser(
    prog="Test capsul module", description="Run Capsul test suite"
)
parser.add_argument(
    "--html",
    action="store",
    default=None,
    metavar="DIRECTORY",
    help="Create tests and coverage HTML reports in given "
    "directory. Entrypoints are test.html and index.html",
)
parser.add_argument(
    "-v", "--verbose", action="count", default=0, help="Increase verbosity"
)
parser.add_argument(
    "-s", action="store_true", default=None, help="Do not capture stdout nor stderr"
)
parser.add_argument(
    "-x",
    "--exitfirst",
    action="store_true",
    help="Exit instantly on first error or failed test",
)
parser.add_argument(
    "-k",
    metavar="EXPRESSION",
    dest="keyword",
    default=None,
    action="store",
    help="Only run tests which match the given substring "
    "expression. An expression is a Python evaluatable "
    "expression where all names are substring-matched "
    "against test names and their parent classes. "
    "Example: -k 'test_method or test_other' matches "
    "all test functions and classes whose name contains "
    "'test_method' or 'test_other', while -k 'not "
    "test_method'vmatches those that don't contain "
    "'test_method' in their names. -k 'not test_method "
    "and not test_other' will eliminate the matches. "
    "Additionally keywords are matched to classes and "
    "functions containing extra names in their "
    "'extra_keyword_matches' set, as well as functions "
    "which have names assigned directly to them. The "
    "matching is case-insensitive.",
)

args = parser.parse_args()
pytest_command = [sys.executable, "-m", "pytest"]
if args.verbose:
    pytest_command.append("-" + "v" * args.verbose)
if args.exitfirst:
    pytest_command.append("-x")
if args.keyword:
    pytest_command += ["-k", args.keyword]
if args.s:
    pytest_command += ["-s"]
capsul_src = Path(__file__).parent.parent
if args.html:
    Path(args.html).mkdir(exist_ok=True)
    pytest_command += ["--cov=capsul", f"--html={args.html}/tests.html"]
    coverage_command = [sys.executable, "-m", "coverage", "html", "-d", args.html]
    env = os.environ.copy()
    print(" ".join(f"'{i}'" for i in pytest_command))
    subprocess.check_call(pytest_command, env=env, cwd=capsul_src)
    print(" ".join(f"'{i}'" for i in coverage_command))
    subprocess.check_call(coverage_command)
else:
    print(" ".join(f"'{i}'" for i in pytest_command))
    subprocess.check_call(pytest_command, cwd=capsul_src)

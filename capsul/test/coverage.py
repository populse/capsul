# -*- coding: utf-8 -*-
# System import
from __future__ import division, print_function
from __future__ import absolute_import
import soma.subprocess
import os
import sys

# Capsul import
import capsul


def run_all_tests(modules=[]):
    """ Run Capsul unitests and get a coverage report and a covergae rate

    Parameters
    ----------
    modules: list
        list of [sub] modules to be tested. Default: ['capsul']

    Returns
    -------
    coverage_rate: int
        the total coverage rate
    coverage_report: str
    """

    # run nose tests
    capsul_path = capsul.__path__[0]
    os.chdir(capsul_path)
    if sys.version_info[0] >= 3:
        nosetests = 'nosetests%d' % sys.version_info[0]
    else:
        nosetests = 'nosetests'
    if not modules:
        modules = ['capsul']
    cmd = "%s --with-coverage %s" % (nosetests, ' '.join(modules))
    process = soma.subprocess.Popen(cmd, stdout=soma.subprocess.PIPE,
                               stderr=soma.subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    if process.returncode:
        error = "Error will running cmd: {0}\n{1}".format(cmd, stderr)
        #raise StandardError(error)

    # Nose returns the output in stderr
    # Filter output
    return clean_coverage_report(stderr)


def clean_coverage_report(nose_coverage):
    """ Grab coverage lines from nose output and get the coverage rate

    Parameters
    ----------
    nose_coverage: str (mandatory)
        the nose coverage report

    Returns
    -------
    coverage_rate: int
        the total coverage rate
    coverage_report: str
        the cleaned nose coverage report
    """
    # Clean report
    if sys.version_info[0] >= 3 and isinstance(nose_coverage, bytes):
        nose_coverage = nose_coverage.decode()
    lines = nose_coverage.splitlines()
    coverage_report = []
    header = None
    tcount = None
    total = [0, 0]
    tested_modules = [
        "capsul/attributes/",
        "capsul/pipeline/",
        "capsul/process/",
        "capsul/study_config/",
        "capsul/subprocess/"
        "capsul/utils/",
        "soma/controller/"
    ]
    for line in lines:

        #print(line)
        # Select modules
        if (header is not None
            and any([line.startswith(x) for x in tested_modules])):

            items = line.split()
            stmts = int(items[1]) # statements
            miss = int(items[2])  # missed statements
            covered = stmts - miss
            # Remove the Missing lines
            percent_index = line.find("%")
            coverage_report.append(line[:percent_index + 1])
            # Get module coverage
            #total[0] += int(line[percent_index - 3: percent_index])
            #total[1] += 1
            total[0] += covered
            total[1] += stmts
        if line.startswith("Name"):
            header = line
        if line.startswith("Ran"):
            tcount = line
    # Get capsul coverage rate
    if total[1] == 0:
        raise ValueError("No tests found - check Capsul installation")
    coverage_rate = float(total[0]) * 100 / total[1]
    coverage_report.insert(0, header.replace("Missing", ""))

    # Format report
    coverage_report.insert(1, "-" * 70)
    coverage_report.append("-" * 70)
    coverage_report.append(
        "TOTAL {0}% ({1} / {2} statements".format(
            int(round(coverage_rate)), total[0], total[1]))
    coverage_report.append("-" * 70)
    coverage_report.append(tcount)
    coverage_report = "\n".join(coverage_report)

    return coverage_rate, coverage_report


if __name__ == "__main__":
    modules = sys.argv[1:]
    rate, report = run_all_tests(modules)
    print(report)
    print(rate)

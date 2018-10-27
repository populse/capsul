##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
from __future__ import division, print_function
import soma.subprocess
import os

# Capsul import
import capsul


def run_all_tests():
    """ Run Capsul unitests and get a coverage report and a covergae rate

    Returns
    -------
    coverge_rate: int
        the total coverage rate
    coverage_report: str
    """

    # run nose tests
    capsul_path = capsul.__path__[0]
    os.chdir(capsul_path)
    cmd = "nosetests --with-coverage capsul"
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
    """ Grab coverage lines from nose output and get the coverge rate

    Parameters
    ----------
    nose_coverage: str (mandatory)
        the nose coverge report

    Returns
    -------
    coverge_rate: int
        the total coverage rate
    coverage_report: str
        the cleaned nose coverage report
    """
    # Clean report
    lines = nose_coverage.splitlines()
    coverage_report = []
    header = None
    tcount = None
    total = [0, 0]
    tested_modules = [
        b"capsul/attributes/",
        b"capsul/pipeline/",
        b"capsul/process/",
        b"capsul/study_config/",
        b"capsul/subprocess/"
        b"capsul/utils/",
        b"soma/controller/"
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
        if line.startswith(b"Name"):
            header = line
        if line.startswith(b"Ran"):
            tcount = line
    # Get capsul coverage rate
    if total[1] == 0:
        raise ValueError("No tests found - check Capsul installation")
    coverge_rate = float(total[0]) * 100 / total[1]
    coverage_report.insert(0, header.replace(b"Missing", ""))

    # Format report
    coverage_report.insert(1, b"-" * 70)
    coverage_report.append(b"-" * 70)
    coverage_report.append(
        b"TOTAL {0}% ({1} / {2} statements".format(
            int(round(coverge_rate)), total[0], total[1]))
    coverage_report.append(b"-" * 70)
    coverage_report.append(tcount)
    coverage_report = "\n".join(coverage_report)

    return coverge_rate, coverage_report


if __name__ == "__main__":
    rate, report = run_all_tests()
    print(report)
    print(rate)

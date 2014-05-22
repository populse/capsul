#! /usr/bin/env python
##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# System import
from __future__ import division
import subprocess
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
    cmd = "nosetests --with-coverage --cover-package=capsul"
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=True)
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
    for line in lines:
        if (line.startswith("capsul.pipeline.") or
                line.startswith("capsul.process.") or
                line.startswith("soma.controller.") or
                line.startswith("capsul.study_config.")):
            # Remove the Missing lines
            percent_index = line.find("%")
            coverage_report.append(line[:percent_index + 1])
            # Get module coverage
            total[0] += int(line[percent_index - 3: percent_index])
            total[1] += 1
        if line.startswith("Name"):
            header = line
        if line.startswith("Ran"):
            tcount = line
    # Get capsul coverage rate
    coverge_rate = total[0] / total[1]
    coverage_report.insert(0, header.replace("Missing", ""))

    # Format report
    coverage_report.insert(1, "-" * 70)
    coverage_report.append("-" * 70)
    coverage_report.append("TOTAL {0}%".format(int(coverge_rate)))
    coverage_report.append("-" * 70)
    coverage_report.append(tcount)
    coverage_report = "\n".join(coverage_report)

    return coverge_rate, coverage_report


if __name__ == "__main__":
    rate, report = run_all_tests()
    print report
    print rate
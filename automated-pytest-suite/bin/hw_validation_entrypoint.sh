#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0

#!/bin/bash
TEST_AUTOMATION_DIR=/usr/wrcptestsuite
TEST_AUTOMATION_HOME=$TEST_AUTOMATION_DIR/automated-pytest-suite/

set -x

if [[ -z $INCLUDE ]]
then
echo "INCLUDE environment variable is not defined"
exit 10
fi


echo "test suite for WRCP platform verfication"
echo "========================================"
echo "Executing the test cases"

cd $TEST_AUTOMATION_HOME
for i in $INCLUDE
do
echo "Running tests on $i"
python3 -m pytest  -m hw_validation --lab=$i --testcase-config=/root/test-config/stx-test_template.conf hw_validation_testcases --junit-xml reports/report-$i.xml
echo "#####################################################################################################"
done

#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import pdb
import os
import re
import time

from pytest import fixture, mark, skip

from utils.tis_log import LOG
from utils.clients.ssh import ControllerClient
from utils.clients.local import LocalHostClient

from keywords import common, kube_helper, host_helper, system_helper, \
    container_helper, keystone_helper
from consts.filepaths import TestServerPath, StxPath
from consts.stx import HostAvailState, Container
from consts.proj_vars import ProjVar
from consts.auth import HostLinuxUser
from testfixtures.recover_hosts import HostsToRecover

filename = "egress.yaml"
def controller_precheck(controller):
    host = system_helper.get_active_controller_name()
    if controller == 'standby':
        controllers = system_helper.get_controllers(
            availability=(HostAvailState.AVAILABLE, HostAvailState.DEGRADED,
                          HostAvailState.ONLINE))
        controllers.remove(host)
        if not controllers:
            skip('Standby controller does not exist or not in good state')
        host = controllers[0]

    return host


@mark.platform_sanity
@mark.parametrize('controller', [
    'active'
])
def test_egress_rules(controller, record_property):
    """
    Test custom pod apply and delete
    Args:
        copy_test_apps (str): module fixture
        delete_test_pod: fixture
        controller: test param

    Setups:
        - Copy test files from test server to stx system (module)
        - Delete test pod if already exists on system

    Test Steps:
        - ssh to given controller
        - kubectl apply custom pod yaml and verify custom pod is added to
            both controllers (if applicable)
        - kubectl delete custom pod and verify it is removed from both
            controllers (if applicable)

    """
    host = controller_precheck(controller,)
    record_property("test_case_id", "3.4.2")
    record_property("test_case_description", "Verify the Egress rule for Egress Network Policies")
    record_property("kubernetes", True)
    source_path = "utils/test_files/{}".format(filename)
    home_dir = HostLinuxUser.get_home()
    common.scp_from_localhost_to_active_controller(
        source_path, dest_path=home_dir)
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        kube_helper.exec_kube_cmd(
        sub_cmd="create -f {}".format(filename))
        LOG.tc_step("Creating pods and the network policy to test the egress policy")


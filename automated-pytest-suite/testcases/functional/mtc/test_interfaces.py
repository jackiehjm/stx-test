#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, skip

from utils.tis_log import LOG
from consts.reasons import SkipSysType
from keywords import host_helper, system_helper, vm_helper, network_helper, \
    kube_helper,system_interface

@mark.platform_sanity
def test_system_health(record_property):
   """
   Verify swact active controller

   Test Steps:
       - Swact active controller
       - Verify standby controller and active controller are swapped
       - Verify nodes are ready in kubectl get nodes

   """
   record_property("test_case_id", "3.2.38")
   record_property("test_case_description", "Verify system health after deployment")

   if system_helper.is_aio_simplex():
       skip("Simplex system detected")

   LOG.tc_step('Verify system health after deployment')

   LOG.tc_step("Verify system health after deployment")
   system_interface.get_system_health()

   LOG.tc_step("Verify system health after deployment")



@mark.platform_sanity
def test_controller_interfaces(record_property):
   record_property("test_case_id", "3.2.30")
   record_property("test_case_description", "Verify system interfaces")
   if system_helper.is_aio_simplex():
       skip("Simplex system detected")
   LOG.tc_step('Verify system interfaces')
   rc,msg = system_interface.get_host_interfaces()
   LOG.tc_step("Verify system interfaces")
   LOG.tc_step(msg)
   assert rc


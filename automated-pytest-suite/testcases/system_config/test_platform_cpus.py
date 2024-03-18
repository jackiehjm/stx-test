#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from pytest import mark, skip

from utils.tis_log import LOG
from consts.reasons import SkipSysType
from keywords import host_helper, system_helper, vm_helper, network_helper, \
    kube_helper,system_interface,config_helper

@mark.test_case_id(100)
@mark.test_case_description("Check cpus assigned to the platform")
@mark.platform_sanity
def test_host_cpus(record_property):
   record_property("test_case_id", "3.2.12")
   record_property("test_case_description", "Check the cpus assigned to the platform")
   if system_helper.is_aio_simplex():
       skip("Simplex system detected")
   LOG.tc_step('Check the cpus assigned to the platform')
   config_helper.check_assigned_platform_controller_cpus()
   config_helper.check_assigned_platform_worker_cpus()
   LOG.tc_step("Check the cpus assigned to the platform")

@mark.test_case_id(100)
@mark.test_case_description("Check the memory assigned to the platform")
@mark.platform_sanity
def test_host_memory(record_property):
   record_property("test_case_id", "3.2.13")
   record_property("test_case_description", "Validate the Memory consumed by the Cloud Infrastructure overhead on a controller/worker")
   if system_helper.is_aio_simplex():
       skip("Simplex system detected")
   LOG.tc_step('Check the cpus assigned to the platform')
   config_helper.check_assigned_platform_controller_mem()
   config_helper.check_assigned_platform_worker_mem()
   LOG.tc_step("Validate the Memory consumed by the Cloud Infrastructure overhead on a controller/worker")


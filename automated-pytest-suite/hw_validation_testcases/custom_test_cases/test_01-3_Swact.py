from pytest import fixture, mark, skip
from utils.tis_log import LOG
from utils import cli
from keywords import host_helper, system_helper
from consts.auth import  Tenant
import time

@mark.hw_validation
def test_1_3_swact(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    host = system_helper.get_active_controller_name()
    first_active = host
    first_standby = system_helper.get_standby_controller_name()
    LOG.tc_step("First Active is "+ first_active)
    LOG.tc_step("First Standby is "+ first_standby)
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Issuing swact command")
        con_ssh.exec_cmd("system host-swact "+host)
        time.sleep(60)
    return first_active 

@mark.hw_validation
def test_1_3_swact_back(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    host = system_helper.get_active_controller_name()
    second_active = host
    second_standby = system_helper.get_standby_controller_name()
    LOG.tc_step("Second Active is "+ second_active)
    LOG.tc_step("Second Standby is "+ second_standby)
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        con_ssh.exec_cmd("system host-show controller-0 | grep Controller")
        con_ssh.exec_cmd("system host-show controller-1 | grep Controller")
        LOG.tc_step("Issuing swact command")
        con_ssh.exec_cmd("system host-swact "+host)
        time.sleep(120)
    return second_standby

@mark.hw_validation
def compare(test_1_3_swact, test_1_3_swact_back):
    host = system_helper.get_active_controller_name()
    LOG.tc_step("Retrieving active controller")

    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        if system_helper.is_aio_simplex():
            skip("Simplex system detected")    
        assert (test_1_3_swact == test_1_3_swact_back), "Swact failed"

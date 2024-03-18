from pytest import fixture, mark, skip
from utils.tis_log import LOG
from utils import cli
from keywords import host_helper, system_helper
from consts.auth import  Tenant
import time

@mark.hw_validation
def test_1_5_Power_Off_Host(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    host = system_helper.get_active_controller_name()
    
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Querying Node Sensor Status")
        standby = system_helper.get_standby_controller_name() 
        con_ssh.exec_cmd("system host-lock " + standby) 
        time.sleep(120)
        con_ssh.exec_cmd("system host-power-off " + standby)
        time.sleep(120)
        code, output = con_ssh.exec_cmd("system host-list")
        time.sleep(5)
        con_ssh.exec_cmd("system host-power-on " + standby)
        time.sleep(900)
        code, output_2 = con_ssh.exec_cmd("system host-list")
        time.sleep(5)
        con_ssh.exec_cmd("system host-unlock " + standby) 
        time.sleep(1020)
        cod, output_3 = con_ssh.exec_cmd("system host-list") 
        time.sleep(5)
        rows = output_3.split("\n")        
        LOG.info("Returning Rows")
        assert ("power-off" in output), "Test Failed"
        assert ("online" in output_2), "Test Failed"
        assert ("available" in rows[4]), "Test Failed"

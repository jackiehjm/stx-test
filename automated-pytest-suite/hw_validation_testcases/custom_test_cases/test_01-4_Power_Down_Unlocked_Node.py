from pytest import fixture, mark, skip
from utils.tis_log import LOG
from utils import cli
from keywords import host_helper, system_helper
from consts.auth import  Tenant

@mark.hw_validation
def test_1_4_Power_Down_Unlocked_Node(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Attempting to Power Off")
        code, output = con_ssh.exec_cmd("system host-power-off controller-0") 
        rows = output.split("\n")        
        LOG.info("Returning Rows")
        if system_helper.is_aio_duplex():
          code, output_2 = con_ssh.exec_cmd("system host-power-off controller-1") 
          rows_2 = output.split("\n")  
          assert ("Can not 'Power-Off'" in output_2), "Test Failed"
        LOG.info("Returning Rows")
        assert ("Can not 'Power-Off'" in output), "Test Failed"

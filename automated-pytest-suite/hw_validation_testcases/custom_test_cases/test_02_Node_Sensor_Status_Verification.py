from pytest import fixture, mark, skip
from utils.tis_log import LOG
from utils import cli
from keywords import host_helper, system_helper
from consts.auth import  Tenant

@mark.hw_validation
def test_02_Node_Sensor_Status_Verification(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Querying Node Sensor Status")
        code, output = con_ssh.exec_cmd("system host-sensor-list "+host)
        rows = output.split("\n")
        assert (len(rows) >= 3), "Interaction with BMC Interfaces Failed"


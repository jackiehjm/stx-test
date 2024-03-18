from pytest import fixture, mark, skip
from utils import cli, table_parser
from consts.timeout import HostTimeout
from consts.stx import HostAvailState, Prompt
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import HostLinuxUser, Tenant
import yaml
import time

@mark.hw_validation
def test_05_Node_Sensor_Status_Verification(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Sending Files")
        home_dir = HostLinuxUser.get_home()
        cnifile = "utils/test_files/Test5_cni-test.yaml"
        cnitest = "utils/test_files/Test5_cni-test.py"

        common.scp_from_localhost_to_active_controller(source_path= cnifile, dest_path=home_dir)
        common.scp_from_localhost_to_active_controller(source_path= cnitest, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl apply -f Test5_cni-test.yaml")
        time.sleep(5)

        LOG.tc_step("Pinging Pods From Each Other")
        ping_output = "bytes from"
        Ping = 'None'
        code, output = con_ssh.exec_cmd("python3 Test5_cni-test.py")
        if ping_output in str(output):
            LOG.info("Ping Succesful")
            Ping = 'Succesful'
        time.sleep(20)

        LOG.tc_step("Removing Files")
        con_ssh.exec_cmd("kubectl delete -f Test5_cni-test.yaml")
        con_ssh.exec_cmd("rm Test5_cni-test.py")
        con_ssh.exec_cmd("rm Test5_cni-test.yaml")
        assert ('Succesful' in Ping), "No Ping Generated"

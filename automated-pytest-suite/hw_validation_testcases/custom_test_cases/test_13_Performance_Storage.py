import yaml
import time
import pytest
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant

hosts=system_helper.get_hypervisors(operational="enabled", availability="available")

@mark.hw_validation
@mark.parametrize('host', hosts)
def test_storage_performance(host, request):
    LOG.tc_step("Checking system health")
    output, _ = system_helper.get_system_health_query()

    LOG.tc_step("Retrieving Active Controller")
    active_ctrl=system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=active_ctrl) as con_ssh:
        home_dir = HostLinuxUser.get_home()
        Test13_yaml = "utils/test_files/Test13_pv.yaml"
        LOG.tc_step("Finding SR-IOV capable interfaces")
        common.scp_from_localhost_to_active_controller(source_path= Test13_yaml, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl apply -f ./Test13_pv.yaml")
        LOG.info("Waiting for Persistent Volume to Create")
        con_ssh.exec_sudo_cmd("docker pull joshuarobinson/fio:3.26  ")
        LOG.info("Pulling Image")
        time.sleep(60)

        LOG.info("Generating read operations for OS drive")
        fiotest = "utils/test_files/Test13_fio.py"
        common.scp_from_localhost_to_active_controller(source_path= fiotest, dest_path=home_dir)
        code, output = con_ssh.exec_cmd("python3 Test13_fio.py")
        final_output = output.strip().split('\n')
        LOG.tc_step("Read IOPS is: " + final_output[0])
        LOG.tc_step("Write IOPS is: " + final_output[1])
        read = float(final_output[0])
        write = float(final_output[1])
        assert (read  >= 6.0), "Read IOPS not above 6K"
        assert (write >= 1.5), "Write IOPS not above 1.5 K"
        con_ssh.exec_cmd("kubectl delete -f Test13_pv.yaml")
        con_ssh.exec_sudo_cmd("docker container prune -f")

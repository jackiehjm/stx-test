import yaml
import time
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant

@mark.hw_validation
def flex_ran_6cell(request):
    if system_helper.is_aio_duplex():
        host = system_helper.get_standby_controller_name()
    else:
        host = system_helper.get_active_controller_name()
    active = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=active) as con_ssh:
        LOG.info("Preparing CPUs and Memory")
        '''
        host_helper.lock_host(host)
        con_ssh.exec_cmd("system host-cpu-modify -f application-isolated -p0 36 controller-0")
        con_ssh.exec_cmd("system host-memory-modify controller-0 0 -1G 7")
        time.sleep(5)
        host_helper.unlock_host(host)
        time.sleep(35)
        '''
@mark.hw_validation
def test_14_2_part2(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        con_ssh.exec_sudo_cmd("cpupower frequency-set -u 2500000")
        FlexRAN = "utils/test_files/Test_14_FlexRAN.py"
        home_dir = HostLinuxUser.get_home()
        common.scp_from_localhost_to_active_controller(source_path= FlexRAN, dest_path=home_dir)
        FlexRAN_yaml = "utils/test_files/Test_14_FlexRAN.yaml"
        common.scp_from_localhost_to_active_controller(source_path= FlexRAN_yaml, dest_path=home_dir)
        time.sleep(5)
        con_ssh.exec_cmd("kubectl create -f Test_14_FlexRAN.yaml")       
        time.sleep(30)
        con_ssh.exec_cmd("python3 Test_14_FlexRAN.py")
        time.sleep(20)
        LOG.tc_step("Executing Two Processes")
        Two_ssh = "utils/test_files/Test_14-2_two_ssh.py"
        common.scp_from_localhost_to_active_controller(source_path= Two_ssh, dest_path=home_dir)
        con_ssh.exec_cmd("python3 Test_14-2_two_ssh.py")
        con_ssh.exec_cmd("kubectl cp fl0:/opt/FlexRAN/bin/nr5g/gnb/l1/l1_mlog_stats.txt Test14-2-l1_mlog_stats.txt")

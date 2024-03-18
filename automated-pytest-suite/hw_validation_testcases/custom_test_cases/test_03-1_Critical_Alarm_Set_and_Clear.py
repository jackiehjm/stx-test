import time
import re
from pytest import mark
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant
from utils import cli, table_parser
from consts.stx import Prompt
from consts.timeout import HostTimeout
from consts.stx import HostAvailState

@mark.hw_validation
def test_alarm_generation(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        active, standby =  system_helper.get_active_standby_controllers()
        home_dir = HostLinuxUser.get_home()
        LOG.tc_step("Verifying Minor Alarm Generation")
        LOG.info("Generating minor alarm")
        standby_host = system_helper.get_standby_controller_name()
        Stress_CPU = "utils/test_files/Test3-1_stress-cpu.yaml"
        LOG.tc_step("Finding SR-IOV capable interfaces")
        common.scp_from_localhost_to_active_controller(source_path= Stress_CPU, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl apply -f Test3-1_stress-cpu.yaml -n kube-system ")
        filesystem_alarm = "Platform CPU threshold exceeded"
        LOG.info("Waiting for Alarm to show")
        time.sleep(300)
        for i in range(60):
            if filesystem_alarm in str(system_helper.get_alarms_table()):
                alarm_present = 'CPU'
                break
            else:
                time.sleep(5)
        LOG.info("Deleting Pod")
        con_ssh.exec_cmd("kubectl delete -f Test3-1_stress-cpu.yaml -n kube-system")

        LOG.info("Waiting for the File System alarm to clear")
        time.sleep(180)
        for i in range(60):
            if filesystem_alarm in str(system_helper.get_alarms_table()):
                time.sleep(5)
            else:
                break
        con_ssh.exec_cmd("rm Test3-1_stress-cpu.yaml")
        assert ('CPU' in alarm_present), "No Alarm Generated" 

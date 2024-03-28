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
@mark.flaky(reruns=3)
def test_3_2_memory_alarm_set_and_clear(request):
    alarm_present = 'none'
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.info("Generating minor alarm")
        standby_host = system_helper.get_standby_controller_name()
        home_dir = HostLinuxUser.get_home()
        Stress = "utils/test_files/Test3-2_stress-memory.py"
        common.scp_from_localhost_to_active_controller(source_path= Stress, dest_path=home_dir)
        time.sleep(3)

        filesystem_alarm = "Memory threshold exceeded"
        alarm_present = 'None'
        code, output = con_ssh.exec_cmd("python3 Test3-2_stress-memory.py")
        LOG.tc_step("Output equals " + str(output))
        LOG.info("Checking if Alarm was generated")
        if filesystem_alarm in str(output):
            LOG.info("Alarm Generated Pytest")
            alarm_present = 'Memory' 
        LOG.info("Waiting for the File System alarm to clear")
        code, output = con_ssh.exec_sudo_cmd("docker images | grep stress | awk '{print $3}'")
        con_ssh.exec_sudo_cmd("docker image rm " + str(output) + " -f")
        for i in range(60):
            if filesystem_alarm in str(system_helper.get_alarms_table()):
                time.sleep(5)
            else:
                break
        con_ssh.exec_cmd("rm Test3-2_stress-memory.py")
        assert ('Memory' in alarm_present), "No Alarm Generated"

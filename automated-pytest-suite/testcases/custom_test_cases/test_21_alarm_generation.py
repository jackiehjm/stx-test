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

@mark.caas
def test_alarm_generation(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        if system_helper.get_alarms_table():
            LOG.error( "There are already alarms present in the system")
        active, standby =  system_helper.get_active_standby_controllers()
        LOG.tc_step("Verifying Minor Alarm Generation")
        LOG.info("Generating minor alarm")
        standby_host = system_helper.get_standby_controller_name()
        command = "fmClientCli -c 'clear###200.013###set###host###host={}###2019-10-14 02:28:09.5432###minor###'ntpd' " \
                  "process has failed###communication###not-applicable###Lock and then Unlock host to recover. Avoid " \
                  "using ‘Force Lock’ action as that will impact compute services running on this host. If lock " \
                  "action fails then contact next level of support to investigate and " \
                  "recover.###False###True###False###'".format(standby_host)
        _, output = con_ssh.exec_cmd(command)
        time.sleep(2)
        output = system_helper.get_alarms_table()
        assert "minor" in str(output), "Minor alarm generation failed"
        table_ = table_parser.table(cli.fm('alarm-list "--uuid" --query alarm_id=200.013', ssh_client=con_ssh,
                                           auth_info=Tenant.get('admin_platform'))[1])
        value = table_parser.get_values(table_, target_header="UUID")[0]
        LOG.info("Clearing the minor alarm")
        cli.fm('alarm-delete {}'.format(value), ssh_client=con_ssh, auth_info=Tenant.get('admin_platform'))       
        assert "ntpd process has failed" not in str(system_helper.get_alarms_table()), "Minor alarm failed to clear" 
        
        LOG.tc_step("Verifying Major and Critical alarms generation in the system")
        LOG.info("Getting size of the /boot directory")
        boot_disk_size_info = con_ssh.exec_cmd("df -kh /boot")
        disk_size_pattern = re.compile(r'(\d+)[A-Z]\s+(\d+)[A-Z]\s+(\d+)[A-Z]\s+(\d+)%\s+\/boot')
        LOG.info("boot_disk_size_info is {}".format(boot_disk_size_info))
        disk_size_matcher = disk_size_pattern.search(boot_disk_size_info[1])
        _, _, avail, _ = disk_size_matcher.groups()

        LOG.info("Creating a file such that disk usage goes above threshold value of 80%")
        avail_size = int(avail)
        filesize = int(0.90 * avail_size)
        request.addfinalizer(lambda: con_ssh.exec_sudo_cmd(cmd="rm -rf /boot/testfile"))
        con_ssh.exec_sudo_cmd("dd if=/dev/zero of=/boot/testfile bs={}M count=1".format(filesize))
        filesystem_alarm = "File System threshold exceeded"
        LOG.info("Waiting for 'File System threshold exceeded' alarm to appear")
        for i in range(60):
            if filesystem_alarm in str(system_helper.get_alarms_table()):
                break
            else:
                time.sleep(2)
        assert "major" and filesystem_alarm in str(system_helper.get_alarms_table()), "Major alarm generation failed"
        LOG.info("Deleting 'testfile'")
        con_ssh.exec_sudo_cmd("rm -rf /boot/testfile")
                
        LOG.info("Waiting for the File System alarm to clear")
        for i in range(60):
            if filesystem_alarm in str(system_helper.get_alarms_table()):
                time.sleep(2)
            else:
                break

        LOG.info("Creating a file such that disk usage goes above threshold value of 90%")
        filesize = int(0.98 * avail_size)
        request.addfinalizer(lambda: con_ssh.exec_sudo_cmd(cmd="rm -rf /boot/testfile"))
        con_ssh.exec_sudo_cmd("dd if=/dev/zero of=/boot/testfile bs={}M count=1".format(filesize))
        LOG.info("Waiting for 'File System threshold exceeded' alarm to appear")
        for i in range(60):
            if filesystem_alarm in str(system_helper.get_alarms_table()):
                break
            else:
                time.sleep(2)
        assert "critical" and filesystem_alarm in str(
            system_helper.get_alarms_table()), "Critical alarm generation failed"
        LOG.info("Deleting 'testfile'")
        con_ssh.exec_sudo_cmd("rm -rf /boot/testfile")

        LOG.info("Waiting for the File System alarm to clear")
        for i in range(60):
            if filesystem_alarm in str(system_helper.get_alarms_table()):
                time.sleep(2)
            else:
                break

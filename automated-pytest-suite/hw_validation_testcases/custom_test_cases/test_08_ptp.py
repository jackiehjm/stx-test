import yaml
import time
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant
from consts.proj_vars import ProjVar

HWV_CONFIG = ProjVar.get_var('HWV_CONFIG')
PTP_NIC_C0 = HWV_CONFIG['ptp_nic_c0']

def check_skip():
    if system_helper.is_aio_duplex():
        skip("Duplex system detected")
    if PTP_NIC_C0 == "NoNIC":
        skip("No NIC configured for PTP")
    if PTP_NIC_C0 == "NoGM":
        skip("No PTP Grand Master available")

@mark.hw_validation
def test_ptp_slave(request):
    check_skip()

    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.info("Preparing PTP Interfaces")
        home_dir = HostLinuxUser.get_home()
        PTP_Test = "utils/test_files/Test8_ptp.sh"
        common.scp_from_localhost_to_active_controller(source_path=PTP_Test, dest_path=home_dir)
        time.sleep(5)

        host_helper.lock_host(host)
        time.sleep(5)

        con_ssh.exec_cmd("chmod +x Test8_ptp.sh")
        con_ssh.exec_cmd("./Test8_ptp.sh")

        LOG.info("Unlocking Host")
        host_helper.unlock_host(host)
        time.sleep(20)

@mark.hw_validation
def test_ptp_gm_present(request):
    check_skip()

    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:

        gm = con_ssh.exec_sudo_cmd("pmc -u -b 0 -d 0 -f /etc/linuxptp/ptpinstance/ptp4l-ptpinst1.conf 'GET TIME_STATUS_NP' |grep gmPresent")
        state = con_ssh.exec_sudo_cmd("pmc -u -b 0 -d 0 -f /etc/linuxptp/ptpinstance/ptp4l-ptpinst1.conf 'GET PORT_DATA_SET' |grep portState")
        ClockClass = con_ssh.exec_sudo_cmd("pmc -u -b 0 -d 0 -f /etc/linuxptp/ptpinstance/ptp4l-ptpinst1.conf 'GET PARENT_DATA_SET' | grep gm.ClockClass")
        con_ssh.exec_cmd("rm Test8_ptp.sh")

        assert ("gmPresent                  true" in gm), "Test Failed"

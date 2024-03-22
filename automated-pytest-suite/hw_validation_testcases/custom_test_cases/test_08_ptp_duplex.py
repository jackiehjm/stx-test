import yaml
import time
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import HostLinuxUser, Tenant
from consts.proj_vars import ProjVar

HWV_CONFIG = ProjVar.get_var('HWV_CONFIG')
PTP_NIC_C0 = HWV_CONFIG['ptp_nic_c0']
PTP_NIC_C1 = HWV_CONFIG['ptp_nic_c1']

PTP_C0 = "controller-0"
PTP_C1 = "controller-1"

@mark.hw_validation
def test_ptp_swact_c0(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    active, standby = system_helper.get_active_standby_controllers()
    if active == PTP_C0:
        host_helper.swact_host(PTP_C0)
        time.sleep(120)

@mark.hw_validation
def test_ptp_gm(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    kube_helper.wait_for_nodes_ready(timeout=30)
    with host_helper.ssh_to_host(hostname=PTP_C1) as con_ssh:
        LOG.info("Preparing PTP Grand Master")
        host_helper.lock_host(PTP_C0, check_cpe_alarm=False)
        home_dir = HostLinuxUser.get_home()
        PTP_gm = "utils/test_files/Test8_ptp_gm.sh"
        common.scp_from_localhost_to_active_controller(source_path=PTP_gm, dest_path=home_dir)
        time.sleep(5)
        con_ssh.exec_cmd("chmod +x Test8_ptp_gm.sh")
        con_ssh.exec_cmd("./Test8_ptp_gm.sh %s %s" % (PTP_C0, PTP_NIC_C0))

    host_helper.unlock_host(PTP_C0, check_containers=False)
    
@mark.hw_validation
def test_ptp_swact_c1(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    host_helper.swact_host(PTP_C1)
    time.sleep(120)

@mark.hw_validation
def test_ptp_slave(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    kube_helper.wait_for_nodes_ready(timeout=30)
    with host_helper.ssh_to_host(hostname=PTP_C0) as con_ssh:
        LOG.info("Preparing PTP Slave")
        host_helper.lock_host(PTP_C1, check_cpe_alarm=False)
        home_dir = HostLinuxUser.get_home()
        PTP_slave = "utils/test_files/Test8_ptp_slave.sh"
        common.scp_from_localhost_to_active_controller(source_path=PTP_slave, dest_path=home_dir)
        time.sleep(5)
        con_ssh.exec_cmd("chmod +x Test8_ptp_slave.sh")
        con_ssh.exec_cmd("./Test8_ptp_slave.sh %s %s" % (PTP_C1, PTP_NIC_C1))
        time.sleep(120)

    host_helper.unlock_host(PTP_C1, check_containers=False)

@mark.hw_validation
def test_ptp_gm_present(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    with host_helper.ssh_to_host(hostname=PTP_C1) as con_ssh:
        gm = con_ssh.exec_sudo_cmd("pmc -u -b 0 -d 0 -f /etc/linuxptp/ptpinstance/ptp4l-ptpinst1.conf 'GET TIME_STATUS_NP' |grep gmPresent")
        state = con_ssh.exec_sudo_cmd("pmc -u -b 0 -d 0 -f /etc/linuxptp/ptpinstance/ptp4l-ptpinst1.conf 'GET PORT_DATA_SET' |grep portState")
        ClockClass = con_ssh.exec_sudo_cmd("pmc -u -b 0 -d 0 -f /etc/linuxptp/ptpinstance/ptp4l-ptpinst1.conf 'GET PARENT_DATA_SET' | grep gm.ClockClass")
        con_ssh.exec_cmd("rm Test8_ptp_*")
        assert ("gmPresent                  true" in gm), "Test Failed"

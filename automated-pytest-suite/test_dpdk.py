import pytest
import time
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant
from utils import cli
import subprocess

@mark.hw_validation
def get_dpdk_interfaces(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh: 
        LOG.tc_step("Preparing Interfaces and Pods")
        home_dir = HostLinuxUser.get_home()
        #host_helper.lock_host(host)
        pktgen = "utils/test_files/Test10_dpdk-pktgen-vfio.yaml"
        testpmd = "utils/test_files/Test10_dpdk-testpmd-vfio.yaml" 
        #Iperf_Test = "utils/test_files/Test9_iperf3.py" 
        Interfaces = "utils/test_files/Test9_Find_Interfaces.py"
        LOG.tc_step("Finding SR-IOV capable interfaces")
        common.scp_from_localhost_to_active_controller(source_path= Interfaces, dest_path=home_dir)
        code, output = con_ssh.exec_cmd("python3 Test9_Find_Interfaces.py")
        rows = output.strip().split('\n')
        LOG.tc_step("Code equals " + str(code))
        LOG.tc_step("Output equals " + str(output))
        LOG.tc_step("Rows[0] equals " + rows[0])
        LOG.tc_step("Rows[1] equals " + rows[1])
        """con_ssh.exec_cmd("system datanetwork-add physnet4 vlan")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov4 -c pci-sriov -N 12 controller-0 " + rows[0] + " --vf-driver=vfio")
        con_ssh.exec_cmd("system host-if-add -c pci-sriov controller-0 sriov04 vf sriov4 -N 5 --vf-driver=vfio")
        con_ssh.exec_cmd("system interface-datanetwork-assign controller-0 sriov04 physnet4")
        con_ssh.exec_cmd("system host-memory-modify controller-0 -1G 10 0")
        con_ssh.exec_cmd("system datanetwork-add physnet5 vlan")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov5 -c pci-sriov -N 12 controller-0 " + rows[1] + " --vf-driver=vfio")
        con_ssh.exec_cmd("system host-if-add -c pci-sriov controller-0 sriov05 vf sriov5 -N 5 --vf-driver=vfio")
        con_ssh.exec_cmd("system interface-datanetwork-assign controller-0 sriov05 physnet5")
        con_ssh.exec_cmd("system host-label-assign controller-0 sriovdp=enabled")
        con_ssh.exec_cmd("system host-label-assign controller-0 kube-cpu-mgr-policy=static")
        con_ssh.exec_cmd("system host-cpu-modify -f application-isolated -p0 16 controller-0")
        host_helper.unlock_host(host)
        time.sleep(20)
        common.scp_from_localhost_to_active_controller(source_path= pktgen, dest_path=home_dir)
        """
        con_ssh.exec_cmd("kubectl create -f Test10_dpdk-pktgen-vfio.yaml")
        time.sleep(10)
        #common.scp_from_localhost_to_active_controller(source_path= testpmd, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl create -f Test10_dpdk-testpmd-vfio.yaml")
        time.sleep(10)
        LOG.tc_step("Getting PCI Devices")
        code, output = con_ssh.exec_cmd("kubectl exec -it dpdk-pktgen -- env|grep PCI | cut -d '=' -f2")
        pktgen = output
        code, output = con_ssh.exec_cmd("kubectl exec -it dpdk-testpmd -- env|grep PCI | cut -d '=' -f2")
        testpmd = output
        LOG.tc_step("pktgen equals: " + pktgen)
        LOG.tc_step("testpmd equals: " + testpmd) 
        code, output = con_ssh.exec_cmd("ls /sys/class/net/" + rows[0] + "/device/driver/")
        card1 = output.strip().split('  ')
        LOG.tc_step("Output equals " + str(output))
        LOG.tc_step("card1[0] equals " + card1[0])
        LOG.tc_step("card1 equals " + card1)
        code, output = con_ssh.exec_cmd("ls /sys/class/net/" + rows[1] + "/device/driver/")
        card2 = output.strip().split('  ')
        LOG.tc_step("Output equals " + str(output))
        LOG.tc_step("card2[0] equals " + card2[0])
        LOG.tc_step("card2 equals " + card2)

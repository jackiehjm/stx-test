import yaml
import time
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant

@mark.hw_validation
def test_04_PV_creation(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.info("Sending files")
        home_dir = HostLinuxUser.get_home()
        con_ssh.exec_sudo_cmd("mkdir /mnt/data")
        con_ssh.exec_sudo_cmd("sh -c \"echo 'persistent file' > /mnt/data/index.html\"")
        con_ssh.exec_sudo_cmd("sh -c \"echo 'TEST PASSED' >> /mnt/data/index.html\"")
        volume = "utils/test_files/Test4_pv-volume.yaml"
        common.scp_from_localhost_to_active_controller(source_path= volume, dest_path=home_dir)
        claim = "utils/test_files/Test4_pv-claim.yaml"
        common.scp_from_localhost_to_active_controller(source_path= claim, dest_path=home_dir)
        pod = "utils/test_files/Test4_pv-pod.yaml"
        common.scp_from_localhost_to_active_controller(source_path= pod, dest_path=home_dir)

        LOG.info("Starting Test")
        con_ssh.exec_cmd("kubectl apply -f Test4_pv-volume.yaml")
        con_ssh.exec_cmd("kubectl apply -f Test4_pv-claim.yaml")
        con_ssh.exec_cmd("kubectl apply -f Test4_pv-pod.yaml")
        time.sleep(60)
        con_ssh.exec_cmd("kubectl get pv task-pv-volume")
        con_ssh.exec_cmd("kubectl get pvc task-pv-claim")
        con_ssh.exec_cmd("kubectl get pod task-pv-pod")
        code, output = con_ssh.exec_cmd("kubectl exec -it task-pv-pod -- /bin/bash -c \"apt update;apt install curl;curl http://localhost/\"")

        con_ssh.exec_cmd("kubectl delete -f Test4_pv-pod.yaml")
        con_ssh.exec_cmd("kubectl delete -f Test4_pv-claim.yaml")
        con_ssh.exec_cmd("kubectl delete -f Test4_pv-volume.yaml")
        con_ssh.exec_cmd("rm Test4_pv-volume.yaml")
        con_ssh.exec_cmd("rm Test4_pv-claim.yaml")
        con_ssh.exec_cmd("rm Test4_pv-pod.yaml")
        con_ssh.exec_sudo_cmd("rm -r /mnt/data")
        assert ('PASSED' in output), "Test Failed"

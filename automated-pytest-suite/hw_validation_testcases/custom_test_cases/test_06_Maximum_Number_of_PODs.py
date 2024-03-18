import yaml
import time
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant

@mark.hw_validation
def test_maximum_number_of_pods_on_node(request):
    host = system_helper.get_active_controller_name()
    LOG.tc_step("Retrieving active controller")

    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        home_dir = HostLinuxUser.get_home()
        simple = "utils/test_files/Test6_simple.yaml"
        common.scp_from_localhost_to_active_controller(source_path= simple, dest_path=home_dir)
        con_ssh.exec_cmd("for i in {1..110};do kubectl create namespace test-$i;done ")
        LOG.info("Waiting for Namespaces to Create")
        time.sleep(60)

        con_ssh.exec_cmd("for i in {1..110};do kubectl create -f Test6_simple.yaml -n test-$i;done")
        LOG.info("Waiting for Pods to Create")
        time.sleep(60)

        pod_number = con_ssh.exec_cmd("kubectl get pods --all-namespaces -o wide|grep -v Completed|grep -v Pending|grep -v OutOfpods|grep -v NAME|grep -v 'controller-1'|wc -l")
        con_ssh.exec_cmd("for i in {1..110};do kubectl delete pods simple -n test-$i & done")
        LOG.info("Waiting for Pods to Delete")        
        time.sleep(180)

        con_ssh.exec_cmd("for i in {1..110};do kubectl delete namespace test-$i & done")
        LOG.info("Waiting for Namespaces to Delete")        
        time.sleep(60)

        con_ssh.exec_cmd("rm Test6_simple.yaml")
        assert int(pod_number[1]) >= 110, "Test Failed"
        LOG.info("Test Passed")

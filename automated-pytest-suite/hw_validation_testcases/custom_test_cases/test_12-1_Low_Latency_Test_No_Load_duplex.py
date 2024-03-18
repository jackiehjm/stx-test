from pytest import fixture, mark, skip
from consts.auth import Tenant
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
import time
from utils import cli
import re
import yaml

@mark.hw_validation
def test_low_latency_with_no_load(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    LOG.tc_step("Retrieving the active controller")
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        standby = system_helper.get_standby_controller_name()
        host_helper.lock_host(standby)
        con_ssh.exec_cmd("system host-memory-modify" + standby + "0 -f application -1G 8")
        con_ssh.exec_cmd("system host-label-assign" + standby + "kube-cpu-mgr-policy=static")
        con_ssh.exec_cmd("system host-label-assign" + standby + "kube-topology-mgr-policy=restricted")
        con_ssh.exec_cmd("system host-cpu-modify -f application-isolated -p0 18" + standby)
        host_helper.unlock_host(standby)
        LOG.tc_step("Issuing swact command")
        con_ssh.exec_cmd("system host-swact "+host)
        time.sleep(120)

@mark.hw_validation
def test_sriov_interfaces(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")    
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        cpu=16
        hugepages=2
        testtime=1440
        yaml_file ="/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/Test12_cyclictest.yaml"
        yaml_dict = common.get_yaml_data(yaml_file)
        pod_name = yaml_dict['metadata']['name']
        yaml_dict["spec"]["nodeName"] = host
        pod_yaml = "yaml_out.yaml"
        with open(pod_yaml, "w+") as file:
            yaml.dump(yaml_dict, file, default_flow_style=False)
        LOG.tc_step('kubectl apply {}, and check {} Pod is created and running'.format(pod_yaml, pod_name))
        assert kube_helper.create_and_verify_pod(request,con_ssh,pod_yaml, pod_name),"Pod {} creation failed".format(pod_name)


        LOG.info("Getting CPU list")
        _,cpu_list = con_ssh.exec_cmd(cmd="kubectl exec cyclictest -- taskset -pc 1 | awk -F' ' '{print $6}'")
        LOG.info("Available CPU are {}".format(cpu_list))

        LOG.tc_step("Running cyclic test for {} mins on 12 threads".format(testtime))
        con_ssh.send("kubectl exec -it {} /bin/bash".format(pod_name))
        try:
            con_ssh.expect(re.compile(r'cyclictest*').pattern, 10)
            LOG.info(" --- Logged in to pod")
        except Exception as err:
            assert False, "Failed to enter to cyclictest pod"

        test_cli = "cyclictest -p99 -n -m -d0 -t 16 -a {}  -D {}m --histofall 12 --histfile testresult".format(cpu_list,testtime)

        con_ssh.send(cmd=test_cli)
        time.sleep((testtime+1)*60)
        con_ssh.send(cmd="exit")
        con_ssh.flush()
        time.sleep(10)

        _, ret = con_ssh.exec_cmd(cmd="kubectl exec cyclictest -- cat testresult", get_exit_code=False)
        LOG.tc_step("Validating Max Latency should be less than 20")
        common.validate_cyclictest_out(ret,maxlatency=20)
        con_ssh.exec_cmd("kubectl delete -f Test12_cyclictest.yaml")
        con_ssh.exec_cmd("rm Test12_cyclictest.yaml")

from pytest import fixture, mark, skip
from consts.auth import Tenant
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
import time
from utils import cli
import re
import yaml
import os
from consts.proj_vars import ProjVar

# The test time is 24 hours
#TEST_TIME = 1440
TEST_TIME = 60

@mark.hw_validation
def test_set_prerequisites(request):
    if system_helper.is_aio_duplex():
        skip("Duplex system detected")

    active = system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=active) as con_ssh:
        cpu = 18
        hugepages = 2

        LOG.tc_step("Setting for test prerequisites")
        host_helper.lock_host(active)

        con_ssh.exec_cmd("system host-memory-modify controller-0 0 -f application -1G 8")
        con_ssh.exec_cmd("system host-label-assign controller-0 kube-cpu-mgr-policy=static")
        con_ssh.exec_cmd("system host-label-assign controller-0 kube-topology-mgr-policy=restricted")
        con_ssh.exec_cmd("system host-cpu-modify -f application-isolated -p0 18 controller-0")

        host_helper.unlock_host(active)

        LOG.tc_step("Checking test Prerequisites")
        _, isocpu = cli.system("host-cpu-list {} --nowrap |grep 'Application-isolated' | cut -d '|' -f 6 | awk '$1 == ""0""' |wc -l".format(active))

        assert int(isocpu)>=cpu, "Isolated CPU are less than {}".format(cpu)

        code, mem_list = cli.system("host-memory-list {} --nowrap".format(active, ssh_client=con_ssh))
        org_1G_hp = common.parse_table_to_dict(mem_list, 18, 0, 15)
        LOG.info("{},{}".format(isocpu, org_1G_hp))

        assert int(org_1G_hp["0"])>=hugepages, "avail 1G hugepages are less than {}".format(hugepages)

@mark.hw_validation
def test_cyclictest_pod(request):
    if system_helper.is_aio_duplex():
        skip("Duplex system detected")

    tmp_dir = ProjVar.get_var('TEMP_DIR')
    active = system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=active) as con_ssh:

        yaml_file ="utils/test_files/Test12_cyclictest.yaml"
        yaml_dict = common.get_yaml_data(yaml_file)
        pod_name = yaml_dict['metadata']['name']
        yaml_dict["spec"]["nodeName"] = active 
        yaml_file_output = os.path.join(tmp_dir, "Test12_cyclictest_out.yaml")
        with open(yaml_file_output, "w+") as file:
            yaml.dump(yaml_dict, file, default_flow_style=False)

        LOG.tc_step('kubectl apply {}, and check {} Pod is created and running'.format(yaml_file_output, pod_name))

        assert kube_helper.create_and_verify_pod(request, con_ssh, yaml_file_output, pod_name), "Pod {} creation failed".format(pod_name)

        LOG.info("Getting CPU list")
        _, cpu_list = con_ssh.exec_cmd(cmd="kubectl exec cyclictest -- taskset -pc 1 | awk -F' ' '{print $6}'")
        LOG.info("Available CPU are {}".format(cpu_list))

        LOG.tc_step("Running cyclic test for {} mins on 12 threads".format(TEST_TIME))
        con_ssh.send("kubectl exec -it {} /bin/bash".format(pod_name))
        try:
            con_ssh.expect(re.compile(r'cyclictest*').pattern, 10)
            LOG.info(" --- Logged in to pod")
        except Exception as err:
            assert False, "Failed to enter to cyclictest pod"

        test_cli = "cyclictest -p99 -n -m -d0 -t 16 -a {}  -D {}m --histofall 12 --histfile testresult".format(cpu_list, TEST_TIME)

        con_ssh.send(cmd=test_cli)
        time.sleep((TEST_TIME + 1) * 60)

        con_ssh.send(cmd="exit")
        con_ssh.flush()
        time.sleep(10)

        _, ret = con_ssh.exec_cmd(cmd="kubectl exec cyclictest -- cat testresult", get_exit_code=False)

        LOG.tc_step("Validating Max Latency should be less than 20")
        common.validate_cyclictest_out(ret, maxlatency=20)

        con_ssh.exec_cmd("kubectl delete -f Test12_cyclictest.yaml")
        con_ssh.exec_cmd("rm Test12_cyclictest.yaml")

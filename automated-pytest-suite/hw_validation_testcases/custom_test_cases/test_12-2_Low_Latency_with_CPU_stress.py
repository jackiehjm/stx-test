from pytest import fixture, mark, skip
from consts.auth import Tenant
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
import time
from utils import cli
import re
import yaml

hosts=system_helper.get_hypervisors(operational="enabled", availability="available")

@mark.hw_validation
@mark.parametrize('host', hosts)
def test_low_latency_with_70pect_load(host, request):
    if system_helper.is_aio_duplex():
        skip("Duplex system detected")
    LOG.tc_step("Retrieving active controller")
    active_ctrl=system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=active_ctrl) as con_ssh:
        cpu=16
        hugepages=2
        testtime=1
        LOG.tc_step("Checking test Prerequisites")
        _,isocpu=cli.system("host-cpu-list {} --nowrap |grep 'Application-isolated' | cut -d '|' -f 6 | awk '$1 == ""0""' |wc -l".format(host))
        assert int(isocpu)>=cpu,"Isolated CPU are less than {}".format(cpu)
        code, mem_list = cli.system("host-memory-list {} --nowrap".format((host), ssh_client=con_ssh))
        org_1G_hp=common.parse_table_to_dict(mem_list,18,0,15)
        LOG.info("{},{}".format(isocpu,org_1G_hp))
        assert int(org_1G_hp["0"])>=hugepages,"avail 1G hp are less than {}".format(hugepages)

        yaml_file ="/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/Test12_cyclictest.yaml"
        yaml_dict = common.get_yaml_data(yaml_file)
        pod_name = yaml_dict['metadata']['name']
        yaml_dict["spec"]["nodeName"] = host
        pod_yaml = "yaml_out.yaml"
        with open(pod_yaml, "w+") as file:
            yaml.dump(yaml_dict, file, default_flow_style=False)
        LOG.tc_step('kubectl apply {}, and check {} Pod is created and running'.format(pod_yaml, pod_name))
        assert kube_helper.create_and_verify_pod(request,con_ssh, pod_yaml, pod_name),"Pod {} creation failed".format(pod_name)


        LOG.info("Getting CPU list")
        _,cpu_list = con_ssh.exec_cmd(cmd="kubectl exec cyclictest -- taskset -pc 1 | awk -F' ' '{print $6}'")
        LOG.info("Available CPU are {}".format(cpu_list))

        LOG.tc_step('Creating 70% load on 12 available CPUs'.format(yaml_file, pod_name))
        con_ssh.send("kubectl exec cyclictest -- /bin/bash -c './stress-ng.sh'")
        r=con_ssh.expect(re.compile(r'dispatching hogs:', re.M).pattern)
        assert r==0,"Failed to start stress-ng"


    with host_helper.ssh_to_host(hostname=active_ctrl) as con_ssh:
        LOG.tc_step("Running cyclic test for {} mins on 12 threads".format(testtime))
        con_ssh.send("kubectl exec -it {} /bin/bash".format(pod_name))
        try:
            con_ssh.expect(re.compile(r'cyclictest*').pattern, 10)
            LOG.info(" --- Logged in to pod")
        except Exception as err:
            assert False, "Failed to enter to cyclictest pod"

        test_cli = "cyclictest -p99 -n -m -d0 -t 12 -a {} -D {}m --histofall 12 --histfile testresult".format(cpu_list,testtime)

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

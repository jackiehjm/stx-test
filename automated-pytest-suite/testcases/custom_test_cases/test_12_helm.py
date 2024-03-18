from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, host_helper, system_helper, kube_helper
import os
import time
@mark.caas
def test_helm(request):
    active_controller = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=active_controller) as con_ssh:
        LOG.tc_step("Setting local values for helm deployment")
        tarball = "test-helm.tar.gz"
        name = "test-helm"
        value_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/helm/values.yaml"
        replicas = common.get_yaml_data(value_file)['replicaCount']
        Chart = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/helm/Chart.yaml"
        deployment_name = common.get_yaml_data(Chart)['name']
        common.scp_from_localhost_to_active_controller("/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/helm", dest_path="/home/sysadmin/",is_dir=True)
        for i in range(0, 5):
            fail_ok = True
            exit_code, _ = con_ssh.exec_cmd(cmd="ls -l /home/sysadmin/helm/", fail_ok=fail_ok)
            if exit_code == 0:
                common.tar_untar_file(con_ssh, action="tar", tarname=tarball, dir="helm/")
                break
            else:
                common.scp_from_localhost_to_active_controller("/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/helm", dest_path="/home/sysadmin/",is_dir=True)
                time.sleep(1)
                continue

        request.addfinalizer(lambda: con_ssh.exec_cmd(cmd="rm -rf /home/sysadmin/helm"))
        request.addfinalizer(lambda: con_ssh.exec_cmd(cmd="rm -rf /home/sysadmin/{}".format(tarball)))
        request.addfinalizer(lambda: con_ssh.exec_cmd(cmd="helm delete {}".format(name)))

        LOG.tc_step("Helm installation")
        _, ret = con_ssh.exec_cmd(cmd="helm install {} {}".format(name, tarball))
        LOG.info(ret)
        r = {}
        for i in ret.split("\n"):
            if i == "":
                continue
            LOG.info(i.split(":"))
            r[i.split(":")[0]] = i.split(":")[1].strip()
        assert r.get("STATUS") == "deployed","Helm is not in deployed state"

        LOG.tc_step("Scaling deployments which were deployed via helm")
        kube_helper.check_deployed_pods(deployment_name,replicas=replicas)
        kube_helper.scale_deployment(deployment_name,replicas=5)
        kube_helper.scale_deployment(deployment_name,replicas=1)


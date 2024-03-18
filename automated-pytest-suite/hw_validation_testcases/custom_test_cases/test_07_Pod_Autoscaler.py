import yaml
import time
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant


@mark.hw_validation
def test_maximum_number_of_pods_on_node(request):
    LOG.tc_step("Retrieving active controller")
    active_ctrl=system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=active_ctrl) as con_ssh:
        home_dir = HostLinuxUser.get_home()
        LOG.info("Applying metrics-server")
        code, output = con_ssh.exec_cmd("ls /usr/local/share/applications/helm/metrics-server*")
        rows = output.strip().split('\n')
        start_marker = "/"
        end_marker = ".tgz"
        start_index = rows[0].find(start_marker)
        end_index = rows[0].find(end_marker) + len(end_marker)
        broken_output = rows[0][start_index:end_index]
        LOG.tc_step("Version of metrics-server application version is: " + broken_output)
        con_ssh.exec_cmd("system application-upload " + broken_output)
        time.sleep(30)

        con_ssh.exec_cmd("system application-apply metrics-server")
        time.sleep(30)
        php_apache = "utils/test_files/Test7_php-apache.yaml"
        LOG.tc_step("Deploying php-apache Application")
        common.scp_from_localhost_to_active_controller(source_path= php_apache, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl apply -f Test7_php-apache.yaml")

        LOG.info("Creating Pod Autoscaler")
        time.sleep(5)
        con_ssh.exec_cmd("kubectl autoscale deployment php-apache --cpu-percent=50 --min=1 --max=10")
        LOG.info("Waiting for Autoscaling")
        time.sleep(5)

        con_ssh.exec_cmd("kubectl get hpa")
        LOG.info("Getting HPA")        
        time.sleep(5)

        con_ssh.exec_cmd("kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- /bin/sh -c 'while sleep 0.001; do wget -q -O - http://php-apache & done'")
        LOG.info("Waiting for Autoscaler")        
        time.sleep(300)
        con_ssh.exec_cmd("kubectl get hpa")
        con_ssh.exec_cmd("kubectl get deployment")
        code, output = con_ssh.exec_cmd("kubectl get pod")
        rows = output.strip().split('\n')
        con_ssh.exec_cmd("kubectl delete hpa php-apache")
        con_ssh.exec_cmd("kubectl delete -f Test7_php-apache.yaml")
        con_ssh.exec_cmd("rm -f Test7_php-apache.yaml")
        assert (len(rows) >= 3), "No Replicas Created"
        LOG.info("Test Passed")

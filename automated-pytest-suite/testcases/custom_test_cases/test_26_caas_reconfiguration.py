from pytest import fixture, mark, skip
from utils.tis_log import LOG
from utils import cli
from keywords import common, host_helper, system_helper
from testfixtures.pre_checks_and_configs import no_simplex
import time

@mark.caas
def test_caas_reconfiguration(request,no_simplex):
    active_controller = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=active_controller) as con_ssh:
        worker_host=system_helper.get_hosts(personality="worker")
        controller_host = system_helper.get_standby_controller_name()
        host = controller_host if (len(worker_host) == 0) else worker_host[0]
        request.addfinalizer(lambda: host_helper.unlock_hosts(host,check_hypervisor_up=False))
        LOG.tc_step("Locking {}".format(host))
        host_helper.lock_host(host)
        code, mem_list = cli.system("host-memory-list {} --nowrap".format(host), ssh_client=con_ssh)
        org_1G_hp=common.parse_table_to_dict(mem_list,18,0,15)

        LOG.tc_step("Modifying 1G hp in host:{} from {} to {}".format(host,int(org_1G_hp["0"]),int(org_1G_hp["0"])+1))
        code, mem_list = cli.system("host-memory-modify {} 0 -f application -1G {}".format(host,int(org_1G_hp["0"])+1), ssh_client=con_ssh)
        pending_1G_hp=common.parse_table_to_dict(mem_list,2,0,1)
        assert int(pending_1G_hp["Total Pending"])==int(org_1G_hp["0"])+1

        LOG.tc_step("Unlocking {} to apply new hp".format(host))
        host_helper.unlock_hosts(host,check_hypervisor_up=False)
        time.sleep(60)
        code, new_mem_list = cli.system("host-memory-list {} --nowrap".format(host), ssh_client=con_ssh)
        new_1G_hp = common.parse_table_to_dict(new_mem_list, 18, 0, 15)
        assert int(new_1G_hp["0"])==int(org_1G_hp["0"])+1

        LOG.tc_step("Reverting back 1G hp from:{} to :{}".format(new_1G_hp["0"],org_1G_hp["0"]))
        host_helper.lock_host(host)
        code, mem_list = cli.system("host-memory-modify {} 0 -f application -1G {}".format(host,int(org_1G_hp["0"])), ssh_client=con_ssh)







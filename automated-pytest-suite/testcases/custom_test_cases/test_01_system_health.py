from pytest import fixture, mark, skip
from utils.tis_log import LOG
from utils import cli
from keywords import host_helper, system_helper
from consts.auth import  Tenant

@mark.caas
def test_01_system_health(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Querying System health")
        code, output = cli.system('health-query', ssh_client=con_ssh, auth_info=Tenant.get('admin_platform'))
        status_list=[]
        errorlist=[]
        rows = output.split("\n")
        for item in range(1,len(rows)):
            if ":" in rows[item]:
               res = rows[item].rsplit(': ', 1)
               LOG.info("Response {}".format(res))
               if (len(res) == 2):
                  status_list.append(res[-1])
               elif (res[-1] == '[Fail]'):
                  errorlist.append(rows[item])
            else:
              pass
        status_list = list(filter(None, status_list))
        assert (len(set(status_list)) == 1), "System health status check is not successful"


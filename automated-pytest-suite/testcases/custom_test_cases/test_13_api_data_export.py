from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from utils import cli
from utils.rest import Rest

@mark.caas
def test_API_data():
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        code, host_list = cli.system("host-list --nowrap", ssh_client=con_ssh)
        hosts=common.parse_table_to_dict(host_list,6,1,2)
        LOG.info("Check sysinv REST API")
        sysinv_rest = Rest('sysinv', platform=True,validateSSL=False)
        resource = '/ihosts'
        status_code, resp = sysinv_rest.get(resource=resource, auth=True)
        message = "Retrieved: status_code: {} message: {}"
        LOG.debug(message.format(status_code, resp))

        LOG.info("Check status_code of 200 is received")
        message = "Expected status_code of 200 - received {} and message {}"
        assert status_code == 200, message.format(status_code, resp)
        hosts.pop("hostname")
        api_hosts=[x['hostname'] for x in resp['ihosts']]
        assert set(hosts.keys())==set(api_hosts),"Host names doesn't matches, API response : {}, vs CLI response : {}".format(api_hosts,hosts.keys())
        for node,personality in hosts.items():
            LOG.info("Check if Node {} is having personality: {}".format(node, personality))
            for x in resp['ihosts']:
                if (x['hostname']) == node:
                    assert(x['personality'])==personality,node +"is of type "+x['personality']+" instead of "+personality



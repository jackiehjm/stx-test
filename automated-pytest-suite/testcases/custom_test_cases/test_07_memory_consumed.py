from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from utils import cli

@mark.caas
def test_memory_consumed():
    host=system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        controllers=list(filter(None,system_helper.get_active_standby_controllers(con_ssh=con_ssh)))
        workers=list(filter(None,system_helper.get_hosts(personality="worker")))
        hosts={"controllers":controllers,"workers":workers}
        LOG.info("Hosts present are: {}".format(hosts))
        for personality,items in hosts.items():
            for host in items:
                code, mem_list = cli.system("host-memory-list {} --nowrap".format(host), ssh_client=con_ssh)
                mem_platform_values = common.parse_table_to_dict(mem_list, 18, 0, 2)
                vs_hp_size_values = common.parse_table_to_dict(mem_list, 18, 0, 5)
                LOG.info("On {} host-memory-list values are {} and {}".format(host,mem_platform_values,vs_hp_size_values))
                mem_platform_values.pop('processor')
                for key in mem_platform_values.keys():
                    assert mem_platform_values[key] != 'None', "host-memory-list values for mem_platform(MiB) is None, which should be 8 GB or less"
                    assert vs_hp_size_values[key] != 'None', "host-memory-list values for vs_hp_size(MiB) is None, which should be 1 GB or less"
                    value= 8000 if (personality=="controllers") else 7000
                    assert ((int(mem_platform_values[key]) <=value)  & (int(vs_hp_size_values[key]) <=1024)), \
                        "host-memory-list values for mem_platform(MiB) and vs_hp_size(MiB) didnot match 8+1 (numa) GB RAM or less, obtained values are {} and {}".format(mem_platform_values,vs_hp_size_values)

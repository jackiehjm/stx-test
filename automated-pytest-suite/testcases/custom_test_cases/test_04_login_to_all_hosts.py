from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import host_helper,system_helper

hosts=system_helper.get_hypervisors()

@mark.caas
@mark.parametrize('host',hosts)
def test_login(host):
    LOG.tc_step("Logging into host {} ...".format(host))

    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        _,hostname=con_ssh.exec_cmd("hostname")
        assert hostname==host
        con_ssh.send(cmd='exit')



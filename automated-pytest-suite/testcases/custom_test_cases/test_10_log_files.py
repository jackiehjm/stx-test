from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper, container_helper, keystone_helper

@mark.caas
def test_log_files():
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        mandatory_logs = ['sm.log', 'daemon.log', 'kern.log', 'hbsAgent.log', 'sysinv.log', 'containerd.log',
                          'mtcAgent.log', 'auth.log']
        _,ret=con_ssh.exec_cmd(cmd="cd /var/log;ls -lrt *log |awk '{print $5, $9}'")
        ret=ret.split("\n")
        all_logs=list(filter(None,ret))
        emptyfiles=[]
        logs={}
        for l in all_logs:
            size,name=l.split()
            logs[name]=size
            if int(size)==0 and name in mandatory_logs:
                emptyfiles.append(name)

        LOG.tc_step("Checking for mandatory logs namely {}".format(mandatory_logs))
        assert set(mandatory_logs).issubset(set(logs)) ,"Mandatory log files {} missing".format(set(mandatory_logs).difference(set(logs)))
        assert len(set(mandatory_logs).intersection(emptyfiles))==0, "Empty Files are {}".format(set(mandatory_logs).intersection(emptyfiles))

        LOG.tc_step("Checking for puppet logs")
        _, ret = con_ssh.exec_sudo_cmd("cat /var/log/puppet/latest/puppet.log |wc -l")
        assert int(ret)>0, "puppet logs are not present"


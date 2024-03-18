from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import Tenant,HostLinuxUser
import random

@mark.caas
def test_performance_monitoring(request):
    host=system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Running the cli command on active_controller")
        home_dir = HostLinuxUser.get_home()
        con_ssh.exec_cmd(cmd="mkdir {}/df_files".format(home_dir))

        def create_file_and_check_storage(filename,bs=1024,count=1):
            dd_cmd="dd if=/dev/zero of={}/df_files/{} bs={}M count={}".format(home_dir,filename,bs,count)
            _, ret = con_ssh.exec_cmd(cmd=dd_cmd)
            df_cmd = "df -a"
            _, ret = con_ssh.exec_cmd(cmd=df_cmd)
            list1=common.convert_sshout_to_table(ret)
            m=0
            for i in list1:
                if (i[4].strip("%").isnumeric()) and "sda" in i[0]:
                    r=(int(i[4].strip("%")))
                    m=max(m,r)
            return m

        test_files=[]
        while True:
            filename="test_"+str(random.randint(1,200))+".file"
            test_files.append(filename)
            avail=create_file_and_check_storage(filename)
            LOG.debug(avail)
            if avail>90:
                break

        request.addfinalizer(lambda: con_ssh.exec_cmd(cmd="rm -rf {}/df_files".format(home_dir)))
        _,alarm = system_helper.wait_for_alarm(timeout=300,reason="File System threshold exceeded")
        con_ssh.exec_cmd(cmd="rm -rf {}/df_files".format(home_dir))
        assert system_helper.wait_for_alarm_gone(alarm, timeout=300),"Alarm didn't supressed in 300 sec"


from consts.auth import HostLinuxUser
from keywords.ping_helper import PingTraffic
from keywords import system_helper
from utils.clients.ssh import SSHClient
from utils.tis_log import LOG
from datetime import datetime

def verify_traffic_after_creating_network_policy(kube_command, destination, duration=10, con_ssh=None):
    logfile = "ping.txt"
    ret = ping_check(destination, duration=duration, interval=1, kube_command=kube_command, logfile=logfile, con_ssh=con_ssh)
    username = HostLinuxUser.get_user()
    password = HostLinuxUser.get_password()
    logfile = "/home/{}/{}".format(username, logfile)
    p1 = PingTraffic()
    start_time = datetime.now()
    out_data = p1.get_background_traffic_result(con_ssh, username, password, logfile, pid=ret, start_time=start_time,duration=10)
    return out_data
		
	
def ping_check(destination, duration=10, interval=1, kube_command='',
               logfile=None, con_ssh=None):
    command = "{}  ping {} -w {} -i {} ".format(kube_command, destination, duration, interval)
    ret, ping_pid = run_ping_in_background(command, logfile, duration, con_ssh)
    assert ret, "Ping execution failed"
    return ping_pid

def run_ping_in_background(command, logfile="ping.txt", duration=10, con_ssh=None):
    username = HostLinuxUser.get_user()
    logfile = "/home/{}/{}".format(username, logfile)
    command = "nohup {} >/dev/null 2>&1 > {} & echo $!".format(command, logfile)
    expect_timeout = 60
    ret = con_ssh.exec_cmd(command, expect_timeout)
    LOG.info(ret)
    try:
        pid_list = ret[1].split()[1:]
    except:
        LOG.info("ping execution failed")
        return False, None
    if pid_list[0] == pid_list[1]:
        return True, pid_list[0]
    time.sleep(5)
    return True

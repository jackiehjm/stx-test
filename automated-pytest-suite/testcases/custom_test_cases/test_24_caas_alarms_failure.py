import time

from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser

@mark.caas
def test_caas_alarm_failure(request):
    """
    1. Generate alarm for node failure
    2. Get the list of alarms and verify corresponding alrams for failure
    3. Lock and unlock the node
    4. Verify alarms are cleared once node is up
    """

    with host_helper.ssh_to_host(system_helper.get_active_controller_name()) as con_ssh:
        if system_helper.is_aio_duplex(con_ssh):
            host = system_helper.get_standby_controller_name()
        else:
            host = system_helper.get_active_controller_name()
        LOG.tc_step("Generating alarm in standby controller node")
        alarm_id = "200.012"
        command = "fmClientCli -c 'clear###{}###set###host###host={}###2019-10-14 02:28:09.5432###critical### controller function has in-service failure while compute services remain healthy.###communication###not-applicable###Lock and then Unlock host to recover. Avoid using ‘Force Lock’ action as that will impact compute services running on this host. If lock action fails then contact next level of support to investigate and recover.###False###True###False###'".format(alarm_id, host)
        request.addfinalizer(lambda: time.sleep(180))
        request.addfinalizer(lambda: common.clear_alarm_by_id(alarm_id, con_ssh))
        _, output = con_ssh.exec_cmd(command)
        time.sleep(5)

        LOG.tc_step("Getting alarm-list to see if the failure alarm is generated")
        alarms = system_helper.get_alarms_table()
        failure_alarm = r'controller function has in-service failure while compute services remain healthy'
        assert failure_alarm in str(alarms), "Failure alarm is not generated in {}".format(host)

        LOG.tc_step("Locking {}".format(host))
        request.addfinalizer(lambda: host_helper.unlock_host(host))
        host_helper.lock_host(host)

        LOG.tc_step("Unlocking {}".format(host))
        host_helper.unlock_host(host)

        LOG.tc_step("Verifying alarm list when {} becomes active".format(host))
        alarms = system_helper.get_alarms_table()
        assert failure_alarm not in str(alarms), "Failure alarm did not clear from {} even after lock/unlock".format(host)


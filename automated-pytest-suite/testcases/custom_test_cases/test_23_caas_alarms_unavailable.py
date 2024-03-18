import time
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper

@mark.caas
def test_caas_alarm_unavailable(request):
    """
    1. Generate alarm for unavailability
    2. Get the list of alarms and verify corresponding alrams for unavailability
    3. Wait for sometime for the alarm to autorecover 
    4. Verify alarm is cleared up.
    """
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Generating alarm in {} node".format(host))
        alarm_id = "200.004"
        command = "fmClientCli -c 'clear###{}###set###host###host={}###2019-10-14 02:28:09.5432###critical### Experienced a service-affecting failure.###communication###not-applicable###Host is being auto recovered by Reboot.###False###True###False###'".format(alarm_id, host)
        start_time = time.time()
        end_time = start_time + 300
        request.addfinalizer(lambda: common.clear_alarm_by_id(alarm_id, con_ssh))
        _, output = con_ssh.exec_cmd(command)        
        time.sleep(10)        
        
        LOG.tc_step("Getting alarm-list to see if the unavailability alarm is generated")
        alarms = system_helper.get_alarms_table()
        unavailability_alarm = r'Experienced a service-affecting failure'
        assert unavailability_alarm in str(alarms), "Unavailability alarm is not generated in {}".format(host)
        
        LOG.tc_step("Waiting for the unavailability alarm in {} to auto-clear".format(host))
        while time.time() < end_time:
            if unavailability_alarm in str(system_helper.get_alarms_table()):
                continue
            else:
                break
        
        LOG.tc_step("Confirming that the unavailability alarm in {} has been clear".format(host))
        assert unavailability_alarm not in str(system_helper.get_alarms_table()), "Unavailability alarm did not auto-clear from {} even after 5 mins".format(host) 

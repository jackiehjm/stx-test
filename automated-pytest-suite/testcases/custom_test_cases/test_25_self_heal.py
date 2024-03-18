from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
import time
from consts.auth import Tenant
from consts.timeout import HostTimeout
from consts.proj_vars import ProjVar
from testfixtures.pre_checks_and_configs import no_simplex

@mark.caas
def test_self_healing(request,no_simplex):
    active,standby=system_helper.get_active_standby_controllers()
    with host_helper.ssh_to_host(hostname=active) as con_ssh:
        request.addfinalizer(lambda: time.sleep(180))
        LOG.tc_step("Running the cli command on active_controller")
        old_table = host_helper.get_sm_dump_table(controller=active, con_ssh=con_ssh)
        LOG.info(old_table)
        idracip,_= system_helper.get_idrac_ip_and_subnet(con_ssh=con_ssh)
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idracip
        payload = '{"ResetType":"ForceOff"}'
        headers = "Content-Type: application/json"
        LOG.info(ProjVar.get_var("IDRAC"))
        curl_req = 'curl -k "{}" -d \'{}\' -X POST -u {}:{} -H \'{}\' -i'.format(url, payload,ProjVar.get_var("IDRAC").get("user"),ProjVar.get_var("IDRAC").get("password"), headers)

        _,ret=con_ssh.exec_cmd(cmd=curl_req)
        assert "204 No Content" in ret, "Force OFF is not successful"

        LOG.info("Waiting for 60 seconds for services to be in Active state in new controller")
        time.sleep(60)

        LOG.tc_step("Reconnecting Active Controller after power OFF")
        retry=1
        while retry<4:
            try:
                con_ssh.connect()
                break
            except:
                LOG.info("not connected in {} attempt".format(retry))
            retry +=1
        assert con_ssh.is_connected(),"Unable to connect to Floating IP after Power OFF"

        def poweron(con_ssh):
            LOG.info("Powering On {}".format(active))
            payload = '{"ResetType":"On"}'
            curl_req = 'curl -k "{}" -d \'{}\' -X POST -u {}:{} -H \'{}\' -i'.format(url, payload,ProjVar.get_var("IDRAC").get("user"), ProjVar.get_var("IDRAC").get("password"), headers)
            _, ret = con_ssh.exec_cmd(cmd=curl_req)

            retry=HostTimeout.REBOOT/10
            attempt=0
            while True :
                LOG.info("{},{}".format(attempt,retry))
                if attempt>retry:
                    assert False, "Powering On of {} Failed".format(active)
                host_status=system_helper.get_host_values(active, ('availability','operational'), con_ssh=con_ssh,auth_info=Tenant.get('admin_platform'))
                if host_status[0] =="available" and host_status[1]=="enabled":
                    break
                else:
                    time.sleep(10)
                attempt+=1
        request.addfinalizer(lambda: poweron(con_ssh))

        inactive_svc=[]
        new_table = host_helper.get_sm_dump_table(controller=standby, con_ssh=con_ssh)
        for i in new_table.get("values"):
            r=i.count("active") if i[0] == 'Service_Groups' else i.count("enabled-active")
            if r !=2 :
                inactive_svc.append(i[1])
        assert len(set(inactive_svc))==0, "Inactive services are: ".format(inactive_svc)
        missing=[]
        mismatch=[]
        for i in old_table:
            for j in new_table:
                if i[1]==j[1]:
                    if i[2]!=j[2] or i[3]!=j[3]:
                        mismatch.append(i[1])
            if i not in new_table:
                missing.append(i[1])
        LOG.warning("Services which didn't retained their state after failover {}".format(mismatch))
        LOG.warning("Services which where present before but are not present in new node {}".format(missing))


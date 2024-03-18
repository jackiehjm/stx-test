#
# Copyright (c) 2019, 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import ipaddress
import re
import os
import time
import yaml

from pytest import skip

from consts.auth import Tenant, HostLinuxUser
from consts.stx import UUID, Prompt, SysType, EventLogID, HostAvailState
from consts.proj_vars import ProjVar
from consts.timeout import SysInvTimeout, MiscTimeout, HostTimeout
from utils import cli, table_parser, exceptions
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG
from testfixtures.fixture_resources import ResourceCleanup
from keywords import common,system_helper

def get_system_health(personality=None, administrative=None, operational=None,
              availability=None, hostname=None, strict=True,
              exclude=False, con_ssh=None,
              auth_info=Tenant.get('admin_platform'),
              field='hostname', rtn_dict=False):
    """
    Get hostnames with given criteria
    Args:
        personality (None|str|tuple|list):
        administrative (None|str|list|tuple):
        operational (None|str|list|tuple):
        availability (None|str|list|tuple):
        hostname (None|tuple|list|str): filter out these hosts only
        strict (bool):
        exclude (bool):
        con_ssh (SSHClient|None):
        auth_info
        field (str|list|tuple)
        rtn_dict (bool): Whether to return dict where each field is a key,
        and value is a list

    Returns (list): hosts

    """
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)

    output =  cli.system('health-query | grep -v "OK"', ssh_client=con_ssh,
                   auth_info=auth_info)[1].split('\n')

    #table_ = table_parser.filter_table(table_, exclude=True, hostname='None')
    print("system health-query | grep -v 'OK'")
    print(output)
    if len(output) > 3:
       return False

def get_host_interfaces(con_ssh=None,auth_info=Tenant.get('admin_platform'),
               rtn_dict=False):
    required_interfaces = ['cluster-host','oam','mgmt','pxeboot']
    if ProjVar.get_var('CHK_IF_REQ_INT_CFG'):
       print(ProjVar.get_var('CHK_IF_REQ_INT_CFG'))
    else:
       print("skip")
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)
    hosts = system_helper.get_controllers()
    for host in hosts:
       table_ = table_parser.table(
         cli.system('interface-network-list '+host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
       interfaces = [ iface[3] for iface in table_['values']]
       check = all(iface in required_interfaces for iface in interfaces)
       if not check:
          print(interfaces)
          msg="All the interfaces are not configured as required by the platform"
          return False, msg
       else:
          msg = "All the required interfaces are configured properly"
          return True, msg


def check_sriov_interfaces(con_ssh=None,auth_info=Tenant.get('admin_platform'),
                  rtn_dict=False):
    if ProjVar.get_var('SRIOV_ENABLED'):
       print(ProjVar.get_var('SRIOV_ENABLED'))
    else:
       print("skip")
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)
    hosts = system_helper.get_controllers()
    for host in hosts:
       table_ = table_parser.table(
         cli.system('host-if-list '+host, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
       interfaces = [ iface[3] for iface in table_['values']]
       print(interfaces)
       check = False
       check = all(False for iface in interfaces if iface != "sriov")
       print(check)
       if not check:
          msg="Unable to find SRIOV iterfaces configured as required by the platform"
          return False, msg
       else:
          msg = "SRIOV interfaces are configured on the platform"
          return True, msg


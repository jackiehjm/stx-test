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
import pdb

from pytest import skip

from consts.auth import Tenant, HostLinuxUser
from consts.stx import UUID, Prompt, SysType, EventLogID, HostAvailState
from consts.proj_vars import ProjVar
from consts.timeout import SysInvTimeout, MiscTimeout, HostTimeout
from utils import cli, table_parser, exceptions
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG
from keywords import common,system_helper

def check_assigned_platform_controller_cpus(con_ssh=None,auth_info=Tenant.get('admin_platform'),
               rtn_dict=False):
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)
    controllers = system_helper.get_controllers()
    workers = system_helper.get_computes()
    for controller in controllers:
       platform_cpu = 0
       table_ = table_parser.table(
                cli.system('host-cpu-list '+controller, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
       cpus = table_parser.get_column(table_,"assigned_function")
       for cpu in cpus:
         if cpu == "Platform":
            platform_cpu += 1
       assert platform_cpu == 4

def check_assigned_platform_controller_mem(con_ssh=None,auth_info=Tenant.get('admin_platform'),
               rtn_dict=False):
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)
    controllers = system_helper.get_controllers()
    workers = system_helper.get_computes()
    for controller in controllers:
       platform_cpu = 0
       table_ = table_parser.table(
                cli.system('host-memory-list '+controller, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
       memory = table_parser.get_column(table_,"mem_platform(MiB)")
       for mem in memory:
         assert int(mem) == 8000


def check_assigned_platform_worker_cpus(con_ssh=None,auth_info=Tenant.get('admin_platform'),
               rtn_dict=False):
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)
    workers = system_helper.get_computes()
    for worker in workers:
       platform_cpu = 0
       table_ = table_parser.table(
                cli.system('host-cpu-list '+worker, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
       cpus = table_parser.get_column(table_,"assigned_function")
       for cpu in cpus:
         if cpu == "Platform":
            platform_cpu += 1
       assert platform_cpu == 2


def check_assigned_platform_worker_mem(con_ssh=None,auth_info=Tenant.get('admin_platform'),
               rtn_dict=False):
    if not con_ssh:
        con_name = auth_info.get('region') if (
                    auth_info and ProjVar.get_var('IS_DC')) else None
        con_ssh = ControllerClient.get_active_controller(name=con_name)
    workers = system_helper.get_computes()
    for worker in workers:
       platform_cpu = 0
       table_ = table_parser.table(
                cli.system('host-memory-list '+worker, ssh_client=con_ssh,
                   auth_info=auth_info)[1])
       memory = table_parser.get_column(table_,"mem_platform(MiB)")
       for mem in memory:
         int(mem) == 7000


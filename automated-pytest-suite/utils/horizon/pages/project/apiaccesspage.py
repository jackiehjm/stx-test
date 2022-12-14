#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from os import listdir
from os.path import isfile
from os.path import join
from re import search

from utils.horizon.pages import basepage
from utils.horizon.regions import tables


class ApiAccessTable(tables.TableRegion):
    name = "endpoints"

    # FIXME: following methods do not work. Only view credentials button can be
    #  found in bind_table_action

    @tables.bind_table_action('download_openrc_v2')
    def download_openstack_rc_v2(self, download_button):
        download_button.contextClick()

    @tables.bind_table_action('download_openrc')
    def download_openstack_rc_v3(self, download_button):
        download_button.contextclick()


class ApiAccessPage(basepage.BasePage):
    PARTIAL_URL = 'project/api_access'

    @property
    def apiaccess_table(self):
        return ApiAccessTable(self.driver)

    def download_openstack_rc_file(self, version=3):
        if version == 2:
            self.apiaccess_table.download_openstack_rc_v2()
        elif version == 3:
            self.apiaccess_table.download_openstack_rc_v3()

    def list_of_files(self, directory, template):
        return [f for f in listdir(directory) if isfile(join(directory, f))
                and f.endswith(template)]

    def get_credentials_from_file(self, version, directory, template):
        self._wait_until(
            lambda _: len(self.list_of_files(directory, template)) > 0)
        file_name = self.list_of_files(directory, template)[0]
        with open(join(directory, file_name), encoding='utf8') as cred_file:
            content = cred_file.read()
        username_re = r'export OS_USERNAME="([^"]+)"'
        if version == 2:
            tenant_name_re = r'export OS_TENANT_NAME="([^"]+)"'
            tenant_id_re = r'export OS_TENANT_ID=(.+)'
        elif version == 3:
            tenant_name_re = r'export OS_PROJECT_NAME="([^"]+)"'
            tenant_id_re = r'export OS_PROJECT_ID=(.+)'
        else:
            raise ValueError("Unknown version: {}. Valid versions: 2, 3 ".format(version))
        username = search(username_re, content).group(1)
        tenant_name = search(tenant_name_re, content).group(1)
        tenant_id = search(tenant_id_re, content).group(1)
        cred_dict = {'OS_USERNAME': username,
                     'OS_TENANT_NAME': tenant_name,
                     'OS_TENANT_ID': tenant_id}
        return cred_dict

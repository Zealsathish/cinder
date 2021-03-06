# Copyright (c) 2015 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
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
"""Tests for huawei 18000 storage."""
import json
import mock
import os
import shutil
import tempfile
import time
from xml.dom import minidom

from oslo_log import log as logging

from cinder import exception
from cinder import test
from cinder.volume import configuration as conf
from cinder.volume.drivers.huawei import huawei_driver
from cinder.volume.drivers.huawei import huawei_utils
from cinder.volume.drivers.huawei import rest_client

LOG = logging.getLogger(__name__)

test_volume = {'name': 'volume-21ec7341-9256-497b-97d9-ef48edcf0635',
               'size': 2,
               'volume_name': 'vol1',
               'id': '21ec7341-9256-497b-97d9-ef48edcf0635',
               'volume_id': '21ec7341-9256-497b-97d9-ef48edcf0635',
               'provider_auth': None,
               'project_id': 'project',
               'display_name': 'vol1',
               'display_description': 'test volume',
               'volume_type_id': None,
               'host': 'ubuntu@huawei#OpenStack_Pool',
               'provider_location': '11',
               }

test_snap = {'name': 'volume-21ec7341-9256-497b-97d9-ef48edcf0635',
             'size': 1,
             'volume_name': 'vol1',
             'id': '21ec7341-9256-497b-97d9-ef48edcf0635',
             'volume_id': '21ec7341-9256-497b-97d9-ef48edcf0635',
             'provider_auth': None,
             'project_id': 'project',
             'display_name': 'vol1',
             'display_description': 'test volume',
             'volume_type_id': None,
             'provider_location': '11',
             }

FakeConnector = {'initiator': 'iqn.1993-08.debian:01:ec2bff7ac3a3',
                 'wwpns': ['10000090fa0d6754'],
                 'wwnns': ['10000090fa0d6755'],
                 'host': 'ubuntuc',
                 }

# A fake response of success response storage
FAKE_COMMON_SUCCESS_RESPONSE = """
{
    "error": {
        "code": 0
    }
}
"""

# A fake response of login huawei storage
FAKE_GET_LOGIN_STORAGE_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": {
        "username": "admin",
        "iBaseToken": "2001031430",
        "deviceid": "210235G7J20000000000"
    }
}
"""

# A fake response of login out huawei storage
FAKE_LOGIN_OUT_STORAGE_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": {
        "ID": 11
    }
}
"""

# A fake response of mock storage pool info
FAKE_STORAGE_POOL_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": [{
        "USERFREECAPACITY": "985661440",
        "ID": "0",
        "NAME": "OpenStack_Pool",
        "USERTOTALCAPACITY": "985661440"
    }]
}
"""

# A fake response of lun or lungroup response
FAKE_LUN_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": {
        "ID": "1",
        "NAME": "5mFHcBv4RkCcD+JyrWc0SA"
    }
}
"""

FAKE_LUN_DELETE_SUCCESS_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": {
        "ID": "11",
        "IOCLASSID": "11",
        "NAME": "5mFHcBv4RkCcD+JyrWc0SA",
        "RUNNINGSTATUS": "2",
        "HEALTHSTATUS": "1",
        "RUNNINGSTATUS": "27"
    }
}
"""

FAKE_QUERY_ALL_LUN_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": [{
        "ID": "1",
        "NAME": "IexzQZJWSXuX2e9I7c8GNQ"
    }]
}
"""

FAKE_LUN_ASSOCIATE_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":[{
        "ID":"11"
    }]
}
"""

FAKE_QUERY_LUN_GROUP_INFO_RESPONSE = """
{
    "error": {
        "code":0
    },
    "data":[{
        "NAME":"OpenStack_LunGroup_1",
        "DESCRIPTION":"5mFHcBv4RkCcD+JyrWc0SA",
        "ID":"11",
        "TYPE":256
    }]
}
"""

FAKE_QUERY_LUN_GROUP_RESPONSE = """
{
    "error": {
        "code":0
    },
    "data":{
        "NAME":"5mFHcBv4RkCcD+JyrWc0SA",
        "DESCRIPTION":"5mFHcBv4RkCcD+JyrWc0SA",
        "ID":"11",
        "TYPE":256
    }
}
"""

FAKE_QUERY_LUN_GROUP_ASSOCIAT_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":{
        "NAME":"5mFHcBv4RkCcD+JyrWc0SA",
        "DESCRIPTION":"5mFHcBv4RkCcD+JyrWc0SA",
        "ID":"11",
        "TYPE":256
    }
}
"""

FAKE_LUN_COUNT_RESPONSE = """
{
    "data":{
        "COUNT":"7"
    },
    "error":{
        "code":0,
        "description":"0"
    }
}
"""
# A fake response of snapshot list response
FAKE_SNAPSHOT_LIST_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": [{
        "ID": 11,
        "NAME": "wr_LMKAjS7O_VtsEIREGYw"
    },
    {
        "ID": 12,
        "NAME": "SDFAJSDFLKJ"
    }]
}
"""

# A fake response of create snapshot response
FAKE_CREATE_SNAPSHOT_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": {
        "ID": 11,
        "NAME": "YheUoRwbSX2BxN7"
    }
}
"""

# A fake response of get snapshot response
FAKE_GET_SNAPSHOT_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": {
        "ID": 11,
        "NAME": "YheUoRwbSX2BxN7"
    }
}
"""

# A fake response of get iscsi response
FAKE_GET_ISCSI_INFO_RESPONSE = """
{
    "data": [{
        "ETHPORTID": "139267",
        "ID": "iqn.oceanstor:21004846fb8ca15f::22003:111.111.101.244",
        "TPGT": "8196",
        "TYPE": 249
    }],
    "error": {
        "code": 0,
        "description": "0"
    }
}
"""

# A fake response of get eth info response
FAKE_GET_ETH_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": [{
        "PARENTTYPE": 209,
        "MACADDRESS": "00:22:a1:0a:79:57",
        "ETHNEGOTIATE": "-1",
        "ERRORPACKETS": "0",
        "IPV4ADDR": "192.168.100.2",
        "IPV6GATEWAY": "",
        "IPV6MASK": "0",
        "OVERFLOWEDPACKETS": "0",
        "ISCSINAME": "P0",
        "HEALTHSTATUS": "1",
        "ETHDUPLEX": "2",
        "ID": "16909568",
        "LOSTPACKETS": "0",
        "TYPE": 213,
        "NAME": "P0",
        "INIORTGT": "4",
        "RUNNINGSTATUS": "10",
        "IPV4GATEWAY": "",
        "BONDNAME": "",
        "STARTTIME": "1371684218",
        "SPEED": "1000",
        "ISCSITCPPORT": "0",
        "IPV4MASK": "255.255.0.0",
        "IPV6ADDR": "",
        "LOGICTYPE": "0",
        "LOCATION": "ENG0.B5.P0",
        "MTU": "1500",
        "PARENTID": "1.5"
    }]
}
"""

FAKE_GET_ETH_ASSOCIATE_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":[{
        "IPV4ADDR":"192.168.100.10",
        "HEALTHSTATUS":"1",
        "RUNNINGSTATUS":"10"
    }]
}
"""
# A fake response of get iscsi device info response
FAKE_GET_ISCSI_DEVICE_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": [{
        "CMO_ISCSI_DEVICE_NAME":\
        "iqn.2006-08.com.huawei:oceanstor:21000022a10a2a39:iscsinametest"
    }]
}
"""

# A fake response of get iscsi device info response
FAKE_GET_ALL_HOST_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": [{
        "PARENTTYPE": 245,
        "NAME": "ubuntuc",
        "DESCRIPTION": "",
        "RUNNINGSTATUS": "1",
        "IP": "",
        "PARENTNAME": "",
        "OPERATIONSYSTEM": "0",
        "LOCATION": "",
        "HEALTHSTATUS": "1",
        "MODEL": "",
        "ID": "1",
        "PARENTID": "",
        "NETWORKNAME": "",
        "TYPE": 21
    },
    {
        "PARENTTYPE": 245,
        "NAME": "ubuntu",
        "DESCRIPTION": "",
        "RUNNINGSTATUS": "1",
        "IP": "",
        "PARENTNAME": "",
        "OPERATIONSYSTEM": "0",
        "LOCATION": "",
        "HEALTHSTATUS": "1",
        "MODEL": "",
        "ID": "2",
        "PARENTID": "",
        "NETWORKNAME": "",
        "TYPE": 21
    }]
}
"""

# A fake response of get host or hostgroup info response
FAKE_GET_ALL_HOST_GROUP_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": [{
        "NAME":"ubuntuc",
        "DESCRIPTION":"",
        "ID":"0",
        "TYPE":14
    }]
}
"""

FAKE_GET_HOST_GROUP_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data":{
        "NAME":"ubuntuc",
        "DESCRIPTION":"",
        "ID":"0",
        "TYPE":14
    }
}
"""

# A fake response of lun copy info response
FAKE_GET_LUN_COPY_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": {
        "COPYSTOPTIME": "-1",
        "HEALTHSTATUS": "1",
        "NAME": "w1PSNvu6RumcZMmSh4/l+Q==",
        "RUNNINGSTATUS": "36",
        "DESCRIPTION": "w1PSNvu6RumcZMmSh4/l+Q==",
        "ID": "0",
        "LUNCOPYTYPE": "1",
        "COPYPROGRESS": "0",
        "COPYSPEED": "2",
        "TYPE": 219,
        "COPYSTARTTIME": "-1"
    }
}
"""

# A fake response of lun copy list info response
FAKE_GET_LUN_COPY_LIST_INFO_RESPONSE = """
{
    "error": {
        "code": 0
    },
    "data": [{
        "COPYSTOPTIME": "1372209335",
        "HEALTHSTATUS": "1",
        "NAME": "w1PSNvu6RumcZMmSh4/l+Q==",
        "RUNNINGSTATUS": "40",
        "DESCRIPTION": "w1PSNvu6RumcZMmSh4/l+Q==",
        "ID": "0",
        "LUNCOPYTYPE": "1",
        "COPYPROGRESS": "100",
        "COPYSPEED": "2",
        "TYPE": 219,
        "COPYSTARTTIME": "1372209329"
    }]
}
"""

# A fake response of mappingview info response
FAKE_GET_MAPPING_VIEW_INFO_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":[{
        "WORKMODE":"255",
        "HEALTHSTATUS":"1",
        "NAME":"IexzQZJWSXuX2e9I7c8GNQ",
        "RUNNINGSTATUS":"27",
        "DESCRIPTION":"",
        "ENABLEINBANDCOMMAND":"true",
        "ID":"1",
        "INBANDLUNWWN":"",
        "TYPE":245
    },
    {
        "WORKMODE":"255",
        "HEALTHSTATUS":"1",
        "NAME":"YheUoRwbSX2BxN767nvLSw",
        "RUNNINGSTATUS":"27",
        "DESCRIPTION":"",
        "ENABLEINBANDCOMMAND":"true",
        "ID":"2",
        "INBANDLUNWWN":"",
        "TYPE":245
    }]
}
"""

FAKE_GET_MAPPING_VIEW_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":{
        "WORKMODE":"255",
        "HEALTHSTATUS":"1",
        "NAME":"mOWtSXnaQKi3hpB3tdFRIQ",
        "RUNNINGSTATUS":"27",
        "DESCRIPTION":"",
        "ENABLEINBANDCOMMAND":"true",
        "ID":"1",
        "INBANDLUNWWN":"",
        "TYPE":245
    }
}
"""

FAKE_FC_INFO_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":[{
        "HEALTHSTATUS":"1",
        "NAME":"",
        "MULTIPATHTYPE":"1",
        "ISFREE":"true",
        "RUNNINGSTATUS":"27",
        "ID":"10000090fa0d6754",
        "OPERATIONSYSTEM":"255",
        "TYPE":223
    },
    {
        "HEALTHSTATUS":"1",
        "NAME":"",
        "MULTIPATHTYPE":"1",
        "ISFREE":"true",
        "RUNNINGSTATUS":"27",
        "ID":"10000090fa0d6755",
        "OPERATIONSYSTEM":"255",
        "TYPE":223
    }]
}
"""

FAKE_ISCSI_INITIATOR_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":[{
        "CHAPNAME":"mm-user",
        "HEALTHSTATUS":"1",
        "ID":"iqn.1993-08.org.debian:01:9073aba6c6f",
        "ISFREE":"true",
        "MULTIPATHTYPE":"1",
        "NAME":"",
        "OPERATIONSYSTEM":"255",
        "RUNNINGSTATUS":"28",
        "TYPE":222,
        "USECHAP":"true"
    }]
}
"""

FAKE_HOST_LINK_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":[{
        "PARENTTYPE":21,
        "TARGET_ID":"0000000000000000",
        "INITIATOR_NODE_WWN":"20000090fa0d6754",
        "INITIATOR_TYPE":"223",
        "RUNNINGSTATUS":"27",
        "PARENTNAME":"ubuntuc",
        "INITIATOR_ID":"10000090fa0d6754",
        "TARGET_PORT_WWN":"24000022a10a2a39",
        "HEALTHSTATUS":"1",
        "INITIATOR_PORT_WWN":"10000090fa0d6754",
        "ID":"010000090fa0d675-0000000000110400",
        "TARGET_NODE_WWN":"21000022a10a2a39",
        "PARENTID":"1",
        "CTRL_ID":"0",
        "TYPE":255,
        "TARGET_TYPE":"212"
    }]
}
"""

FAKE_PORT_GROUP_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":[{
        "ID":11,
        "NAME":"test"
    }]
}
"""

FAKE_ERROR_INFO_RESPONSE = """
{
    "error":{
        "code":31755596
    }
}
"""

FAKE_ERROR_LUN_INFO_RESPONSE = """
{
    "error":{
        "code":0
    },
    "data":{
        "ID":"11",
        "IOCLASSID":"11",
        "NAME":"5mFHcBv4RkCcD+JyrWc0SA"
    }
}
"""
# mock login info map
MAP_COMMAND_TO_FAKE_RESPONSE = {}
MAP_COMMAND_TO_FAKE_RESPONSE['/xx/sessions'] = (
    FAKE_GET_LOGIN_STORAGE_RESPONSE)
MAP_COMMAND_TO_FAKE_RESPONSE['sessions'] = (
    FAKE_LOGIN_OUT_STORAGE_RESPONSE)

# mock storage info map
MAP_COMMAND_TO_FAKE_RESPONSE['storagepool'] = (
    FAKE_STORAGE_POOL_RESPONSE)

# mock lun info map
MAP_COMMAND_TO_FAKE_RESPONSE['lun'] = (
    FAKE_LUN_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/11/GET'] = (
    FAKE_LUN_DELETE_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/1/GET'] = (
    FAKE_LUN_DELETE_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/11/DELETE'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun?range=[0-65535]/GET'] = (
    FAKE_QUERY_ALL_LUN_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/associate?TYPE=11&ASSOCIATEOBJTYPE=256'
                             '&ASSOCIATEOBJID=11/GET'] = (
    FAKE_LUN_ASSOCIATE_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/associate?TYPE=11&ASSOCIATEOBJTYPE=256'
                             '&ASSOCIATEOBJID=12/GET'] = (
    FAKE_LUN_ASSOCIATE_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/associate?ID=1&TYPE=11&ASSOCIATEOBJTYPE=21'
                             '&ASSOCIATEOBJID=0/GET'] = (
    FAKE_LUN_ASSOCIATE_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/associate?TYPE=11&ASSOCIATEOBJTYPE=21'
                             '&ASSOCIATEOBJID=1/GET'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lungroup?range=[0-8191]/GET'] = (
    FAKE_QUERY_LUN_GROUP_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lungroup'] = (
    FAKE_QUERY_LUN_GROUP_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lungroup/associate'] = (
    FAKE_QUERY_LUN_GROUP_ASSOCIAT_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lungroup/associate?ID=11&ASSOCIATEOBJTYPE=11'
                             '&ASSOCIATEOBJID=1/DELETE'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lungroup/associate?TYPE=256&ASSOCIATEOBJTYPE=11'
                             '&ASSOCIATEOBJID=11/GET'] = (
    FAKE_LUN_ASSOCIATE_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lungroup/associate?ID=11&ASSOCIATEOBJTYPE=11'
                             '&ASSOCIATEOBJID=11/DELETE'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/count?TYPE=11&ASSOCIATEOBJTYPE=256'
                             '&ASSOCIATEOBJID=11/GET'] = (
    FAKE_LUN_COUNT_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lun/expand/PUT'] = (
    FAKE_LUN_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['lungroup/associate?ID=12&ASSOCIATEOBJTYPE=11'
                             '&ASSOCIATEOBJID=12/DELETE'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)
# mock snapshot info map
MAP_COMMAND_TO_FAKE_RESPONSE['snapshot'] = (
    FAKE_CREATE_SNAPSHOT_INFO_RESPONSE)

# mock snapshot info map
MAP_COMMAND_TO_FAKE_RESPONSE['snapshot/11/GET'] = (
    FAKE_GET_SNAPSHOT_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['snapshot/activate'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['snapshot/stop/PUT'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['snapshot/11/DELETE'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['snapshot?range=[0-32767]/GET'] = (
    FAKE_SNAPSHOT_LIST_INFO_RESPONSE)

# mock QoS info map
MAP_COMMAND_TO_FAKE_RESPONSE['ioclass/11/GET'] = (
    FAKE_LUN_DELETE_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['ioclass/11/DELETE'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['ioclass/active/11/PUT'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

# mock iscsi info map
MAP_COMMAND_TO_FAKE_RESPONSE['iscsi_tgt_port/GET'] = (
    FAKE_GET_ISCSI_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['eth_port/GET'] = (
    FAKE_GET_ETH_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['eth_port/associate?TYPE=213&ASSOCIATEOBJTYPE=257'
                             '&ASSOCIATEOBJID=11/GET'] = (
    FAKE_GET_ETH_ASSOCIATE_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['iscsidevicename'] = (
    FAKE_GET_ISCSI_DEVICE_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['iscsi_initiator?range=[0-256]/GET'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['iscsi_initiator/'] = (
    FAKE_ISCSI_INITIATOR_RESPONSE)

# mock host info map
MAP_COMMAND_TO_FAKE_RESPONSE['host?range=[0-65535]/GET'] = (
    FAKE_GET_ALL_HOST_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['hostgroup?range=[0-8191]/GET'] = (
    FAKE_GET_ALL_HOST_GROUP_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['hostgroup'] = (
    FAKE_GET_HOST_GROUP_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['host/associate?TYPE=21&ASSOCIATEOBJTYPE=14'
                             '&ASSOCIATEOBJID=0/GET'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['hostgroup/associate'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

# mock copy info map
MAP_COMMAND_TO_FAKE_RESPONSE['luncopy'] = (
    FAKE_GET_LUN_COPY_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['LUNCOPY?range=[0-1023]/GET'] = (
    FAKE_GET_LUN_COPY_LIST_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['LUNCOPY/start/PUT'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['LUNCOPY/0/DELETE'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

# mock mapping view info map
MAP_COMMAND_TO_FAKE_RESPONSE['mappingview?range=[0-8191]/GET'] = (
    FAKE_GET_MAPPING_VIEW_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['mappingview'] = (
    FAKE_GET_MAPPING_VIEW_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['MAPPINGVIEW/CREATE_ASSOCIATE/PUT'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

# mock FC info map
MAP_COMMAND_TO_FAKE_RESPONSE['fc_initiator?ISFREE=true&range=[0-8191]/GET'] = (
    FAKE_FC_INFO_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['fc_initiator/10000090fa0d6754/PUT'] = (
    FAKE_COMMON_SUCCESS_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['host_link?INITIATOR_TYPE=223'
                             '&INITIATOR_PORT_WWN=10000090fa0d6754/GET'] = (
    FAKE_HOST_LINK_RESPONSE)

MAP_COMMAND_TO_FAKE_RESPONSE['portgroup?range=[0-8191]&TYPE=257/GET'] = (
    FAKE_PORT_GROUP_RESPONSE)


def Fake_sleep(time):
    pass


class Fake18000Client(rest_client.RestClient):

    def __init__(self, configuration):
        rest_client.RestClient.__init__(self, configuration)
        self.delete_flag = False
        self.terminateFlag = False
        self.deviceid = None
        self.test_fail = False
        self.checkFlag = False

    def _change_file_mode(self, filepath):
        pass

    def _parse_volume_type(self, volume):
        poolinfo = self._find_pool_info()
        volume_size = self._get_volume_size(poolinfo, volume)

        params = {'LUNType': 0,
                  'WriteType': '1',
                  'PrefetchType': '3',
                  'qos_level': 'Qos-high',
                  'StripUnitSize': '64',
                  'PrefetchValue': '0',
                  'PrefetchTimes': '0',
                  'qos': 'OpenStack_Qos_High',
                  'MirrorSwitch': '1',
                  'tier': 'Tier_high',
                  }

        params['volume_size'] = volume_size
        params['pool_id'] = poolinfo['ID']
        return params

    def _get_snapshotid_by_name(self, snapshot_name):
        return "11"

    def _check_snapshot_exist(self, snapshot_id):
        return True

    def call(self, url=False, data=None, method=None):
        url = url.replace('http://100.115.10.69:8082/deviceManager/rest', '')
        command = url.replace('/210235G7J20000000000/', '')
        data = None

        if method:
            command = command + "/" + method

        for item in MAP_COMMAND_TO_FAKE_RESPONSE.keys():
            if command == item:
                data = MAP_COMMAND_TO_FAKE_RESPONSE[item]
                if self.test_fail:
                    data = FAKE_ERROR_INFO_RESPONSE
                    if command == 'lun/11/GET':
                        data = FAKE_ERROR_LUN_INFO_RESPONSE

                    self.test_fail = False

        return json.loads(data)


class Fake18000ISCSIStorage(huawei_driver.Huawei18000ISCSIDriver):
    """Fake Huawei Storage, Rewrite some methods of HuaweiISCSIDriver."""

    def __init__(self, configuration):
        self.configuration = configuration
        self.xml_file_path = self.configuration.cinder_huawei_conf_file

    def do_setup(self):
        self.restclient = Fake18000Client(configuration=self.configuration)


class Fake18000FCStorage(huawei_driver.Huawei18000FCDriver):
    """Fake Huawei Storage, Rewrite some methods of HuaweiISCSIDriver."""

    def __init__(self, configuration):
        self.configuration = configuration
        self.xml_file_path = self.configuration.cinder_huawei_conf_file

    def do_setup(self):
        self.restclient = Fake18000Client(configuration=self.configuration)


class Huawei18000ISCSIDriverTestCase(test.TestCase):

    def setUp(self):
        super(Huawei18000ISCSIDriverTestCase, self).setUp()
        self.tmp_dir = tempfile.mkdtemp()
        self.fake_conf_file = self.tmp_dir + '/cinder_huawei_conf.xml'
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.create_fake_conf_file()
        self.addCleanup(os.remove, self.fake_conf_file)
        self.configuration = mock.Mock(spec=conf.Configuration)
        self.configuration.cinder_huawei_conf_file = self.fake_conf_file
        self.xml_file_path = self.configuration.cinder_huawei_conf_file
        self.stubs.Set(time, 'sleep', Fake_sleep)
        driver = Fake18000ISCSIStorage(configuration=self.configuration)
        self.driver = driver
        self.driver.do_setup()
        self.portgroup = 'test'
        self.target_ip = '192.168.100.10'

    def test_login_success(self):
        deviceid = self.driver.restclient.login()
        self.assertEqual('210235G7J20000000000', deviceid)

    def test_create_volume_success(self):
        self.driver.restclient.login()
        lun_info = self.driver.create_volume(test_volume)
        self.assertEqual('1', lun_info['provider_location'])

    def test_delete_volume_success(self):
        self.driver.restclient.login()
        delete_flag = self.driver.delete_volume(test_volume)
        self.assertTrue(delete_flag)

    def test_create_snapshot_success(self):
        self.driver.restclient.login()
        lun_info = self.driver.create_snapshot(test_volume)
        self.assertEqual(11, lun_info['provider_location'])

    def test_delete_snapshot_success(self):
        self.driver.restclient.login()
        delete_flag = self.driver.delete_snapshot(test_snap)
        self.assertTrue(delete_flag)

    def test_create_volume_from_snapsuccess(self):
        self.driver.restclient.login()
        lun_info = self.driver.create_volume_from_snapshot(test_volume,
                                                           test_volume)
        self.assertEqual('1', lun_info['provider_location'])

    def test_initialize_connection_success(self):
        self.driver.restclient.login()
        iscsi_properties = self.driver.initialize_connection(test_volume,
                                                             FakeConnector)
        self.assertEqual(1, iscsi_properties['data']['target_lun'])

    def test_terminate_connection_success(self):
        self.driver.restclient.login()
        self.driver.restclient.terminateFlag = True
        self.driver.terminate_connection(test_volume, FakeConnector)
        self.assertTrue(self.driver.restclient.terminateFlag)

    def test_get_volume_status(self):
        self.driver.restclient.login()
        data = self.driver.get_volume_stats()
        self.assertEqual('1.1.1', data['driver_version'])

    def test_extend_volume(self):
        self.driver.restclient.login()
        lun_info = self.driver.extend_volume(test_volume, 3)
        self.assertEqual('1', lun_info['provider_location'])

    def test_login_fail(self):
        self.driver.restclient.test_fail = True
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.restclient.login)

    def test_create_snapshot_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.create_snapshot, test_volume)

    def test_create_volume_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.create_volume, test_volume)

    def test_delete_volume_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        delete_flag = self.driver.delete_volume(test_volume)
        self.assertTrue(delete_flag)

    def test_delete_snapshot_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        delete_flag = self.driver.delete_volume(test_snap)
        self.assertTrue(delete_flag)

    def test_initialize_connection_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        iscsi_properties = self.driver.initialize_connection(test_volume,
                                                             FakeConnector)
        self.assertEqual(1, iscsi_properties['data']['target_lun'])

    def test_get_default_timeout(self):
        result = huawei_utils._get_default_timeout(self.xml_file_path)
        self.assertEqual('43200', result)

    def test_get_wait_interval(self):
        result = huawei_utils.get_wait_interval(self.xml_file_path,
                                                'LUNReadyWaitInterval')
        self.assertEqual(2, result)

    def test_lun_is_associated_to_lungroup(self):
        self.driver.restclient.login()
        self.driver.restclient._associate_lun_to_lungroup('11', '11')
        result = self.driver.restclient._is_lun_associated_to_lungroup('11',
                                                                       '11')
        self.assertTrue(result)

    def test_lun_is_not_associated_to_lun_group(self):
        self.driver.restclient.login()
        self.driver.restclient._associate_lun_to_lungroup('12', '12')
        self.driver.restclient.remove_lun_from_lungroup('12', '12')
        result = self.driver.restclient._is_lun_associated_to_lungroup('12',
                                                                       '12')
        self.assertFalse(result)

    def test_get_tgtip(self):
        self.driver.restclient.login()
        portg_id = self.driver.restclient.find_tgt_port_group(self.portgroup)
        result = self.driver.restclient._get_tgt_ip_from_portgroup(portg_id)
        self.assertEqual(result, self.target_ip)

    def test_get_lun_conf_params(self):
        self.driver.restclient.login()
        luninfo = huawei_utils.get_lun_conf_params(self.xml_file_path)
        luninfo['pool_id'] = '0'
        luninfo['volume_size'] = 2
        luninfo['volume_description'] = 'test volume'
        luninfo = huawei_utils.init_lun_parameters('5mFHcBv4RkCcD+JyrWc0SA',
                                                   luninfo)
        self.assertEqual('5mFHcBv4RkCcD+JyrWc0SA', luninfo['NAME'])

    def tset_get_iscsi_conf(self):
        self.driver.restclient.login()
        iscsiinfo = huawei_utils.get_iscsi_conf(self.xml_file_path)
        self.assertEqual('iqn.1993-08.debian:01:ec2bff7ac3a3',
                         iscsiinfo['Initiator'])

    def test_check_conf_file(self):
        self.driver.restclient.login()
        self.driver.restclient.checkFlag = True
        huawei_utils.check_conf_file(self.xml_file_path)
        self.assertTrue(self.driver.restclient.checkFlag)

    def test_get_conf_host_os_type(self):
        self.driver.restclient.login()
        host_os = huawei_utils.get_conf_host_os_type('100.97.10.30',
                                                     self.configuration)
        self.assertEqual('0', host_os)

    def create_fake_conf_file(self):
        """Create a fake Config file.

          Huawei storage customize a XML configuration file, the configuration
          file is used to set the Huawei storage custom parameters, therefore,
          in the UT test we need to simulate such a configuration file.
        """
        doc = minidom.Document()

        config = doc.createElement('config')
        doc.appendChild(config)

        storage = doc.createElement('Storage')
        config.appendChild(storage)
        controllerip0 = doc.createElement('ControllerIP0')
        controllerip0_text = doc.createTextNode('10.10.10.1')
        controllerip0.appendChild(controllerip0_text)
        storage.appendChild(controllerip0)
        controllerip1 = doc.createElement('ControllerIP1')
        controllerip1_text = doc.createTextNode('10.10.10.2')
        controllerip1.appendChild(controllerip1_text)
        storage.appendChild(controllerip1)
        username = doc.createElement('UserName')
        username_text = doc.createTextNode('admin')
        username.appendChild(username_text)
        storage.appendChild(username)
        userpassword = doc.createElement('UserPassword')
        userpassword_text = doc.createTextNode('Admin@storage')
        userpassword.appendChild(userpassword_text)
        storage.appendChild(userpassword)
        url = doc.createElement('RestURL')
        url_text = doc.createTextNode('http://100.115.10.69:8082/'
                                      'deviceManager/rest/')
        url.appendChild(url_text)
        storage.appendChild(url)

        storagepool = doc.createElement('StoragePool')
        pool_text = doc.createTextNode('OpenStack_Pool')
        storagepool.appendChild(pool_text)
        storage.appendChild(storagepool)

        lun = doc.createElement('LUN')
        config.appendChild(lun)
        storagepool = doc.createElement('StoragePool')
        pool_text = doc.createTextNode('OpenStack_Pool')
        storagepool.appendChild(pool_text)
        lun.appendChild(storagepool)

        timeout = doc.createElement('Timeout')
        timeout_text = doc.createTextNode('43200')
        timeout.appendChild(timeout_text)
        lun.appendChild(timeout)

        lun_ready_wait_interval = doc.createElement('LUNReadyWaitInterval')
        lun_ready_wait_interval_text = doc.createTextNode('2')
        lun_ready_wait_interval.appendChild(lun_ready_wait_interval_text)
        lun.appendChild(lun_ready_wait_interval)

        prefetch = doc.createElement('Prefetch')
        prefetch.setAttribute('Type', '1')
        prefetch.setAttribute('Value', '0')
        lun.appendChild(prefetch)

        iscsi = doc.createElement('iSCSI')
        config.appendChild(iscsi)
        defaulttargetip = doc.createElement('DefaultTargetIP')
        defaulttargetip_text = doc.createTextNode('100.115.10.68')
        defaulttargetip.appendChild(defaulttargetip_text)
        iscsi.appendChild(defaulttargetip)
        initiator = doc.createElement('Initiator')
        initiator.setAttribute('Name', 'iqn.1993-08.debian:01:ec2bff7ac3a3')
        initiator.setAttribute('TargetIP', '192.168.100.2')
        iscsi.appendChild(initiator)

        host = doc.createElement('Host')
        host.setAttribute('HostIP', '100.97.10.30')
        host.setAttribute('OSType', 'Linux')
        config.appendChild(host)

        fakefile = open(self.fake_conf_file, 'w')
        fakefile.write(doc.toprettyxml(indent=''))
        fakefile.close()


class Huawei18000FCDriverTestCase(test.TestCase):

    def setUp(self):
        super(Huawei18000FCDriverTestCase, self).setUp()
        self.tmp_dir = tempfile.mkdtemp()
        self.fake_conf_file = self.tmp_dir + '/cinder_huawei_conf.xml'
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.create_fake_conf_file()
        self.addCleanup(os.remove, self.fake_conf_file)
        self.configuration = mock.Mock(spec=conf.Configuration)
        self.configuration.cinder_huawei_conf_file = self.fake_conf_file
        self.xml_file_path = self.configuration.cinder_huawei_conf_file
        self.stubs.Set(time, 'sleep', Fake_sleep)
        driver = Fake18000FCStorage(configuration=self.configuration)
        self.driver = driver
        self.driver.do_setup()

    def test_login_success(self):
        deviceid = self.driver.restclient.login()
        self.assertEqual('210235G7J20000000000', deviceid)

    def test_create_volume_success(self):
        self.driver.restclient.login()
        lun_info = self.driver.create_volume(test_volume)
        self.assertEqual('1', lun_info['provider_location'])

    def test_delete_volume_success(self):
        self.driver.restclient.login()
        delete_flag = self.driver.delete_volume(test_volume)
        self.assertTrue(delete_flag)

    def test_create_snapshot_success(self):
        self.driver.restclient.login()
        lun_info = self.driver.create_snapshot(test_volume)
        self.assertEqual(11, lun_info['provider_location'])

    def test_delete_snapshot_success(self):
        self.driver.restclient.login()
        delete_flag = self.driver.delete_snapshot(test_snap)
        self.assertTrue(delete_flag)

    def test_create_volume_from_snapsuccess(self):
        self.driver.restclient.login()
        lun_info = self.driver.create_volume_from_snapshot(test_volume,
                                                           test_volume)
        self.assertEqual('1', lun_info['provider_location'])

    def test_initialize_connection_success(self):
        self.driver.restclient.login()
        iscsi_properties = self.driver.initialize_connection(test_volume,
                                                             FakeConnector)
        self.assertEqual(1, iscsi_properties['data']['target_lun'])

    def test_terminate_connection_success(self):
        self.driver.restclient.login()
        self.driver.restclient.terminateFlag = True
        self.driver.terminate_connection(test_volume, FakeConnector)
        self.assertTrue(self.driver.restclient.terminateFlag)

    def test_get_volume_status(self):
        self.driver.restclient.login()
        data = self.driver.get_volume_stats()
        self.assertEqual('1.1.1', data['driver_version'])

    def test_extend_volume(self):
        self.driver.restclient.login()
        lun_info = self.driver.extend_volume(test_volume, 3)
        self.assertEqual('1', lun_info['provider_location'])

    def test_login_fail(self):
        self.driver.restclient.test_fail = True
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.restclient.login)

    def test_create_snapshot_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.create_snapshot, test_volume)

    def test_create_volume_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.create_volume, test_volume)

    def test_delete_volume_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        delete_flag = self.driver.delete_volume(test_volume)
        self.assertTrue(delete_flag)

    def test_delete_snapshot_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        delete_flag = self.driver.delete_snapshot(test_snap)
        self.assertTrue(delete_flag)

    def test_initialize_connection_fail(self):
        self.driver.restclient.login()
        self.driver.restclient.test_fail = True
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.initialize_connection,
                          test_volume, FakeConnector)

    def test_get_default_timeout(self):
        result = huawei_utils._get_default_timeout(self.xml_file_path)
        self.assertEqual('43200', result)

    def test_get_wait_interval(self):
        result = huawei_utils.get_wait_interval(self.xml_file_path,
                                                'LUNReadyWaitInterval')
        self.assertEqual(2, result)

    def test_lun_is_associated_to_lungroup(self):
        self.driver.restclient.login()
        self.driver.restclient._associate_lun_to_lungroup('11', '11')
        result = self.driver.restclient._is_lun_associated_to_lungroup('11',
                                                                       '11')
        self.assertTrue(result)

    def test_lun_is_not_associated_to_lun_group(self):
        self.driver.restclient.login()
        self.driver.restclient._associate_lun_to_lungroup('12', '12')
        self.driver.restclient.remove_lun_from_lungroup('12', '12')
        result = self.driver.restclient._is_lun_associated_to_lungroup('12',
                                                                       '12')
        self.assertFalse(result)

    def test_get_lun_conf_params(self):
        self.driver.restclient.login()
        luninfo = huawei_utils.get_lun_conf_params(self.xml_file_path)
        luninfo['pool_id'] = '0'
        luninfo['volume_size'] = 2
        luninfo['volume_description'] = 'test volume'
        luninfo = huawei_utils.init_lun_parameters('5mFHcBv4RkCcD+JyrWc0SA',
                                                   luninfo)
        self.assertEqual('5mFHcBv4RkCcD+JyrWc0SA', luninfo['NAME'])

    def test_check_conf_file(self):
        self.driver.restclient.login()
        self.driver.restclient.checkFlag = True
        huawei_utils.check_conf_file(self.xml_file_path)
        self.assertTrue(self.driver.restclient.checkFlag)

    def test_get_conf_host_os_type(self):
        self.driver.restclient.login()
        host_os = huawei_utils.get_conf_host_os_type('100.97.10.30',
                                                     self.configuration)
        self.assertEqual('0', host_os)

    def create_fake_conf_file(self):
        """Create a fake Config file

        Huawei storage customize a XML configuration file,
        the configuration file is used to set the Huawei storage custom
        parameters, therefore, in the UT test we need to simulate such a
        configuration file
        """
        doc = minidom.Document()

        config = doc.createElement('config')
        doc.appendChild(config)

        storage = doc.createElement('Storage')
        config.appendChild(storage)
        controllerip0 = doc.createElement('ControllerIP0')
        controllerip0_text = doc.createTextNode('10.10.10.1')
        controllerip0.appendChild(controllerip0_text)
        storage.appendChild(controllerip0)
        controllerip1 = doc.createElement('ControllerIP1')
        controllerip1_text = doc.createTextNode('10.10.10.2')
        controllerip1.appendChild(controllerip1_text)
        storage.appendChild(controllerip1)
        username = doc.createElement('UserName')
        username_text = doc.createTextNode('admin')
        username.appendChild(username_text)
        storage.appendChild(username)
        userpassword = doc.createElement('UserPassword')
        userpassword_text = doc.createTextNode('Admin@storage')
        userpassword.appendChild(userpassword_text)
        storage.appendChild(userpassword)
        url = doc.createElement('RestURL')
        url_text = doc.createTextNode('http://100.115.10.69:8082/'
                                      'deviceManager/rest/')
        url.appendChild(url_text)
        storage.appendChild(url)

        storagepool = doc.createElement('StoragePool')
        pool_text = doc.createTextNode('OpenStack_Pool')
        storagepool.appendChild(pool_text)
        storage.appendChild(storagepool)

        lun = doc.createElement('LUN')
        config.appendChild(lun)
        storagepool = doc.createElement('StoragePool')
        pool_text = doc.createTextNode('OpenStack_Pool')
        storagepool.appendChild(pool_text)
        lun.appendChild(storagepool)

        timeout = doc.createElement('Timeout')
        timeout_text = doc.createTextNode('43200')
        timeout.appendChild(timeout_text)
        lun.appendChild(timeout)

        lun_ready_wait_interval = doc.createElement('LUNReadyWaitInterval')
        lun_ready_wait_interval_text = doc.createTextNode('2')
        lun_ready_wait_interval.appendChild(lun_ready_wait_interval_text)
        lun.appendChild(lun_ready_wait_interval)

        iscsi = doc.createElement('iSCSI')
        config.appendChild(iscsi)
        defaulttargetip = doc.createElement('DefaultTargetIP')
        defaulttargetip_text = doc.createTextNode('100.115.10.68')
        defaulttargetip.appendChild(defaulttargetip_text)
        iscsi.appendChild(defaulttargetip)
        initiator = doc.createElement('Initiator')
        initiator.setAttribute('Name', 'iqn.1993-08.debian:01:ec2bff7ac3a3')
        initiator.setAttribute('TargetIP', '192.168.100.2')
        iscsi.appendChild(initiator)

        prefetch = doc.createElement('Prefetch')
        prefetch.setAttribute('Type', '1')
        prefetch.setAttribute('Value', '0')
        lun.appendChild(prefetch)

        host = doc.createElement('Host')
        host.setAttribute('HostIP', '100.97.10.30')
        host.setAttribute('OSType', 'Linux')
        config.appendChild(host)

        fakefile = open(self.fake_conf_file, 'w')
        fakefile.write(doc.toprettyxml(indent=''))
        fakefile.close()

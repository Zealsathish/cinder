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

STATUS_HEALTH = '1'
STATUS_RUNNING = '10'

HOSTGROUP_PREFIX = 'OpenStack_HostGroup_'
LUNGROUP_PREFIX = 'OpenStack_LunGroup_'
MAPPING_VIEW_PREFIX = 'OpenStack_Mapping_View_'
QOS_NAME_PREFIX = 'OpenStack_'

DEFAULT_WAIT_TIMEOUT = 3600 * 24 * 30
DEFAULT_WAIT_INTERVAL = 5
ERROR_CONNECT_TO_SERVER = -403
ERROR_UNAUTHORIZED_TO_SERVER = -401

MAX_HOSTNAME_LENTH = 31

OS_TYPE = {'Linux': '0',
           'Windows': '1',
           'Solaris': '2',
           'HP-UX': '3',
           'AIX': '4',
           'XenServer': '5',
           'Mac OS X': '6',
           'VMware ESX': '7'}

HUAWEI_VALID_KEYS = ['maxIOPS', 'minIOPS', 'minBandWidth',
                     'maxBandWidth', 'latency', 'IOType']

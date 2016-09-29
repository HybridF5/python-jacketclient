# Copyright 2016
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

"""
sub volume type interface.
"""

from jacketclient import base


class SubVolumeType(base.Resource):
    """image mapper."""

    NAME_ATTR = 'name'

    def __repr__(self):
        return "<VolumeType: %s>" % self.name


class SubVolumeTypeManager(base.ManagerWithFind):
    """Manager :class:`sub volume type` resources."""

    resource_class = SubVolumeType

    def list(self):
        """
        list all sub flavor
        :return:
        """

        return self._list("/sub_volume_type/detail", "sub_volume_types")

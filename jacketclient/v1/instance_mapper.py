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
instance mapper interface.
"""

from six.moves.urllib import parse

from jacketclient import base
from jacketclient import exceptions
from jacketclient.i18n import _


class InstanceMapper(base.Resource):
    """image mapper."""

    def __repr__(self):
        return "<Instance Mapper: %s>" % self.name


class InstanceMapperManager(base.ManagerWithFind):
    """Manager :class:`instance mapper` resources."""

    resource_class = InstanceMapper

    def list(self, detailed=True, limit=None):
        """
        list all instance mapper
        :param detailed: detail
        :param limit:
        :return:
        """

        qparams = {}

        if limit:
            qparams['limit'] = int(limit)

        qparams = sorted(qparams.items(), key=lambda x: x[0])
        query_string = "?%s" % parse.urlencode(qparams) if qparams else ""

        detail = ""
        if detailed:
            detail = "/detail"

        return self._list("/instance_mapper%s%s" % (detail, query_string),
                          "instances_mapper")

    def get(self, instance_id):
        """Get a specific instance mapper."""

        return self._get("/instance_mapper/%s" % instance_id, "instance_mapper")

    @staticmethod
    def _build_body(instance_id, dest_instance_id, project_id=None, **kwargs):

        instance_mapper = {}

        if instance_id is None:
            raise exceptions.CommandError(_("instance id must be specified."))

        instance_mapper['instance_id'] = instance_id
        if dest_instance_id:
            instance_mapper['dest_instance_id'] = dest_instance_id

        if project_id:
            instance_mapper['project_id'] = project_id

        for key, value in kwargs.iteritems():
            if value:
                instance_mapper[key] = value

        return {'instance_mapper': instance_mapper}

    def create(self, instance_id, dest_instance_id, project_id=None, **kwargs):
        """create instance mapper
        :param instance_id:
        :param dest_instance_id:
        :param project_id:
        :param kwargs:
        :return:
        """

        if dest_instance_id is None:
            raise exceptions.CommandError(
                _("dest instance id must be specified."))

        body = self._build_body(instance_id, dest_instance_id,
                                project_id=project_id, **kwargs)

        return self._create("/instance_mapper", body, "instance_mapper")

    def delete(self, instance_id):

        return self._delete("/instance_mapper/%s" % instance_id)

    def update(self, instance_id, dest_instance_id, project_id=None,
               set_properties=None, unset_properties=None):
        """update instance mapper
        :param instance_id:
        :param dest_instance_id:
        :param project_id:
        :param kwargs:
        :return:
        """

        kwargs = {'set_properties': set_properties,
                  'unset_properties': unset_properties}

        body = self._build_body(instance_id, dest_instance_id,
                                project_id=project_id, **kwargs)

        if 'instance_id' in body['instance_mapper']:
            del body['instance_mapper']['instance_id']

        return self._update("/instance_mapper/%s" % instance_id, body,
                            "instance_mapper")

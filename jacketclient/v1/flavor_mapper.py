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
flavor mapper interface.
"""

from six.moves.urllib import parse

from jacketclient import base
from jacketclient import exceptions
from jacketclient.i18n import _


class FlavorMapper(base.Resource):
    """image mapper."""

    def __repr__(self):
        return "<Flavor Mapper: %s>" % self.name


class FlavorMapperManager(base.ManagerWithFind):
    """Manager :class:`flavor mapper` resources."""

    resource_class = FlavorMapper

    def list(self, detailed=True, limit=None):
        """
        list all flavor mapper
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

        return self._list("/flavor_mapper%s%s" % (detail, query_string), "flavors_mapper")

    def get(self, flavor_id):
        """Get a specific flavor mapper."""

        return self._get("/flavor_mapper/%s" % flavor_id, "flavor_mapper")

    @staticmethod
    def _build_body(flavor_id, dest_flavor_id, project_id=None, **kwargs):

        flavor_mapper = {}

        if flavor_id is None:
            raise exceptions.CommandError(_("flavor id must be specified."))

        if dest_flavor_id is None:
            raise exceptions.CommandError(_("dest flavor id must be specified."))

        flavor_mapper['flavor_id'] = flavor_id
        flavor_mapper['dest_flavor_id'] = dest_flavor_id

        if project_id:
            flavor_mapper['project_id'] = project_id

        for key, value in kwargs.iteritems():
            if value:
                flavor_mapper[key] = value

        return {'flavor_mapper': flavor_mapper}

    def create(self, flavor_id, dest_flavor_id, project_id=None, **kwargs):
        """create flavor mapper
        :param flavor_id:
        :param dest_flavor_id:
        :param project_id:
        :param kwargs:
        :return:
        """

        body = self._build_body(flavor_id, dest_flavor_id, project_id=project_id, **kwargs)

        return self._create("/flavor_mapper", body, "flavor_mapper")

    def delete(self, flavor_id):

        return self._delete("/flavor_mapper/%s" % flavor_id)

    def update(self, flavor_id, dest_flavor_id, project_id=None, **kwargs):
        """update flavor mapper
        :param flavor_id:
        :param dest_flavor_id:
        :param project_id:
        :param kwargs:
        :return:
        """

        body = self._build_body(flavor_id, dest_flavor_id, project_id=project_id, **kwargs)

        if 'flavor_id' in body['flavor_mapper']:
            del body['flavor_mapper']['flavor_id']

        return self._update("/flavor_mapper/%s" % flavor_id, body, "flavor_mapper")

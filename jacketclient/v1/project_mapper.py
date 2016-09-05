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
project mapper interface.
"""

from six.moves.urllib import parse

from jacketclient import base
from jacketclient import exceptions
from jacketclient.i18n import _


class ProjectMapper(base.Resource):
    """project mapper."""

    def __repr__(self):
        return "<Project Mapper: %s>" % self.name


class ProjectMapperManager(base.ManagerWithFind):
    """Manager :class:`project mapper` resources."""

    def list(self, detailed=True, limit=None):
        """
        list all project mapper
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

        return self._list("/project_mapper%s%s" % (detail, query_string), "project_mapper")

    def get(self, project_id):
        """Get a specific project mapper."""

        return self._get("/project_mapper/%s" % project_id, "project_mapper")

    @staticmethod
    def _build_body(self, project_id, dest_project_id, **kwargs):

        project_mapper = {}

        if project_id is None:
            raise exceptions.CommandError(_("project id must be specified."))

        if dest_project_id is None:
            raise exceptions.CommandError(_("dest project id must be specified."))

        project_mapper['project_id'] = project_id
        project_mapper['dest_project_id'] = dest_project_id

        for key, value in kwargs.iteritems():
            if value:
                project_mapper[key] = value

        return {'project_mapper': project_mapper}

    def create(self, project_id, dest_project_id, **kwargs):
        """create project mapper
        :param project_id:
        :param dest_project_id:
        :param kwargs:
        :return:
        """

        body = self._build_body(project_id, dest_project_id, **kwargs)

        return self._create("/project_mapper", body, "project_mapper")

    def delete(self, project_id):

        return self._delete("/project_mapper/%s" % project_id)

    def update(self, project_id, dest_project_id, **kwargs):
        """update project mapper
        :param project_id:
        :param dest_project_id:
        :param kwargs:
        :return:
        """

        body = self._build_body(project_id, dest_project_id, **kwargs)

        return self._update("/project_mapper", body, "project_mapper")

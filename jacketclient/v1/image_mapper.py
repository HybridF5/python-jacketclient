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
image mapper interface.
"""

from six.moves.urllib import parse

from jacketclient import base
from jacketclient import exceptions
from jacketclient.i18n import _


class ImageMapper(base.Resource):
    """image mapper."""

    def __repr__(self):
        return "<Image Mapper: %s>" % self.name


class ImageMapperManager(base.ManagerWithFind):
    """Manager :class:`image mapper` resources."""

    def list(self, detailed=True, limit=None):
        """
        list all image mapper
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

        return self._list("/image_mapper%s%s" % (detail, query_string), "image_mapper")

    def get(self, image_id):
        """Get a specific image mapper."""

        return self._get("/image_mapper/%s" % image_id, "image_mapper")

    @staticmethod
    def _build_body(self, image_id, dest_image_id, project_id=None, **kwargs):

        image_mapper = {}

        if image_id is None:
            raise exceptions.CommandError(_("image id must be specified."))

        if dest_image_id is None:
            raise exceptions.CommandError(_("dest image id must be specified."))

        image_mapper['image_id'] = image_id
        image_mapper['dest_image_id'] = dest_image_id

        if project_id:
            image_mapper['project_id'] = project_id

        for key, value in kwargs.iteritems():
            if value:
                image_mapper[key] = value

        return {'image_mapper': image_mapper}

    def create(self, image_id, dest_image_id, project_id=None, **kwargs):
        """create image mapper
        :param image_id:
        :param dest_image_id:
        :param project_id:
        :param kwargs:
        :return:
        """

        body = self._build_body(image_id, dest_image_id, project_id=project_id, **kwargs)

        return self._create("/image_mapper", body, "image_mapper")

    def delete(self, image_id):

        return self._delete("/image_mapper/%s" % image_id)

    def update(self, image_id, dest_image_id, project_id=None, **kwargs):
        """update image mapper
        :param image_id:
        :param dest_image_id:
        :param project_id:
        :param kwargs:
        :return:
        """

        body = self._build_body(image_id, dest_image_id, project_id=project_id, **kwargs)

        return self._update("/image_mapper", body, "image_mapper")

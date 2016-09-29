# Copyright 2010 Jacob Kaplan-Moss

# Copyright 2011 OpenStack Foundation
# Copyright 2013 IBM Corp.
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

from __future__ import print_function

import argparse
import copy
import datetime
import functools
import getpass
import locale
import logging
import os
import sys
import time
import warnings

from oslo_utils import encodeutils
from oslo_utils import netutils
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
import six

import jacketclient
from jacketclient import api_versions
from jacketclient import base
from jacketclient import client
from jacketclient import exceptions
from jacketclient.i18n import _
from jacketclient.i18n import _LE
from jacketclient import shell
from jacketclient import utils


logger = logging.getLogger(__name__)

DEFAULT_IMAGE_MAPPER_KEYS = ['image_id', 'dest_image_id', 'project_id']
DEFAULT_FLAVOR_MAPPER_KEYS = ['flavor_id', 'dest_flavor_id', 'project_id']
DEFAULT_PROJECT_MAPPER_KEYS = ['project_id', 'dest_project_id']


# NOTE(mriedem): Remove this along with the deprecated commands in the first
# python-jacketclient release AFTER the jacket server 15.0.0 'O' release.
def emit_image_deprecation_warning(command_name):
    print('WARNING: Command %s is deprecated and will be removed after Nova '
          '15.0.0 is released. Use python-glanceclient or openstackclient '
          'instead.' % command_name, file=sys.stderr)


def _key_value_pairing(text):
    try:
        (k, v) = text.split('=', 1)
        return (k, v)
    except ValueError:
        msg = _LE("'%s' is not in the format of 'key=value'") % text
        raise argparse.ArgumentTypeError(msg)


def _property_parsing(raw_properties):
    return dict(_key_value_pairing(datum) for datum in raw_properties)


def _columns_get(objs, default_columns):
    columns = set()
    for item in objs:
        keys = item._info.keys()
        keys_set = set(keys)
        columns = columns | keys_set
    columns = list(columns)

    if not columns:
        return default_columns
    else:
        return columns


def _print_flavor_extra_specs(flavor):
    try:
        return flavor.get_keys()
    except exceptions.NotFound:
        return "N/A"


def _translate_keys(collection, convert):
    for item in collection:
        keys = item.__dict__.keys()
        for from_key, to_key in convert:
            if from_key in keys and to_key not in keys:
                setattr(item, to_key, item._info[from_key])


def _translate_flavor_keys(collection):
    _translate_keys(collection, [('ram', 'memory_mb')])


def _print_flavor_list(flavors, show_extra_specs=False):
    _translate_flavor_keys(flavors)

    headers = [
        'ID',
        'Name',
        'Memory_MB',
        'Disk',
        'Ephemeral',
        'Swap',
        'VCPUs',
        'RXTX_Factor',
        'Is_Public',
    ]

    if show_extra_specs:
        formatters = {'extra_specs': _print_flavor_extra_specs}
        headers.append('extra_specs')
    else:
        formatters = {}

    utils.print_list(flavors, headers, formatters)


def _print_volume_type_list(vtypes):
    utils.print_list(vtypes, ['ID', 'Name', 'Description', 'Is_Public'])


@utils.arg(
    'image_id',
    metavar='<image_id>',
    help=_("ID of image (see 'glance image-list')."))
@utils.arg(
    'dest_image_id',
    metavar='<dest_image_id>',
    help=_("ID of dest image. "))
@utils.arg(
    '--project-id',
    default=None,
    metavar='<project-id>',
    help=_("ID of project (see 'keystone tenant-list')."))
@utils.arg(
    '--property',
    metavar="<key=value>",
    action='append',
    dest='property',
    default=[],
    help=_("Arbitrary property to associate with image id."
           "May be used multiple times."))
def do_image_mapper_create(cs, args):
    """create a new image mapper."""

    raw_properties = args.property
    properties = _property_parsing(raw_properties)

    image_mapper = cs.image_mapper.create(args.image_id, args.dest_image_id, args.project_id,
                           **properties)
    utils.print_dict(image_mapper._info)


def do_image_mapper_list(cs, args):
    """list all image mapper"""

    image_mappers = cs.image_mapper.list()

    columns = _columns_get(image_mappers, DEFAULT_IMAGE_MAPPER_KEYS)
    utils.print_list(image_mappers, columns)

@utils.arg(
    'image_id',
    default=None,
    metavar='<image_id>',
    help=_("ID of image (see 'glance image-list')."))
def do_image_mapper_show(cs, args):
    """show image mapper"""

    image_mapper = cs.image_mapper.get(args.image_id)

    utils.print_dict(image_mapper._info)


@utils.arg(
    'image_id',
    metavar='<image_id>',
    nargs='+',
    help=_("ID of image (see 'glance image-list')."))
def do_image_mapper_delete(cs, args):
    """delete image mapper"""

    utils.do_action_on_many(
        lambda s: cs.image_mapper.delete(s),
        args.image_id,
        _("Request to delete image mapper %s has been accepted."),
        _("Unable to delete the specified image mapper(s)."))


@utils.arg(
    'image_id',
    metavar='<image_id>',
    help=_("ID of image (see 'glance image-list')."))
@utils.arg(
    'dest_image_id',
    default=None,
    metavar='<dest_image_id>',
    help=_("ID of dest image. "))
@utils.arg(
    '--project-id',
    default=None,
    metavar='<project-id>',
    help=_("ID of project (see 'keystone tenant-list')."))
@utils.arg(
    '--property',
    metavar="<key=value>",
    action='append',
    dest='property',
    default=[],
    help=_("Arbitrary property to associate with image id."
           "May be used multiple times."))
def do_image_mapper_update(cs, args):
    """create a new image mapper."""

    raw_properties = args.property
    properties = _property_parsing(raw_properties)

    image_mapper = cs.image_mapper.update(args.image_id, args.dest_image_id, args.project_id,
                                          **properties)
    utils.print_dict(image_mapper._info)


@utils.arg(
    'flavor_id',
    metavar='<flavor_id>',
    help=_("ID of flavor (see 'nova flavor-list')."))
@utils.arg(
    'dest_flavor_id',
    metavar='<dest_flavor_id>',
    help=_("ID of dest flavor. "))
@utils.arg(
    '--project-id',
    default=None,
    metavar='<project-id>',
    help=_("ID of project (see 'keystone tenant-list')."))
@utils.arg(
    '--property',
    metavar="<key=value>",
    action='append',
    dest='property',
    default=[],
    help=_("Arbitrary property to associate with flavor id."
           "May be used multiple times."))
def do_flavor_mapper_create(cs, args):
    """create a new flavor mapper."""

    raw_properties = args.property
    properties = _property_parsing(raw_properties)
    print(args)
    flavor_mapper = cs.flavor_mapper.create(args.flavor_id, args.dest_flavor_id, args.project_id,
                           **properties)
    utils.print_dict(flavor_mapper._info)


def do_flavor_mapper_list(cs, args):
    """list all flavor mapper"""

    flavor_mappers = cs.flavor_mapper.list()

    columns = _columns_get(flavor_mappers, DEFAULT_FLAVOR_MAPPER_KEYS)
    utils.print_list(flavor_mappers, columns)

@utils.arg(
    'flavor_id',
    default=None,
    metavar='<flavor_id>',
    help=_("ID of flavor (see 'nova flavor-list')."))
def do_flavor_mapper_show(cs, args):
    """show flavor mapper"""

    flavor_mapper = cs.flavor_mapper.get(args.flavor_id)

    utils.print_dict(flavor_mapper._info)


@utils.arg(
    'flavor_id',
    metavar='<flavor_id>',
    nargs='+',
    help=_("ID of flavor (see 'nova flavor-list')."))
def do_flavor_mapper_delete(cs, args):
    """delete flavor mapper"""

    utils.do_action_on_many(
        lambda s: cs.flavor_mapper.delete(s),
        args.flavor_id,
        _("Request to delete flavor mapper %s has been accepted."),
        _("Unable to delete the specified flavor mapper(s)."))


@utils.arg(
    'flavor_id',
    metavar='<flavor_id>',
    help=_("ID of flavor (see 'nova flavor-list')."))
@utils.arg(
    'dest_flavor_id',
    default=None,
    metavar='<dest_flavor_id>',
    help=_("ID of dest flavor. "))
@utils.arg(
    '--project-id',
    default=None,
    metavar='<project-id>',
    help=_("ID of project (see 'keystone tenant-list')."))
@utils.arg(
    '--property',
    metavar="<key=value>",
    action='append',
    dest='property',
    default=[],
    help=_("Arbitrary property to associate with flavor id."
           "May be used multiple times."))
def do_flavor_mapper_update(cs, args):
    """create a new flavor mapper."""

    raw_properties = args.property
    properties = _property_parsing(raw_properties)

    flavor_mapper = cs.flavor_mapper.update(args.flavor_id, args.dest_flavor_id, args.project_id,
                                          **properties)
    utils.print_dict(flavor_mapper._info)



@utils.arg(
    'project_id',
    metavar='<project_id>',
    help=_("ID of project (see 'keystone project-list')."))
@utils.arg(
    'dest_project_id',
    metavar='<dest_project_id>',
    help=_("ID of dest project. "))
@utils.arg(
    '--property',
    metavar="<key=value>",
    action='append',
    dest='property',
    default=[],
    help=_("Arbitrary property to associate with project id."
           "May be used multiple times."))
def do_project_mapper_create(cs, args):
    """create a new project mapper."""

    raw_properties = args.property
    properties = _property_parsing(raw_properties)

    project_mapper = cs.project_mapper.create(args.project_id, args.dest_project_id,
                           **properties)
    utils.print_dict(project_mapper._info)


def do_project_mapper_list(cs, args):
    """list all project mapper"""

    project_mappers = cs.project_mapper.list()

    columns = _columns_get(project_mappers, DEFAULT_PROJECT_MAPPER_KEYS)
    utils.print_list(project_mappers, columns)

@utils.arg(
    'project_id',
    default=None,
    metavar='<project_id>',
    help=_("ID of project (see 'keystone project-list')."))
def do_project_mapper_show(cs, args):
    """show project mapper"""

    project_mapper = cs.project_mapper.get(args.project_id)

    utils.print_dict(project_mapper._info)


@utils.arg(
    'project_id',
    metavar='<project_id>',
    nargs='+',
    help=_("ID of project (see 'keystone project-list')."))
def do_project_mapper_delete(cs, args):
    """delete project mapper"""

    utils.do_action_on_many(
        lambda s: cs.project_mapper.delete(s),
        args.project_id,
        _("Request to delete project mapper %s has been accepted."),
        _("Unable to delete the specified project mapper(s)."))


@utils.arg(
    'project_id',
    metavar='<project_id>',
    help=_("ID of project (see 'keystone project-list')."))
@utils.arg(
    'dest_project_id',
    default=None,
    metavar='<dest-project-id>',
    help=_("ID of dest project. "))
@utils.arg(
    '--property',
    metavar="<key=value>",
    action='append',
    dest='property',
    default=[],
    help=_("Arbitrary property to associate with project id."
           "May be used multiple times."))
def do_project_mapper_update(cs, args):
    """create a new project mapper."""

    raw_properties = args.property
    properties = _property_parsing(raw_properties)

    project_mapper = cs.project_mapper.update(args.project_id, args.dest_project_id,
                                              **properties)
    utils.print_dict(project_mapper._info)


def do_sub_flavor_list(cs, args):
    sub_flavors = cs.sub_flavor.list()

    _print_flavor_list(sub_flavors)

def do_sub_volume_type_list(cs, args):
    sub_volume_types = cs.sub_volume_type.list()

    _print_volume_type_list(sub_volume_types)

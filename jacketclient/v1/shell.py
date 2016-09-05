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


# NOTE(mriedem): Remove this along with the deprecated commands in the first
# python-jacketclient release AFTER the jacket server 15.0.0 'O' release.
def emit_image_deprecation_warning(command_name):
    print('WARNING: Command %s is deprecated and will be removed after Nova '
          '15.0.0 is released. Use python-glanceclient or openstackclient '
          'instead.' % command_name, file=sys.stderr)


def deprecated_network(fn):
    @functools.wraps(fn)
    def wrapped(cs, *args, **kwargs):
        command_name = '-'.join(fn.__name__.split('_')[1:])
        print('WARNING: Command %s is deprecated and will be removed '
              'after Nova 15.0.0 is released. Use python-neutronclient '
              'or python-openstackclient instead.' % command_name,
              file=sys.stderr)
        # The network proxy API methods were deprecated in 2.36 and will return
        # a 404 so we fallback to 2.35 to maintain a transition for CLI users.
        want_version = api_versions.APIVersion('2.35')
        cur_version = cs.api_version
        if cs.api_version > want_version:
            cs.api_version = want_version
        try:
            return fn(cs, *args, **kwargs)
        finally:
            cs.api_version = cur_version
    wrapped.__doc__ = 'DEPRECATED: ' + fn.__doc__
    return wrapped


def _key_value_pairing(text):
    try:
        (k, v) = text.split('=', 1)
        return (k, v)
    except ValueError:
        msg = _LE("'%s' is not in the format of 'key=value'") % text
        raise argparse.ArgumentTypeError(msg)


def _meta_parsing(metadata):
    return dict(v.split('=', 1) for v in metadata)



@utils.arg(
    '--image',
    default=None,
    metavar='<flavor>',
    help=_("Name or ID of flavor (see 'nova flavor-list')."))
@utils.arg(
    '--image',
    default=None,
    metavar='<image>',
    help=_("Name or ID of image (see 'glance image-list'). "))
@utils.arg(
    '--image-with',
    default=[],
    type=_key_value_pairing,
    action='append',
    metavar='<key=value>',
    help=_("Image metadata property (see 'glance image-show'). "))
@utils.arg(
    '--boot-volume',
    default=None,
    metavar="<volume_id>",
    help=_("Volume ID to boot from."))
@utils.arg(
    '--snapshot',
    default=None,
    metavar="<snapshot_id>",
    help=_("Snapshot ID to boot from (will create a volume)."))
@utils.arg(
    '--min-count',
    default=None,
    type=int,
    metavar='<number>',
    help=_("Boot at least <number> servers (limited by quota)."))
@utils.arg(
    '--max-count',
    default=None,
    type=int,
    metavar='<number>',
    help=_("Boot up to <number> servers (limited by quota)."))
@utils.arg(
    '--meta',
    metavar="<key=value>",
    action='append',
    default=[],
    help=_("Record arbitrary key/value metadata to /meta_data.json "
           "on the metadata server. Can be specified multiple times."))
@utils.arg(
    '--file',
    metavar="<dst-path=src-path>",
    action='append',
    dest='files',
    default=[],
    help=_("Store arbitrary files from <src-path> locally to <dst-path> "
           "on the new server. Limited by the injected_files quota value."))
@utils.arg(
    '--key-name',
    default=os.environ.get('NOVACLIENT_DEFAULT_KEY_NAME'),
    metavar='<key-name>',
    help=_("Key name of keypair that should be created earlier with \
           the command keypair-add."))
@utils.arg('name', metavar='<name>', help=_('Name for the new server.'))
@utils.arg(
    '--user-data',
    default=None,
    metavar='<user-data>',
    help=_("user data file to pass to be exposed by the metadata server."))
@utils.arg(
    '--availability-zone',
    default=None,
    metavar='<availability-zone>',
    help=_("The availability zone for server placement."))
@utils.arg(
    '--security-groups',
    default=None,
    metavar='<security-groups>',
    help=_("Comma separated list of security group names."))
@utils.arg(
    '--block-device-mapping',
    metavar="<dev-name=mapping>",
    action='append',
    default=[],
    help=_("Block device mapping in the format "
           "<dev-name>=<id>:<type>:<size(GB)>:<delete-on-terminate>."))
@utils.arg(
    '--block-device',
    metavar="key1=value1[,key2=value2...]",
    action='append',
    default=[],
    start_version='2.0',
    end_version='2.31',
    help=_("Block device mapping with the keys: "
           "id=UUID (image_id, snapshot_id or volume_id only if using source "
           "image, snapshot or volume) "
           "source=source type (image, snapshot, volume or blank), "
           "dest=destination type of the block device (volume or local), "
           "bus=device's bus (e.g. uml, lxc, virtio, ...; if omitted, "
           "hypervisor driver chooses a suitable default, "
           "honoured only if device type is supplied) "
           "type=device type (e.g. disk, cdrom, ...; defaults to 'disk') "
           "device=name of the device (e.g. vda, xda, ...; "
           "if omitted, hypervisor driver chooses suitable device "
           "depending on selected bus; note the libvirt driver always "
           "uses default device names), "
           "size=size of the block device in MB(for swap) and in "
           "GB(for other formats) "
           "(if omitted, hypervisor driver calculates size), "
           "format=device will be formatted (e.g. swap, ntfs, ...; optional), "
           "bootindex=integer used for ordering the boot disks "
           "(for image backed instances it is equal to 0, "
           "for others need to be specified) and "
           "shutdown=shutdown behaviour (either preserve or remove, "
           "for local destination set to remove)."))
@utils.arg(
    '--block-device',
    metavar="key1=value1[,key2=value2...]",
    action='append',
    default=[],
    start_version='2.32',
    help=_("Block device mapping with the keys: "
           "id=UUID (image_id, snapshot_id or volume_id only if using source "
           "image, snapshot or volume) "
           "source=source type (image, snapshot, volume or blank), "
           "dest=destination type of the block device (volume or local), "
           "bus=device's bus (e.g. uml, lxc, virtio, ...; if omitted, "
           "hypervisor driver chooses a suitable default, "
           "honoured only if device type is supplied) "
           "type=device type (e.g. disk, cdrom, ...; defaults to 'disk') "
           "device=name of the device (e.g. vda, xda, ...; "
           "tag=device metadata tag (optional) "
           "if omitted, hypervisor driver chooses suitable device "
           "depending on selected bus; note the libvirt driver always "
           "uses default device names), "
           "size=size of the block device in MB(for swap) and in "
           "GB(for other formats) "
           "(if omitted, hypervisor driver calculates size), "
           "format=device will be formatted (e.g. swap, ntfs, ...; optional), "
           "bootindex=integer used for ordering the boot disks "
           "(for image backed instances it is equal to 0, "
           "for others need to be specified) and "
           "shutdown=shutdown behaviour (either preserve or remove, "
           "for local destination set to remove)."))
@utils.arg(
    '--swap',
    metavar="<swap_size>",
    default=None,
    help=_("Create and attach a local swap block device of <swap_size> MB."))
@utils.arg(
    '--ephemeral',
    metavar="size=<size>[,format=<format>]",
    action='append',
    default=[],
    help=_("Create and attach a local ephemeral block device of <size> GB "
           "and format it to <format>."))
@utils.arg(
    '--hint',
    action='append',
    dest='scheduler_hints',
    default=[],
    metavar='<key=value>',
    help=_("Send arbitrary key/value pairs to the scheduler for custom "
           "use."))
@utils.arg(
    '--nic',
    metavar="<net-id=net-uuid,net-name=network-name,v4-fixed-ip=ip-addr,"
            "v6-fixed-ip=ip-addr,port-id=port-uuid>",
    action='append',
    dest='nics',
    default=[],
    start_version='2.0',
    end_version='2.31',
    help=_("Create a NIC on the server. "
           "Specify option multiple times to create multiple NICs. "
           "net-id: attach NIC to network with this UUID "
           "net-name: attach NIC to network with this name "
           "(either port-id or net-id or net-name must be provided), "
           "v4-fixed-ip: IPv4 fixed address for NIC (optional), "
           "v6-fixed-ip: IPv6 fixed address for NIC (optional), "
           "port-id: attach NIC to port with this UUID "
           "(either port-id or net-id must be provided)."))
@utils.arg(
    '--nic',
    metavar="<net-id=net-uuid,net-name=network-name,v4-fixed-ip=ip-addr,"
            "v6-fixed-ip=ip-addr,port-id=port-uuid>",
    action='append',
    dest='nics',
    default=[],
    start_version='2.32',
    help=_("Create a NIC on the server. "
           "Specify option multiple times to create multiple nics. "
           "net-id: attach NIC to network with this UUID "
           "net-name: attach NIC to network with this name "
           "(either port-id or net-id or net-name must be provided), "
           "v4-fixed-ip: IPv4 fixed address for NIC (optional), "
           "v6-fixed-ip: IPv6 fixed address for NIC (optional), "
           "port-id: attach NIC to port with this UUID "
           "tag: interface metadata tag (optional) "
           "(either port-id or net-id must be provided)."))
@utils.arg(
    '--config-drive',
    metavar="<value>",
    dest='config_drive',
    default=False,
    help=_("Enable config drive."))
@utils.arg(
    '--poll',
    dest='poll',
    action="store_true",
    default=False,
    help=_('Report the new server boot progress until it completes.'))
@utils.arg(
    '--admin-pass',
    dest='admin_pass',
    metavar='<value>',
    default=None,
    help=_('Admin password for the instance.'))
@utils.arg(
    '--access-ip-v4',
    dest='access_ip_v4',
    metavar='<value>',
    default=None,
    help=_('Alternative access IPv4 of the instance.'))
@utils.arg(
    '--access-ip-v6',
    dest='access_ip_v6',
    metavar='<value>',
    default=None,
    help=_('Alternative access IPv6 of the instance.'))
@utils.arg(
    '--description',
    metavar='<description>',
    dest='description',
    default=None,
    help=_('Description for the server.'),
    start_version="2.19")
def do_boot(cs, args):
    """Boot a new server."""
    boot_args, boot_kwargs = _boot(cs, args)

    extra_boot_kwargs = utils.get_resource_manager_extra_kwargs(do_boot, args)
    boot_kwargs.update(extra_boot_kwargs)

    server = cs.servers.create(*boot_args, **boot_kwargs)
    _print_server(cs, args, server)

    if args.poll:
        _poll_for_status(cs.servers.get, server.id, 'building', ['active'])

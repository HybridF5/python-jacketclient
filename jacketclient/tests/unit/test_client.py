# Copyright 2012 OpenStack Foundation
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


import json
import logging

import fixtures
from keystoneauth1 import adapter
import mock
import requests

import jacketclient.api_versions
import jacketclient.client
import jacketclient.extension
from jacketclient.tests.unit import utils
import jacketclient.v1.client


class ClientConnectionPoolTest(utils.TestCase):

    @mock.patch("keystoneauth1.session.TCPKeepAliveAdapter")
    def test_get(self, mock_http_adapter):
        mock_http_adapter.side_effect = lambda: mock.Mock()
        pool = jacketclient.client._ClientConnectionPool()
        self.assertEqual(pool.get("abc"), pool.get("abc"))
        self.assertNotEqual(pool.get("abc"), pool.get("def"))


class ClientTest(utils.TestCase):

    def test_client_with_timeout(self):
        auth_url = "http://example.com"
        instance = jacketclient.client.HTTPClient(user='user',
                                                password='password',
                                                projectid='project',
                                                timeout=2,
                                                auth_url=auth_url)
        self.assertEqual(2, instance.timeout)
        mock_request = mock.Mock()
        mock_request.return_value = requests.Response()
        mock_request.return_value.status_code = 200
        mock_request.return_value.headers = {
            'x-server-management-url': 'example.com',
            'x-auth-token': 'blah',
        }
        with mock.patch('requests.request', mock_request):
            instance.authenticate()
            requests.request.assert_called_with(
                mock.ANY, mock.ANY, timeout=2, headers=mock.ANY,
                verify=mock.ANY)

    def test_client_reauth(self):
        auth_url = "http://www.example.com"
        instance = jacketclient.client.HTTPClient(user='user',
                                                password='password',
                                                projectid='project',
                                                timeout=2,
                                                auth_url=auth_url)
        instance.auth_token = 'foobar'
        mgmt_url = "http://mgmt.example.com"
        instance.management_url = mgmt_url
        instance.get_service_url = mock.Mock(return_value=mgmt_url)
        instance.version = 'v1.0'
        mock_request = mock.Mock()
        mock_request.side_effect = jacketclient.exceptions.Unauthorized(401)
        with mock.patch('requests.request', mock_request):
            try:
                instance.get('/servers/detail')
            except Exception:
                pass
            get_headers = {'X-Auth-Project-Id': 'project',
                           'X-Auth-Token': 'foobar',
                           'User-Agent': 'python-jacketclient',
                           'Accept': 'application/json'}
            reauth_headers = {'Content-Type': 'application/json',
                              'Accept': 'application/json',
                              'User-Agent': 'python-jacketclient'}
            data = {
                "auth": {
                    "tenantName": "project",
                    "passwordCredentials": {
                        "username": "user",
                        "password": "password"
                    }
                }
            }

            expected = [mock.call('GET',
                                  'http://mgmt.example.com/servers/detail',
                                  timeout=mock.ANY,
                                  headers=get_headers,
                                  verify=mock.ANY),
                        mock.call('POST', 'http://www.example.com/tokens',
                                  timeout=mock.ANY,
                                  headers=reauth_headers,
                                  allow_redirects=mock.ANY,
                                  data=mock.ANY,
                                  verify=mock.ANY)]
            self.assertEqual(expected, mock_request.call_args_list)
            token_post_call = mock_request.call_args_list[1]
            self.assertEqual(data, json.loads(token_post_call[1]['data']))

    @mock.patch.object(jacketclient.client.HTTPClient, 'request',
                       return_value=(200, "{'versions':[]}"))
    def _check_version_url(self, management_url, version_url, mock_request):
        projectid = '25e469aa1848471b875e68cde6531bc5'
        auth_url = "http://example.com"
        instance = jacketclient.client.HTTPClient(user='user',
                                                password='password',
                                                projectid=projectid,
                                                auth_url=auth_url)
        instance.auth_token = 'foobar'
        instance.management_url = management_url % projectid
        mock_get_service_url = mock.Mock(return_value=instance.management_url)
        instance.get_service_url = mock_get_service_url
        instance.version = 'v1.0'

        # If passing None as the part of url, a client accesses the url which
        # doesn't include "v1/<projectid>" for getting API version info.
        instance.get(None)
        mock_request.assert_called_once_with(version_url, 'GET',
                                             headers=mock.ANY)
        mock_request.reset_mock()

        # Otherwise, a client accesses the url which includes "v1/<projectid>".
        instance.get('servers')
        url = instance.management_url + 'servers'
        mock_request.assert_called_once_with(url, 'GET', headers=mock.ANY)

    def test_client_version_url(self):
        self._check_version_url('http://example.com/v1/%s',
                                'http://example.com/')
        self._check_version_url('http://example.com/v1.1/%s',
                                'http://example.com/')
        self._check_version_url('http://example.com/v3.785/%s',
                                'http://example.com/')

    def test_client_version_url_with_project_name(self):
        self._check_version_url('http://example.com/jacket/v1/%s',
                                'http://example.com/jacket/')
        self._check_version_url('http://example.com/jacket/v1.1/%s',
                                'http://example.com/jacket/')
        self._check_version_url('http://example.com/jacket/v3.785/%s',
                                'http://example.com/jacket/')

    def test_get_client_class_v2(self):
        output = jacketclient.client.get_client_class('2')
        self.assertEqual(output, jacketclient.v1.client.Client)

    def test_get_client_class_v2_int(self):
        output = jacketclient.client.get_client_class(2)
        self.assertEqual(output, jacketclient.v1.client.Client)

    def test_get_client_class_v1_1(self):
        output = jacketclient.client.get_client_class('1.1')
        self.assertEqual(output, jacketclient.v1.client.Client)

    def test_get_client_class_unknown(self):
        self.assertRaises(jacketclient.exceptions.UnsupportedVersion,
                          jacketclient.client.get_client_class, '0')

    def test_get_client_class_latest(self):
        self.assertRaises(jacketclient.exceptions.UnsupportedVersion,
                          jacketclient.client.get_client_class, 'latest')
        self.assertRaises(jacketclient.exceptions.UnsupportedVersion,
                          jacketclient.client.get_client_class, '2.latest')

    def test_client_with_os_cache_enabled(self):
        cs = jacketclient.client.Client("2", "user", "password", "project_id",
                                      auth_url="foo/v1", os_cache=True)
        self.assertTrue(cs.os_cache)
        self.assertTrue(cs.client.os_cache)

    def test_client_with_os_cache_disabled(self):
        cs = jacketclient.client.Client("2", "user", "password", "project_id",
                                      auth_url="foo/v1", os_cache=False)
        self.assertFalse(cs.os_cache)
        self.assertFalse(cs.client.os_cache)

    def test_client_with_no_cache_enabled(self):
        cs = jacketclient.client.Client("2", "user", "password", "project_id",
                                      auth_url="foo/v1", no_cache=True)
        self.assertFalse(cs.os_cache)
        self.assertFalse(cs.client.os_cache)

    def test_client_with_no_cache_disabled(self):
        cs = jacketclient.client.Client("2", "user", "password", "project_id",
                                      auth_url="foo/v1", no_cache=False)
        self.assertTrue(cs.os_cache)
        self.assertTrue(cs.client.os_cache)

    def test_client_set_management_url_v1_1(self):
        cs = jacketclient.client.Client("2", "user", "password", "project_id",
                                      auth_url="foo/v1")
        cs.set_management_url("blabla")
        self.assertEqual("blabla", cs.client.management_url)

    def test_client_get_reset_timings_v1_1(self):
        cs = jacketclient.client.Client("2", "user", "password", "project_id",
                                      auth_url="foo/v1")
        self.assertEqual(0, len(cs.get_timings()))
        cs.client.times.append("somevalue")
        self.assertEqual(1, len(cs.get_timings()))
        self.assertEqual("somevalue", cs.get_timings()[0])

        cs.reset_timings()
        self.assertEqual(0, len(cs.get_timings()))

    @mock.patch('jacketclient.client.HTTPClient')
    def test_contextmanager_v1_1(self, mock_http_client):
        fake_client = mock.Mock()
        mock_http_client.return_value = fake_client
        with jacketclient.client.Client("2", "user", "password", "project_id",
                                      auth_url="foo/v1"):
            pass
        self.assertTrue(fake_client.open_session.called)
        self.assertTrue(fake_client.close_session.called)

    def test_client_with_password_in_args_and_kwargs(self):
        # check that TypeError is not raised during instantiation of Client
        cs = jacketclient.client.Client("2", "user", "password", "project_id",
                                      password='pass')
        self.assertEqual('pass', cs.client.password)

    def test_get_password_simple(self):
        cs = jacketclient.client.HTTPClient("user", "password", "", "")
        cs.password_func = mock.Mock()
        self.assertEqual("password", cs._get_password())
        self.assertFalse(cs.password_func.called)

    def test_get_password_none(self):
        cs = jacketclient.client.HTTPClient("user", None, "", "")
        self.assertIsNone(cs._get_password())

    def test_get_password_func(self):
        cs = jacketclient.client.HTTPClient("user", None, "", "")
        cs.password_func = mock.Mock(return_value="password")
        self.assertEqual("password", cs._get_password())
        cs.password_func.assert_called_once_with()

        cs.password_func = mock.Mock()
        self.assertEqual("password", cs._get_password())
        self.assertFalse(cs.password_func.called)

    def test_auth_url_rstrip_slash(self):
        cs = jacketclient.client.HTTPClient("user", "password", "project_id",
                                          auth_url="foo/v1/")
        self.assertEqual("foo/v1", cs.auth_url)

    def test_token_and_bypass_url(self):
        cs = jacketclient.client.HTTPClient(None, None, None,
                                          auth_token="12345",
                                          bypass_url="jacket/v100/")
        self.assertIsNone(cs.auth_url)
        self.assertEqual("12345", cs.auth_token)
        self.assertEqual("jacket/v100", cs.bypass_url)
        self.assertEqual("jacket/v100", cs.management_url)

    def test_service_url_lookup(self):
        service_type = 'jacket'
        cs = jacketclient.client.HTTPClient(None, None, None,
                                          auth_url='foo/v1',
                                          service_type=service_type)

        @mock.patch.object(cs, 'get_service_url', return_value='jacket/v5')
        @mock.patch.object(cs, 'request', return_value=(200, '{}'))
        @mock.patch.object(cs, 'authenticate')
        def do_test(mock_auth, mock_request, mock_get):

            def set_service_catalog():
                cs.service_catalog = 'catalog'

            mock_auth.side_effect = set_service_catalog
            cs.get('/servers')
            mock_get.assert_called_once_with(service_type)
            mock_request.assert_called_once_with('jacket/v5/servers',
                                                 'GET', headers=mock.ANY)
            mock_auth.assert_called_once_with()

        do_test()

    def test_bypass_url_no_service_url_lookup(self):
        bypass_url = 'jacket/v100'
        cs = jacketclient.client.HTTPClient(None, None, None,
                                          auth_url='foo/v1',
                                          bypass_url=bypass_url)

        @mock.patch.object(cs, 'get_service_url')
        @mock.patch.object(cs, 'request', return_value=(200, '{}'))
        def do_test(mock_request, mock_get):
            cs.get('/servers')
            self.assertFalse(mock_get.called)
            mock_request.assert_called_once_with(bypass_url + '/servers',
                                                 'GET', headers=mock.ANY)

        do_test()

    @mock.patch("jacketclient.client.requests.Session")
    def test_session(self, mock_session):
        fake_session = mock.Mock()
        mock_session.return_value = fake_session
        cs = jacketclient.client.HTTPClient("user", None, "", "")
        cs.open_session()
        self.assertEqual(cs._session, fake_session)
        cs.close_session()
        self.assertIsNone(cs._session)

    def test_session_connection_pool(self):
        cs = jacketclient.client.HTTPClient("user", None, "",
                                          "", connection_pool=True)
        cs.open_session()
        self.assertIsNone(cs._session)
        cs.close_session()
        self.assertIsNone(cs._session)

    def test_get_session(self):
        cs = jacketclient.client.HTTPClient("user", None, "", "")
        self.assertIsNone(cs._get_session("http://example.com"))

    @mock.patch("jacketclient.client.requests.Session")
    def test_get_session_open_session(self, mock_session):
        fake_session = mock.Mock()
        mock_session.return_value = fake_session
        cs = jacketclient.client.HTTPClient("user", None, "", "")
        cs.open_session()
        self.assertEqual(fake_session, cs._get_session("http://example.com"))

    @mock.patch("jacketclient.client.requests.Session")
    @mock.patch("jacketclient.client._ClientConnectionPool")
    def test_get_session_connection_pool(self, mock_pool, mock_session):
        service_url = "http://service.example.com"

        pool = mock.MagicMock()
        pool.get.return_value = "http_adapter"
        mock_pool.return_value = pool
        cs = jacketclient.client.HTTPClient("user", None, "",
                                          "", connection_pool=True)
        cs._current_url = "http://current.example.com"

        session = cs._get_session(service_url)
        self.assertEqual(session, mock_session.return_value)
        pool.get.assert_called_once_with(service_url)
        mock_session().mount.assert_called_once_with(service_url,
                                                     'http_adapter')

    def test_init_without_connection_pool(self):
        cs = jacketclient.client.HTTPClient("user", None, "", "")
        self.assertIsNone(cs._connection_pool)

    @mock.patch("jacketclient.client._ClientConnectionPool")
    def test_init_with_proper_connection_pool(self, mock_pool):
        fake_pool = mock.Mock()
        mock_pool.return_value = fake_pool
        cs = jacketclient.client.HTTPClient("user", None, "",
                                          connection_pool=True)
        self.assertEqual(cs._connection_pool, fake_pool)

    def test_log_req(self):
        self.logger = self.useFixture(
            fixtures.FakeLogger(
                format="%(message)s",
                level=logging.DEBUG,
                nuke_handlers=True
            )
        )
        cs = jacketclient.client.HTTPClient("user", None, "",
                                          connection_pool=True)
        cs.http_log_debug = True
        cs.http_log_req('GET', '/foo', {'headers': {}})
        cs.http_log_req('GET', '/foo', {'headers':
                                        {'X-Auth-Token': None}})
        cs.http_log_req('GET', '/foo', {'headers':
                                        {'X-Auth-Token': 'totally_bogus'}})
        cs.http_log_req('GET', '/foo', {'headers':
                                        {'X-Foo': 'bar',
                                         'X-Auth-Token': 'totally_bogus'}})
        cs.http_log_req('GET', '/foo', {'headers': {},
                                        'data':
                                            '{"auth": {"passwordCredentials": '
                                            '{"password": "zhaoqin"}}}'})

        output = self.logger.output.split('\n')

        self.assertIn("REQ: curl -g -i '/foo' -X GET", output)
        self.assertIn(
            "REQ: curl -g -i '/foo' -X GET -H "
            '"X-Auth-Token: None"',
            output)
        self.assertIn(
            "REQ: curl -g -i '/foo' -X GET -H "
            '"X-Auth-Token: {SHA1}b42162b6ffdbd7c3c37b7c95b7ba9f51dda0236d"',
            output)
        self.assertIn(
            "REQ: curl -g -i '/foo' -X GET -H "
            '"X-Auth-Token: {SHA1}b42162b6ffdbd7c3c37b7c95b7ba9f51dda0236d"'
            ' -H "X-Foo: bar"',
            output)
        self.assertIn(
            "REQ: curl -g -i '/foo' -X GET -d "
            '\'{"auth": {"passwordCredentials": {"password":'
            ' "{SHA1}4fc49c6a671ce889078ff6b250f7066cf6d2ada2"}}}\'',
            output)

    def test_log_resp(self):
        self.logger = self.useFixture(
            fixtures.FakeLogger(
                format="%(message)s",
                level=logging.DEBUG,
                nuke_handlers=True
            )
        )

        cs = jacketclient.client.HTTPClient("user", None, "",
                                          connection_pool=True)
        cs.http_log_debug = True
        text = ('{"access": {"token": {"id": "zhaoqin"}}}')
        resp = utils.TestResponse({'status_code': 200, 'headers': {},
                                   'text': text})

        cs.http_log_resp(resp)
        output = self.logger.output.split('\n')

        self.assertIn('RESP: [200] {}', output)
        self.assertIn('RESP BODY: {"access": {"token": {"id":'
                      ' "{SHA1}4fc49c6a671ce889078ff6b250f7066cf6d2ada2"}}}',
                      output)

    @mock.patch.object(jacketclient.client.HTTPClient, 'request')
    def test_timings(self, m_request):
        m_request.return_value = (None, None)

        client = jacketclient.client.HTTPClient(user='zqfan', password='')
        client._time_request("http://no.where", 'GET')
        self.assertEqual(0, len(client.times))

        client = jacketclient.client.HTTPClient(user='zqfan', password='',
                                              timings=True)
        client._time_request("http://no.where", 'GET')
        self.assertEqual(1, len(client.times))
        self.assertEqual('GET http://no.where', client.times[0][0])


class SessionClientTest(utils.TestCase):

    @mock.patch.object(adapter.LegacyJsonAdapter, 'request')
    @mock.patch.object(jacketclient.client, '_log_request_id')
    def test_timings(self, mock_log_request_id, m_request):
        m_request.return_value = (mock.MagicMock(status_code=200), None)

        client = jacketclient.client.SessionClient(session=mock.MagicMock())
        client.request("http://no.where", 'GET')
        self.assertEqual(0, len(client.times))

        client = jacketclient.client.SessionClient(session=mock.MagicMock(),
                                                 timings=True)
        client.request("http://no.where", 'GET')
        self.assertEqual(1, len(client.times))
        self.assertEqual('GET http://no.where', client.times[0][0])

    @mock.patch.object(adapter.LegacyJsonAdapter, 'request')
    @mock.patch.object(jacketclient.client, '_log_request_id')
    def test_log_request_id(self, mock_log_request_id, mock_request):
        response = mock.MagicMock(status_code=200)
        mock_request.return_value = (response, None)
        client = jacketclient.client.SessionClient(session=mock.MagicMock(),
                                                 service_name='jacket')
        client.request("http://no.where", 'GET')
        mock_log_request_id.assert_called_once_with(client.logger, response,
                                                    'jacket')


class DiscoverExtensionTest(utils.TestCase):

    @mock.patch("jacketclient.client._discover_via_entry_points")
    @mock.patch("jacketclient.client._discover_via_contrib_path")
    @mock.patch("jacketclient.client._discover_via_python_path")
    @mock.patch("jacketclient.extension.Extension")
    def test_discover_all(self, mock_extension,
                          mock_discover_via_python_path,
                          mock_discover_via_contrib_path,
                          mock_discover_via_entry_points):
        def make_gen(start, end):
            def f(*args, **kwargs):
                for i in range(start, end):
                    yield "name-%s" % i, i
            return f

        mock_discover_via_python_path.side_effect = make_gen(0, 3)
        mock_discover_via_contrib_path.side_effect = make_gen(3, 5)
        mock_discover_via_entry_points.side_effect = make_gen(5, 6)

        version = jacketclient.api_versions.APIVersion("2.0")

        result = jacketclient.client.discover_extensions(version)

        self.assertEqual([mock.call("name-%s" % i, i) for i in range(0, 6)],
                         mock_extension.call_args_list)
        mock_discover_via_python_path.assert_called_once_with()
        mock_discover_via_contrib_path.assert_called_once_with(version)
        mock_discover_via_entry_points.assert_called_once_with()
        self.assertEqual([mock_extension()] * 6, result)

    @mock.patch("jacketclient.client._discover_via_entry_points")
    @mock.patch("jacketclient.client._discover_via_contrib_path")
    @mock.patch("jacketclient.client._discover_via_python_path")
    @mock.patch("jacketclient.extension.Extension")
    def test_discover_only_contrib(self, mock_extension,
                                   mock_discover_via_python_path,
                                   mock_discover_via_contrib_path,
                                   mock_discover_via_entry_points):
        mock_discover_via_contrib_path.return_value = [("name", "module")]

        version = jacketclient.api_versions.APIVersion("2.0")

        jacketclient.client.discover_extensions(version, only_contrib=True)
        mock_discover_via_contrib_path.assert_called_once_with(version)
        self.assertFalse(mock_discover_via_python_path.called)
        self.assertFalse(mock_discover_via_entry_points.called)
        mock_extension.assert_called_once_with("name", "module")

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

from keystoneauth1 import fixture

from jacketclient import exceptions
from jacketclient import service_catalog
from jacketclient.tests.unit import utils


SERVICE_CATALOG = fixture.V2Token()
SERVICE_CATALOG.set_scope()

_s = SERVICE_CATALOG.add_service('jacket')
_e = _s.add_endpoint("https://jacket1.host/v1/1")
_e["tenantId"] = "1"
_e["versionId"] = "1.0"
_e = _s.add_endpoint("https://jacket1.host/v1.1/2", region="North")
_e["tenantId"] = "2"
_e["versionId"] = "1.1"
_e = _s.add_endpoint("https://jacket1.host/v1/1", region="North")
_e["tenantId"] = "1"
_e["versionId"] = "2"

_s = SERVICE_CATALOG.add_service('volume')
_e = _s.add_endpoint("https://volume1.host/v1/1", region="South")
_e["tenantId"] = "1"
_e = _s.add_endpoint("https://volume1.host/v1.1/2", region="South")
_e["tenantId"] = "2"


class ServiceCatalogTest(utils.TestCase):
    def test_building_a_service_catalog(self):
        sc = service_catalog.ServiceCatalog(SERVICE_CATALOG)

        self.assertRaises(exceptions.AmbiguousEndpoints, sc.url_for,
                          service_type='jacket')
        self.assertEqual("https://jacket1.host/v1/1",
                         sc.url_for('tenantId', '1', service_type='jacket'))
        self.assertEqual("https://jacket1.host/v1.1/2",
                         sc.url_for('tenantId', '2', service_type='jacket'))

        self.assertRaises(exceptions.EndpointNotFound, sc.url_for,
                          "region", "South", service_type='jacket')

    def test_building_a_service_catalog_insensitive_case(self):
        sc = service_catalog.ServiceCatalog(SERVICE_CATALOG)
        # Matching south (and catalog has South).
        self.assertRaises(exceptions.AmbiguousEndpoints, sc.url_for,
                          'region', 'south', service_type='volume')

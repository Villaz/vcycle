__author__ = 'Luis Villazon Esteban'

from connectors import CloudConnector, CloudException
import requests
import time
import base64
from time import mktime
import logging

logging.getLogger("requests").setLevel(logging.WARNING)


class Occi(CloudConnector):

    token = None
    expires = None
    categories = {}
    session = None

    def __init__(self, logger=None, **kwargs):
        CloudConnector.__init__(self)
        self.params = kwargs
        self.session = requests.Session()
        self.session.mount(kwargs['endpoint'], requests.adapters.HTTPAdapter(pool_connections=20, max_retries=3))
        self.__auth()
        self._get_definitions()

    def __check_token(self):
        """ Checks if the token exists and it is not expired.

        This function checks if a token has been created to authorize the requests to the provider.
        If the token does not exist, the authorization is done using a proxy or certificate.
        In the case that the token exists, the function check if it is valid or it has expired. In the case the
        token has expired, a new authorization is requests to renew it.
        """
        if self.token is None:
            return None
        if self.expires < int(time.time()):
            self.__auth()

    def __auth(self):
        """ Asks for a new tokens

        Does a HEAD request to get the authenticate url, if the url does not exist, the authentication is donde via
        certificate or proxy. If the url exists, a new request is donde to the url
        """
        response = requests.head(self.params['endpoint'], verify=False)
        #Is Openstack
        if 'www-authenticate' in response.headers:
            url = response.headers['www-authenticate']
            url = url[url.find("=")+2:len(url)-1]
            openstack = OpenstackAuth(endpoint=url, proxy=self.params['proxy'])
            self.token, self.expires = openstack.auth()
            self.session.headers.clear()
            self.session.headers.update({"X-Auth-Token": self.token})

    def list(self, prefix=None):
        """ Reads information from provider and returns a list of all deployed vms

        :param prefix: Only returns vms with the prefix in their hostname
        :type prefix: string
        :return List of VMs
        """
        self.__check_token()
        #headers = {}
        #if self.token is not None:
        #    headers["X-Auth-Token"] = self.token
        response = self.session.get(self.params['endpoint']+"/compute/",
                                    cert=self.params['proxy'],
                                    timeout=60,
                                    verify=False)
        response = response.text
        if response is None:
            return []

        uris = [line[line.find(":")+2:] for line in response.split("\n")[1:]]
        uris = ["%s/compute/%s" % (self.params['endpoint'], url[url.rfind("/")+1:]) for url in uris]

        import threading
        threadList = []
        vms = []
        for arg in uris:
            thr = threading.Thread(target=self.__describe, args=(arg, self.token, vms))
            threadList.append(thr)
            time.sleep(0.1)
            thr.start()

        for th in threadList:
            th.join()
        return [vm for vm in vms if prefix is None or prefix in vm['hostname'] or vm['hostname'] == 'UNKNOWN']

    def delete(self, identifier):
        """Deletes a VM in the provider

        :param identifier: vm identifier
        """
        self.__check_token()
        headers = {'Accept': 'application/occi+json',
                   'Content-Type': 'application/occi+json'
        }
        #if self.token is not None:
        #    headers["X-Auth-Token"] = self.token
        response = self.session.delete("%s/compute/%s" % (self.params['endpoint'], identifier),
                                       cert=self.params['proxy'],
                                       headers=headers,
                                       timeout=60,
                                       verify=False)
        if response.status_code != 200:
            raise CloudException(response.text)

    def create(self, **kwargs):
        """Creates a new VM in the provider. Received as parameter a dictionary of values.

        :param hostname: The hostname of the VM
        :param image: The image that will be use to create the VM
        :param flavor: The flavor that will be use to create the VM
        :param user_data: User data to contextualize the VM
        :type user_data: string or None
        """
        import uuid
        self.__check_token()
        if kwargs['image'] not in self.categories:
            raise CloudException("Check the image, it not exists")
        if kwargs['flavor'] not in self.categories:
            raise CloudException("Check the flavor, it not exists")
        data = 'Category: compute;scheme="http://schemas.ogf.org/occi/infrastructure#";class="kind";location="/compute/";title="Compute Resource"\n'
        data += 'Category: %s;%s;class="mixin";location="/%s"\n' % (kwargs['image'], self.categories[kwargs['image']]['scheme'], kwargs['image'])
        data += 'Category: %s;%s;class="mixin";location="/%s"\n' % (kwargs['flavor'], self.categories[kwargs['flavor']]['scheme'], kwargs['flavor'])
        data += 'Category: user_data;scheme="http://schemas.openstack.org/compute/instance#";class="mixin";location="/mixin/user_data/";title="OS contextualization mixin"\n';
        data += 'X-OCCI-Attribute: occi.core.id="%s"\n' % str(uuid.uuid4())
        data += 'X-OCCI-Attribute: occi.core.title="%s"\n' % kwargs['hostname']
        data += 'X-OCCI-Attribute: occi.compute.hostname="%s"\n' % kwargs['hostname']

        if 'user_data' in kwargs:
            data += 'X-OCCI-Attribute: org.openstack.compute.user_data="%s"' % base64.b64encode(kwargs['user_data'])

        headers = {'Accept': 'text/plain,text/occi',
                   'Content-Type': 'text/plain,text/occi',
                   'Connection': 'close'
        }

        #if self.token is not None:
        #    headers['X-Auth-Token'] = self.token

        response = self.session.post("%s/compute/" % self.params['endpoint'],
                                     data=data,
                                     headers=headers,
                                     cert=self.params['proxy'],
                                     timeout=60,
                                     verify=False)
        if response.status_code not in [200, 201]:
            raise CloudException(response.text)
        else:
            vm = {'id':None, 'hostname': kwargs['hostname'], 'state': 'CREATING' }
            if 'Location' in response.headers:
                vm['id'] = response.headers['Location']
                vm['id'] = vm['id'][vm['id'].rfind("/")+1:]
            elif 'location' in response.headers:
                vm['id'] = response.headers['location']
                vm['id'] = vm['id'][vm['id'].rfind("/")+1:]
            else:
                vm['id'] = response.text[response.text.find(":")+1:].rstrip()
        return vm

    def __describe(self, uri, token, vms):
        """ Returns a description of a given VM

        :param uri: VM Descriptor
        :param token: The token use to authorize the connection
        :type token: string or None
        :param vms: Array where the vm will be added
        """
        headers = {'Accept': 'application/occi+json',
                   'Content-Type': 'application/occi+json'}
        #if token is not None:
        #    headers['X-Auth-Token'] = token

        try:
            response = self.session.get(uri,
                                        cert=self.params['proxy'],
                                        headers=headers,
                                        timeout=60,
                                        verify=False)
        except requests.Timeout as timeout:
            id = uri[uri.rfind('/')+1:]
            if id.startswith('http'):
                id = uri[uri.rfind('/')+1:]
            computer = {'id': id, 'hostname': 'UNKNOWN', 'state': 'UNKNOWN'}
            vms.append(computer)
            return

        response = response.json()

        computer = {'id': response['attributes']['occi.core.id'],
                    'hostname': response['attributes']['occi.compute.hostname']}

        if 'org.openstack.compute.state' in response['attributes']:
            state = response['attributes']['org.openstack.compute.state'].upper()
            if state in ['ERROR']:
                computer['state'] = 'ERROR'
            elif state in ['BUILDING', 'ACTIVE']:
                computer['state'] = 'CREATING'
            else:
                computer['state'] = 'ENDED'
        else:
            state = response['attributes']['occi.compute.state'].upper()
            if state in ['ERROR']:
                computer['state'] = 'ERROR'
            elif state in ['ACTIVE', 'INACTIVE']:
                computer['state'] = 'CREATING'
            else:
                computer['state'] = 'ENDED'
        vms.append(computer)

    def _get_definitions(self):
        """Store the schema definitions to create VMs

        """
        self.__check_token()
        headers = {'Accept': 'text/plain,text/occi'}
        #if self.token is not None:
        #    headers["X-Auth-Token"] = self.token
        response = self.session.get("%s/-/" % self.params['endpoint'],
                                    headers=headers,
                                    cert=self.params['proxy'],
                                    verify=False)
        categories = response.text.split("\n")[1:]
        for category in categories:
            values = category.split(";")
            cat = values[0][values[0].find(":")+1:].strip()
            self.categories[cat] = {}
            for property in values:
                if property.find("scheme=") >= 0:
                    self.categories[cat]["scheme"] = property.strip()
                if property.find("class=") >= 0:
                    self.categories[cat]["class"] = property.strip()
                if property.find("title=") >= 0:
                    self.categories[cat]["title"] = property.strip()
                if property.find("location=") >= 0:
                    aux = property.strip()
                    aux = aux.replace("https://","")
                    aux = aux.replace("http://","")
                    aux = aux[aux.find("/"):]
                    self.categories[cat]["location"] = 'location="'+aux


class OpenstackAuth:

    def __init__(self, **kwargs):
        """ Openstack constructor

        :param kwargs: Dictionary of params.
        :param proxy: Local path where the proxy is stored.
        :param endpoint: Endpoint to do the authentication
        """
        self.params = kwargs

        if self.params['endpoint'].endswith("/v2.0"):
            self.params['endpoint'] = self.params['endpoint'].replace("/v2.0", "")
        elif self.params['endpoint'].endswith("/v2.0/"):
            self.params['endpoint'] = self.params['endpoint'].replace("/v2.0/", "")


    def auth(self):
        """ Does the authentication

        The authentication is done in two steps.
        In the first step a request to authenticate the user in the system is done.
        In the second step the user needs to authenticate in the tenant, and he recieves the final token
        """
        token, expires = self.get_key()
        return self.__auth_in_tenant(token, self.__get_tenants(token))

    def get_key(self):
        """ Returns the system token

        """
        response = requests.post(self.params['endpoint']+"/v2.0/tokens",
                                 data='{"auth":{"voms": true}}',
                                 headers={"Content-Type": "application/json"},
                                 cert=self.params['proxy'], verify=False)
        if response.status_code == 200:
            body = response.json()
            expires = int(mktime(time.strptime(body['access']['token']['expires'], "%Y-%m-%dT%H:%M:%SZ")))
            token = body['access']['token']['id']
        return token, expires

    def __get_tenants(self, token):
        """ Returns all the tenants available in the provider

        :param token: Authorization token
        :return: The name of all tenants
        """
        response = requests.get(self.params['endpoint']+"/v2.0/tenants",
                                 data='{"auth":{"voms": true}}',
                                 headers={"Content-Type": "application/json", "X-Auth-Token": token},
                                 cert=self.params['proxy'], verify=False)
        return [tenant['name'] for tenant in response.json()['tenants']]

    def __auth_in_tenant(self, token, tenants):
        """ Returns the token linked to the tenant

        Loop all tenants, trying to authorize the user with  each tenant, ones a tenant is valid, a token is returned

        :param token: System token
        :param tenants:  list of tenants
        :return: token and expiration date
        """
        import json
        for tenant in tenants:
            data = {'auth':{'voms': True, 'tenantName': tenant}}
            headers = {
                'Accept': 'application/json',
                'X-Auth-Token': token,
                'Content-Type': 'application/json',
                'Content-Length': len(json.dumps(data))
            }
            response = requests.post("%s/v2.0/tokens" % self.params['endpoint'],
                          data=json.dumps(data),
                          headers= headers,
                          cert=self.params['proxy'],
                          verify=False)
            response = response.json()
            if 'access' in response:
                return response['access']['token']['id'], response['access']['token']['expires']


def create(**kwargs):
    return Occi(**kwargs)
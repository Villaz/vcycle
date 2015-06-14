import requests
from requests.auth import HTTPBasicAuth
import json
from models.models import * 
import abc

def _error_400(response=None):
    message = 'Problem with request syntax'
    if response is not None:
        message = "%s : %s" % (message, response)
    raise Exception(message)
   
   
def _error_401(response=None):
    raise Exception('No username or password provided/ Username or password is wrong')
   
   
def _error_404(response=None):
    raise Exception('No resource found')
   
   
def _error_500(response=None):
    raise Exception('An error ocurred when performing the operation')


class Op:
    status = {400: _error_400, 401: _error_401, 404: _error_404, 500: _error_500}
   
    @abc.abstractmethod
    def list_result(self, result):
        pass
   
    def list(self, provider = None):
        params = {}
        if provider is not None:
            params['provider-location-uid'] = self.dbce.providers[provider]['id']
        self.status[200] = self.list_result
        request = self.dbce.execute(self.url, params)
        return self.status[request.status_code](request.json())
      

class DBCE:
   
    def __init__(self, endpoint, key, version):
        self.endpoint = endpoint
        self.key = key
        self.version = version
        self.machine = MachineOp(self)

    def execute(self, url, params=None, method='GET', data=None):
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'DBCE-ApiKey': self.key}

        request = None
        if method == 'GET':
            request = requests.get(url,
                                   headers=headers,
                                   params=params,
                                   verify=False)
        elif method == 'POST':
            request = requests.post(url,
                                    headers=headers,
                                    params=params,
                                    verify=False,
                                    data=data)
        elif method == 'PUT':
            request = requests.put(url,
                                   headers=headers,
                                   params=params,
                                   verify=False)
        elif method == 'DELETE':
            request = requests.delete(url,
                                      headers=headers,
                                      params=params,
                                      verify=False)

        if not request.status_code in [200,201,202]:
            raise Exception(str(request.status_code) +" "+request.text)
        return request


class MachineOp(Op):
   
    def __init__(self, dbce):
        self.dbce = dbce
        self.url = "%s/%s/machines" % (dbce.endpoint, dbce.version)
        self.status = {400:_error_400,401:_error_401,404:_error_404,500:_error_500}

    def list_result(self, response):
        servers = []
        for machine in response['machines']:
            server = Machine(machine['id'], machine['name'],
                             machine['description'], machine['created'], machine['updated'],
                             machine['state'], machine['cpu'], machine['memory'], machine['disks'],
                             machine['networkInterfaces'])
            servers.append(server)
        return servers

    def list(self):
        self.status[200] = self.list_result
        request = self.dbce.execute("%s" % self.url)

    def describe(self, machine_id):
        def _status_200(machine):
            return Machine( machine['id'],
                            machine['name'],
                            machine['state'],
                            machine['memory'],
                            machine['disks'],
                            machine['networkInterfaces'])

        self.status[200] = _status_200
        request = self.dbce.execute("%s/%s" %(self.url, machine_id))
        return self.status[request.status_code](request.json())

    def delete(self, machine_id):
        def _status_202():
           pass
      
        params = {}
        self.status[202] = _status_202
        request = self.dbce.execute("%s/%s" %(self.url, machine_id),method='DELETE')
        return self.status[request.status_code]()

    def create(self, name, platform, image, flavor, network, public_key=None, user_data=None):
        def status_415(response):
            print response

        def _status_201(machine):
            return Machine(machine['id'],
                           machine['name'],
                           machine['state'],
                           machine['cpu'],
                           machine['memory'],
                           machine['disks'],
                           machine['networkInterfaces'],
                           )
        json_request = {
            'name': name,
            'platform': {
                id: platform
            },
            'image': {
                'id': image
            },
            'configuration': {
                'id': flavor
            },
            'network': {
                'id': network
            }
        }

        if public_key is not None:
            json_request['publicKey'] = public_key
        if user_data is not None:
            json_request['cloudConfig'] = user_data

        self.status[201] = _status_201
        self.status[415] = status_415
        request = self.dbce.execute("%s" % self.url,method='POST',data=json.dumps(json_request))
        return self.status[request.status_code](request.json())

    def add_network_address(self, machine_id, network_id):
        def _status_202():
            return "Request has been successfully accepted"

        self.status[202] = _status_202
        request = requests.post("%s/machines/%s/actions/assign-public-ip" %(self.url, machine_id))
        return self.status[request.status_code]()
      
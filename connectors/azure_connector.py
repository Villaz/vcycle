__author__ = 'Luis Villazon Esteban'

from azure import *
from azure.servicemanagement import *
from connectors import CloudConnector, CloudException


class Azure(CloudConnector):

    def __init__(self, **kwargs):
        """

        :param kwargs: Dictionary with information about azure connection
        :param subscription: Subscription id used to connect with azure
        :param pfx: Certificate use to grant access to VMs
        """
        CloudConnector.__init__(self)
        self.params = kwargs

    def list(self, prefix=None):
        """ Reads information from provider and returns a list of all deployed vms

        ProvisioningFailed has been marked as good state.
        If the you are using a custom script to contextualize the VM,
        Azure probably returns this state, but the VM is running and the contextualization file will be executed.

        :param prefix: Only returns vms with the prefix in their hostname
        :type prefix: string
        :return List of VMs
        """
        try:
            sms = ServiceManagementService(self.params['subscription'], self.params['cert'])
            results = sms.list_hosted_services()
        except Exception as ex:
            if 'file' in str(ex):
                raise CloudException("No cert file , check the path.")
            raise CloudException(str(ex))
        vms = []
        for result in results:
            try:
                info = sms.get_hosted_service_properties(result.service_name, True)
            except WindowsAzureMissingResourceError as ex:
                print "% don't have vms? " % result.service_name
                continue

            if len(info.deployments) == 0: continue
            if prefix is not None and not result.service_name.startswith(prefix): continue

            try:
                status = info.deployments[0].role_instance_list[0].instance_status
            except Exception as ex:
                import json
                print json.dumps(info,indent=2)
                print str(ex)
                vms.append({'id': result.service_name,'hostname': result.service_name, 'state': 'CREATING'})
                continue

            vm = {'id': result.service_name,'hostname': result.service_name}
            print status

            if status in ['Unknown', 'CreatingVM', 'StartingVM', 'CreatingRole', 'StartingRole',
                                           'ReadyRole', 'BusyRole', 'Preparing','ProvisioningFailed']:
                vm['state'] = 'CREATING'
            elif status in ['StoppingRole', 'StoppingVM', 'DeletingVM',
                            'StoppedVM', 'RestartingRole','StoppedDeallocated']:
                vm['state'] = 'STOPPED'
            else:
                vm['state'] = 'CREATING'
            vms.append(vm)
        return vms

    def delete(self, identifier):
        """Deletes a VM in the provider

        :param identifier: vm identifier
        """
        sms = ServiceManagementService(self.params['subscription'], self.params['cert'])
        try:
            sms.delete_hosted_service(identifier, True)
        except Exception as e:
            raise CloudException(str(e))

    def create(self, **kwargs):
        """Creates a new VM

        :param kwargs: Paramters to create the vm
        :param hostname: Name's machine
        :param location: Location where VM will be created.
        :param image: Image to use to create the VM
        :param flavor: Flavor to use to create the VM
        :param pfx: location on local disk of the certificate to upload, must be in pfx format.
        :param username: Username in the VM
        :param password: Password in the VM
        :param user_data: User data to contextualize the VM
        :type user_data: string
        :return: Id , hostname and state of the created VM
        """
        try:
            self.__create_service(name=kwargs['hostname'], location=kwargs['location'])
            fingerprint, path = self.__add_certificate_to_service(name=kwargs['hostname'], pfx=kwargs['pfx'])
            self.__create_vm(name=kwargs['hostname'],
                             flavor=kwargs['flavor'],
                             image=kwargs['image'],
                             username=kwargs['username'],
                             password=kwargs['password'],
                             user_data=kwargs['user_data'],
                             fingerprint=(fingerprint, path))
            return {'id': kwargs['hostname'], 'hostname': kwargs['hostname'], 'state': 'CREATING'}
        except Exception as ex:
            try:
                self.delete(kwargs['hostname'])
                raise CloudException(str(ex))
            except Exception as ex:
                raise CloudException(str(ex))

    def __create_service(self, name="", location=None):
        """ Create a new service

        :param name: Name of the service
        :param location: Location of the service

        """
        sms = ServiceManagementService(self.params['subscription'], self.params['cert'])
        result = sms.check_hosted_service_name_availability(name)
        if not result:
            raise CloudException("The service name %s is not available" % name)
        try:
            result = sms.create_hosted_service(name, name, name, location)
            sms.wait_for_operation_status(result.request_id)
        except Exception as ex:
            raise CloudException("The service name %s is not available" % name)

    def __add_certificate_to_service(self, name="", pfx=""):
        """ Adds a certificate into the service.

        The certificate is used to connect via ssh to the VM

        :param name: Name of the service where the certificate will be added
        :param pfx: location on local disk of the certificate to upload

        """
        import base64
        sms = ServiceManagementService(self.params['subscription'], self.params['cert'])
        result = sms.add_service_certificate(name, base64.b64encode(open(pfx).read()), 'pfx', '')
        sms.wait_for_operation_status(result.request_id)
        list = sms.list_service_certificates(name)
        for certificate in list:
            return certificate.thumbprint, certificate.certificate_url

    def __create_vm(self, name="", flavor="", image="", username="", password="", user_data=None, fingerprint=None):
        """ Creates  new VM

        :param name: Name of the new VM
        :param flavor: Flavor to create the VM
        :param image: Image to create the VM
        :param username: username to use to connect to the vm via SSH
        :param password:  password to use to connect to the vm via SSH
        :param user_data: contextualization file

        """
        sms = ServiceManagementService(self.params['subscription'], self.params['cert'])

        configuration_set = LinuxConfigurationSet(host_name=name,
                                                  user_name=username,
                                                  user_password=password,
                                                  disable_ssh_password_authentication=False,
                                                  custom_data=user_data)

        if fingerprint is not None:
            configuration_set.ssh.public_keys.public_keys.append(PublicKey(fingerprint=fingerprint[0], path=fingerprint[1]))

        network_set = ConfigurationSet()
        network_set.input_endpoints.input_endpoints.append(ConfigurationSetInputEndpoint(name='SSH',
                                                                                         protocol="TCP",
                                                                                         port=22,
                                                                                         local_port=22))

        result = sms.create_virtual_machine_deployment(name,
                                              name,
                                              'production',
                                              name,
                                              name,
                                              configuration_set,
                                              None,
                                              network_config= network_set,
                                              role_size=flavor,
                                              vm_image_name=image,
                                              provision_guest_agent=True)
        # The VM is created async, we not wait for confirmation. Assume the VM is created.
        '''
        try:
            sms.wait_for_operation_status(result.request_id)
        except Exception as ex:
            if 'Timed' in str(ex):
                return
            else:
                raise CloudException(str(ex))
        '''


def create(**kwargs):
    return Azure(**kwargs)

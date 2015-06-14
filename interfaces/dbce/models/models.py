import json

class Machine:
   
    def __init__(self,
                 id,
                 name,
                 state,
                 cpu,
                 memory,
                 disks,
                 network_interfaces):
        self.id = id[id.rfind('/')+1:]
        self.name = name
        self.status = state
        self.cpu = cpu
        self.memory = memory
        self.disks = disks
        if len(network_interfaces['machineNetworkInterfaces']) > 0:
            self.network_interfaces = network_interfaces['machineNetworkInterfaces'][0]['addresses']['machineNetworkInterfaceAddresses']
        else:
            self.network_interfaces = []

    def __repr__(self):
        return "%s %s %s" % (self.id, self.name, self.status)
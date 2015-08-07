#!/usr/bin/env python
__author__ = 'Luis Villazon Esteban'

import argparse
import json

try:
    import configuration
except Exception:
    import vcycle.configuration as configuration

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--conf", nargs='?', default=u"/etc/vcycle/vcycle.conf", help="Path to configuration file")
    parser.add_argument("-p", "--provider", nargs='?', help="Name of the provider(connector)")
    parser.add_argument("-i", "--id", nargs='?', help="Name of the provider(connector)")

    args = parser.parse_args()

    configuration_file = configuration.load(args.conf)

    connector = configuration_file['vcycle']['connectors'][args.provider]
    type = connector['type']
    try:
        module = __import__("vcycle.connectors.%s" % type)
        mod = getattr(module, 'connectors')
        class_ = getattr(mod, type)
    except ImportError:
        module = __import__("vcycle.connectors.%s_connector" % type)
        mod = getattr(module, 'connectors')
        class_ = getattr(mod, "%s_connector" % type)
    connector = class_.create(**connector)

    try:
        connector.add_network_address(args.id)
        print json.dumps(connector.describe(args.id), indent=2)
    except Exception:
        print "Sorry, this funcionality is not implemented in this provider"



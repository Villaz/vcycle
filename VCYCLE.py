#!/usr/bin/env python

import sys
from vcycle import daemon, main


class Vcycle(daemon.Daemon):
        def run(self):
            main.start_process()

if __name__ == "__main__":
        vcycle = Vcycle('/tmp/vcycle.pid')
        if len(sys.argv) == 2:
                if 'start' == sys.argv[1]:
                        vcycle.start()
                elif 'stop' == sys.argv[1]:
                        vcycle.stop()
                elif 'restart' == sys.argv[1]:
                        vcycle.restart()
                else:
                        print "Unknown command"
                        sys.exit(2)
                sys.exit(0)
        else:
                print "usage: %s start|stop|restart" % sys.argv[0]
                sys.exit(2)

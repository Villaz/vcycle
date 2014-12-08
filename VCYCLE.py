#!/usr/bin/python
#
#  VCYCLE.py - vcycle library
#
#  Andrew McNab, University of Manchester.
#  Copyright (c) 2013-4. All rights reserved.
#
#  Redistribution and use in source and binary forms, with or
#  without modification, are permitted provided that the following
#  conditions are met:
#
#    o Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer. 
#    o Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution. 
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
#  CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
#  INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
#  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
#  TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
#  OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.
#

import os
import sys
import time
import json
import tempfile
import logging
import ConfigParser
import string
import pycurl
import StringIO

tenancies    = None
lastFizzles = {}
loggers = {}

def readConf(requirePassword=True):

  global vcycleVersion, spaces, lastFizzles
  
  try:
    f = open('/var/lib/vcycle/doc/VERSION', 'r')
    vcycleVersion = f.readline().split('=',1)[1].strip()
    f.close()
  except:
    vcycleVersion = '0.0.0'
  
  spaces = {}

  spaceStrOptions = [ 'tenancy_name', 'url', 'username', 'proxy' , 'type', 'auth' ]

  spaceIntOptions = [ 'max_machines' ]

  vmtypeStrOptions = [ 'ce_name', 'image_name', 'flavor_name', 'root_key_name', 'x509dn', 'network', 'public_key' ]

  vmtypeIntOptions = [ 'max_machines', 'backoff_seconds', 'fizzle_seconds', 'max_wallclock_seconds' ]

  parser = ConfigParser.RawConfigParser()
  
  # Look for configuration files in /etc/vcycle.d
  try:
    confFiles = os.listdir('/etc/vcycle.d')
  except:
    pass 
  else:
    for oneFile in sorted(confFiles):
      if oneFile[-5:] == '.conf':      
        try:
          parser.read('/etc/vcycle.d/' + oneFile)
        except Exception as e:
          logLine('Failed to parse /etc/vcycle.d/' + oneFile + ' (' + str(e) + ')')

  # Standalone configuration file, read last in case of manual overrides
  parser.read('/etc/vcycle.conf')

  # First look for space sections

  for spaceSectionName in parser.sections():
    split1 = spaceSectionName.lower().split(None,1)

    if split1[0] == 'vmtype':    
      continue
      
    elif split1[0] != 'space':
      return 'Section type ' + split1[0] + ' not recognised'
      
    else:
      spaceName = split1[1]
# NEED TO CHECK THIS IS JUST a-z,0-9,-,_,.
      space = {}
      
      # Get the options from this section for this space
      if not parser.has_option(spaceSectionName, 'space_name') :
         return 'Option space_name required in [' + spaceSectionName + ']'
      
      if not parser.has_option(spaceSectionName, 'url') :
         return 'Option url required in [' + spaceSectionName + ']'
      
      if not parser.has_option(spaceSectionName, 'proxy') and not parser.has_option(spaceSectionName, 'username'):
         return 'Option proxy or username is required in [' + spaceSectionName + ']'
      
      space['space_name'] = parser.get(spaceSectionName,'space_name') 
      space['url'] = parser.get(spaceSectionName,'url')
      space['type'] = parser.get(spaceSectionName,'type')
      
      if not parser.has_option(spaceSectionName, 'auth'):
         space['auth'] = 'x509'
      else:
         space['auth'] = parser.get(spaceSectionName,'auth')
      
      if parser.has_option(spaceSectionName,'proxy'):
         space['proxy'] = parser.get(spaceSectionName,'proxy') 
         requirePassword = False
      else:
         space['username'] = parser.get(spaceSectionName,'username') 
      
      
      for opt in spaceIntOptions:
        try:
          space[opt] = int(parser.get(spaceSectionName, opt))
        except:
          return 'Option ' + opt + ' required in [' + spaceSectionName + ']'

      try:
        # We use ROT-1 (A -> B etc) encoding so browsing around casually doesn't
        # reveal passwords in a memorable way. 
        space['password'] = ''.join([ chr(ord(c)-1) for c in parser.get(spaceSectionName, 'password')])
      except:
        if requirePassword:
          return 'Option password is required in [' + spaceSectionName + ']'
        else:
          space['password'] = ''

      try:
         space['delete_old_files'] = bool(parser.get(spaceSectionName, 'delete_old_files'))
      except:
         space['delete_old_files'] = True

      # Get the options for each vmtype section associated with this space

      vmtypes = {}

      for vmtypeSectionName in parser.sections():
        split2 = vmtypeSectionName.lower().split(None,2)

        if split2[0] == 'vmtype':

          if split2[1] == spaceName:
            vmtypeName = split2[2]
            
            
            vmtype = {}

            for opt in vmtypeStrOptions:              
              if parser.has_option(vmtypeSectionName, opt) :
                vmtype[opt] = parser.get(vmtypeSectionName, opt)
              else:
                if opt is 'network' or 'public_key':
                   continue
                return 'Option ' + opt + ' required in [' + vmtypeSectionName + ']'

            for opt in vmtypeIntOptions:
              try:
                vmtype[opt] = int(parser.get(vmtypeSectionName, opt))
              except:
                return 'Option ' + opt + ' required in [' + vmtypeSectionName + ']'

            try:
              vmtype['heartbeat_file'] = parser.get(vmtypeSectionName, 'heartbeat_file')
            except:
              pass

            try:
              vmtype['heartbeat_seconds'] = int(parser.get(vmtypeSectionName, 'heartbeat_seconds'))
            except:
              pass
            
            try:
              vmtype['user_data'] = parser.get(vmtypeSectionName, 'user_data')
            except:
              vmtype['user_data'] = 'user_data'
            
            
            for (oneOption,oneValue) in parser.items(vmtypeSectionName):
              if (oneOption[0:17] == 'user_data_option_') or (oneOption[0:15] == 'user_data_file_'):
                if string.translate(oneOption, None, '0123456789abcdefghijklmnopqrstuvwxyz_') != '':
                  return 'Name of user_data_xxx (' + oneOption + ') must only contain a-z 0-9 and _'
                else:
                  vmtype[oneOption] = parser.get(vmtypeSectionName, oneOption)
            
            if parser.has_option(vmtypeSectionName, 'log_machineoutputs') and \
               parser.get(vmtypeSectionName, 'log_machineoutputs').strip().lower() == 'true':
              vmtype['log_machineoutputs'] = True
            else:
              vmtype['log_machineoutputs'] = False

            if parser.has_option(vmtypeSectionName, 'machineoutputs_days'):
              vmtype['machineoutputs_days'] = float(parser.get(vmtypeSectionName, 'machineoutputs_days'))
            else:
              vmtype['machineoutputs_days'] = 3.0
                    
            if spaceName not in lastFizzles:
              lastFizzles[spaceName] = {}
              
            if vmtypeName not in lastFizzles[spaceName]:
              lastFizzles[spaceName][vmtypeName] = int(time.time()) - vmtype['backoff_seconds']

            vmtypes[vmtypeName] = vmtype

      if len(vmtypes) < 1:
        return 'No vmtypes defined for space ' + spaceName + ' - each space must have at least one vmtype'

      space['vmtypes']     = vmtypes
      tenancies[spaceName] = space

  return None

def createFile(targetname, contents, mode=None):
  # Create a text file containing contents in the vcycle tmp directory
  # then move it into place. Rename is an atomic operation in POSIX,
  # including situations where targetname already exists.
   
  try:
    ftup = tempfile.mkstemp(prefix='/var/lib/vcycle/tmp/temp',text=True)
    os.write(ftup[0], contents)
       
    if mode: 
      os.fchmod(ftup[0], mode)

    os.close(ftup[0])
    os.rename(ftup[1], targetname)
    return True
  except:
    return False

def getUserDataContents(spaceName, vmtypeName, serverName):

  # Get raw user_data template file, either from network ...
  if (spaces[spaceName]['vmtypes'][vmtypeName]['user_data'][0:7] == 'http://') or (spaces[spaceName]['vmtypes'][vmtypeName]['user_data'][0:8] == 'https://'):
    buffer = StringIO.StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, spaces[spaceName]['vmtypes'][vmtypeName]['user_data'])
    c.setopt(c.WRITEFUNCTION, buffer.write)
    c.setopt(c.TIMEOUT, 30)
    c.setopt(c.FOLLOWLOCATION, True)
    c.setopt(c.SSL_VERIFYPEER, 1)
    c.setopt(c.SSL_VERIFYHOST, 2)

    if os.path.isdir('/etc/grid-security/certificates'):
      c.setopt(c.CAPATH, '/etc/grid-security/certificates')
    else:
      logLine('/etc/grid-security/certificates directory does not exist - relying on curl bundle of commercial CAs')
                                    
    try:
      c.perform()
    except Exception as e:
      raise NameError('Failed to read ' + spaces[spaceName]['vmtypes'][vmtypeName]['user_data'] + ' (' + str(e) + ')')

    c.close()
    userDataContents = buffer.getvalue()

  # ... or from filesystem
  else:
    if spaces[spaceName]['vmtypes'][vmtypeName]['user_data'][0] == '/':
      userDataFile = spaces[spaceName]['vmtypes'][vmtypeName]['user_data']
    else:
     userDataFile = '/var/lib/vcycle/vmtypes/' + spaceName + '/' + vmtypeName + '/' + spaces[spaceName]['vmtypes'][vmtypeName]['user_data']

    try:
      userDataContents = open(userDataFile, 'r').read()  
    except Exception as e:
      raise NameError('Failed reading user_data file ' + userDataFile + ' (' + str(e) + ')')

  # Default substitutions
  userDataContents = userDataContents.replace('##user_data_space##',         spaceName)
  userDataContents = userDataContents.replace('##user_data_vmtype##',        vmtypeName)
  userDataContents = userDataContents.replace('##user_data_vm_hostname##',   serverName)
  userDataContents = userDataContents.replace('##user_data_vmlm_version##',  'Vcycle ' + vcycleVersion)
  userDataContents = userDataContents.replace('##user_data_vmlm_hostname##', os.uname()[1])

  # Site configurable substitutions for this vmtype
  for oneOption, oneValue in (spaces[spaceName]['vmtypes'][vmtypeName]).iteritems():
    if oneOption[0:17] == 'user_data_option_':
      userDataContents = userDataContents.replace('##' + oneOption + '##', oneValue)

    if oneOption[0:15] == 'user_data_file_':
      try:
        if oneValue[0] == '/':
          f = open(oneValue, 'r')
        else:
          f = open('/var/lib/vcycle/vmtypes/' + spaceName + '/' + vmtypeName + '/' + oneValue, 'r')
                           
          userDataContents = userDataContents.replace('##' + oneOption + '##', f.read())
          f.close()
      except:
        raise NameError('Failed to read ' + oneValue + ' for ' + oneOption)

  try:
    o = open('/var/lib/vcycle/machines/' + serverName + '/' + '/user_data', 'w')
    o.write(userDataContents)
    o.close()
  except:
    raise NameError('Failed to writing /var/lib/vcycle/machines/' + serverName + '/user_data')
      
  return userDataContents

def logLine(space, text):
  global loggers
  if not space in loggers:
     logger = logging.getLogger(space)
     logger.propagate = False
     logger.setLevel(logging.DEBUG)
     # create file handler which logs even debug messages
     fh = logging.FileHandler("/var/log/vcycle-%s.log" % space)
     fh.setLevel(logging.DEBUG)
     formatter = logging.Formatter('%(asctime)s - %(message)s')
     fh.setFormatter(formatter)
     logger.addHandler(fh)
     loggers[space] = logger

  loggers[space].debug(text)
  #sys.stderr.write(time.strftime('%b %d %H:%M:%S [') + str(os.getpid()) + ']: ' + text + '\n')
  #sys.stderr.flush()

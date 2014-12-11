import VCYCLE
import os
import time, random
import abc
import shutil

class vcycleBase(object):
   '''Base Class where other class inherit'''
   __metaclass__ = abc.ABCMeta
   
   creationsPerCycle = 5
   
   def __init__(self):
      pass
   
   def oneCycle(self, spaceName, space):
      '''Principal method.
      Checks every vm running. 
      If the vm is stopped or it was running more than 
      a period of time the vm will be deleted. 
      If there are free space, the method will create new vms.'''
  
      VCYCLE.logLine(spaceName, 'Processing space ' + spaceName)
  
      totalRunning = 0
      totalFound   = 0

      notPassedFizzleSeconds = {}
      foundPerVmtype         = {}
      runningPerVmtype       = {}
      weightedPerVmtype      = {}
      serverNames            = []

      for vmtypeName,vmtype in space['vmtypes'].iteritems(): 
         notPassedFizzleSeconds[vmtypeName] = 0
         foundPerVmtype[vmtypeName]         = 0
         runningPerVmtype[vmtypeName]       = 0
         weightedPerVmtype[vmtypeName]      = 0
      
      self.spaceName = spaceName
      self.space = space 
      self.client = self._create_client()
      
      #Update the servers running on the site   
      try:
         servers_in_space = self._servers_list()
      except Exception as e:
         VCYCLE.logLine(spaceName, 'client.servers.list() fails with exception ' + str(e))
         return
      
      #Get the running and total found servers inside space
      for oneServer in servers_in_space:
         (totalRunning, totalFound) = self.for_server_in_list(oneServer, totalRunning, totalFound, notPassedFizzleSeconds, foundPerVmtype, runningPerVmtype, weightedPerVmtype)
         if not oneServer is None and oneServer.name[:7] == 'vcycle-':
            serverNames.append(oneServer.name)
                  
      VCYCLE.logLine(spaceName, 'space ' + spaceName + ' has %d ACTIVE:running vcycle VMs out of %d found in any state for any vmtype or none' % (totalRunning, totalFound))
      for vmtypeName,vmtype in space['vmtypes'].iteritems():
         VCYCLE.logLine(spaceName, 'vmtype ' + vmtypeName + ' has %d ACTIVE:running out of %d found in any state' % (runningPerVmtype[vmtypeName], foundPerVmtype[vmtypeName]))
      
      # Get rid of directories about old VMs
      self.cleanupDirectories(spaceName, serverNames)
      self.cleanupMachineoutputs(spaceName)
      
      # Now decide whether to create new VMs
      creationsThisCycle = 0

      # Keep going till limits exhausted
      while True:
         if totalFound >= space['max_machines']:
            VCYCLE.logLine(spaceName, 'Reached limit (%d) on number of machines to create for space %s' % (space['max_machines'], spaceName))
            return

         if creationsThisCycle >= self.creationsPerCycle:
            VCYCLE.logLine(spaceName, 'Already reached limit of %d machine creations this cycle' % creationsThisCycle )
            return

         # Go through vmtypes, possibly creating one from each, before starting again
         vmtypeNames = space['vmtypes'].keys()
         random.shuffle(vmtypeNames)
    
         # Go through vmtypes, finding the one to create (if any)
         vmtypeNameToCreate = None
        
         for vmtypeName in vmtypeNames:
            vmtype = space['vmtypes'][vmtypeName]
            
            if VCYCLE.spaces[spaceName]['vmtypes'][vmtypeName]['target_share'] <= 0.0:
               # Skip over any vmtypes with no target share
               continue
            elif foundPerVmtype[vmtypeName] >= vmtype['max_machines']:
               VCYCLE.logLine(spaceName, 'Reached limit (%d) on number of machines to create for vmtype %s' % (vmtype['max_machines'], vmtypeName))
            elif int(time.time()) < (VCYCLE.lastFizzles[spaceName][vmtypeName] + vmtype['backoff_seconds']):
               VCYCLE.logLine(spaceName, 'Free capacity found for %s ... but only %d seconds after last fizzle' % (vmtypeName, int(time.time()) - VCYCLE.lastFizzles[spaceName][vmtypeName]) )
            elif (int(time.time()) < (VCYCLE.lastFizzles[spaceName][vmtypeName] + vmtype['backoff_seconds'] + vmtype['fizzle_seconds'])) and (notPassedFizzleSeconds[vmtypeName] > 0):
               VCYCLE.logLine(spaceName, 'Free capacity found for %s ... but still within fizzleSeconds+backoffSeconds(%d) of last fizzle (%ds ago) and %d running but not yet passed fizzleSeconds (%d)' % 
               (vmtypeName, vmtype['fizzle_seconds'] + vmtype['backoff_seconds'], int(time.time()) - VCYCLE.lastFizzles[spaceName][vmtypeName], notPassedFizzleSeconds[vmtypeName], vmtype['fizzle_seconds']))
            elif vmtypeNameToCreate is None:
               vmtypeNameToCreate = vmtypeName
            elif weightedPerVmtype[vmtypeName] < weightedPerVmtype[vmtypeNameToCreate]:
               vmtypeNameToCreate = vmtypeName
            
         if vmtypeNameToCreate:   
            VCYCLE.logLine(spaceName, 'Free capacity found for ' + vmtypeName + ' within ' + spaceName + ' ... creating')
            errorMessage = self.createMachine(vmtypeName, proxy='proxy' in space)
            creationsThisCycle += 1
            if errorMessage:
               VCYCLE.logLine(spaceName, errorMessage)
            else:
               totalFound                                 += 1
               foundPerVmtype[vmtypeNameToCreate]         += 1
               notPassedFizzleSeconds[vmtypeNameToCreate] += 1
               weightedPerVmtype[vmtypeNameToCreate]      += (1.0 / VCYCLE.spaces[spaceName]['vmtypes'][vmtypeNameToCreate]['target_share'])
              
         else:
            VCYCLE.logLine(spaceName, 'No more free capacity and/or suitable vmtype found within ' + spaceName)
            return
         
   
   def for_server_in_list(self, server, totalRunning, totalFound,
                          notPassedFizzleSeconds, foundPerVmtype, runningPerVmtype, weightedPerVmtype):
      '''Executes for every server found in the space, if the server is stopped or it has been running
      more than an specific time, the method will delete the server.'''
      spaceName = self.spaceName
      # This includes VMs that we didn't create and won't manage, to avoid going above space limit
      totalFound += 1
      
      # Just in case other VMs are in this space
      if server is None or server.name[:7] != 'vcycle-':
        return (totalRunning , totalFound)
      
      try:
        fileSpaceName = open('/var/lib/vcycle/machines/' + server.name + '/space_name', 'r').read().strip()
      except:
        # Not one of ours? Cleaned up directory too early?
        server.delete()
        VCYCLE.logLine(spaceName, 'Deleted ' + server.name + ' which has no tenancy name')
        return (totalRunning , totalFound)
      else:
        # Weird inconsistency, maybe the name changed? So log a warning and ignore this VM
        if fileSpaceName != self.spaceName:        
          VCYCLE.logLine(spaceName, 'Skipping ' + server.name + ' which is in ' + self.space['space_name'] + ' but has space_name=' + fileSpaceName)
          return (totalRunning , totalFound)

      try:
        vmtypeName = open('/var/lib/vcycle/machines/' + server.name + '/vmtype_name', 'r').read().strip()
      except:
        # Something went wrong?
        VCYCLE.logLine(spaceName, 'Skipping ' + server.name + ' which has no vmtype name')
        return (totalRunning , totalFound)

      if vmtypeName not in foundPerVmtype:
        foundPerVmtype[vmtypeName]  = 1
      else:
        foundPerVmtype[vmtypeName] += 1

      if (vmtypeName in weightedPerVmtype) and (VCYCLE.spaces[spaceName]['vmtypes'][vmtypeName]['target_share'] > 0.0):
         weightedPerVmtype[vmtypeName] += (1.0 / VCYCLE.spaces[spaceName]['vmtypes'][vmtypeName]['target_share'])
        
      properties = self._retrieve_properties(server, vmtypeName)
      totalRunning = self._update_properties(server, vmtypeName, runningPerVmtype, notPassedFizzleSeconds, properties, totalRunning)
      if self._delete(server, vmtypeName, properties):
         foundPerVmtype[vmtypeName] -= 1
         totalFound -= 1

         if vmtypeName in self.space['vmtypes'] and self.space['vmtypes'][vmtypeName]['log_machineoutputs']:
            VCYCLE.logLine(spaceName, 'Saving machineoutputs to /var/lib/vcycle/machineoutputs/' + spaceName + '/' + vmtypeName + '/' + server.name)
            VCYCLE.logMachineoutputs(server.name, vmtypeName, spaceName)
      
      return (totalRunning , totalFound)


   def createMachine(self, vmtypeName, proxy=False):
      '''Creates a new VM'''
      spaceName = self.spaceName
      serverName = self._server_name(name=spaceName)
      os.makedirs('/var/lib/vcycle/machines/' + serverName + '/machinefeatures')
      os.makedirs('/var/lib/vcycle/machines/' + serverName + '/jobfeatures')
      os.makedirs('/var/lib/vcycle/machines/' + serverName + '/machineoutputs')

      VCYCLE.createFile('/var/lib/vcycle/machines/' + serverName + '/vmtype_name',  vmtypeName,  0644)
      VCYCLE.createFile('/var/lib/vcycle/machines/' + serverName + '/space_name', spaceName, 0644)

      VCYCLE.createFile('/var/lib/vcycle/machines/' + serverName + '/machinefeatures/phys_cores', '1',        0644)
      VCYCLE.createFile('/var/lib/vcycle/machines/' + serverName + '/machinefeatures/vac_vmtype', vmtypeName, 0644)
      VCYCLE.createFile('/var/lib/vcycle/machines/' + serverName + '/machinefeatures/vac_space',  VCYCLE.spaces[spaceName]['vmtypes'][vmtypeName]['ce_name'],0644)

      VCYCLE.createFile('/var/lib/vcycle/machines/' + serverName + '/jobfeatures/cpu_limit_secs',  str(VCYCLE.spaces[spaceName]['vmtypes'][vmtypeName]['max_wallclock_seconds']), 0644)
      VCYCLE.createFile('/var/lib/vcycle/machines/' + serverName + '/jobfeatures/wall_limit_secs', str(VCYCLE.spaces[spaceName]['vmtypes'][vmtypeName]['max_wallclock_seconds']), 0644)

      try:
         server = self._create_machine(serverName, vmtypeName, proxy=proxy)
      except Exception as e:
         return 'Error creating new server: ' + str(e)
      
      if not server is None:
         VCYCLE.createFile('/var/lib/vcycle/machines/' + serverName + '/machinefeatures/vac_uuid', server.id, 0644)
      
      if not server is None:
         VCYCLE.logLine(spaceName, 'Created ' + serverName + ' (' + server.id + ') for ' + vmtypeName + ' within ' + spaceName)
      else:
         VCYCLE.logLine(spaceName, 'Created ' + serverName + ' for ' + vmtypeName + ' within ' + spaceName)
      return None


   def cleanupDirectories(self, spaceName, serverNames):
      if not VCYCLE.spaces[spaceName]['delete_old_files']:
         return

      try:
         dirslist = os.listdir('/var/lib/vcycle/machines/')
      except:
         return
      
      # Go through the per-machine directories
      for onedir in dirslist:

         # Get the space name
         try:
            fileSpaceName = open('/var/lib/vcycle/machines/' + onedir + '/space_name', 'r').read().strip()
         except:
            continue

         # Ignore if not in this space, unless not in any defined space
         if fileSpaceName in VCYCLE.spaces and (fileSpaceName != spaceName):
            continue

         # Get the vmtype
         try:
            vmtypeName = open('/var/lib/vcycle/machines/' + onedir + '/vmtype_name', 'r').read().strip()
         except:
            continue

         try:
            onedirCtime = int(os.stat('/var/lib/vcycle/machines/' + onedir).st_ctime)
         except:
            continue
        
         # Ignore directories created in the last 60 minutes to avoid race conditions
         # (with other Vcycle instances? OpenStack latencies?)
         if onedirCtime > (time.time() - 3600):
            continue

         # If the VM still exists then no deletion either
         if onedir in serverNames:
            continue

         # Save machineoutputs if not done so already
         if vmtypeName in self.space['vmtypes'] and self.space['vmtypes'][vmtypeName]['log_machineoutputs']:
            VCYCLE.logLine(spaceName, 'Saving machineoutputs to /var/lib/vcycle/machineoutputs/' + spaceName + '/' + vmtypeName + '/' + onedir)
            VCYCLE.logMachineoutputs(onedir, vmtypeName, spaceName)

         try:
            shutil.rmtree('/var/lib/vcycle/machines/' + onedir)
            VCYCLE.logLine(spaceName, 'Deleted /var/lib/vcycle/machines/' + onedir + ' (' + fileSpaceName + ' ' + str(int(time.time()) - onedirCtime) + 's)')
         except:
            VCYCLE.logLine(spaceName, 'Failed deleting /var/lib/vcycle/machines/' + onedir + ' (' + fileSpaceName + ' ' + str(int(time.time()) - onedirCtime) + 's)')


   def cleanupMachineoutputs(self, spaceName):
      try:
         spacesDirslist = os.listdir('/var/lib/vcycle/machinesoutputs/')
      except:
         return
      
      # Go through the per-machine directories
      for spaceDir in spacesDirslist:
         try:
            vmtypesDirslist = os.listdir('/var/lib/vcycle/machinesoutputs/' + spaceDir)
         except:
            continue

         for vmtypeDir in vmtypesDirslist:
            try:
               hostNamesDirslist = os.listdir('/var/lib/vcycle/machinesoutputs/' + spaceDir + '/' + vmtypeDir)
            except:
               continue
 
            for hostNameDir in hostNamesDirslist:
               hostNameDirCtime = int(os.stat('/var/lib/vcycle/machinesoutputs/' + spaceDir + '/' + vmtypeDir + '/' + hostNameDir).st_ctime)
               try: 
                  expirationDays = VCYCLE.spaces[spaceName][vmtypeDir]['machineoutputs_days']
               except:
                  # use the default if something goes wrong (configuration file changed?)
                  expirationDays = 3.0
           
               if hostNameDirCtime < (time.time() - (86400 * expirationDays)):
                  try:
                     shutil.rmtree('/var/lib/vcycle/machinesoutputs/' + spaceDir + '/' + vmtypeDir + '/' + hostNameDir)
                     VCYCLE.logLine(spaceName, 'Deleted /var/lib/vcycle/machinesoutputs/' + spaceDir + '/' + vmtypeDir + '/' + hostNameDir + ' (' + str((int(time.time()) - hostNameDirCtime)/86400.0) + ' days)')
                  except:
                     VCYCLE.logLine(spaceName, 'Failed deleting /var/lib/vcycle/machinesoutputs/' + spaceDir + '/' + vmtypeDir + '/' + hostNameDir + ' (' + str((int(time.time()) - hostNameDirCtime)/86400.0) + ' days)')


   @abc.abstractmethod
   def _create_client(self):
      '''Creates a new Client. It is an abstract method'''
      pass


   @abc.abstractmethod
   def _servers_list(self):
      '''Returns a list with of the servers created in a space. It is an abstract method'''
      pass
   
   
   @abc.abstractmethod
   def _retrieve_properties(self, server, vmtypeName):
      '''Returns the properties of a VM. It is an abstract method'''
      pass

   
   @abc.abstractmethod
   def _update_properties(self, server, vmtypeName,runningPerVmtype, notPassedFizzleSeconds, properties, totalRunning):
      '''Updates the properties of a VM'''
      pass
   
   
   @abc.abstractmethod
   def _describe(self, server):
      '''Returns the description of a VM.'''
      pass
   
   @abc.abstractmethod
   def _delete(self, server, vmtypeName, properties):
      '''Deletes a VM'''
      pass
   
   
   @abc.abstractmethod
   def _server_name(self,name=None):
      '''Returns the name of a VM'''
      pass


   @abc.abstractmethod
   def _create_machine(self, serverName, vmtypeName, proxy=False):
      '''Creates a new VM inside a space'''
      pass

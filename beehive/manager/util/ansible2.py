'''
Created on Feb 17, 2017

@author: darkbk

from : https://serversforhackers.com/running-ansible-2-programmatically
'''
import os
import json
from ansible.inventory import Inventory
#from ansible.inventory.manager import InventoryManager
#from ansible.vars.manager import VariableManager
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.utils.display import Display as OrigDisplay
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from logging import getLogger
from datetime import datetime

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

logger = getLogger(__name__)

'''
class Display(OrigDisplay):
    def __init__(self, verbosity=0):
        OrigDisplay.__init__(self, verbosity)
        
    def display(self, msg, color=None, stderr=False, screen_only=True, 
                log_only=False):
        OrigDisplay.display(self, msg, color=color, stderr=stderr, 
                            screen_only=screen_only, log_only=log_only)
        logger.debug(msg)
'''

#display = Display()


class Options(object):
    """Options class to replace Ansible OptParser
    """
    def __init__(self, verbosity=None, inventory=None, listhosts=None, subset=None, module_paths=None, extra_vars=None,
                 forks=None, ask_vault_pass=None, vault_password_files=None, new_vault_password_file=None,
                 output_file=None, tags=None, skip_tags=[], one_line=None, tree=None, ask_sudo_pass=None, ask_su_pass=None,
                 sudo=None, sudo_user=None, become=None, become_method=None, become_user=None, become_ask_pass=None,
                 ask_pass=None, private_key_file=None, remote_user=None, connection=None, timeout=None, ssh_common_args=None,
                 sftp_extra_args=None, scp_extra_args=None, ssh_extra_args=None, poll_interval=None, seconds=None, check=None,
                 syntax=None, diff=None, force_handlers=None, flush_cache=None, listtasks=None, listtags=None, module_path=None,
                 limit=None):
        self.verbosity = verbosity
        self.inventory = inventory
        self.listhosts = listhosts
        self.subset = subset
        self.module_paths = module_paths
        self.extra_vars = extra_vars
        self.forks = forks
        self.ask_vault_pass = ask_vault_pass
        self.vault_password_files = vault_password_files
        self.new_vault_password_file = new_vault_password_file
        self.output_file = output_file
        self.tags = tags
        self.skip_tags = skip_tags
        self.one_line = one_line
        self.tree = tree
        self.ask_sudo_pass = ask_sudo_pass
        self.ask_su_pass = ask_su_pass
        self.sudo = sudo
        self.sudo_user = sudo_user
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.become_ask_pass = become_ask_pass
        self.ask_pass = ask_pass
        self.private_key_file = private_key_file
        self.remote_user = remote_user
        self.connection = connection
        self.timeout = timeout
        self.ssh_common_args = ssh_common_args
        self.sftp_extra_args = sftp_extra_args
        self.scp_extra_args = scp_extra_args
        self.ssh_extra_args = ssh_extra_args
        self.poll_interval = poll_interval
        self.seconds = seconds
        self.check = check
        self.syntax = syntax
        self.diff = diff
        self.force_handlers = force_handlers
        self.flush_cache = flush_cache
        self.listtasks = listtasks
        self.listtags = listtags
        self.limit = limit
        self.module_path = module_path
        self.cwd = limit


class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """
    def __init__(self, display=None, frmt=None):
        CallbackBase.__init__(self, display=display)
        self.frmt = frmt
    
    def v2_runner_on_ok(self, result):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host.get_name()
        logger.debug(u'Get host: %s' % host)
        logger.debug(u'Get format: %s' % self.frmt)
        logger.debug(u'Get result: %s' % result._result.get(u'stdout_lines', None))
        if self.frmt == u'json':
            print json.dumps({host.name: result._result.get(u'stdout_lines', None)}, indent=4)
        elif self.frmt == u'text':
            print(host)
            print(u'-----------------------------')
            for item in result._result.get(u'stdout_lines', []):
                print(u'  %s' % item)
            print(u'')
                        
    def v2_runner_on_failed(self, result, ignore_errors=False):
        host = result._host.get_name()
        logger.debug(u'Get host: %s' % host)
        logger.debug(u'Get format: %s' % self.frmt)
        self.logger.warn(result._result)
        logger.error(u'Get result: %s' % result._result.get(u'stderr_lines', None))
        if self.frmt == u'json':
            print json.dumps({host.name: result._result.get(u'stderr_lines', None)}, indent=4)
        elif self.frmt == u'text':
            print(host)
            print(u'-----------------------------')
            for item in result._result.get(u'stderr_lines', []):
                print(u'  %s' % item)
            print(u'')            


class CallbackModule(CallbackBase):
    """
    This callback module tells you how long your plays ran for.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'timer'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):

        super(CallbackModule, self).__init__()

        self.start_time = datetime.now()

    def days_hours_minutes_seconds(self, runtime):
        minutes = (runtime.seconds // 60) % 60
        r_seconds = runtime.seconds - (minutes * 60)
        return runtime.days, runtime.seconds // 3600, minutes, r_seconds

    def playbook_on_stats(self, stats):
        self.v2_playbook_on_stats(stats)

    def v2_playbook_on_stats(self, stats):
        end_time = datetime.now()
        runtime = end_time - self.start_time
        self._display.display("Playbook run took %s days, %s hours, %s minutes, %s seconds" % (self.days_hours_minutes_seconds(runtime)))


class Runner(object):
    """Ansible api v2 playbook runner
    """
    def __init__(self, inventory=None, verbosity=2, module=u'', vault_password=None):
        self.options = Options()
        self.options.private_key_file = None
        self.options.verbosity = verbosity
        self.options.connection = u'ssh'  # Need a connection type "smart" or "ssh"
        
        # set module
        self.options.module_path = module
        
        # Set global verbosity
        self.display = display
        self.display.verbosity = verbosity
        
        # Gets data from YAML/JSON files
        self.loader = DataLoader()
        if vault_password is not None:
            self.loader.set_vault_password(vault_password)
        
        # All the variables from all the various places
        self.variable_manager = VariableManager()
        
        # invontory reference
        self.inventory = inventory
        
        self.passwords = None
        logger.debug(u'Create new runner: %s' % self)
        
    def get_inventory(self, group=None):
        """Get inventory, using most of above objects
        """
        try:
            inventory = Inventory(loader=self.loader, 
                                  variable_manager=self.variable_manager, 
                                  host_list=self.inventory)
            hosts = inventory.get_group_dict()
            if group is not None:
                hosts = hosts[group]
            return hosts
        except Exception as ex:
            logger.error(ex, exc_info=1)
            raise Exception(ex)
    
    def get_inventory_with_vars(self, group):
        """Get inventory, using most of above objects
        """
        inventory = Inventory(loader=self.loader, 
                              variable_manager=self.variable_manager, 
                              host_list=self.inventory)
        self.variable_manager.set_inventory(inventory)
        #self.variable_manager.group_vars_files = u'%s/group_vars/%s' % (self.inventory, group)
        #print self.variable_manager.get_vars(self.loader)
        #print inventory.get_group_variables(group, True)
        hosts = inventory.list_hosts(group)

        #print inventory.groups[group].vars
        #print inventory.get_host_variables('10.102.184.52')

        #print inventory.get_vars(group, new_pb_basedir, return_results)
        
        return hosts, None
    
    def run_playbook(self, group, playbook, private_key_file, run_data, become_pas, tags=[], vault_password=None):
        """
        """
        
        # Gets data from YAML/JSON files
        self.loader = DataLoader()
        if vault_password is not None:
            self.loader.set_vault_password(vault_password)
        
        # All the variables from all the various places
        self.variable_manager = VariableManager()
        
        # All the variables from all the various places
        self.variable_manager.extra_vars = run_data
        self.variable_manager.group_vars_files = u'%s/group_vars' % self.inventory
        #print self.variable_manager.get_vars(self.loader)
        
        # set options
        self.options.tags = tags
        self.options.limit = group
        
        # Set inventory, using most of above objects
        inventory = Inventory(loader=self.loader, 
                              variable_manager=self.variable_manager, 
                              host_list=self.inventory)
        inventory.subset(group)
        logger.debug(u'Run playbook: %s' % playbook)
        logger.debug(u'Run playbook with vars: %s' % run_data)
        logger.debug(u'Run playbook with tags: %s' % tags)
        logger.debug(u'Run playbook over group: %s' % group)
        logger.debug(u'Run playbook over hosts: %s' % inventory.list_hosts(group))
        #logger.debug(u'Run playbook tasks: %s' % self.options.listtasks)
        self.variable_manager.set_inventory(inventory)

        # Setup playbook executor, but don't run until run() called
        self.pbex = PlaybookExecutor(
            playbooks=[playbook], 
            inventory=inventory, 
            variable_manager=self.variable_manager,
            loader=self.loader, 
            options=self.options,
            passwords=None)
        
        # Results of PlaybookExecutor
        res = self.pbex.run()
        '''
        stats = self.pbex._tqm._stats

        # Test if success for record_logs
        run_success = True
        ihosts = sorted(stats.processed.keys())
        for h in ihosts:
            t = stats.summarize(h)
            if t[u'unreachable'] > 0 or t[u'failures'] > 0:
                run_success = False'''
    
        # Remove created temporary files
        #os.remove(hosts.name)
        #os.remove(u'/tmp/.ssh')

        return res
    
    def run_task(self, group, gather_facts=u'no', tasks=[], frmt=u'json'):
        """
        """
        # set options
        self.options.tags = []        
        
        # Set inventory, using most of above objects
        #inventory = InventoryManager(self.loader, sources=self.inventory)
        inventory = Inventory(loader=self.loader, 
                              variable_manager=self.variable_manager, 
                              host_list=self.inventory)
        inventory.subset(group)
        self.variable_manager.set_inventory(inventory)        

        # create play with tasks
        play_source =  dict(
                name = u'Ansible Play',
                hosts = group,
                gather_facts = gather_facts,
                tasks = tasks
            )
        play = Play().load(play_source, 
                           variable_manager=self.variable_manager, 
                           loader=self.loader)

        # Instantiate our ResultCallback for handling results as they come in
        results_callback = ResultCallback(display=display, frmt=frmt)

        # run it
        tqm = None
        result = None
        try:
            # Use our custom callback instead of the ``default`` callback plugin
            tqm = TaskQueueManager(
                      inventory=inventory,
                      variable_manager=self.variable_manager,
                      loader=self.loader,
                      options=self.options,
                      passwords=self.passwords,
                      stdout_callback=results_callback,  
                  )
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()

        return result

# set global display
#import ansible.inventory
#ansible.inventory.display = Runner.display
#ansible.inventory.logger = getLogger(u'ansible')
        
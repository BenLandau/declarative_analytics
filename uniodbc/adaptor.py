import inspect
import yaml
from pprint import pprint as pp
import os
import pymssql

class Adaptor():
    def __init__(self,verbose=False):
        self.verbose = verbose
        try:
            self.configs = self.read_config(os.getcwd()+"/uniodbc/config_private.yml")
        except FileNotFoundError:
            self.configs = self.read_config(os.getcwd()+"/uniodbc/config.yml")
        self.connections = {}
        self.caller_scope = inspect.stack()[1][0].f_locals


    def read_config(self,filename):
        with open(filename,'r') as f:
            configs = yaml.load(f)
        return configs


    def connect(self,datasource):
        # Refresh scope
        self.caller_scope = inspect.stack()[1][0].f_globals
        # Print scope
        if self.verbose: pp(self.caller_scope)
        # Do connection
        connector = getattr(self.caller_scope[self.configs[datasource]['module']],
                'connect')
        self.connections[datasource] = connector(**self.configs[datasource]['params'])
        return self.connections[datasource]

    def list_datasources(self):
        datasources = list(self.configs.keys())
        datasources.sort()
        for ds in datasources:
            print('{:20}{:10}'.format(ds,'Connected' if ds in self.connections.keys() else ''))

    def execute(self,datasource,query,descriptor=False):
        if datasource not in self.connections.keys():
            self.connect(datasource)

        cursor = self.connections[datasource].cursor()

        cursor.execute(query)
        if descriptor:
            return {
                 "columns": [col[0] for col in cursor.description]
                ,"data": cursor.fetchall()
            }
        else:
            return cursor.fetchall()


from uniodbc.adaptor import Adaptor
import yaml
import jinja2 as j2
import os
import datetime
import numpy as np
import pymssql
import pyodbc
import pandas as pd
from pprint import pprint

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

class DataManager():
    def __init__(self,adaptor):
        self.ad = adaptor
        '''
        Get query configs and render the queries
        '''
        with open(DIR_PATH+'/queries.yml','r') as f:
            query_metadata = yaml.load(f)
        self.query_metadata = query_metadata
        raw_queries = query_metadata['queries']
        query_templates = query_metadata['query_templates']
        self.queries = {}
        if 'globals' in query_metadata:
            globals = query_metadata['globals']

        for query_name, query_dict in raw_queries.items():
            if 'query_template' in query_dict:

                template_name = query_dict['query_template']
                # Extract template from the entry
                temp = j2.Template(query_templates[template_name]['template'])
                # Retrieve query parameters
                temp_params = query_templates[template_name]['parameters']
                # Iterate over parameters and fill in
                self.queries[query_name] = {
                     'source': query_dict['source']
                    ,'template': temp
                    ,'params': dict(
                         implemented = {}
                        ,unimplemented = []
                        ,deferred={}
                        ,from_csv = {}
                    )
                    ,'query': None
                    ,'data': None
                    ,'query_type': None
                }

                # Check for query type
                if 'type' in query_dict:
                    self.queries[query_name]['query_type'] = query_dict['type']

                param_values = query_dict['parameter_values']
                for param in temp_params:
                    try:
                        # Check for static or dynamic values
                        if 'value' in param_values[param]:
                            # Check the static value field is not none for implementation
                            if param_values[param]['value'] is None:
                                self.queries[query_name]['params']['unimplemented'].append(param)
                            else:
                                self.queries[query_name]['params']['implemented'][param] = param_values[param]['value']
                        elif 'from_global' in param_values[param]:
                            try:
                                self.queries[query_name]['params']['implemented'][param] = globals[param_values[param]['from_global']]
                            except KeyError:
                                print('No Globals Variables found in data configuration')
                                raise(KeyError)
                        elif 'from_query' in param_values[param]:
                            self.queries[query_name]['params']['deferred'][param] = param_values[param]['from_query']
                        elif 'from_csv' in param_values[param]:
                            self.queries[query_name]['params']['from_csv'][param] = param_values[param]['from_csv']
                    except KeyError:
                        print("Parameter '{}' missing from query spec in query '{}'".format(param,query_name))
                        raise(KeyError)

                if not any([self.queries[query_name]['params']['unimplemented'],self.queries[query_name]['params']['deferred']]):
                    self.queries[query_name]['query'] = temp.render(**self.queries[query_name]['params']['implemented'])




            elif 'query' in query_dict:
                self.queries[query_name] = dict(
                    query = query_dict['query']
                    ,source = query_dict['source']
                    ,data = None
                )
            else:
                raise(ValueError)


    def get_all_data(self):
        raise(NotImplementedError)

    def get_data(self,query_name,**kwargs):
        print('  [*] Getting',query_name,'data...')
        # Test if template query
        if 'template' in self.queries[query_name]:
            # Test for unimplemented
            if self.queries[query_name]['params']['unimplemented']:
                if set(kwargs.keys()) == set(self.queries[query_name]['params']['unimplemented']):
                    self.queries[query_name]['params']['implemented'].update(kwargs)
                    self.queries[query_name]['params']['unimplemented'] = []
                else:
                    print('The following parameters are still unimplemented for {}:'.format(query_name),
                          self.queries[query_name]['params']['unimplemented'])
                    raise(ValueError)

            #Test for csv
            if self.queries[query_name]['params']['from_csv']:
                for csv_param_name, filename in self.queries[query_name]['params']['from_csv'].items():
                    csv_data = pd.read_csv(filename).values.squeeze().tolist()
                    self.queries[query_name]['params']['implemented'][csv_param_name] = \
                        self.parse_result(csv_data)
                self.queries[query_name]['params']['from_csv']= {}

            # Test for deferred
            if self.queries[query_name]['params']['deferred']: # If ANY deferred
                for deferred_param_name,deferred_query_name in self.queries[query_name]['params']['deferred'].items():
                    # If the deferred call hasn't been made yet
                    if self.queries[deferred_query_name]['data'] is None:
                        self.get_data(deferred_query_name)

                    # # Remove param from deferred list
                    # self.queries[query_name]['params']['deferred'].pop(deferred_param_name)
                    # Assign to implemented params list
                    self.queries[query_name]['params']['implemented'][deferred_param_name] = \
                        self.queries[deferred_query_name]['data']
                self.queries[query_name]['params']['deferred'] = {}


            temp = self.queries[query_name]['template']
            self.queries[query_name]['params']['implemented'] = self._parse_yaml(self.queries[query_name]['params']['implemented'])
            self.queries[query_name]['query'] = temp.render(**self.queries[query_name]['params']['implemented'])
            self.queries[query_name]['query'] = self.clean_query(self.queries[query_name]['query'],self.queries[query_name]['query_type'])

        result = self.ad.execute(self.queries[query_name]['source'],self.queries[query_name]['query'],descriptor=True)
        data = self.parse_result(np.array(result['data']))
        columns = result['columns']
        # Squeeze here
        data = np.array(data).squeeze().tolist()
        self.queries[query_name]['data'] = self._parse(data)
        self.queries[query_name]['columns'] = columns
        print('  [x] Getting',query_name,'data complete!')

    def get_df(self,query_name):
        if not self.queries[query_name]['data']:
            self.get_data(query_name)
        return pd.DataFrame(dict(zip(
            self.queries[query_name]['columns'],
            np.array(self.queries[query_name]['data']).T)))



    ####################### USEABILITY #########################

    def get_query_info(self):
        '''
        Useability function.
        Shows query list and status.
        '''
        output = []
        for key in self.queries.keys():
            if self.queries[key]['data'] is not None:
                output.append([key,'queried'])
            else:
                output.append([key,'not queried'])
        return pd.DataFrame(output,columns=['Query Name','Status'])

    ####################### HELPERS #########################

    def deferred_call(self,query_name,execute=False):
        if execute:
            return self.get_data(query_name)


    def _flatten(self,input):
        '''
        Flatten list of tuples, for example [(1,),(2,),(3,)] as is often returned
        TODO: This can be implemented *way* better. It's not even a truly recursive algorithm...
        '''
        ans = []
        def flatten(feed):
            try:
                for elem in feed:
                    flatten(elem)
            except:
                ans.append(feed)

        flatten(input)

        return tuple(ans)

    def _parse_yaml(self,input_dict):
        '''
        :param input_dict:
        Takes an input dictionary from loaded YAML and imposes custom parsing rules.
        :return:
        Returns dictionary with custom rules applied.
        '''
        new_dict = {}
        for input_name,input in input_dict.items():
            new_dict[input_name] = self._parse(input)
        return new_dict

    def _parse(self,input):
        '''
        :param input:
        Takes an input value, and manipulates it based on rules here.
        Called by _parse_yaml
        :return:
        Returns parsed value with rules applied.
        '''
        if isinstance(input,datetime.datetime):
            output = input.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(input,datetime.date):
            output = input.strftime('%Y-%m-%d')
        elif isinstance(input,str):
            output = input.strip()
        else:
            output = input

        return output

    ######## DATA Parsing ###########

    def parse_result(self,result):
    # Parser
        vector_parser = np.vectorize(self._parse)
        return vector_parser(np.array(result)).tolist()

    def dec_2_float(self,result,cast_type=float):
        return np.array(result).astype(cast_type)

    def clean_query(self,query,query_type):
        output = query
        if query_type is None:
            output = output.replace('[','(').replace(']',')')
        elif query_type == 'openquery':
            out_list = output.split("'")
            out_list = [out_list[0],"'".join(out_list[1:-1]),out_list[-1]]
            out_list[1] = out_list[1].replace('[','(').replace(']',')').replace("'",r"''")
            output = "'".join(out_list)
        return output



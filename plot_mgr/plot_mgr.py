from plotly.offline import *
import plotly.graph_objs as go
from plotly.tools import FigureFactory as ff
from plotly import tools
import yaml
import os

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

class PlotManager():
    def __init__(self,data_manager):
        self.dm = data_manager
        '''
        Get plot configs and create traces.
        '''
        with open(DIR_PATH+'/plots.yml','r') as f:
            self.plot_metadata = yaml.load(f)
        self.plots = {}
        # Build layout, build traces
		# for plotname,plot_details in self.plot_metadata['plots'].items():
        if 'fig_order' in self.plot_metadata:
            namelist = self.plot_metadata['fig_order']
        else:
            namelist = self.plot_metadata['plots'].keys()
        for plotname in namelist:
            plot_details = self.plot_metadata['plots'][plotname]
            print('  [*] Building',plotname,'plot...')
            self.plots[plotname] = {}
            self.plots[plotname]['traces'] = []
            self.plots[plotname]['layout'] = self.layout_factory(
                plot_details['layout']
            )
            # Check whether scatter requested
            if plot_details['plot_type'] == 'scatter':
                for trace_spec in plot_details['traces']:
                    mode = trace_spec['mode'] if 'mode' in trace_spec else 'lines'

                    self.plots[plotname]['traces'].append(
                        self.scatter_factory(
                             trace_spec['name']
                            ,self.dm.get_df(trace_spec['data']['query'])
                            ,trace_spec['data']['dimension']
                            ,trace_spec['data']['measure']
                            ,mode
                            ,trace_spec['properties']
                        )
                    )
            print('  [*] Building',plotname,'plot complete!')

    def build_figure(self,plotname):
        self.plots[plotname]['figure'] = self.figure_factory(
             self.plots[plotname]['traces']
            ,self.plots[plotname]['layout']
        )


    def scatter_factory(self,name,df,dimension,measure,mode,properties_dict):
        trace = go.Scatter(
             x = df[dimension].values
            ,y = df[measure].values
            ,name = name
            ,mode = mode
            ,line=properties_dict
        )
        return trace

    def layout_factory(self,titles_dict):
        layout = go.Layout(**titles_dict)
        return layout

    def figure_factory(self,traces,layout):
        return go.Figure(data=traces,layout=layout)


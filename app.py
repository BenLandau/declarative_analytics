import pymssql
from plot_mgr.plot_mgr import *
from data_mgr.data_mgr import *
from uniodbc.adaptor import *
import pandas as pd
from pprint import pprint

from plotly.offline import *
import plotly.graph_objs as go
from plotly.tools import FigureFactory as ff
from plotly import tools

import dash
import dash_core_components as dcc
import dash_html_components as html
import yaml
from generate_plots import plotgen

with open('plot_mgr/plots.yml','r') as f:
    plot_config = yaml.load(f)

# ADAPTOR -> DATA_MANAGER -> PLOT_MANAGER

ad = Adaptor()
dm = DataManager(ad)
pm = PlotManager(dm)

app = dash.Dash()

if 'fig_order' in plot_config:
    print('  [x] USING PLOT ORDER FROM YAML')
    fig_order = plot_config['fig_order']
else:
    print('  [x] NO PLOT ORDER IN YAML: PLOTTING ALL IN RANDOM ORDER')
    fig_order = plot_config['plots'].keys()

for elem in fig_order:
    pm.build_figure(elem)

elements = [dcc.Graph(id=x,figure=pm.plots[x]['figure']) for x in fig_order]

app.layout = html.Div([
    html.Meta(name='HWBB'),
    html.Div(
    children = [

        html.H1(children='HWBB Report Dashboard (Top 50 as of 12 Nov 2017)')

        ] + elements
    )])

if __name__ == '__main__':
    app.run_server(host='0.0.0.0',debug=False)

## Synopsis

This is a declarative framework designed to allow data extraction, manipulation and presentation all without writing a single line of code. The framework exposes YAML APIs for the user to fill in at lightning speed, while letting the Python backend do all the heavy lifting.

Workflow with this software involves three steps:
	1. Describe what data connections are required for your project (uniodbc/config.yml)
	2. Outline the data you would like to make available, using a combination of queries and query templates (`data_mgr/queries.yml`)
	3. Specify how you would like your plots to look (`plot_mgr/plots.yml`)

After running `python3 app.py` in the root folder, the plots will then be exposed at `localhost:8050`.

The templating scheme used here is very basic YAML. Indentation is key in YAML if you would like to avoid frustration - see [this basic guide](http://docs.ansible.com/ansible/latest/YAMLSyntax.html) to familisarise yourself with the general idea.

## Installation

TODO

## Running the program

Simply go into the root directory and run `python3 app.py`. Then navigate to `localhost:8050` to view your graphs once they have been rendered.

## API Reference

### Step 1: Defining Database Connections
All the action takes place in `uniodbc/config.yml`, where you will be defining what databases are needed and how to connect to them. Open `config.yml` in your favourite IDE (e.g. Notepad++), where you'll follow the format of this snippet roughly:
```
--
  conn_1:
    comment: First connection object!
    params:
      driver: SQL Server
      server: <Server Name>
      uid: <username>
      pwd: <password>
    module: pyodbc
...

```

Here we've defined three different data sources: `bilby`, `sqlserver` and `hive`. These names are defined on the shallowest indent, and will be the way you'll refer to these data sources in later steps.

* The `comment` field allows you to give a brief description of the datasource if you like - you can leave it blank if you like.
* The `params` field is where you provide the connection parameters. These are roughly your username, password and server name. Different modules give these parameters different names, but the example above covers most of the potential use-cases. 
* The `module` field describes what module to use. As a general rule, use:
	- `pymssql` for SQL Server connections
	- `pyodbc` for anything else


### Step 2: Defining queries
For this step, go into the `data_mgr` folder, and edit `queries.yml`. Here the data to be obtained from the databases is named and defined.

```
globals:
  int_week: 2017-09-25 00:00:00
  pre_week: 2017-04-24 00:00:00

queries:
  static_value_example:
    source: conn_1
    query_template: template_1
    parameter_values:
      var_1:
        from_csv: file_at_root.csv
      var_2:
        value: 5000


  static_query_example:
    source: conn_1 
    query: >
      select week_starting from main_db..weekly_scores

  param_from_query:
    source: conn_1 
    query_template: template_1 
    parameter_values:
      var_1:
        from_csv: cdrs.csv
      var_2:
        from_query: static_query_example 

  param_from_global:
    source: conn_1 
    query_template: template_1 
    parameter_values:
      var_1:
        value: 100
      var_2:
        from_global: int_week

query_templates:

  template_1:
    template: >
        SELECT some_attribute, some_other_attribute 
        FROM a_table
        WHERE
          some_field = {{var_1}}
          AND some_other_field = {{var_2}} 
    parameters:
      - var_1 
      - var_2 

    [... more query templates ...]

```

Here there are three top-level elements:
    1. `globals` are named variables that you would like to reuse throughput the file as query template parameters.
    2. `queries` are the accessible data containers that you will access later when plotting or manipulating algorithmically.
    3. `query_templates` are parameterised queries that you can reuse in the `queries` section. Parameters are notated in the body of the query using double brackets with a name inside, like so: `{{ variable _name }}`

Now to the contents of these elements:

#### Globals
This section is pretty simple, it's just an indented key value pair: `[variable name]: [variable value}`

#### Queries
There are five queries defined above: `throughput_pdf_recent`, `throughput_pdf_intermediate`, `non_cdr_cells`, `latest_week_starting`, `pdcp_vol_ts`. Names are defined by the top-level query entry, and properties are indented to show they belong to that query name. The properties are:

`source` - The data source name. Here you enter one of the data source names defined in Step 1. This is case sensitive and must match exactly.
`query_template` or `query`: If wanting to use a `query_template` (as in all the above queries except for `latest_week_starting`), simply write the name of the query template you'd like to use, and the `parameter_values` with which to render the template.
If using a static `query` (as in `latest_week_starting`, then directly insert the query as seen above. The right angle bracket `>` is required to prevent the program misinterpreting line breaks in your query.
`type`: Optional parameter used to signal if the `openquery()` function is used within the query. This notifies the query parser that special escaping of characters is required for the server object interface.

`parameter_values` - Required only if using `query_template`. Nest the parameter names under here. As value inputs to the parameters you have a few choices:
    * `value`: Inputs a static value to the parameter. As seen in `static_value_example` for `var_1`.
    * `from_global`: Inputs a static variable by name from the list of variables defined in `globals`. See the `param_from_global` query parameter `var_2`.
    * `from_query`: Uses the output of another query as an input to this query parameter. Simply enter the name of the query to be used (see `var_2` in `param_from_query`). *NOTE*: The output of the query to be used _must_ only return a single column. Multi-column query outputs are not yet compatible.
    * `from_csv`: Pulls a list of objects from a csv file located in the root directory of this repository. The CSV file must also be single-columned.



### Step 3: Defining Plots
For this step, edit the file `plot_mgr/plots.yml`. Here is a sample extract:
```
plots:

  comparison_1:
    plot_type: scatter
    layout:
      # Titles here are whatever you like to appear on the plot.
      title: Comparison 1 Title
      xaxis:
        title: Dimension Name
        # Optional range parameter as array with min and max values.
        range:
          - 0
          - 100
      yaxis:
        title: Measure Name 
    traces:
      - name: First line on these axes
        data:
          query: static_value_example 
          # Dimension is x-axis. Measure is y-axis.
          # The value of each of these must be the name of a field returned in the query.
          # In this example 'some_attribute' and 'some_other_attribute' were both returned
          # as columns in the sql query output.
          dimension: some_attribute
          measure: some_other_attribute
        properties:
          color: blue
      - name: Second line on these axes 
        data:
          query: param_from_query 
          dimension: some_attribute
          measure: some_other_attribute
        properties:
          color: orange

  comparison_2:
    plot_type: scatter
    layout:
      title: Comparison 2 Title
      xaxis:
        title: Dimension Name
      yaxis:
        title: Measure Name 
        
    traces:
      - name: Only one line on second set of axes
        data:
          query: static_value_example 
          dimension: some_attribute 
          measure: some_other_attribute 
        properties:
          color: blue
          # Make a dashed line! Follows all plotly properties.
          dash: dash

# Here list the plots you would like to build. 
# Plot names defined above but not mentioned here
# are not processed - ie data is not pulled from the db. 
# Essentially 'lazy evaluation'
# Order sensitive.
fig_order:
  - comparison_1
  - comparison_2

```
There are two headings in this file: `plots` and `fig_order`.

#### Plots

There are two plots defined in this extract; `comparison_1` and `comparison_2`. First the `plot_type` is defined - at this stage only `scatter` is supported.

The `layout` describes the global attribute for that particular plot. Title is set in the `title` parameter, and x/y axis titles are defined under `xaxis` and `yaxis` entries. A range can optionally be set for either or both axes as shown in `comparison_1`.

The `traces` heading allows you to define a list of traces (or lines) to draw on the given plot. Each trace must be prefixed by a dash (`-`) and nested under it as shown above. `comparison_1`, for example, has two traces on a single plot. The `name` parameter defines the name that will appear in the legend, and `properties` defines the colour and style of the line with `color` and `dash` respectively. If `dash` is not defined, a solid line will be drawn. If `dash: dash` is written then the line will be dashed.

Finally the `data` to be plotted is defined as above using `query` names from Step 2. The `dimension` parameter is the column to be used as the x-axis from the output of the query SQL (it's good practice to name your output columns for use here). The `measure` parameter is the y-axis column from the query output.

#### fig_order

Optional heading if a particular order is required for plots, or if only some plots defined are actually to be displayed. Essentially a list of plots, the renderer will cycle through them and plot only the ones written in their particular order.

If omitted, all plots will be rendered in random order.

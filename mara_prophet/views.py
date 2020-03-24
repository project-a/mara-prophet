import flask
from mara_page import acl, navigation, response, _, html, bootstrap
from mara_prophet import config
import io
import pickle
import mara_db.postgresql
import base64
import pandas as pd

import matplotlib

matplotlib.use('agg')

from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

acl_resource = acl.AclResource(name='Forecasts')

blueprint = flask.Blueprint('forecasts', __name__, static_folder='static', url_prefix='/forecasts')


def forecasts_navigation_entry():
    return navigation.NavigationEntry(
        label='Forecasts',
        uri_fn=lambda: flask.url_for('forecasts.view_plots'),
        icon='fast-forward',
        description='KPI forecasting')


@blueprint.route('/')
@acl.require_permission(acl_resource)
def view_plots():
    return response.Response(
        html=[
            _.div(id='forecast-container')[
                _.div(class_="")[
                    [[_.div(class_='row')[
                          _.div(class_='col-xl-12')[_.div(class_='section-header')[forecast.metric_name]]],
                      _.div(class_='row')[
                          _.div(class_='col-xl-12')[
                              _.p()['Number of days: ' + str(forecast.number_of_days), _.br(),
                                    'Time-series query: ',
                                    html.highlight_syntax(forecast.time_series_query,
                                                          language='postgresql')],

                              bootstrap.card(
                                  header_left='Forecast plot of "' + forecast.metric_name + '"',
                                  header_right=_.div()[
                                      # config.forecast_table_name
                                      # _.a(class_='query-control', style='margin-right: 10px',
                                      #     href='#')[
                                      #     _.span(class_='fa fa-download')[' ']],

                                      _.a(class_='query-control',
                                          href=f"javascript:showQueryDetails('"
                                          f"{flask.url_for('forecasts.query_details', name=forecast.metric_name)}')")[
                                          _.span(class_='fa fa-eye')[' ']]
                                  ],
                                  body=[
                                      html.asynchronous_content(
                                          flask.url_for(
                                              'forecasts.get_plot_image',
                                              name=forecast.metric_name.lower().replace(' ', '_').replace('-', '_'),
                                              components='False')),
                                      _.br(), _.br(),
                                      _.div(class_='modal fade', id='query-details-dialog',
                                            tabindex="-1")[
                                          _.div(class_='modal-dialog modal-lg', role='document')[
                                              _.div(class_='modal-content')[
                                                  _.div(class_='modal-header')[
                                                      _.h5(class_='modal-title')['Time-series query'],
                                                      _.button(
                                                          **{'type': "button", 'class': "close",
                                                             'data-dismiss': "modal",
                                                             'aria-label': "Close"})[
                                                          _.span(**{'aria-hidden': 'true'})['&times']]],
                                                  _.div(class_='modal-body', id='query-details')['']
                                              ]
                                          ]],
                                  ])
                          ]
                          ,
                          _.div(class_='col-xl-12')[
                              bootstrap.card(
                                  header_left='Forecast components (trend, holidays, seasonality) of "{}"'.format(
                                      forecast.metric_name),
                                  header_right='',
                                  body=[
                                      html.asynchronous_content(
                                          flask.url_for(
                                              'forecasts.get_plot_image',
                                              name=forecast.metric_name.lower().replace(' ', '_').replace('-', '_'),
                                              components='True')),
                                  ])], _.hr()
                      ]]
                     for forecast in config.forecasts()
                     ]
                ]
            ],
            _.script['''''']
        ],
        title='Forecasts',
        css_files=[
            'https://fonts.googleapis.com/css?family=Open+Sans:300,400,700',
            flask.url_for('forecasts.static', filename='forecast.css')],
        js_files=[
            flask.url_for('forecasts.static', filename='forecast.js'),
            'https://www.gstatic.com/charts/loader.js'
        ]
    )


def get_main_plot_figure(name, source_df, forecast_df):
    source_df.set_index('ds', inplace=True)
    forecast_df.set_index('ds', inplace=True)
    source_df.index = pd.to_datetime(source_df.index)

    # this data frame has the predicted data starting from the last date of the source time series
    predicted_data_df = forecast_df.loc[(forecast_df.index > max(source_df.index))]

    plot_df = source_df.join(predicted_data_df[['yhat', 'yhat_lower', 'yhat_upper']], how='outer')

    fig = plt.figure(facecolor='w', figsize=(17, 4))
    ax = fig.add_subplot(111)
    ax.plot(plot_df.y)
    ax.plot(plot_df.yhat, color='black', linestyle=':')
    ax.fill_between(plot_df.index, plot_df['yhat_upper'], plot_df['yhat_lower'], alpha=0.6, color='darkgray')
    ax.set_xlabel('Date')
    ax.set_ylabel(str(name).replace('_', ' ').capitalize())

    handles, labels = ax.get_legend_handles_labels()
    labels = ['Actual metric', 'Predicted metric']
    ax.legend(handles, labels)

    fig.tight_layout()
    return fig


def get_components_figure(m, fcst):
    uncertainty = True
    plot_cap = True
    weekly_start = 0
    yearly_start = 0
    from fbprophet import plot
    components = ['trend']
    if m.train_holiday_names is not None and 'holidays' in fcst:
        components.append('holidays')
    components.extend([name for name in m.seasonalities if name in fcst])
    npanel = len(components)

    fig, axes = plt.subplots(npanel, 1, facecolor='w', figsize=(17, 3 * npanel))

    if npanel == 1:
        axes = [axes]

    multiplicative_axes = []

    for ax, plot_name in zip(axes, components):
        if plot_name in ('trend', 'holidays'):
            plot.plot_forecast_component(
                m=m, fcst=fcst, name=plot_name, ax=ax, uncertainty=uncertainty,
                plot_cap=plot_cap,
            )
        elif plot_name == 'weekly':
            plot.plot_weekly(
                m=m, ax=ax, uncertainty=uncertainty, weekly_start=weekly_start,
            )
        elif plot_name == 'yearly':
            plot.plot_yearly(
                m=m, ax=ax, uncertainty=uncertainty, yearly_start=yearly_start,
            )
        else:
            plot.plot_seasonality(
                m=m, name=plot_name, ax=ax, uncertainty=uncertainty,
            )
        if plot_name in m.component_modes['multiplicative']:
            multiplicative_axes.append(ax)

    fig.tight_layout()

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    png_bytes = str(base64.b64encode(output.getvalue()).decode("utf-8"))

    return png_bytes


@blueprint.route('/_get_plot_image/<string:name>/<string:components>')
@acl.require_permission(acl_resource)
def get_plot_image(name, components):
    # plot the latest forecast
    with mara_db.postgresql.postgres_cursor_context('mara') as cursor:
        cursor.execute(f'''
        SELECT metric_name, forecasts_df, source_df, components_figure 
        FROM forecasts WHERE metric_name = {'%s'}
        ORDER BY forecast_ts DESC
        LIMIT 1''', (name,))
        result = cursor.fetchone()

    png_bytes = None
    if result:
        forecast_df = pickle.loads(result[1])
        source_df = pickle.loads(result[2])
        components_figure = pickle.loads(result[3])

        png_bytes = components_figure
        if components != 'True':
            # get main forecast plot figure
            figure = get_main_plot_figure(name, source_df, forecast_df)

            output = io.BytesIO()
            FigureCanvas(figure).print_png(output)
            png_bytes = str(base64.b64encode(output.getvalue()).decode("utf-8"))

    return str(_.img(src="data:image/png;base64," +
                         png_bytes
                     )
               ) if result else 'No data yet.'


@blueprint.route('/_query_details/<string:name>')
@acl.require_permission(acl_resource)
def query_details(name):
    query = ''
    for forecast in config.forecasts():
        if forecast.metric_name == name:
            query = forecast.time_series_query
            days = forecast.number_of_days
            break
    return str(bootstrap.table(
        headers=[],
        rows=[_.tr[_.td[html.highlight_syntax(query, language='postgresql')]],
              _.tr[_.td['Number of days forecasted: ' + str(days)]]]))

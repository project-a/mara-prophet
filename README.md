# Mara Prophet

A lightweight framework for producing, integrating and historizing [Facebook-prophet](https://github.com/facebook/prophet) 
forecasts for time series data in Mara.

Mara prophet is a laconic and simplified python module for integrating and historizing high quality forecasts for time series data 
produced with [Facebook-prophet](https://github.com/facebook/prophet) in Mara, 
by absolving on the same time the overhead of integration and multiple configurations.

Mara-prophet provides a framework for:

- Producing, validating and historizing Facebook prophet's models and forecasts
- Visualizing, by default, the analysis results as standalone KPI charts
- Time series component analysis containing trend, yearly/weekly seasonality and holiday effects
- On demand database integration (currently PostgreSQL only) of the historical time series and forecasts for ease of ETL and further reporting processing

## Resulting data

Mara prophet comes packed with a default visualization of the historical and forecasting data along with a component analysis, 
both highlighted in an auto-migrated python ```Flask``` view by using the [mara-page](https://github.com/mara/mara-page) module.
An example of this view is highlighted below:

![Forecast plot](docs/forecast_plot.png)
![Components plot](docs/components_plot.png)

Basic configurations are provided for ease of Mara integration, with data and fitted models stored in a PostgreSQL database 
by using the [mara-db](https://github.com/mara/mara-db) module and structured as:

```SQL
id               INTEGER,
metric_name      TEXT,
forecast_ts      TIMESTAMP,
model            BYTEA,
forecasts_df     BYTEA,
source_df        BYTEA,
hyper_parameters JSONB

Primary Keys: metric_name, forecast_ts
```

The main aim of this table is to allow analysing the performance of the prediction models and asynchronously 
rendering the forecast and component plots.

Additionally, an ETL integrated table containing the historical data and forecasts, can be specified on demand by overwriting 
the respective configuration in [mara_prophet/config.py](mara_prophet/config.py) as:

```python
patch(mara_prophet.config.forecast_table_name)(lambda: 'dim.forecast')
```

The historical time series and the resulting data stored in this table are currently structured as:

```SQL
metric_date  DATE,
metric_name  TEXT,
metric_value DOUBLE PRECISION,
lower_ci     DOUBLE PRECISION,
upper_ci     DOUBLE PRECISION

Primary Keys: metric_date, metric_name
```

While multiple metrics and their respective forecasts can be integrated in the same table.

## Getting Started

The main input that Mara-prophet requires is a list of ```Forecast``` objects and can defined by overwriting 
the forecasts function in [mara_prophet/config.py](mara_prophet/config.py) as:

```python
import mara_prophet.config
from mara_prophet import sql
from mara_prophet.forecast import Forecast

@patch(mara_prophet.config.forecasts)
def forecasts() -> [Forecast]:
    return [
        Forecast(
            metric_name='Revenue',
            number_of_days=360,
            time_series_query=mara_prophet.sql.build_time_series_sql_query(
                schema_name='schema_name',
                table_name='table_name',
                ds_column='"Date"',
                y_expression='sum("Revenue")',
                where_condition='"Date" >= \'2018-01-01\'::DATE')
        ),
        
        # ...
    ]
```

In order to run a time-series analysis for each defined ```Forecast``` object, the ```run_forecast(metric_name: str)``` function
needs to be triggered, providing the name of the current metric to be forecasted:

```python
from mara_prophet.forecast import run_forecast

run_forecast('Revenue')
```

### Usage and ETL-integration

Facebook-prophet modeling is fast due to models fitted in [Stan](https://mc-stan.org/) and robust by automatically handling 
trend changes, outliers, missing data and crucial change-points in the historical time-series. More about the Facebook-prophet's 
modeling and inner mechanisms can be found at the official docs [here](https://facebook.github.io/prophet/).

Therefore, Mara-prophet is proved to work better on data with strong multi-seasonal effects and 
can be easily used in several cases and pipelines that involve reliable KPI forecasting which can enable useful insights.

One obvious use-case can be considered by transforming and combining forecasting data of a pre-defined set of metrics (KPIs)
 with their respective actual and target values.

Such an example ```Business-targets``` pipeline is highlighted below:

![Business target pipeline](docs/pipeline.png)

By integrating the forecasting results in such a pipeline, we can aim for the following:

- Benchmarking for judging KPI performance and target setting (over/under-estimations)
- Metrics’ breakdowns analysis. Ability to detect different seasonality and trend per any meaningful level  (i.e. country) 
by running multiple forecast models (one per each relevant level value)
- Identifying current weaknesses and strengths before they happen (anomaly detection)
- Further combined reporting and visualizations

### Prerequisites
TBD

### Installation
TBD
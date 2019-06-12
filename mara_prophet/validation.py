import logging
import sys

from fbprophet.diagnostics import cross_validation, performance_metrics
import numpy as np
import mara_db.postgresql
from psycopg2 import Binary
import pickle
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ForecastCrossValidationBase(Base):
    """
    Stores cross validation results from a given forecast
    """
    __tablename__ = 'forecasts_cross_validation'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    forecast_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('forecasts.id'))
    horizon_days = sqlalchemy.Column(sqlalchemy.Integer)
    initial_days = sqlalchemy.Column(sqlalchemy.Integer)
    period_days = sqlalchemy.Column(sqlalchemy.Integer)
    cross_validation_df = sqlalchemy.Column(sqlalchemy.LargeBinary)
    metrics_df = sqlalchemy.Column(sqlalchemy.LargeBinary)


def insert_cross_validation_results_into_table(forecast_id: int, horizon_days: int, initial_days: int, period_days: int,
                                               cross_validation_df, metrics_df):
    with mara_db.postgresql.postgres_cursor_context('mara') as cursor:
        cursor.execute(
            f"INSERT INTO forecasts_cross_validation"
            f"(forecast_id, horizon_days, initial_days, period_days, cross_validation_df, metrics_df) "
            f"VALUES ({'%s, %s, %s, %s, %s, %s'})",
            (forecast_id, horizon_days, initial_days, period_days, Binary(cross_validation_df), Binary(metrics_df)))


def run_forecast_cross_validation(forecast_id: int, horizon_days: int, initial_days: int = None,
                                  period_days: int = None):
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)

    with mara_db.postgresql.postgres_cursor_context('mara') as cursor:
        cursor.execute("SELECT model FROM forecasts WHERE id = %s", (forecast_id,))
        result = cursor.fetchone()

    if result:
        model = pickle.loads(result[0])

        logging.info(f'Running cross validation for metric forecast id={forecast_id}')
        cross_validation_df = cross_validation(
            model,
            horizon=f'{str(horizon_days)} days',
            initial=f'{str(initial_days)} days' if initial_days else None,
            period=f'{str(period_days)} days' if period_days else None
        )

        # Data at original scale
        cross_validation_df['y'] = np.exp(cross_validation_df['y'])
        cross_validation_df['yhat'] = np.exp(cross_validation_df['yhat'])
        cross_validation_df['yhat_upper'] = np.exp(cross_validation_df['yhat_upper'])
        cross_validation_df['yhat_lower'] = np.exp(cross_validation_df['yhat_lower'])

        logging.info(f'Calculating performance metrics from cross-validation results of forecast id={forecast_id}')
        metrics_df = performance_metrics(cross_validation_df, rolling_window=1)

        cross_validation_df_pickled = pickle.dumps(cross_validation_df)
        metrics_df_pickled = pickle.dumps(metrics_df)

        insert_cross_validation_results_into_table(forecast_id, horizon_days, initial_days, period_days,
                                                   cross_validation_df_pickled, metrics_df_pickled)

    else:
        logging.info(f'No forecast found with id={forecast_id}')

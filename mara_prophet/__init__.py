"""Make the functionalities of this package auto-discoverable by mara-app"""


def MARA_CONFIG_MODULES():
    from . import config
    return [config]


def MARA_AUTOMIGRATE_SQLALCHEMY_MODELS():
    from . import forecast, validation
    return [forecast.ForecastBase, validation.ForecastCrossValidationBase]


def MARA_FLASK_BLUEPRINTS():
    from . import views
    return [views.blueprint]


def MARA_ACL_RESOURCES():
    from . import views
    return [views.acl_resource]


def MARA_NAVIGATION_ENTRIES():
    from . import views
    return [views.forecasts_navigation_entry()]

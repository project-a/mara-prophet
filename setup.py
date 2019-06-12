from setuptools import setup, find_packages

setup(
    name='mara-prophet',
    version='1.0.0',
    description="Business KPI forecasting module based on time-series analysis",

    install_requires=[
        'mara-db>=3.2.0',
        'pystan==2.18.1.0',
        'fbprophet==0.4.post2'
    ],

    dependency_links=[
        'git+https://github.com/mara/mara-db.git@3.2.0#egg=mara-db-3.2.0'
    ],

    setup_requires=[
        'pystan==2.18.1.0'
    ],

    packages=find_packages(),

    author='Mara contributors',
    license='MIT',

    entry_points={},
)

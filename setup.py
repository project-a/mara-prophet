from setuptools import setup, find_packages

setup(
    name='mara-prophet',
    version='2.0.1',
    description="Business KPI forecasting module based on time-series analysis",

    install_requires=[
        'mara-db>=3.2.0',
        'fbprophet==0.6',
    ],

    packages=find_packages(),
    author='Mara contributors',
    license='MIT',
    entry_points={},
    python_requires='>=3.6'
)

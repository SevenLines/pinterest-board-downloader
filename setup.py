from setuptools import setup, find_packages
from os.path import join, dirname

import pinterest

setup(
    name='pinterest-downloader',
    version=pinterest.__version__,
    packages=find_packages(),
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    entry_points={
        'console_scripts':
            ['pinterest = pinterest']
    },
    install_requires=[
        "lxml==4.3.1",
        "requests==2.21",
    ]
)

from setuptools import setup, find_packages
from os.path import join, dirname

setup(
    name='pinterest-downloader',
    version='0.0.1',
    packages=find_packages(),
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    entry_points={
        'console_scripts':
            ['pinterest = src:main']
    },
    install_requires=[
        "lxml==4.6.5",
        "requests==2.21",
    ]
)

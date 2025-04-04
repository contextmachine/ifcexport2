# setup.py

from setuptools import setup, find_packages

setup(
    name='ifcexport2',
    version='0.4.0',
    packages=find_packages(),
    install_requires=[
"ifcopenshell",
"numpy",
"ujson",
"lark",
"requests",
"click",
"rich",
"celery[redis]",
"fastapi[all]",
"uvicorn[standard]",
"aiofiles"
    ],
    entry_points={
        'console_scripts': [
            'ifcexport2=ifcexport2.cli:ifcexport2_cli',
        ],
    },
)
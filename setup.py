# setup.py

from setuptools import setup, find_packages

setup(
    name='ifcexport2',
    version='0.7.1',
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
"aiofiles",
        "psutil",
        "kubernetes",
        "tqdm"
    ],
    entry_points={
        'console_scripts': [
            'ifcexport2=ifcexport2.cli:ifcexport2_cli',
        ],
    },
)
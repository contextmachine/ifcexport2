# setup.py

from setuptools import setup, find_packages

setup(
    name='ifcexport2',
    version='0.1',
    packages=find_packages(),
    install_requires=[
"ifcopenshell",
"numpy",
"ujson",
"lark",
"requests"
    ],
    entry_points={
        'console_scripts': [
            'ifcexport2=ifcexport2.ifc_to_mesh:main',
        ],
    },
)
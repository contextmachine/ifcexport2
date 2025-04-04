from __future__ import annotations

import ifcopenshell
import ifcopenshell.util.element
from typing import Any, Dict, AnyStr
import re

Psets=Dict[str,Dict[str,Any]]
FlatProps=Dict[str,Any]
def extract_psets(ifc_element)->Psets:

    psets =ifcopenshell.util.element.get_psets(ifc_element)
    return psets

def psets_flatten(psets:Psets)->FlatProps:
    flat_props=dict()
    for name, pset in psets.items():
        for key, val in pset.items():
            flat_props[f'{name}/{key}'] = val

    return flat_props
def camel_to_space(s: str) -> str:
    """
    Convert a CamelCase string into a space-separated string.

    Args:
        s (str): The CamelCase string to convert.

    Returns:
        str: A new string with spaces inserted before uppercase letters (except at the start).
    """
    # The regex pattern (?<!^)(?=[A-Z]) finds positions in the string where there is an uppercase letter
    # that is not at the beginning. The re.sub() then inserts a space at those positions.
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', s)

def extract_props(element_id:int,ifc_model:ifcopenshell.file, additional_props:dict=None)->FlatProps:
    ifc_object=ifc_model.by_id(element_id)
    props=psets_flatten(extract_psets(ifc_object))

    info=ifc_object.get_info()
    props['name'] = info.get('Name')

    props['type'] = info.get('type')
    props['id'] = info.get('id')
    props['description']=info.get('Description')
    if additional_props:
        props.update(additional_props)

    if props['name']=='Undefined':
        props['name']=camel_to_space('Undefined'+props['type'].replace("Ifc",''))

    return props
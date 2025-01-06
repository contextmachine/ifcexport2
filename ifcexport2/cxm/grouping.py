from __future__ import annotations,absolute_import
import itertools
from marshal import loads

from .models import ObjectData, GeometryObject,find_object_by_uuid
from typing import List,Union,Any,Optional


def group_dictionaries(data: list, grouping_keys: list[str]) :
    """
    Group dictionaries based on the value of a specified key.
    Args:
    data (list): A list of dictionaries.
    grouping_key (str): The key to group by.
    return_indices (bool): If True, lists of object indexes will be returned instead of lists of objects. defaults to False.
    Returns:
    dict: A dictionary where keys are unique values of the grouping key,
          and values are lists of dictionaries with that value.
    Raises:
    TypeError: If data is not a list or grouping_key is not a string.
    ValueError: If data is an empty list.
    """
    # Type checking

    grouping_key=grouping_keys[0]
    print(data,grouping_key)
    if not isinstance(data, list):
        raise TypeError("data must be a list")
    if not isinstance(grouping_key, str):
        raise TypeError("grouping_key must be a string")
    # Check for empty list
    if not data:
        return {}
    result = {}
    for i,item in enumerate(data):
        if isinstance(item, dict) and grouping_key in item:


            group = item[grouping_key]
            if group not in result:

                result[group] = []

            else:
                result[group].append(

                    item
                )
    if grouping_keys.__len__()>1:


        return {k:group_dictionaries(v, grouping_keys[1:]) for k, v in result.items()}


    return  result


def _check_dict_userdata_properties(data:dict):
    return (data.get('userData') is not None
            and data.get('userData', {}).get("properties") is not None)


def _check_property_in_dict_userdata(data: dict, prop:str):
    return (_check_dict_userdata_properties(data)
            and prop in data['userData']["properties"].keys())




def flatten_geometries(obj: Union[ObjectData, GeometryObject, dict]):
    result = []
    if not isinstance(obj, dict):
        data=obj.to_dict()
    else:
        data=obj
    if 'children' in data.keys() and data['children'] is not None:

        if all([not (_check_dict_userdata_properties(child) and child['userData'].get('properties')) for child in data['children']]):
            result.append(data)

        else:
            for child in data['children']:

                if _check_dict_userdata_properties(child) and  child['userData'].get('properties'):


                    result.extend(flatten_geometries(child))





    else:
        result.append(data)



    return result




def find_object_by_property(data: Union[ObjectData, GeometryObject, dict], prop: str):
    """
    Recursively searches for an object by its UUID within an ObjectData or GeometryObject hierarchy.

    Args:
        data: The root ObjectData or GeometryObject to search within.
        uuid: The UUID of the object to find.

    Returns:
        The object with the matching UUID, or None if not found.
    """
    # Check if the current object has the matching UUID
    l=[]
    if isinstance(data,dict):

        if _check_property_in_dict_userdata(data,prop):
            l.append( data)
        else:
           pass

        # Recursively search in the children
        if 'children' in data.keys() and data['children'] is not None:
            for child in data['children']:
                l.extend(find_object_by_property(child, prop))
        return l
    elif isinstance(data,(ObjectData,GeometryObject)):

        if prop in data.userData.properties.keys():
            l.append(data)

        if data.children is not None:
            if  len(data.children)!=0:
                # Recursively search in the children
                for child in data.children:
                    l.extend(find_object_by_property(child, prop))


        return l


        # If the object was not found in the current node or any children, return None

    else:
        raise ValueError("Unexpected type {}\n\t{}".format(type(data),data))

def _props_tree_recursive(data:ObjectData, props_data:dict, depth=0,max_depth:int=-1):

    if isinstance(data,dict) and _check_dict_userdata_properties(data):

        for key in data['userData']['properties'].keys():
            if key not in props_data:
                props_data[key] = {data['userData']['properties'][key]: [data]}
            elif data['userData']['properties'][key] not in props_data[key]:
                props_data[key][data['userData']['properties'][key]] = [data]

            else:
                props_data[key][data['userData']['properties'][key]].append(data)

        dd=data
    elif isinstance(data,(ObjectData,GeometryObject)):
        for key in data.userData.properties.keys():
            if key not in props_data:
                props_data[key]={data.userData.properties[key]:[data]}
            elif  data.userData.properties[key] not in props_data[key]:
                props_data[key][ data.userData.properties[key]]=[data]

            else:
                props_data[key][data.userData.properties[key]].append(data)

        dd=data.__dict__

    else:
        raise ValueError("Unexpected type {}\n\t{}".format(type(data),data))
    if (depth-max_depth)==0:
        return

    else:
        if 'children' in dd.keys():
            for child in dd['children']:
                _props_tree_recursive(child, props_data,depth+1,max_depth)


def props_tree(data:ObjectData):
    props_t=dict()
    _props_tree_recursive(data,props_t)

    return props_t

def get_uid_agnostic(data:ObjectData|GeometryObject|dict):
    if isinstance(data,dict):
        return data['uuid']
    else:
        return data.uuid


from  ifcexport2.cxm.models import find_object_by_uuid


def _trav_to_obj(obj, names, ddd):
    if isinstance(ddd, list):
        return ObjectData(type="Group", name="Group", children=[find_object_by_uuid(obj, d['uuid']) for d in ddd])

    else:
        grp = []
        for k, v in ddd.items():
            if len(names) == 1:

                gr = _trav_to_obj(obj, [], v)

            else:
                gr = _trav_to_obj(obj, names[1:], v)
            gr.name = "Group"
            gr.userData.properties[names[0]] = k
            grp.append(gr)
        return ObjectData(type="Group", name="Group", children=grp)


def group_by_props(obj, props):
    gg = find_object_by_property(obj.object, props[0])
    prp = [{'uuid': g.uuid, **g.userData.properties} for g in gg
           ]

    res = group_dictionaries(prp, props)
    return _trav_to_obj(obj.object, props, res)

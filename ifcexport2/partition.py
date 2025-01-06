import math
from collections import defaultdict
from itertools import batched
from ifcexport2.mesh_to_three import create_three_js_root

def _build_maps(root):



    levels=defaultdict(list)
    geom={g['uuid']:g for g in root['geometries']}
    mat = {g['uuid']: g for g in root['materials']}


    def inner(obj, level=0):

        levels[level].append(obj)
        if 'children' in obj and obj['children'] is not None:
            for i in obj['children']:

                inner(i, level+1)




    inner(root['object'],0)

    return levels,geom,mat


def partition_viewer_json(root:dict, parts:int):
    levels,geom,mat=_build_maps(root)
    parts_objs=[]
    for l in list(levels.keys()):
        level_size=len(levels[l])
        if level_size>=parts:
            parts_objs = list(batched(levels[l], math.ceil(level_size/ parts)))
            break
    mat_index=[set() for ppp in parts_objs]
    roots=[]
    for i,prt in enumerate(parts_objs):

        new_root=create_three_js_root(name=f'{root.get("name","Object")}-{i}',props=root.get('userData',{}).get('properties',{}))

        for p in prt:
            new_root['object']['children'].append(p)

            if 'geometry' in p.keys():
                new_root['geometries'].append(geom[p['geometry']])
                if mat[p['material']]['uuid'] not in mat_index[i]:
                    mat_index[i].add(mat[p['material']]['uuid'])
                    new_root['materials'].append(mat[p['material']])

        roots.append(new_root)

    return roots



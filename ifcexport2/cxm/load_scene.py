from  ifcexport2.cxm.models import ObjectData, Object3DJSON


def group_by_one(objs, keys):
    ll = dict()
    key = keys[0]
    ll['undefined'] = []
    for i in objs:

        if key in i.userData.properties:
            pn = i.userData.properties[key]

            if pn not in ll:
                ll[pn] = [i]
            else:

                ll[pn].append(i)
        else:
            ll['undefined'].append(i)
    if len(keys) > 1:
        for k, f in list(ll.items()):
            ll[k] = group_by_one(f, keys[1:])

    return ll


def to_grp(ddd):
    if isinstance(ddd, list):
        return ObjectData(type="Group", name="Group", children=ddd)

    else:
        grp = []
        for k, v in ddd.items():
            gr = to_grp(v)

            gr.name = "Group"
            gr.userData.properties['name'] = k
            grp.append(gr)
        return ObjectData(type="Group", name="Group", children=grp)



import copy
from  ifcexport2.cxm.utils import remove_none_values
def group_by_props(objects,props ):
    return to_grp(group_by_one(objects,props))
if __name__ == '__main__':

    def fetch_ne():
        with open('/Users/andrewastakhov/Downloads/sw-w.json') as f:
            import ujson
            resp1 = Object3DJSON.from_dict(ujson.loads(f.read()))
        with open('/Users/andrewastakhov/Downloads/sw-l2.json') as f:
            import ujson
            resp2 = Object3DJSON.from_dict(ujson.loads(f.read()))
        check = [u.uuid for u in resp1.materials]

        for mat in resp2.materials:

            if mat.uuid not in check:
                resp1.materials.append(mat)
                check.append(mat.uuid)
        for mat in resp1.materials:
            mat.flatShading = True
            mat.side = 2
        return Object3DJSON(geometries=resp1.geometries + resp2.geometries, materials=resp1.materials,
                            metadata=resp1.metadata,
                            object=ObjectData(type="Group", name='Group', children=[resp2.object, resp1.object]))


    ob=fetch_ne()
    res3=group_by_props(ob.object.children[0].children+ob.object.children[1].children, ['zone','pair_name'])
    ob2=copy.deepcopy(ob)
    ob2.object=res3
    with open('test5.json','w') as f:
        import ujson
        f.write(ujson.dumps(remove_none_values(ob2.to_dict())))

import logging
from typing import NamedTuple


def get_ifc_elements(model)->list:
    return model.by_type('IfcElement')
def get_ifc_elements_id(model)->list[int]:
    return [item.id() for item in model.by_type('IfcElement')]




def build_product_definitions_to_shapes(model):
    shapes_dct=dict()
    prod_to_shapes = dict()
    for shape_repr in model.by_type('IfcShapeRepresentation'):
        for prodshape in shape_repr.OfProductRepresentation:
            if prodshape.id() not in prod_to_shapes:
                prod_to_shapes[prodshape.id()] =[]
            for item in shape_repr.Items:
                shape_id=item.id()
                shapes_dct[shape_id]=item

                prod_to_shapes[prodshape.id()].append(shape_id)

    return prod_to_shapes,shapes_dct


def build_elements_to_product_definitions(model):
    dct = dict()

    for prodshape in model.by_type('IfcProductDefinitionShape'):

        for elem in prodshape.ShapeOfProduct:

            if elem.id() not in dct:
                dct[elem.id()] = []
            dct[elem.id()].append(prodshape.id())


    return dct

class ShapeItem(NamedTuple):
    shape_id: int
    matrix:list


def get_shapes_by_element(el, elements_to_product_definitions, product_definitions_to_shapes , model):

    return [[model.by_id(i) for i in product_definitions_to_shapes[prod_def_id]] for prod_def_id in elements_to_product_definitions[el.id() if hasattr(el,'id') else el]]
def trav_getitem(dct,key_or_list,default=None):
    if isinstance(key_or_list,(list,tuple)):
        return [trav_getitem(dct,item,default) for item in key_or_list]
    else:
        return dct.get(key_or_list,default)


def trav_ifc_ids(id_or_list, model):
    if isinstance(id_or_list,int):
        return model.by_id(id_or_list)
    else:
        return [trav_ifc_ids(i,model) for i in id_or_list]


def get_elem_to_shapes(model):
    dct = dict()
    prod_to_shapes = dict()
    for shape_repr in model.by_type('IfcShapeRepresentation'):
        for prodshape in shape_repr.OfProductRepresentation:
            if prodshape.id() not in prod_to_shapes:
                prod_to_shapes[prodshape.id()] = [item.id() for item in shape_repr.Items]
            else:
                prod_to_shapes[prodshape.id()].extend((item.id() for item in shape_repr.Items))
    
    for prodshape in model.by_type('IfcProductDefinitionShape'):
        
        for elem in prodshape.ShapeOfProduct:
            
            if elem.id() not in dct:
                dct[elem.id()] = [
                ]
            dct[elem.id()].append(prod_to_shapes[prodshape.id()])
    
    return dct
import logging
logger=logging.getLogger('ifcexport2')


def get_element_styles(elem_id, el_to_shapes: dict, styles_data):
    styles_for_elem = []
    shapes = []
    if elem_id not  in el_to_shapes :
        logger.warning(
            'no items found in model with id {}. '.format(elem_id) )
        return
    for items in el_to_shapes[elem_id]:
        
        for shape_id in items:
            stls = styles_data.get_styles(shape_id, [])
            
            if len(stls) == 0:
                logger.warning(
                    'no styles found for shape id {}. elem_id={}, shapes={}'.format(shape_id, elem_id, shapes))
            
            else:
                shapes.extend([shape_id] * len(stls))
                styles_for_elem.extend(stls)
    
    return styles_for_elem, shapes
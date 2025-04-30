import uuid
import math


def _rgb_float_to_int(r: float, g: float, b: float) -> int:
    """(0-1 floats) → 24-bit int  (0,0,0) → 0, (1,1,1) → 0xFFFFFF"""
    return (round(r * 255) << 16) | (round(g * 255) << 8) | round(b * 255)

from ifcexport2.mesh_to_three import material
# ------------------------------------------------------------
#  main converter
# ------------------------------------------------------------
def ifc_surface_to_threejs(style, *, name=None,pbr: bool = False, vertexColors: bool = False) -> dict:
    """
    Convert a single IfcSurfaceStyleRendering → Three-JS material dict.

    Parameters
    ----------
    style : dict
        The IFC style (keys: SurfaceColour, Transparency, SpecularColour, SpecularHighlight …)
    pbr   : bool, optional
        False  → MeshPhongMaterial (1-to-1 faithful mapping)   [default]
        True   → MeshStandardMaterial (approximate PBR mapping)

    Returns
    -------
    dict  (ready for json.dumps / ObjectLoader.parse)
    """
    # 1) diffuse / base colour
    col = style.SurfaceColour
    if name is None:
        name = f'IfcSurfaceStyleRendering-{style.id()}'
    if col.Red == 0 and col.Green == 0 and col.Blue == 0 and col.Name is None:
        r, g, b = 255 / 150, 255 / 150, 255 / 150
    else:
        r, g, b = col.Red, col.Green, col.Blue
    color_int = _rgb_float_to_int(r, g, b)

    # 2) transparency → opacity
    opacity = 1.0 - (0.0 if style.Transparency is None else style.Transparency)

    # 3) specular colour (single grey-scale ratio in IFC)

    s_intensity = style.SpecularColour.wrappedValue
    specular_int = _rgb_float_to_int(s_intensity, s_intensity, s_intensity)

    # 4) Phong shininess exponent
    shininess = (style.SpecularHighlight.wrappedValue if style.SpecularHighlight is not None else 30.0)
    if vertexColors:
        color_int=_rgb_float_to_int(1., 1., 1.)
    # ------------------------------------------------------------------
    common = {
        "uuid": str(uuid.uuid4()),
        "name": name,
        "color": color_int,
        "opacity": opacity,
        "transparent": opacity < 1.0,
        "side": 2,  # Double sided – IFC expects no back-face cull
        "vertexColors": vertexColors,  # Preserve any vertex colours present
        "flatShading": True

    }

    if not pbr:  # ---------- MeshPhongMaterial ----------
        common.update({
            "type": "MeshPhongMaterial",
            "specular": specular_int,
            "shininess": shininess
        })
    else:  # ---------- MeshStandardMaterial -------
        roughness = math.sqrt(2.0 / (shininess + 2.0))  # heuristic mapping
        common.update({
            "type": "MeshStandardMaterial",
            "roughness": round(roughness, 3),
            "metalness": s_intensity if s_intensity is not None else 0.04,  # IFC specular ≪ 0.04 ⇒ dielectric
            "specularIntensity": round(s_intensity, 4)
        })

    return common

def build_surface_style(ifc_surface_style_rendering):
    colors=[]
    mats={}

    for i in ifc_surface_style_rendering.Styles:

        if i.is_a('IfcSurfaceStyleRendering'):
            col=i.SurfaceColour
            if col.Red == 0 and col.Green == 0 and col.Blue == 0 and col.Name is None:
                r, g, b = 255 / 150, 255 / 150, 255 / 150
            else:
                r, g, b = col.Red, col.Green, col.Blue
            colors.append((r,g,b))
            mats.update(ifc_surface_to_threejs(i,pbr=False, vertexColors=False ,name=ifc_surface_style_rendering.Name))
        elif i.is_a('IfcSurfaceStyleShading'):
            col = i.SurfaceColour
            if col.Red == 0 and col.Green == 0 and col.Blue == 0 and col.Name is None:
                r, g, b = 255 / 150, 255 / 150, 255 / 150
            else:
                r, g, b = col.Red, col.Green, col.Blue
            colors.append((r, g, b))
            mats=material((int(r*255), int(g*255), int(b*255)))

        else:
            pass
    return colors,mats

import ifcopenshell.util
import ifcopenshell.util.representation

from ifcopenshell.util.element import get_styles,get_material
from ifcexport2.ifc_elements import get_ifc_elements_id, get_ifc_elements


def get_elements_styles(els,mats_to_styles):
    dct=dict()

    for el in els:
        dct[el.id()] = None
        styles=list(filter(lambda st: st.is_a('IfcSurfaceStyle'), get_styles(el)))


        if len(styles)==0:
            mat=get_material(el)
            if mat is None:
                continue
            styles_ids=mats_to_styles.get(mat.id())
            if styles_ids is None:
                continue
            dct[el.id()] = list(set(styles_ids))
        else:
            dct[el.id()] = list(set([i.id() for i in styles]))

    return dct




def build_surface_styles(ifc_surface_style_renderings):
    return {i.id():build_surface_style(i)for i in ifc_surface_style_renderings}
def build_materials_styles(model):
    dt=dict()
    for item in  model.by_type('IfcStyledRepresentation'):

       if item.RepresentationIdentifier=='Style' and  item.RepresentationType=='Material':
           mat_id=item.OfProductRepresentation[0].RepresentedMaterial.id()

           dt[mat_id]=[]
           for st in item.Items:

               for style_assigment in st.Styles:
                   for stt in style_assigment.Styles:
                       if stt.is_a('IfcSurfaceStyle'):
                           dt[mat_id].append(stt.id())
    return dt


def build_styled_items(ifc_styled_items):

    dt = dict()
    for st in ifc_styled_items:

        for style_assigment in st.Styles:
            for stt in style_assigment.Styles:
                if stt.is_a('IfcSurfaceStyle'):
                    if st.Item is None:
                        pass
                    else:
                        dt[st.Item.id()] = stt.id()

    return dt

def build_surf_style_data(model):
    elems=get_ifc_elements(model)
    mat_styles=build_materials_styles(model)
    surf_styles=build_surface_styles(model.by_type('IfcSurfaceStyle'))


    styled_items = build_styled_items(model.by_type('IfcStyledItem')
                                      )
    elems_styles=get_elements_styles(elems,mat_styles)
    print('styled_items', styled_items)
    print(surf_styles, styled_items)
    for k,v in styled_items.items():
        if v :
            vv=elems_styles.get(k)
            if isinstance( vv,(tuple,list)) and len(vv)==0:
                elems_styles[k]=v
            elif vv is None:
                elems_styles[k] = v


    print(elems_styles)

    return surf_styles,styled_items ,elems_styles
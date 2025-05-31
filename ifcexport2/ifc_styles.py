import uuid
import math
from collections import defaultdict
from typing import Any,Optional,Tuple
from dataclasses import dataclass,field

    
def _rgb_float_to_int(r: float, g: float, b: float) -> int:
    """(0-1 floats) → 24-bit int  (0,0,0) → 0, (1,1,1) → 0xFFFFFF"""
    return (round(r * 255) << 16) | (round(g * 255) << 8) | round(b * 255)

from ifcexport2.mesh_to_three import material
# ------------------------------------------------------------
#  main converter
# ------------------------------------------------------------

import logging
logger = logging.getLogger('ifcexport2')
from dataclasses import dataclass
from typing import Optional, Tuple



@dataclass
class ColorData:
    rgb_int: Optional[Tuple[int, int, int]] = None
    rgb_float: Optional[Tuple[float, float, float]] = None
    decimal: Optional[int] = None
    hex: Optional[str] = None
    
    def _raise_float_range(self,c):
        raise ValueError(f"rgb_float components must be in 0.0-1.0: {self.rgb_float}")
    def __post_init__(self):
        # Determine rgb_int first
        if self.rgb_int is None:
            if self.rgb_float is not None:
                # Convert floats [0.0-1.0] to ints [0-255]
                self.rgb_int = tuple(
                    int(round(c * 255)) if 0.0 <= c <= 1.0 else self._raise_float_range(c)
                    for c in self.rgb_float
                )
            elif self.decimal is not None:
                if not (0 <= self.decimal <= 0xFFFFFF):
                    raise ValueError(f"Decimal value out of range: {self.decimal}")
                self.rgb_int = (
                    (self.decimal >> 16) & 0xFF,
                    (self.decimal >> 8) & 0xFF,
                    self.decimal & 0xFF
                )
            elif self.hex is not None:
                hex_str = self.hex.lstrip('#')
                if len(hex_str) != 6:
                    raise ValueError(f"Invalid hex color: {self.hex}")
                try:
                    self.rgb_int = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
                except ValueError:
                    raise ValueError(f"Invalid hex color: {self.hex}")
            else:
                raise ValueError("At least one color representation must be provided")
        else:
            # Validate provided rgb_int
            if any(not (0 <= v <= 255) for v in self.rgb_int):
                raise ValueError(f"rgb_int components must be in 0-255: {self.rgb_int}")

        # Helper for float range error
 

        # Compute rgb_float if missing
        if self.rgb_float is None:
            self.rgb_float = tuple(c / 255 for c in self.rgb_int)

        # Compute decimal if missing
        if self.decimal is None:
            r, g, b = self.rgb_int
            self.decimal = (r << 16) + (g << 8) + b

        # Compute hex if missing
        if self.hex is None:
            self.hex = '#{:02x}{:02x}{:02x}'.format(*self.rgb_int)

    def __repr__(self):
        return (
            f"ColorData(rgb_int={self.rgb_int}, rgb_float={self.rgb_float}, "
            f"decimal={self.decimal}, hex='{self.hex}')"
        )
from ifcexport2.mesh_to_three import material,default_material
@dataclass
class IfcColorData:
    color: ColorData
    name: Optional[str] = None


@dataclass
class StyleShading:
    ifc_id: int
    ifc_entity: Any
    name: str
    color_data: IfcColorData
    material: dict
@dataclass
class SurfaceStyle:
    
    ifc_id: int
    ifc_entity: Any
    name: str
    shading: Optional[StyleShading]=None
    
    
def ifc_surface_to_threejs(style, *, name=None,pbr: bool = False, vertexColors: bool = False) -> StyleShading:
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
    style_id = style.id()
    col = style.SurfaceColour
    if vertexColors:
        logger.warning(f"vertexColors material creation: style={style},name={name},pbr={pbr},vertexColors={vertexColors}, color={col}")
    if name is None:
        
        name = f'IfcSurfaceStyleRendering-{style.id()}'
    if col.Red == 0 and col.Green == 0 and col.Blue == 0 and col.Name is None:
        r, g, b = 150/255, 150/255, 150/255
    else:
        r, g, b = col.Red, col.Green, col.Blue
    color_data=IfcColorData(color=ColorData(rgb_float=(r,g,b)), name=name)
    color_int = color_data.color.decimal
    
    # 2) transparency → opacity
    opacity = 1.0 - (0.0 if style.Transparency is None else style.Transparency)

    # 3) specular colour (single grey-scale ratio in IFC)

    s_intensity = style.SpecularColour.wrappedValue
    specular_int = _rgb_float_to_int(s_intensity, s_intensity, s_intensity)

    # 4) Phong shininess exponent
    shininess = (style.SpecularHighlight.wrappedValue if style.SpecularHighlight is not None else 30.0)
  
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
    return StyleShading(ifc_entity=style, ifc_id=style_id, name=name, color_data=color_data, material=common)
    

def build_surface_style_shading(ifc_surface_style_rendering)-> StyleShading | None:
    i=ifc_surface_style_rendering
    
    if i.is_a('IfcSurfaceStyleRendering'):
          
            
            return ifc_surface_to_threejs(i,pbr=False, vertexColors=False ,name=getattr(i,'Name',getattr(i,'name', None)))
    elif i.is_a('IfcSurfaceStyleShading'):
            col = i.SurfaceColour
            if col.Red == 0 and col.Green == 0 and col.Blue == 0 and col.Name is None:
                r, g, b = 150/255, 150/255, 150/255
            else:
                r, g, b = col.Red, col.Green, col.Blue
  
            mat=material((int(r*255), int(g*255), int(b*255)))
            return StyleShading(ifc_entity=i, ifc_id=i.id(), color_data=IfcColorData(ColorData(rgb_float=(r, g, b)), name=col.Name), name=f'IfcSurfaceStyleShading-{i.id()}', material=mat)
    else:
            return

def build_surface_styles(model):

    surface_style_shadings = {i.id(): build_surface_style_shading(i) for i in model.by_type('IfcSurfaceStyleShading', include_subtypes=True)}
    surf_styles = model.by_type("IfcSurfaceStyle")
    surface_styles=dict()
    for stl in surf_styles:
        stl_id=stl.id()
        rendering = None
        shading = None
        prefer_shading = None
        
        for i in stl.Styles:
            
            if i.is_a('IfcSurfaceStyleRendering'):
                rendering = i
            
            elif i.is_a('IfcSurfaceStyleShading'):
                shading = i
        prefer_shading = rendering
        if rendering is None:
            prefer_shading = shading
        if prefer_shading is not None:
            surface_styles[stl_id] = SurfaceStyle(ifc_id=stl_id,ifc_entity=stl,shading=surface_style_shadings[prefer_shading.id()],name=getattr(stl,'Name',getattr(stl,'name',None)))
    return surface_styles



import ifcopenshell.util
import ifcopenshell.util.representation

from ifcopenshell.util.element import get_styles,get_material
from ifcexport2.ifc_elements import get_ifc_elements_id, get_ifc_elements


def get_elements_styles(els,mats_to_styles=None,model=None):
    dct=dict()
    if mats_to_styles is None:
        if model is None:
            raise ValueError('model is not specified')
        mats_to_styles=build_materials_styles(model)
    for el in els:
        dct[el.id()] = None
        
        styles=list(filter(lambda st: st.is_a('IfcSurfaceStyle'), get_styles(el)))

        
        if len(styles)==0:
            
            mat=get_material(el)
            print(mat)
            if mat is None:
                continue
            styles_ids=mats_to_styles.get(mat.id())
            if styles_ids is None:
                continue
            dct[el.id()] = list(set(styles_ids))
        else:
            dct[el.id()] = list(set([i.id() for i in styles]))

    return dct


def get_surface_style_rendering(model):
   return model.by_type('IfcSurfaceStyleRendering')


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


def build_styled_items(ifc_styled_items, surface_styles:dict[int,SurfaceStyle]):

    dt = defaultdict(list)
    for st in ifc_styled_items:

        for style_assigment in st.Styles:
            for stt in style_assigment.Styles:
                if stt.is_a('IfcSurfaceStyle'):
                    if st.Item is None:
                        pass
                 
                    else:
                        stt_id=stt.id()
                        if stt_id in surface_styles:
                            dt[st.Item.id()].append(stt.id())
                        

    return dt
@dataclass
class SurfaceStylesData:
    surface_style: dict[int,SurfaceStyle]
    styled_items: dict[int,list[int]]
    def get_styles(self, item_id:int, default=None):
        _=self.styled_items.get(item_id, default)
        if _ is None:
            return default
        
        return [self.surface_style[i] for i in _]
    def find_composite(self):
        for k, st in self.styled_items.items():
            if len(st)>1:
                yield k
                
        
def build_surf_style_data(model)->SurfaceStylesData:
    #elems=get_ifc_elements(model)
    #mat_styles=build_materials_styles(model)
    surf_styles=build_surface_styles(model)
    

    styled_items = build_styled_items(model.by_type('IfcStyledItem'),surf_styles)
    
    #elems_styles=get_elements_styles(elems,mat_styles)
    #print('styled_items', styled_items)
    #print(surf_styles, styled_items)
    #for k,v in styled_items.items():
    #    if v :
    #        vv=elems_styles.get(k)
    #        if isinstance( vv,(tuple,list)) and len(vv)==0:
    #            elems_styles[k]=v
    #        elif vv is None:
    #            elems_styles[k] = v


    #print(elems_styles)
  
    return   SurfaceStylesData(dict(surf_styles),styled_items)
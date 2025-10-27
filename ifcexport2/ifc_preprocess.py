import dataclasses
from abc import ABC
from collections.abc import Callable

import ifcopenshell
from typing import Generator, runtime_checkable, Optional, NamedTuple
from typing import Generator
from ifcopenshell.entity_instance import entity_instance
IfcEntityInstance = entity_instance
IfcProductStream = Generator[IfcEntityInstance, None, None]


def iter_products_with_repr(ifc, excluded_types=None) -> IfcProductStream:
    """Yield IfcProducts that have a Representation, excluding given types."""
    excluded_types = set(excluded_types or ())
    for p in ifc.by_type("IfcProduct"):
        if p.is_a() in excluded_types:
            continue
        if getattr(p, "Representation", None):
            yield p

from ifcopenshell.util.unit import calculate_unit_scale, get_project_unit, convert_file_length_units, get_unit_symbol,convert_unit, \
    get_unit_name, get_full_unit_name



class IfcProductInfo(NamedTuple):
    categories:set[str]
    product_count:int
class ProductInfoExtractor:
    def __init__(self, excluded_types:list[str]=None) -> None:
        self.categories = set()
        self.product_count: int = 0
        self.excluded_types = excluded_types if excluded_types is not None else []
        
        
    def categories_callback(self, product:IfcEntityInstance) -> None:
        self.categories.add(product.get_info().get('type',None))
    def products_count_callback(self, product:IfcEntityInstance) -> None:
        self.product_count += 1
    
    def build(self, ifc_file:ifcopenshell.file)->IfcProductInfo:
        self.categories = set()
        self.product_count = 0
        iterator=iter_products_with_repr(ifc_file,set(self.excluded_types))
        for product in iterator:
            self.categories_callback(product)
            self.products_count_callback(product)
        return IfcProductInfo(self.categories, self.product_count)
    
    
        

from dataclasses import InitVar
@dataclasses.dataclass
class IfcUnit:
    name: str
    prefix: Optional[str]
    unit_type: str
    @property
    def Name(self):
        return self.name
    
    @property
    def Prefix(self):
        return self.prefix
    
    @property
    def UnitType(self):
        return self.unit_type


@dataclasses.dataclass
class IfcUnitInfo(IfcUnit):
    model: InitVar[ifcopenshell.file]=dataclasses.field(init=True, repr=False)
    symbol:str=dataclasses.field(init=False)
    full_name:str=dataclasses.field(init=False)
    name:str=dataclasses.field(init=False)
    prefix:str=dataclasses.field(init=False)
    scale:float=dataclasses.field(init=False)
    unit_type: str = dataclasses.field(init=True, kw_only=True, default="LENGTHUNIT")
    _unit:Optional[ifcopenshell.entity_instance]=dataclasses.field(init=False,repr=False,default=None,hash=False,compare=False)
    
    def __post_init__(self,model):
        self.scale=calculate_unit_scale(model)
        self._unit=get_project_unit(model,self.unit_type,use_cache=False)
        self.symbol=get_unit_symbol(self._unit)
        unit_info = self._unit.get_info()
        self.name=unit_info['Name']
        self.prefix=unit_info['Prefix']
        self.full_name=get_full_unit_name(    self._unit)
    
METRE=IfcUnit('METRE',None, 'LENGTHUNIT')



    
@dataclasses.dataclass
class IfcInfo:
    
    units:IfcUnitInfo
    categories:list[str]
    product_count:int
    
    

def preprocess_ifc(ifc_file:ifcopenshell.file, excluded_types:list[str]=None)->IfcInfo:
    if excluded_types is None:
        excluded_types = []
    extractor=ProductInfoExtractor(excluded_types)
    info=extractor.build(ifc_file)
    unit_type: str = "LENGTHUNIT"
    return IfcInfo(IfcUnitInfo(ifc_file, unit_type=unit_type),list(info.categories),info.product_count)

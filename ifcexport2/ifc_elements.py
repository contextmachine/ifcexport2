def get_ifc_elements(model)->list:
    return model.by_type('IfcElement')
def get_ifc_elements_id(model)->list[int]:
    return [item.id() for item in model.by_type('IfcElement')]
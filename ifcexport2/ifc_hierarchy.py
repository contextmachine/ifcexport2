import itertools
from typing import NamedTuple, List, Dict, Optional, Tuple


import ifcopenshell


class Hierarchy(NamedTuple):
    hierarchy: dict[int, list[int]]
    root_elements: list[int]



def build_hierarchy( ifc_model:ifcopenshell.file, include_spatial_hierarchy:bool=True
)->Hierarchy:
    """
    Build a hierarchy of ifc entities and determine root elements.

    Args:
        ifc_model (ifcopenshell.file): The IFC file object.


    Returns:
        Hierarchy: A tuple where the first element is a dictionary representing
               the hierarchy and the second element is a list of
               root element ids (those not child of any element).

    """
    assembly_hierarchy = {}
    # Keep track of all elements that appear as a child in any assembly.
    all_ids = set()
    has_parent_ids = set()

    # Iterate over all aggregation relationships in the file.

    for rel in ifc_model.by_type("IfcRelAggregates") :

        # Get the id of the parent assembly.
        parent = rel.RelatingObject

        parent_id = parent.id()  # Assumes that the element has an id() method.

        if parent_id not in assembly_hierarchy:
            all_ids.add(parent_id)

            assembly_hierarchy[parent_id] = []

        # Only process if the parent is in our list of geometric elements.

        # Process each child object in the relationship.
        for child in rel.RelatedObjects:
            child_id = child.id()

            assembly_hierarchy[parent_id].append(child_id)

            has_parent_ids.add(child_id)
    if include_spatial_hierarchy:
        for rel in ifc_model.by_type("IfcRelContainedInSpatialStructure") :


            parent = rel.RelatingStructure

            parent_id = parent.id()  # Assumes that the element has an id() method.

            if parent_id not in assembly_hierarchy:
                all_ids.add(parent_id)

                assembly_hierarchy[parent_id] = []

            # Only process if the parent is in our list of geometric elements.

            # Process each child object in the relationship.
            for child in rel.RelatedElements:
                child_id = child.id()

                assembly_hierarchy[parent_id].append(child_id)

                has_parent_ids.add(child_id)

    # Root elements are those that are never a child in any assembly.
    root_elements = all_ids.difference(has_parent_ids)

    return Hierarchy(assembly_hierarchy, list(root_elements))



def clean_hierarchy(hierarchy: Hierarchy, require_objects: List[int]) -> Hierarchy:
    orig = hierarchy.hierarchy

    # Build a reverse mapping: child -> set of parents.
    reverse: Dict[int, set] = {}
    for parent, children in orig.items():
        for child in children:
            reverse.setdefault(child, set()).add(parent)

    # Pass 1: Mark forced nodes.
    # For each required node, add the node and all of its descendants.
    forced = set()
    def dfs(node: int) -> None:
        if node in forced:
            return
        forced.add(node)
        for child in orig.get(node, []):
            dfs(child)
    for req in require_objects:
        dfs(req)

    # Pass 2: Propagate upward.
    # Any node that is the parent of a forced node must be kept.
    necessary = set(forced)
    queue = list(forced)
    while queue:
        node = queue.pop()
        for parent in reverse.get(node, []):
            if parent not in necessary:
                necessary.add(parent)
                queue.append(parent)

    # Rebuild the hierarchy dictionary:
    # Only keep a node if it’s in the 'necessary' set,
    # and filter its children to include only those in the set.
    new_hierarchy = {}
    for node in necessary:
        children = orig.get(node, [])
        new_children = [child for child in children if child in necessary]
        if new_children:
            new_hierarchy[node] = new_children

    # Rebuild the root elements.
    # A node becomes a new root if it has no parent in the necessary set.
    new_roots = []
    for node in necessary:
        if node not in reverse or all(parent not in necessary for parent in reverse[node]):
            new_roots.append(node)

    return Hierarchy(hierarchy=new_hierarchy, root_elements=new_roots)


def simplify_hierarchy(hierarchy: Hierarchy,require_objects: List[int]):
    orig = hierarchy.hierarchy
    new_hierarchy = {}
    stack=[*hierarchy.root_elements]

    while True:
        current=stack.pop()
        children=orig.get(current)
        if children is None:
            continue
        elif len(children)==1:
            children[0]

    for root in hierarchy.root_elements:
        orig[root]
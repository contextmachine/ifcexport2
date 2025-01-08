import gc
import struct
import time

import ujson

from ifcexport2.mesh_to_three import Object3DStorage

from typing import List, Optional
from dataclasses import dataclass,field

class Node:
    """
    A minimalistic class for the demonstration.

    - If it's a leaf:
        self.is_leaf = True
        self.size = <some integer>  # leaf weight
        self.children = []  # empty
    - If it's a group:
        self.is_leaf = False
        self.size = 0  # not used for a group
        self.children = [<child Node>, <child Node>, ...]
    """

    def __init__(self, is_leaf: bool, size: int = 0, children: Optional[List["Node"]] = None, uid=None):
        self.is_leaf = is_leaf
        self.size = size
        self.uid=uid
        self.children = children if children is not None else []

    def __repr__(self):
        # Helpful for debugging
        if self.is_leaf:
            return f"Leaf(size={self.size})"
        else:
            return f"Group(children={len(self.children)})"


def compute_subtree_sizes(node: Node, cache: dict) -> int:
    """
    Compute the total size of the subtree rooted at `node`.
    Store the result in `cache[node]`.
    Return the computed size.
    """
    if node.is_leaf:
        cache[node] = node.size
        return node.size
    else:
        total = 0
        for child in node.children:
            total += compute_subtree_sizes(child, cache)
        cache[node] = total
        return total


def count_leaves(node: Node) -> int:
    """
    Return the count of leaves in the subtree rooted at `node`.
    """
    if node.is_leaf:
        return 1
    return sum(count_leaves(child) for child in node.children)


def flatten_leaves(node: Node) -> List[Node]:
    """
    Return a flat list of all leaf nodes in the subtree rooted at `node`.
    """
    if node.is_leaf:
        return [node]
    all_leaves = []
    for child in node.children:
        all_leaves.extend(flatten_leaves(child))
    return all_leaves


def split_into_k_subtrees(root: Node, k: int) -> List[Node]:
    """
    Main function: split the given tree (root) into up to `k` subtrees such that
    the total sizes of these subtrees are as balanced as possible (heuristically).

    Returns a list of new subtree roots (original subtrees, unmodified).
    """
    # 1) Precompute subtree sizes
    subtree_sizes = {}
    total_size = compute_subtree_sizes(root, subtree_sizes)

    # 2) Count number of leaves
    total_leaves = count_leaves(root)

    # 3) Edge case: if k >= total_leaves,
    #    just return each leaf as a separate group (or subtree).
    if k >= total_leaves:
        return flatten_leaves(root)

    # 4) If the root is a "group" consisting only of leaves (i.e. shallow tree),
    #    then distribute them directly into k bins.
    if root.is_leaf:
        # If it's just a single leaf, that's trivial:
        return [root]

    # Check if the tree is at most one level deep in leaves
    # (i.e. root is a group, but all children are leaves).
    if all(child.is_leaf for child in root.children):
        # Distribute leaves into k bins (a simple first-fit approach).
        leaf_nodes = root.children  # all leaves at top level
        new_subtrees = [Node(is_leaf=False, children=[]) for _ in range(k)]  # k empty groups
        bin_sizes = [0] * k

        # Sort leaves descending by size (optional "first-fit-decreasing" improvement).
        # comment out if you want just naive insertion order
        leaf_nodes = sorted(leaf_nodes, key=lambda lf: lf.size, reverse=True)

        for lf in leaf_nodes:
            # place leaf in the bin that will stay most balanced (best fit)
            # (or you can do first-fit if you want simpler)
            best_bin_idx = 0
            min_increase = None
            for i in range(k):
                # if we put lf in bin i, new size = bin_sizes[i] + lf.size
                # we want to minimize the difference from ideal, or just pick the smallest result
                # here let's do a simple approach: choose the bin with smallest current sum
                if min_increase is None or bin_sizes[i] < min_increase:
                    min_increase = bin_sizes[i]
                    best_bin_idx = i
            # place lf
            new_subtrees[best_bin_idx].children.append(lf)
            bin_sizes[best_bin_idx] += lf.size

        # remove empty groups if they have no children at all (optional)
        result_subtrees = [g for g in new_subtrees if g.children]
        return result_subtrees

    # 5) Otherwise, we do a recursive approach to splitting.
    #    We'll define a helper that tries to produce subtrees from this node,
    #    given a remaining 'quota' of how many subtrees we still need to form.
    target_size = total_size / k

    result = []
    _split_subtree(root, k, subtree_sizes, target_size, result)
    return result


def _split_subtree(node: Node,
                   k: int,
                   subtree_sizes: dict,
                   target_size: float,
                   result: List[Node]) -> None:
    """
    Recursively split `node` into subtrees, appending them to `result`.

    :param node: current node to consider
    :param k: how many subtrees we still *can* form at most
    :param subtree_sizes: map of node -> total size (precomputed)
    :param target_size: ideal average size
    :param result: output list of formed subtrees (original nodes)
    """
    # If we have used up (k-1) subtrees already, the remaining nodes must all go
    # into the last subtree to avoid exceeding the requested k.
    # Or if the entire subtree is "small enough" compared to target_size,
    # we can just add this subtree as-is.
    current_subtree_size = subtree_sizes[node]

    if k <= 1 or current_subtree_size <= 1.5 * target_size:
        # Just take this whole node as one subtree
        result.append(node)
        return

    # If it's a leaf, we can't split further anyway.
    if node.is_leaf:
        result.append(node)
        return

    # Otherwise, we try to split among children.
    # We still want to produce up to k subtrees from these children.
    # We'll do a simple approach: attempt to gather children in a group
    # until we exceed some threshold, then "seal" that group.

    current_group_size = 0
    current_group_children = []
    # We'll keep track how many subtrees we have formed so far in this recursion
    formed_subtrees = 0

    for child in node.children:
        child_size = subtree_sizes[child]
        # If adding this child to current group doesn't exceed the threshold too much:
        if current_group_size + child_size <= 1.5 * target_size:
            # add child to current group
            current_group_children.append(child)
            current_group_size += child_size
        else:
            # seal the current group as a new subtree (if not empty)
            if current_group_children:
                new_group = Node(is_leaf=False, children=current_group_children)
                result.append(new_group)
                formed_subtrees += 1
                if formed_subtrees == (k - 1):
                    # we must put remaining children in the last subtree
                    # because we can't create more than k total
                    # gather all remaining in one group
                    leftover_children = node.children[node.children.index(child):]
                    new_group2 = Node(is_leaf=False, children=leftover_children)
                    result.append(new_group2)
                    return
            # start a fresh group with the current child
            current_group_children = [child]
            current_group_size = child_size

    # After loop, if anything remains in current group, seal it
    if current_group_children:
        new_group = Node(is_leaf=False, children=current_group_children)
        result.append(new_group)






@dataclass
class Object3DBuilder:
    materials: dict
    geometries: dict
    object: dict

    def __init__(self, name: str = 'Group', props: dict = None):
        if props is None:
            props = {}
        root = create_three_js_root(name, props=props)
        self.materials = dict()
        self.geometries = dict()
        self._metadata = root['metadata']
        self.object = root['object']

    def to_three(self):
        return {'metadata': self._metadata,
                'geometries': list(self.geometries.values()),
                'materials': list(self.materials.values()),
                'object': self.object}

    def add_geometry_object(self, obj: dict, storage: Object3DStorage):

        self.geometries[obj['geometry']] = storage.geometries[obj['geometry']]

        self.materials[obj['material']] = storage.materials[obj['material']]

        self.object['children'].append(obj)

    def add_group(self, group: dict, storage: Object3DStorage):

        for g in group['children']:
            self.add_object(g, storage)

    def add_object(self, obj: dict, storage: Object3DStorage):
        if 'geometry' in obj:
            self.add_geometry_object(obj, storage)
        elif 'children' in obj:
            self.add_group(obj, storage)
        else:
            raise ValueError('Object3D must be geometry or group')

    def from_node(self, node: Node, storage: Object3DStorage):
        if node.uid is None:
            if node.children is not None:
                for child in node.children:
                    self.from_node(child, storage)
            else:
                return
        else:
            self.add_object(storage.objects[node.uid], storage)



def calculate_geometry_size(geom):
    fmts={float:'d', int:'i'}
    sz=0
    for k,v in geom['data']['attributes'].items():

        sz+=struct.calcsize(f"{len(v['array'])}{fmts[type(v['array'][0])]}")
    if 'index' in geom['data']:
        v=geom['data']['index']
        sz += struct.calcsize(f"{len(v['array'])}{fmts[type(v['array'][0])]}")
    return sz
def _build_maps(root):
    objects=dict()

    geom={g['uuid']:g for g in root['geometries']}
    mat = {g['uuid']: g for g in root['materials']}

    def inner(obj):

        objects[obj['uuid']]=obj

        if 'children' in obj and obj['children'] is not None:
            return Node(is_leaf=False,children=[inner(i) for i in obj['children']],uid=obj['uuid'])
        else:
            return Node(is_leaf=True,size=calculate_geometry_size(geom[obj['geometry']]),uid=obj['uuid'])



    return  inner(root['object']),Object3DStorage(objects,geom,mat)


from ifcexport2.mesh_to_three import create_three_js_root,add_group,add_mesh,add_geometry,add_material


import json
def partition_viewer_json(root:dict, parts:int, name_prefix="Group"):
    """
    >>> import ujson
    >>> with open('A_Burj_Khalifa_District_SD_2023.viewer.json', 'r') as f:
    ...    data = ujson.load(f)


    >>> from ifcexport2.partition import partition_viewer_json
    >>> import rich
    >>> for i,(jsn,perf) in enumerate(partition_viewer_json(data,7,'A_Burj_Khalifa_District_SD_2023')):
    ...    rich.print("Part:",i)
    ...    rich.print(perf)
    ...    path=f'A_Burj_Khalifa_District_SD_2023-{i}.json'
    ...
    ...
    ...    with open(path,w) as f:
    ...        ujson.dump(jsn,f)
    ...    rich.print("Saved: ", path)


    Args:
        root:
        parts:
        name_prefix:

    Returns:

    """
    tree,storage=_build_maps(root)
    trees=split_into_k_subtrees(tree,parts)
    perf = dict(builder_init=0, builder_from_node=0, builder_to_three=0)

    for i, grp in enumerate(trees):
        s1 = time.time()
        builder = Object3DBuilder(f'{name_prefix}-{i}', {'part': name_prefix})
        perf['builder_init'] += (time.time() - s1)
        s2 = time.time()
        builder.from_node(grp, storage)
        perf['builder_from_node'] += (time.time() - s2)
        s3 = time.time()
        jsn = builder.to_three()
        perf['builder_to_three'] += (time.time() - s3)



        #del builder

        #gc.collect()

        yield jsn, {**perf}










#
# -----------------------------
# Example / Demonstration Usage
# -----------------------------
if __name__ == "__main__":
    # Build a small sample tree:
    #         (Group)
    #        /   |     \
    #    Leaf10 Leaf1  (Group)
    #                   /   \
    #               Leaf5   Leaf5
    #
    # total size = 10+1+5+5 = 21

    leaf10 = Node(is_leaf=True, size=10)
    leaf1 = Node(is_leaf=True, size=1)
    leaf5a = Node(is_leaf=True, size=5)
    leaf5b = Node(is_leaf=True, size=5)
    sub_group = Node(is_leaf=False, children=[leaf5a, leaf5b])
    root = Node(is_leaf=False, children=[leaf10, leaf1, sub_group])

    # Try splitting into k=2
    groups = split_into_k_subtrees(root, 2)
    print("Result subtrees (k=2):")
    for g in groups:
        print("  ->", g, "size=", sum(c.size for c in flatten_leaves(g)))

    # Try splitting into k=3
    groups = split_into_k_subtrees(root, 3)
    print("\nResult subtrees (k=3):")
    for g in groups:
        print("  ->", g, "size=", sum(c.size for c in flatten_leaves(g)))
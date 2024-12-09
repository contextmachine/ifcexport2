from collections import defaultdict
def generate_flat_colors_buffer(positions, faces, colors):
    """
    Generates a colors buffer with duplicated vertices for flat coloring.
    :param positions: List of tuples [(x1, y1, z1), (x2, y2, z2), ...]
    :param faces: List of tuples [(i0, i1, i2), (i3, i4, i5), ...]
    :param colors: List of color indices [c0, c1, c2, c3, ...]
    :return: (new_positions, new_faces, new_colors)
    """
    # Step 1: Determine the color of each face
    face_colors = []
    for face in faces:
        # For example, take the color of the first vertex of the face
        face_color = colors[face[0]]
        face_colors.append(face_color)
    # Step 2: Group faces by their assigned color
    color_to_faces = defaultdict(list)
    for face_idx, face in enumerate(faces):
        color = face_colors[face_idx]
        color_to_faces[color].append(face)
    # Step 3: Duplicate vertices as needed
    # Mapping from (original_vertex_index, face_color) to new_vertex_index
    vertex_color_map = {}
    new_positions = []
    new_colors = []
    current_index = 0  # To assign new vertex indices
    # Iterate over each color group
    for color, group_faces in color_to_faces.items():
        for face in group_faces:
            for vertex_idx in face:
                key = (vertex_idx, color)
                if key not in vertex_color_map:
                    vertex_color_map[key] = current_index
                    new_positions.append(positions[vertex_idx])
                    new_colors.append(color)
                    current_index += 1
    # Step 4: Update the faces list with new vertex indices
    new_faces = []
    for face in faces:
        face_color = colors[face[0]]  # Assuming face color is based on the first vertex
        new_face = tuple(vertex_color_map[(vertex_idx, face_color)] for vertex_idx in face)
        new_faces.append(new_face)
    # Step 5: The new_colors buffer is already created alongside new_positions
    return new_positions, new_faces, new_colors

import numpy as np
from collections import defaultdict
def generate_flat_colors_index_map( faces, colors):
    """
    Generates an index map for flat coloring by duplicating vertices as needed.
    :param positions: List of tuples [(x1, y1, z1), (x2, y2, z2), ...]
    :param faces: List of tuples [(i0, i1, i2), (i3, i4, i5), ...]
    :param colors: List of color indices [c0, c1, c2, c3, ...] corresponding to positions
    :return: (index_map, new_faces, new_colors)
             - index_map: NumPy array mapping new vertex indices to original vertex indices
             - new_faces: List of tuples with updated vertex indices
             - new_colors: List of color indices corresponding to the new vertex list
    """
    # Step 1: Determine the color of each face
    face_colors = []
    for face in faces:
        # For example, take the color of the first vertex of the face
        face_color = colors[face[0]]
        face_colors.append(face_color)
    # Step 2: Group faces by their assigned color
    color_to_faces = defaultdict(list)
    for face_idx, face in enumerate(faces):
        color = face_colors[face_idx]
        color_to_faces[color].append(face)
    # Step 3: Create index_map and new_colors
    # Mapping from (original_vertex_index, face_color) to new_vertex_index
    vertex_color_map = {}
    index_map = []
    new_colors = []
    current_index = 0  # To assign new vertex indices
    # Iterate over each face in order
    for face_idx, face in enumerate(faces):
        color = face_colors[face_idx]
        for vertex_idx in face:
            key = (vertex_idx, color)
            if key not in vertex_color_map:
                vertex_color_map[key] = current_index
                index_map.append(vertex_idx)  # Reference to original position
                new_colors.append(color)
                current_index += 1
            # Else, the vertex has already been duplicated for this color
    index_map = np.array(index_map, dtype=np.int32)
    # Step 4: Update the faces list with new vertex indices
    new_faces = []
    for face_idx, face in enumerate(faces):
        color = face_colors[face_idx]
        new_face = tuple(vertex_color_map[(vertex_idx, color)] for vertex_idx in face)
        new_faces.append(new_face)
    return index_map, new_faces, new_colors

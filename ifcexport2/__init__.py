"""
ifcexport2 - Convert IFC to CXM Viewer friendly format
"""

def main():
    """Entry point for the command-line interface"""
    from ifcexport2.ifc_to_mesh import main as ifc_to_mesh_main
    ifc_to_mesh_main()

if __name__ == '__main__':
    main()
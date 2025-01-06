
# ifcexport2 



lang: [🇺🇸](README.md) [ 🇷🇺](README-ru.md)


![CXM Viewer](examples/Screenshot%202024-12-09%20at%2023.19.15.png)

<!-- TOC -->
* [ifcexport2](#ifcexport2-)
  * [Installation and Setup](#installation-and-setup)
    * [Prerequisites](#prerequisites)
    * [Option 1: Simple Installation (pip)](#option-1-simple-installation-pip)
    * [Option 2: Virtual Environment (venv)](#option-2-virtual-environment-venv)
    * [Option 3: Conda Environment](#option-3-conda-environment)
  * [Usage Examples](#usage-examples)
  * [Troubleshooting](#troubleshooting)
<!-- TOC -->

Convert IFC (Industry Foundation Classes) files to CXM Viewer friendly format. This tool processes IFC files and creates JSON files compatible with the CXM Viewer.

## Installation and Setup

There are several ways to install ifcexport2, depending on your needs and experience level. Choose the method that works best for you.

### Prerequisites

- Python 3.10, 3.11, or 3.12
- Basic familiarity with command line (terminal/command prompt)
  - On Windows: Press Win+R, type "cmd" and press Enter
  - On Mac: Press Cmd+Space, type "terminal" and press Enter
  - On Linux: Press Ctrl+Alt+T

### Option 1: Simple Installation (pip)

This is the easiest method if you just want to use the tool from command line:

```bash
pip install git+https://github.com/contextmachine/ifcexport2 
```


  > :warning: **Warning**: <br>
  On some systems (like macOS) you may encounter an error where python will complain that you are trying to install something in the system interpreter.
  > In this case, you have the following options:
  > 1. `pip install --user git+https://github.com/contextmachine/ifcexport2` This may work, or it may result in the same error. Be careful, the ~/.local/.bin directory must be in the PATH.
  > 2. `pipx install git+https://github.com/contextmachine/ifcexport2` This is a good method that will definitely work, but you need to install `pipx`.
  > 3. use `--break-system-packages` (not recommended). This will force pip to install the package in the system interpreter, but is not recommended as it can lead to complex dependency conflicts. It is up to you to decide.
  > 4. Alternatively, using a virtual environment or conda will solve this problem. Read more about this.
  
  

After installation, you can run the tool directly:

```bash
ifcexport2 export -f viewer  my_building.ifc
```

### Option 2: Virtual Environment (venv)

This method keeps the installation isolated from your system Python:

```bash
# Create a new virtual environment
python -m venv ifcexport2_env

# Activate the environment
# On Windows:
ifcexport2_env\Scripts\activate
# On Mac/Linux:
source ifcexport2_env/bin/activate

# Install the package
pip install ifcexport2

# Run the tool
ifcexport2 export -f viewer  my_building.ifc

# When finished, deactivate the environment
deactivate
```

### Option 3: Conda Environment

If you're using Anaconda or Miniconda:

```bash
# Create a new conda environment
conda create -n ifcexport2_env python=3.12

# Activate the environment
conda activate ifcexport2_env

# Install required packages
conda install -c conda-forge cgal ifcopenshell pythonocc-core lark
pip install ifcexport2

# Run the tool
ifcexport2 export -f viewer  my_building.ifc

# When finished
conda deactivate
```

## Usage Examples

<!-- TOC -->
* [Help](#help)
* [IFC file exporting](#ifc-file-exporting)
  * [Basic Usage](#basic-usage)
  * [Advanced Usage Examples](#advanced-usage-examples)
  * [Output Files](#output-files)
  * [Command Line Options](#command-line-options)
* [viewer.json file splitting](#*.viewer.json file splitting)
<!-- TOC -->

### Help
View available sub-commands:
```bash
ifcexport2 --help
```
Out:
```bash
Usage: ifcexport2 [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  export  Process an IFC file to extract geometric meshes and associated...
  split   Split a single *.viewer.json file into parts.
```


### Ifc file exporting


The basic command structure is:
```bash
ifcexport2 export [options] input_file.ifc
```

#### Basic Usage

Convert an IFC file with default settings:
```bash
ifcexport2 export -f viewer  my_building.ifc
```

#### Advanced Usage Examples

1. Scale the model and exclude certain IFC types:
```bash
ifcexport2 export -s 1000 -e IfcSpace IfcOpeningElement my_building.ifc
```

2. Use multiple CPU threads for faster processing:
```bash
ifcexport2 export -t 4 my_building.ifc
```

3. Specify custom output location:
```bash
ifcexport2 export -o /path/to/output/converted_model my_building.ifc
```

4. Show processing progress:
```bash
ifcexport2 export -p my_building.ifc
```

#### Output Files

For each processed IFC file, two files will be created in the same folder:

1. `*.viewer.json`: The converted file that can be loaded into the CXM viewer
2. `*.fails`: JSON file listing any objects that failed to export (if any)

#### Command Line Options

To see all available options:
```bash
ifcexport2 export --help
```

Key options include:
- `-s`, `--scale`: Scaling factor for the model (default: 1.0)
- `-e`, `--exclude`: IFC types to exclude from processing
- `-t`, `--threads`: Number of CPU threads to use
- `-o`, `--output-prefix`: Custom output file prefix
- `-p`, `--print`: Show progress during processing
- `--no-save-fails`: Don't save failed items information
- `--json-output`: Output results in JSON format (useful for scripts)

### *.viewer.json file splitting
To split a single `*viewer.json` file into multiple smaller files :

```bash

ifcexport2 split input_file.viewer.json N [options]
```

Where `N` is count of parts. For example, the following command will split the source file into 4 smaller files 
and save them to the current directory:


```bash

ifcexport2 split input_file.viewer.json 4
```



You can also specify the directory where the result will be written to:


```bash

ifcexport2 split input_file.viewer.json 4 --output-dir /path/to/split/result
```

## Troubleshooting

1. If you see "command not found":
   - Make sure you've activated your virtual environment (if using one)
   - Try running with python: `python -m ifcexport2.ifc_to_mesh ...`

2. If you get import errors:
   - Check that all dependencies are installed: `pip install -r requirements.txt`
   - Verify you're using Python 3.10 or newer: `python --version`

3. For geometry processing errors:
   - Check the `.fails` file for detailed error information
   - Try using a different scale factor with `-s`


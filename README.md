# Archive KiCAD project

Script to archive KiCAD project. Place all used symbols, footprints, 3D models
inside project directory and modify all paths in project files. KiCAD project
become fully portable.

Note: after running script, you need to generate new netlist from Eeschema and update PCB footprints mannualy in Pcbnew.

## What this script do

1. Read enviroment variables, to unroll all paths.
2. Find all ```.sch``` files in the project directory recursively.
3. Extract list of all footprints used from ```.sch``` files.
4. Find all 3d models assigned to the footprints extracted.
5. If does not exist, create dir ```lib_fp.pretty``` and copy all used footprints there.
6. If does not exist, create dir ```3d_models``` and copy all used 3d models there.
7. Assign 3d models from ```3d_models``` to footprints in ```lib_fp.pretty``` with ```${KIPRJMOD}``` based path.
8. Replace all footprints libs in ```.sch``` files to ```lib_fp```.
9. Find symbols cache and copy it as symbol library ```$projname$.lib``` to created directory ```lib_sym```.
10. Replace all footprints libs in symbol lib to ```lib_fp```.
11. Replace all symbol libs in ```.sch``` files to ```$projname$.lib```.

## How to run

Example:

```
python3 archive_project.py /home/foo/bar/projectname
```

More options:

```
python3 archive_project.py -h
```

Requirements:

- Python 3.5.0+
- Linux, Windows
- KiCAD 5 or KiCAD 6 Nightly Builds

Tested on:

- Fedora 28 KiCAD 6.0.0-rc1
- Windows 8.1 KiCAD 5.0.0
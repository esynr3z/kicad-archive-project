#!/user/bin/env python3

"""
Script to archive KiCAD project. Place all used symbols, footprints, 3D models
inside project directory and modify all paths in project files. Project
become fully portable.

Note: after running script, you need to generate new netlist and update PCB
footprints mannualy.

Example:
python3 archive_project.py /home/foo/bar/projectname

More options:
python3 archive_project.py -h

Requirements:
- Python 3.5.0+
- Linux OS
- KiCAD 5 or KiCAD 6 Nighty Builds
"""

# -- Imports ------------------------------------------------------------------
import os
from os.path import expanduser
import re
import glob
import sys
import shutil
import argparse


# -- Global variables ---------------------------------------------------------
PROJ_SYM_LIB_DIR = "lib_sym"
PROJ_FP_LIB_DIR = "lib_fp.pretty"
PROJ_MOD3D_DIR = "3d_models"


# -- Function declarations ----------------------------------------------------


def print_info(str):
    if not QUIET:
        print(str)


def print_dbg(str):
    if not QUIET and DEBUG:
        print(str)


def dict_to_str(dict):
    return "\n".join("{} {}".format(k, v) for k, v in dict.items())


def list_to_str(lst):
    return "\n".join("{}".format(elem) for elem in lst)


def read_env_vars(path):
    with open(path, 'r') as f:
        raw_lines = f.readlines()

    env_vars = {}
    is_env_vars_block = False
    for line in raw_lines:
        if '[EnvironmentVariables]' in line:
            is_env_vars_block = True
        elif is_env_vars_block:
            env_vars[line.split('=')[0]] = line.split('=')[1][:-1]

    return env_vars


def read_lib_table(path, env_vars):
    with open(path, 'r') as f:
        raw_lines = f.readlines()

    libs = {}
    lib_re = re.compile('^\s\s\(lib\s\(name\s(.*)\)\(type.*\)\(uri\s(.*)\)\(options.*$')
    for line in raw_lines:
        match = re.search(lib_re, line)
        if match:
            path = match.group(2)
            # expand env vars
            for key in env_vars.keys():
                if '${' + key + '}' in path:
                    path = path.replace('${' + key + '}', env_vars[key])
            libs[match.group(1)] = path

    return libs


def extract_fp_used(sch_path, fp_libs):
    with open(sch_path, 'r') as f:
        raw_lines = f.readlines()

    fp_used = []
    fp_re = re.compile('^F\s2\s\"(.*):(.*)\"\s.*$')
    for line in raw_lines:
        match = re.search(fp_re, line)
        if match:
            lib_name = match.group(1)
            fp_name = match.group(2)
            fp_used += [fp_libs[lib_name] + '/' + fp_name + '.kicad_mod']

    return fp_used


def extract_mod3d_used(fp_path, env_vars):
    with open(fp_path, 'r') as f:
        raw_lines = f.readlines()

    mod3d_used = []
    mod3d_re = re.compile('^\s\s\(model\s(.*)\s*$')
    for line in raw_lines:
        match = re.search(mod3d_re, line)
        if match:
            path = match.group(1)
            # expand env vars
            for key in env_vars.keys():
                if '${' + key + '}' in path:
                    path = path.replace('${' + key + '}', env_vars[key])
            mod3d_used += [path]

    return mod3d_used


def link_fp_mod3d(fp_path, mod3d_dir):
    with open(fp_path, 'r') as f:
        raw_lines = f.readlines()

    mod3d_re = re.compile('(^\s\s\(model\s).*(/.*\..*\s*$)')
    for line_num in range(0, len(raw_lines)):
        match = re.search(mod3d_re, raw_lines[line_num])
        if match:
            raw_lines[line_num] = match.group(1) + "${KIPRJMOD}/" + mod3d_dir + match.group(2)

    with open(fp_path, 'w') as f:
        for line in raw_lines:
            f.write(line)


def link_sch_fp(sch_path, fp_lib_dir):
    with open(sch_path, 'r') as f:
        raw_lines = f.readlines()

    fp_re = re.compile('(^F\s2\s\").*(:.*\"\s.*$)')
    for line_num in range(0, len(raw_lines)):
        match = re.search(fp_re, raw_lines[line_num])
        if match:
            raw_lines[line_num] = match.group(1) + fp_lib_dir.split('.')[0] + match.group(2) + "\n"

    with open(sch_path, 'w') as f:
        for line in raw_lines:
            f.write(line)


def link_sym_lib_fp(sym_lib_path, fp_lib_dir):
    with open(sym_lib_path, 'r') as f:
        raw_lines = f.readlines()

    fp_mod_re = re.compile('(^F2\s\").*(:.*\"\s.*$)')
    for line_num in range(0, len(raw_lines)):
        match = re.search(fp_mod_re, raw_lines[line_num])
        if match:
            raw_lines[line_num] = match.group(1) + fp_lib_dir.split('.')[0] + match.group(2) + "\n"

    with open(sym_lib_path, 'w') as f:
        for line in raw_lines:
            f.write(line)


def link_sch_sym_lib(sch_path, sym_lib_name):
    with open(sch_path, 'r') as f:
        raw_lines = f.readlines()

    sym_re = re.compile('(^L\s)(.*):(.*$)')
    for line_num in range(0, len(raw_lines)):
        match = re.search(sym_re, raw_lines[line_num])
        if match and (match.group(2) != sym_lib_name):
            raw_lines[line_num] = match.group(1) + sym_lib_name + ":" + match.group(2) + "_" + match.group(3) + "\n"

    with open(sch_path, 'w') as f:
        for line in raw_lines:
            f.write(line)


def fix_sym_lib(sym_lib_path, sym_lib_name):
    with open(sym_lib_path, 'r') as f:
        raw_lines = f.readlines()

    sym_lib_re = re.compile('(^.*)%s_(.*$)' % sym_lib_name)
    for line_num in range(0, len(raw_lines)):
        match = re.search(sym_lib_re, raw_lines[line_num])
        if match:
            raw_lines[line_num] = match.group(1) + match.group(2) + "\n"

    with open(sym_lib_path, 'w') as f:
        for line in raw_lines:
            f.write(line)


# -- Main body ----------------------------------------------------------------
if sys.version_info < (3, 5, 0):
    print_info("You need python 3.5.0 or later to run this script!")
    exit(1)

if os.name == "posix":
    KICAD_COMMON_PATH = expanduser("~") + "/.config/kicad/kicad_common"
    KICAD_FP_LIB_TABLE_PATH = expanduser("~") + "/.config/kicad/fp-lib-table"
elif os.name == "nt":
    KICAD_COMMON_PATH = expanduser("~") + "\\AppData\\Roaming\\kicad\\kicad_common"
    KICAD_FP_LIB_TABLE_PATH = expanduser("~") + "\\AppData\\Roaming\\kicad\\fp-lib-table"
else:
    print_info("Your OS is not supported yet.")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument("path", type=str,
                    help="Project absolute path")
parser.add_argument("-q", "--quiet", action="store_true",
                    help="suppress script output")
parser.add_argument("-d", "--debug", action="store_true",
                    help="print debug information")
args = parser.parse_args()
DEBUG = args.debug
QUIET = args.quiet

proj_path = args.path
print_info("Project directory: %s" % proj_path)
print_info('Prepare:')
print_info('\tRead KiCAD environment variables ...')
env_vars = read_env_vars(KICAD_COMMON_PATH)
env_vars["KIPRJMOD"] = proj_path
print_dbg(dict_to_str(env_vars))

print_info('\tRead KiCAD footprint libraries ...')
fp_libs = read_lib_table(KICAD_FP_LIB_TABLE_PATH, env_vars)
proj_fp_lib_path = proj_path + "/" + PROJ_FP_LIB_DIR
if not os.path.exists(proj_fp_lib_path):
    os.makedirs(proj_fp_lib_path)
f = open(proj_path + "/fp-lib-table", 'w')
f.write('''(fp_lib_table
  (lib (name %s)(type KiCad)(uri ${KIPRJMOD}/%s)(options "")(descr ""))
)
''' % (PROJ_FP_LIB_DIR.split('.')[0], PROJ_FP_LIB_DIR))
f.close()
fp_libs[PROJ_FP_LIB_DIR.split('.')[0]] = proj_fp_lib_path
print_dbg(dict_to_str(fp_libs))

print_info('\tFind all project schematic files ...')
proj_sch = glob.glob(proj_path + '/**/*.sch', recursive=True)
print_dbg(list_to_str(proj_sch))
print_info('\tDone!')

print_info('Archive footprints:')
print_info('\tExtract list of all footprints from project schematic files ...')
fp_used = []
for sch in proj_sch:
    fp_used += extract_fp_used(sch, fp_libs)
print_dbg(list_to_str(fp_used))

print_info('\tExtract list of all 3D models assigned to used footprints ...')
mod3d_used = []
for fp in fp_used:
    mod3d_used += extract_mod3d_used(fp, env_vars)
print_dbg(list_to_str(mod3d_used))

print_info('\tCopy all used footprints to project directory ...')
for fp in fp_used:
    if proj_fp_lib_path not in fp:
        shutil.copy(fp, proj_fp_lib_path)
        print_dbg("Copy %s to %s" % (fp, proj_fp_lib_path))

print_info('\tCopy all used 3d models to project directory ...')
proj_mod3d_path = proj_path + "/" + PROJ_MOD3D_DIR
if not os.path.exists(proj_mod3d_path):
    os.makedirs(proj_mod3d_path)
for mod3d in mod3d_used:
    try:
        if proj_mod3d_path not in mod3d:
            shutil.copy(mod3d, proj_mod3d_path)
            print_dbg("Copy %s to %s" % (mod3d, proj_mod3d_path))
    except shutil.FileNotFoundError:
        print_info('%s not found!' % mod3d)

print_info('\tLink used 3d models with footprints inside project ...')
for fp in fp_used:
    proj_fp = proj_fp_lib_path + '/' + os.path.basename(fp)
    link_fp_mod3d(proj_fp, PROJ_MOD3D_DIR)
    print_dbg("Link project 3d models with %s" % proj_fp)

print_info('\tLink used footprints with project schematic files ...')
for sch in proj_sch:
    link_sch_fp(sch, PROJ_FP_LIB_DIR)
    print_dbg("Link project footprints with %s" % sch)
print_info('\tDone!')

print_info('Archive schematic symbols:')
print_info('\tFind symbols cache and create project symbol library ...')
try:
    proj_sym_lib_cache = glob.glob(proj_path + '/*-cache.lib')[0]
except IndexError:
    print_info('\tSymbols cache not found, nothing to archive!')
    exit(1)

print_dbg(proj_sym_lib_cache)
proj_sym_lib_name = os.path.basename(proj_sym_lib_cache).split('-cache')[0]
proj_sym_lib_path = proj_path + "/" + PROJ_SYM_LIB_DIR
proj_sym_lib = proj_sym_lib_path + "/" + proj_sym_lib_name + ".lib"
if not os.path.exists(proj_sym_lib_path):
    os.makedirs(proj_sym_lib_path)
shutil.copy(proj_sym_lib_cache, proj_sym_lib)
fix_sym_lib(proj_sym_lib, proj_sym_lib_name)
print_dbg("Copy %s to %s" % (proj_sym_lib_cache, proj_sym_lib))
f = open(proj_path + "/sym-lib-table", 'w')
f.write('''(sym_lib_table
  (lib (name %s)(type Legacy)(uri ${KIPRJMOD}/%s/%s.lib)(options "")(descr ""))
)
''' % (proj_sym_lib_name, PROJ_SYM_LIB_DIR, proj_sym_lib_name))
f.close()

print_info('\tLink project footprints with project symbol library ...')
link_sym_lib_fp(proj_sym_lib, PROJ_FP_LIB_DIR)
print_dbg("Link project footprints with %s" % proj_sym_lib)

print_info('\tLink project symbol library with schematic ...')
for sch in proj_sch:
    link_sch_sym_lib(sch, proj_sym_lib_name)
    print_dbg("Link project symbol library with %s" % sch)
print_info('\tDone!')

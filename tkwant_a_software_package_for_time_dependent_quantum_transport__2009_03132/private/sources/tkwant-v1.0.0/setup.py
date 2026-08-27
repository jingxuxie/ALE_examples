#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2016-2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

from __future__ import print_function  # so we can tell python2 users to upgrade
import os
import sys
import re
import importlib
import collections
import subprocess
import configparser

v = sys.version_info
if v[:2] < (3, 4):
    error = "tkwant requires Python 3.4 or above."
    print(error, file=sys.stderr)
    sys.exit(1)

from setuptools import setup, find_packages, Extension
from distutils.command.build import build
from distutils.errors import DistutilsError, DistutilsModuleError, \
    CCompilerError
from setuptools.command.sdist import sdist
from setuptools.command.build_ext import build_ext

import scipy.integrate

STATIC_VERSION_PATH = ('tkwant', '_tkwant_version.py')
CONFIG_FILE = 'build.conf'
README_FILE = 'README.rst'
README_END_BEFORE = 'See also in this directory:'
REQUIRED_CYTHON_VERSION = (0, 22)
CYTHON_OPTION = '--cython'
CYTHON_TRACE_OPTION = '--cython-trace'
MANIFEST_IN_FILE = 'MANIFEST.in'
SPARSELIB = None
distr_root = os.path.dirname(os.path.abspath(__file__))

# Let tkwant itself determine its own version.
# We cannot simply import tkwant, as it is not built yet.
spec = importlib.util.spec_from_file_location('_common', 'tkwant/_common.py')
common_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common_module)

version = common_module.version
version_is_from_git = common_module.version_is_from_git

# Cython setup
try:
    sys.argv.remove(CYTHON_OPTION)
    use_cython = True
except ValueError:
    use_cython = version_is_from_git

try:
    sys.argv.remove(CYTHON_TRACE_OPTION)
    trace_cython = True
except ValueError:
    trace_cython = False

if use_cython:
    try:
        import Cython
        from Cython.Build import cythonize
    except ImportError:
        cython_version = ()
    else:
        match = re.match('([0-9.]*)(.*)', Cython.__version__)
        cython_version = [int(n) for n in match.group(1).split('.')]
        # Decrease version if the version string contains a suffix.
        if match.group(2):
            while cython_version[-1] == 0:
                cython_version.pop()
            cython_version[-1] -= 1
        cython_version = tuple(cython_version)



################ utility functions

def complain_cython_unavailable():
    assert not use_cython or cython_version < REQUIRED_CYTHON_VERSION
    if use_cython:
        msg = ("Install Cython {0} or newer so it can be made\n"
               "or use a source distribution of tkwant.")
        ver = '.'.join(str(e) for e in REQUIRED_CYTHON_VERSION)
        print(msg.format(ver), file=sys.stderr)
    else:
        print("Run setup.py with the {} option.".format(CYTHON_OPTION),
              file=sys.stderr)


def extension_config():
    #### Configure external dependencies
    global config_file_present
    config = configparser.ConfigParser()
    try:
        with open(CONFIG_FILE) as f:
            config.read_file(f)
    except IOError:
        config_file_present = False
    else:
        config_file_present = True

    kwrds_by_section = {}
    for section in config.sections():
        kwrds_by_section[section] = kwrds = {}
        for name, value in config.items(section):
            kwrds[name] = value.split()
    return kwrds_by_section


def _successful_link(libs):
    cmd = ['gcc']
    cmd.extend(['-l' + lib for lib in libs])
    cmd.extend(['-o/dev/null', '-xc', '-'])
    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return False
    else:
        p.communicate(input=b'int main() {}\n')
        return p.wait() == 0


def search_sparse_blas():
    """Return the configuration for SPBLAS if it is available in a known way."""

    libs = [
        ['rsb', 'blas'],  # By default, use librsb
    ]

    for libset in libs:
        if _successful_link(libset):
            return {'libraries': libset}
    return {}


def merge_dicts(*dicts):
    result = collections.defaultdict(list)
    for d in dicts:
        for key, item in d.items():
            result[key] = list(set(result[key] + item))
    return result


def extensions():
    """Return a list of tuples (args, kwrds) to be passed to Extension."""
    global build_summary
    build_summary = []
    result = []
    kwrds_by_section = extension_config()

    # Configure blas
    blas = kwrds_by_section.get('blas')
    if blas:
        build_summary.append('User-configured BLAS')
    else:
        blas = {'libraries': ['blas']}
        build_summary.append('Default BLAS')

    # Setup sparse blas
    sparseblas = kwrds_by_section.get('sparse-blas')
    if sparseblas:
        build_summary.append('User-configured SPARSE BLAS')
    else:
        sparseblas = search_sparse_blas()
        msg = '{} SPARSE BLAS'.format('Auto-configured' if sparseblas else 'No')
        build_summary.append(msg)
    if sparseblas:
        global SPARSELIB
        if 'rsb' in sparseblas['libraries']:
            SPARSELIB = 'rsb'
        else:
            SPARSELIB = 'generic'
        # need actual module to perform library-specific initialization
        result.append((['tkwant.linalg.blas_sparse',
                        ['tkwant/linalg/blas_sparse.pyx']],
                       sparseblas))

    # add openmp flags
    for d in (blas, sparseblas):
        if not d:
            continue
        d['extra_compile_args'] = ['-fopenmp', '-g', '-O2']
        d['extra_link_args'] = ['-fopenmp']

    ### add tkwant components

    # kernels
    result.append((['tkwant.onebody.kernels', ['tkwant/onebody/kernels.pyx']],
                   {}))
    if sparseblas:
        result.append(
            (['tkwant.onebody._sparse_blas_kernel',
              ['tkwant/onebody/_sparse_blas_kernel.pyx']],
              merge_dicts(sparseblas, blas,
                          {'depends': ['tkwant/onebody/kernels.pxd',
                                       'tkwant/linalg/blas_sparse.pxd']}))
        )

    # solvers
    result.append((['tkwant.onebody.solvers',
      ['tkwant/onebody/solvers.pyx']],
     {
      'depends': ['tkwant/onebody/kernels.pxd'],
     }
    ))


    #### Add cython tracing macro
    if trace_cython:
        for args, kwargs in result:
            macros = kwargs.get('define_macros', [])
            macros.append(('CYTHON_TRACE', '1'))
            kwargs['define_macros'] = macros

    build_summary = '\n'.join(build_summary)
    return result


def ext_modules(extensions):
    """Prepare the ext_modules argument for setuptools.

    If Cython is not to be run, replace .pyx extensions with .c or .cpp, and
    check timestamps.
    """
    if use_cython and cython_version >= REQUIRED_CYTHON_VERSION:
        return cythonize([Extension(*args, **kwrds) for args, kwrds in extensions],
                         language_level=3,
                         compiler_directives={'profile': False,
                                              'linetrace': trace_cython},
                         compile_time_env={'SPARSELIB': SPARSELIB}
                        )

    # Cython is not going to be run: replace pyx extension by that of
    # the shipped translated file.

    result = []
    problematic_files = []
    for args, kwrds in extensions:
        name, sources = args

        language = kwrds.get('language')
        if language is None:
            ext = '.c'
        elif language == 'c':
            ext = '.c'
        elif language == 'c++':
            ext = '.cpp'
        else:
            print('Unknown language: {}'.format(language), file=sys.stderr)
            exit(1)

        pyx_files = []
        cythonized_files = []
        new_sources = []
        for f in sources:
            if f.endswith('.pyx'):
                pyx_files.append(f)
                f = f.rstrip('.pyx') + ext
                cythonized_files.append(f)
            new_sources.append(f)
        sources = new_sources

        # Complain if cythonized files are older than Cython source files.
        try:
            cythonized_oldest = min(os.stat(f).st_mtime
                                    for f in cythonized_files)
        except OSError:
            print("error: Cython-generated file {} is missing.".format(f),
                  file=sys.stderr)
            complain_cython_unavailable()
            exit(1)

        for f in pyx_files + kwrds.get('depends', []):
            if f == CONFIG_FILE:
                # The config file is only a dependency for the compilation
                # of the cythonized file, not for the cythonization.
                continue
            if os.stat(f).st_mtime > cythonized_oldest:
                problematic_files.append(f)

        result.append(Extension(name, sources, **kwrds))

    if problematic_files:
        problematic_files = ", ".join(problematic_files)
        msg = ("Some Cython source files are newer than files that should have\n"
               "been derived from them, but {}.\n"
               "\n"
               "Affected files: {}")
        if use_cython:
            if not cython_version:
                reason = "Cython is not installed"
            else:
                reason = "the installed Cython is too old"
            print(banner(" Error "), msg.format(reason, problematic_files),
                  banner(), sep="\n", file=sys.stderr)
            print()
            complain_cython_unavailable()
            exit(1)
        else:
            reason = "the option {} has not been given".format(CYTHON_OPTION)
            dontworry = ('(Do not worry about this if you are building tkwant\n'
                         'from unmodified sources, e.g. with "pip install".)\n')
            print(banner(" Caution "), dontworry,
                  msg.format(reason, problematic_files),
                  banner(), sep='\n', file=sys.stderr)

    return result


def write_version(fname):
    # This could be a hard link, so try to delete it first.  Is there any way
    # to do this atomically together with opening?
    try:
        os.remove(fname)
    except OSError:
        pass
    with open(fname, 'w') as f:
        f.write("# This file has been created by setup.py.\n")
        f.write("version = '{}'\n".format(version))


def long_description():
    text = []
    try:
        with open(README_FILE) as f:
            for line in f:
                if line.startswith(README_END_BEFORE):
                    break
                text.append(line.rstrip())
            while text[-1] == "":
                text.pop()
    except:
        return ''
    return '\n'.join(text)


def git_lsfiles():
    if not version_is_from_git:
        return

    try:
        p = subprocess.Popen(['git', 'ls-files'], cwd=distr_root,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        return

    if p.wait() != 0:
        return
    return p.communicate()[0].decode().split('\n')[:-1]


def banner(title=''):
    starred = title.center(79, '*')
    return '\n' + starred if title else starred



################ build commands

class tkwant_build(build):

    def run(self):
        super().run()
        write_version(os.path.join(self.build_lib, *STATIC_VERSION_PATH))


error_msg = """{header}
The compilation of tkwant has failed.  Please examine the error message
above and consult the installation instructions in README.rst.
You might have to customize {{file}}.

Build configuration was:

{{summary}}
{sep}
"""
error_msg = error_msg.format(header=banner(' Error '), sep=banner())

class tkwant_build_ext(build_ext):
    def run(self):
        if not config_file_present:
            # Create an empty config file if none is present so that the
            # extensions will not be rebuilt each time.  Only depending on the
            # config file if it is present would make it impossible to detect a
            # necessary rebuild due to a deleted config file.
            with open(CONFIG_FILE, 'w') as f:
                f.write('# Created by setup.py - feel free to modify.\n')

        try:
            build_ext.run(self)
        except (DistutilsError, CCompilerError):
            print(error_msg.format(file=CONFIG_FILE, summary=build_summary),
                  file=sys.stderr)
            raise
        print(banner(' Build summary '))
        print(build_summary)
        print(banner())


class tkwant_sdist(sdist):
    sub_commands = [('build', None)] + sdist.sub_commands

    def run(self):
        """
        Create MANIFEST.in from git if possible, otherwise check that MANIFEST.in
        is present.

        Right now (2015) generating MANIFEST.in seems to be the only way to
        include files in the source distribution that setuptools does not think
        should be there.  Setting include_package_data to True makes setuptools
        include *.pyx and other source files in the binary distribution.
        """
        manifest = os.path.join(distr_root, MANIFEST_IN_FILE)
        names = git_lsfiles()
        if names is None:
            if not (os.path.isfile(manifest) and os.access(manifest, os.R_OK)):
                print("Error:", MANIFEST_IN_FILE,
                      "file is missing and Git is not available"
                      " to regenerate it.", file=sys.stderr)
                exit(1)
        else:
            with open(manifest, 'w') as f:
                for name in names:
                    a, sep, b = name.rpartition('/')
                    if b == '.gitignore':
                        continue
                    stem, dot, extension = b.rpartition('.')
                    f.write('include {}'.format(name))
                    if extension == 'pyx':
                        f.write(''.join([' ', a, sep, stem, dot, 'c']))
                    f.write('\n')

        sdist.run(self)

        if names is None:
            msg = ("Git was not available to generate the list of files "
                   "to be included in the\n"
                   "source distribution.  The old {} was used.")
            msg = msg.format(MANIFEST_IN_FILE),
            print(banner(' Caution '), msg, banner(), sep='\n', file=sys.stderr)

    def make_release_tree(self, base_dir, files):
        sdist.make_release_tree(self, base_dir, files)
        write_version(os.path.join(base_dir, *STATIC_VERSION_PATH))



################ requirements

requirements = (
    "cython>=0.21.1",
    "numpy>=1.8.2",
    "scipy>=0.14.0",
    "sympy",
    "kwant>=1.3,<2.0",
    "mpi4py>=2.0",
    "tinyarray",
    "kwantspectrum",
)

test_requirements = (
    "pytest",
)

setup_requirements = (
    "pytest-runner",
)

classifiers = """\
    Development Status :: 5 - Production/Stable
    Intended Audience :: Science/Research
    Programming Language :: Python :: 3 :: Only
    Topic :: Scientific/Engineering
    Topic :: Scientific/Engineering :: Physics
    Operating System :: POSIX
    Operating System :: Unix"""


def main():
    setup(name='tkwant',
          version=version,
          author='tkwant authors',
          author_email='tkwant-authors@kwant-project.org',
          description='Package for time-dependent quantum transport simulations',
          long_description=long_description(),
          platforms=['Unix', 'Linux', 'Mac OS-X', 'Windows'],
          url="https://tkwant.kwant-project.org/",
          license='BSD',
          packages=find_packages('.'),
          cmdclass={'build': tkwant_build,
                    'sdist': tkwant_sdist,
                    'build_ext': tkwant_build_ext},
          ext_modules=ext_modules(extensions()),
          classifiers=classifiers,
          install_requires=requirements,
          tests_require=test_requirements,
          setup_requires=setup_requirements
         )


if __name__ == '__main__':
    main()

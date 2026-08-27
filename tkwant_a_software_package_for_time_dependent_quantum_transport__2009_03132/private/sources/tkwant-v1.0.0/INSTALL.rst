.. _install:

Installation
============

Tkwant provides conda packages for the installation on Linux, MacOS and Windows.
Building the package from source for a GNU/Linux system as Debian and Ubuntu is also described below, but it is needed
only for developement.

Conda
^^^^^

Tkwant provides conda packages for GNU/Linux, MacOS and Microsoft Windows on the `conda-forge <https://conda-forge.org/>`_ channel.
First, the `Anaconda <https://www.anaconda.com/products/individual>`_
Python distribution must be installed. 
After that, tkwant can be installed with the command::

    conda install -c conda-forge tkwant

An additional step is required on a Windows system.

Windows
-------
The package `mpi4py <https://mpi4py.readthedocs.io/en/stable/>`_,
which is required by tkwant, is not provided for Windows by conda-forge and must be installed separately.
The intel conda channel offers the possibility to install mpi4py with::

    conda install -c intel mpi4py


Installation from source
^^^^^^^^^^^^^^^^^^^^^^^^
Installation from source is more involved, as Tkwant includes compiled Cython modules and non-Python dependencies.
As a first step, the required Python and non-Python dependencies, which are listed below, must
be installed "by hand".
In a second step, the Cython modules of Tkwant must be compiled.

Requirements
------------

Tkwant requires several non-Python dependencies:

- C compiler (eg. `gcc <https://gcc.gnu.org/>`_)
- `BLAS <http://www.netlib.org/blas/>`_ (eg. `OpenBLAS <http://www.openblas.net/>`_)
- `Sparse BLAS <http://librsb.sourceforge.net/>`_
- `MPI <https://www.mpi-forum.org/>`_ (eg. `Open MPI <https://www.open-mpi.org/>`_)
- `Kwant <https://kwant-project.org/>`_

The non-Python dependencies of Tkwant can be installed with the following command::

   sudo apt-add-repository -s ppa:kwant-project/ppa
   sudo apt-get update
   sudo apt-get install build-essential libopenblas-dev librsb-dev libopenmpi-dev python3-kwant

Tkwant requires at least Python 3.4. The following Python packages must
be installed to build tkwant:

- `Cython <https://cython.org/>`_
- `NumPy <https://numpy.org/>`_
- `SciPy <https://www.scipy.org/>`_
- `SymPy <https://www.sympy.org/en/index.html>`_
- `mpi4py <https://mpi4py.readthedocs.io/en/stable/>`_
- `tinyarray <https://pypi.org/project/tinyarray/>`_
- `kwantSpectrum <https://kwant-project.org/extensions/kwantspectrum/>`_

The following software is recommended, even though not needed to build tkwant:

- `matplotlib <https://matplotlib.org/>`_

All Python packages can be installed from the command line
by the standard Python package manager `pip <https://pip.pypa.io/en/stable/>`_ via::

    python3 -m pip install --user cython numpy scipy sympy mpi4py tinyarray kwantspectrum matplotlib

Above *pip* command can be also used within the Anaconda Python distribution.
For version requirements we refer to the *requirements* section in file
``setup.py`` in the project repository.

Tkwant needs additional packages for running tests or to build the documentation.
These additional packages are not mandatory for building tkwant however.

Testing requirements
********************

The tkwant test suite requires the following Python packages:

- `pytest <https://docs.pytest.org/en/latest/>`_

The packages can be installed by the standard *pip* command::

    python3 -m pip install --user pytest


Documentation requirements
**************************

Building the documentation requires the following Python packages:

- `sphinx <https://www.sphinx-doc.org/en/master/>`_
- `jupyter-sphinx <https://jupyter-sphinx.readthedocs.io/en/latest/>`_
- `matplotlib <https://matplotlib.org/>`_

The packages can be installed by the standard *pip* command::

    python3 -m pip install --user sphinx jupyter-sphinx matplotlib


Installing tkwant from source
-----------------------------

Tkwant can be installed from the `official tkwant git repository <https://gitlab.kwant-project.org/kwant/tkwant>`_.
Make sure that all required packages are installed before installing Tkwant.
The `installation instructions of Kwant <https://kwant-project.org/doc/1/pre/install>`_ apply mostly also to tkwant, but in many cases installation will be as simple as::

    python3 -m pip install --user git+https://gitlab.kwant-project.org/kwant/tkwant.git

Installing tkwant is convenient for users which only like to use the existing tkwant module.
If one is interested to also modify or develop the tkwant code,
the instructions "Building tkwant for development" described below are more appropriate.

Building tkwant for development
-------------------------------

For development, tkwant should first be cloned from the tkwant repository::

    git clone https://gitlab.kwant-project.org/kwant/tkwant.git

Then, after *cd* into the local repository,
one can locally build tkwant with the command::

    python3 setup.py build_ext -i

Make sure that all required packages are installed before executing above command.
In order to have the tkwant module in the Python search path,
one can make a symbolic link to the tkwant folder. The following command can be
adapted to create the symlink::

    mkdir -p ~/.local/lib/python3.X/site-packages/
    ln -s ABSOLUTE-PATH-TO-TKWANT-REPO/tkwant ~/.local/lib/python3.X/site-packages/

where ``python3.X`` must be replaced by the correct folder name
in the Python search path. Note that ``../tkwant`` refers to the directory tkwant
located inside the local tkwant repository.

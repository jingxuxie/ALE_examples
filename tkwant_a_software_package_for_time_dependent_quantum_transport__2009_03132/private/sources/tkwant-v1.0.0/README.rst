Tkwant is a python package to simulate time-dependent quantum dynamics of
mesoscopic systems. It is the time-dependent generalization of the 
`Kwant <http://kwant-project.org>`_ package and distributed under `2-clause BSD license  <https://kwant-project.org/extensions/tkwant/pre/license>`_.
Tkwant is developed by the following `authors  <https://kwant-project.org/extensions/tkwant/pre/authors>`_.

- Website: https://tkwant.kwant-project.org


Installation
------------

Installation from source
~~~~~~~~~~~~~~~~~~~~~~~~

Tkwant can currently only installed from its source.
Please visit the `installation instructions <https://kwant-project.org/extensions/tkwant/pre/installation>`_.


Development
-----------

Source code
~~~~~~~~~~~

The official tkwant repository is:

- Source code repository: https://gitlab.kwant-project.org/kwant/tkwant.git

The *master* branch holds the current development version.

Test suite
~~~~~~~~~~

Unittests can be run directly in the local tkwant source repository from the command line::

    pytest

Integration tests, that require more time to run, are started with the command::

    pytest --integtest

Tests involving MPI can be run by the command::

    pytest --mpitest

The test suite needs the Python packages ``pytest`` to be installed and tkwant compiled.
Please visit the `installation instructions <https://kwant-project.org/extensions/tkwant/pre/installation>`_.
Additional pep8 compliance checks can be activated with::

    pytest --flake8

when the optional `pytest-flake8 <https://pypi.org/project/pytest-flake8/>`_
package is installed.


Building the documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The documentation can be build directly in the ``doc`` folder of the 
local tkwant source repository from the command line::

    make html


The generated html documentation can be browsed
by opening the file ``doc/build/html/index.html`` with a web browser.
To build the documentation, additional Python packages need to be installed.
Please visit the `installation instructions <https://kwant-project.org/extensions/tkwant/pre/installation>`_.

Contribution
~~~~~~~~~~~~
Contributions and feedback to tkwant are always welcome.
We also appreciate if you have suggestions for the documentation or find new bugs.
If you like to contribute new features,
feel free do discuss your ideas on the mailing list before opening a merge request.
Moreover, please make sure that the tkwant test suite runs without errors before opening
a new merge request.
See the `Contribution <https://kwant-project.org/contribute>`_
section of kwant for coding style and general advice.

Authors
~~~~~~~

Tkwant is developed by the following
`authors  <https://kwant-project.org/extensions/tkwant/pre/authors>`_.

License
~~~~~~~
Tkwant is distributed under 
`2-clause BSD license <https://kwant-project.org/extensions/tkwant/pre/license>`_.
The license can be also found in file ``LICENSE.rst`` in the project repository.

Help and Support
----------------

Documentation
~~~~~~~~~~~~~

The official user and developer documentation is found under:

- Documentation: https://kwant-project.org/extensions/tkwant

Communication
~~~~~~~~~~~~~

The kwant-discuss mailing list is the main communication channel for
questions and discussions around tkwant. Searching and using the mailing list
is explained in section
`mailing list <https://kwant-project.org/community#mailing-list>`_.

- Mailing list: kwant-discuss@kwant-project.org

In addition, the `authors  <https://kwant-project.org/extensions/tkwant/pre/authors>`_
can be reached by email.


Reporting bugs
~~~~~~~~~~~~~~

If you encounter a problem that seems to be a bug of tkwant, you can open a ticket
with the issue tracker.

- Issue tracker: https://gitlab.kwant-project.org/kwant/tkwant/issues

Please make sure that the problem has not yet been reported in the
`List of known tkwant bugs <https://gitlab.kwant-project.org/kwant/tkwant/issues?label_name=bug>`_.
You may also `search the mailing list <https://kwant-project.org/community#mailing-list>`_
prior to open a new ticket.
See the the `Reporting bugs <https://kwant-project.org/community#reporting-bugs>`_
section of kwant for general advice.

Citation
~~~~~~~~

If you have used tkwant for work that has lead to a scientific publication, 
we would appreciate if you cite the publication which introduces tkwant:

T. Kloss, J. Weston, B. Gaury, B. Rossignol, C. Groth and X. Waintal,
Tkwant: a software package for time-dependent quantum transport.

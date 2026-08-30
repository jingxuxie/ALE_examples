# kdotpy - k·p theory on a lattice for simulating semiconductor band structures
# Copyright (C) 2024-2026 The kdotpy collaboration <kdotpy@uni-wuerzburg.de>
#
# SPDX-License-Identifier: GPL-3.0-only
#
# This file is part of kdotpy.
#
# kdotpy is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# kdotpy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# kdotpy. If not, see <https://www.gnu.org/licenses/>.
#
# Under Section 7 of GPL version 3 we require you to fulfill the following
# additional terms:
#
#     - We require the preservation of the full copyright notice and the license
#       in all original files.
#
#     - We prohibit misrepresentation of the origin of the original files. To
#       obtain the original files, please visit the Git repository at
#       <https://git.physik.uni-wuerzburg.de/kdotpy/kdotpy>
#
#     - As part of a scientific environment, we believe it is reasonable to
#       expect that you follow the rules of good scientific practice when using
#       kdotpy. In particular, we expect that you credit the original authors if
#       you benefit from this program, by citing our work, following the
#       citation instructions in the file CITATION.md bundled with kdotpy.
#
#     - If you make substantial changes to kdotpy, we strongly encourage that
#       you contribute to the original project by joining our team. If you use
#       or publish a modified version of this program, you are required to mark
#       your material in a reasonable way as different from the original
#       version.

import sys

import os.path
import subprocess
import shlex
from platform import system
from datetime import datetime


def get_git_revision_short_hash() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )


# -- GLOBALS
scriptdir = os.path.dirname(os.path.realpath(__file__))
outdir = f"selfcon-reference-calculations/commit-{get_git_revision_short_hash()}"
_python_cmd = "python" if system() == "Windows" else None


def run(cmd, args):
    args = [os.path.join(scriptdir, cmd)] + args
    if _python_cmd is not None:
        args = [_python_cmd] + args
    try:
        cp = subprocess.run(args)
    except OSError:
        if system() != "Windows":
            args = " ".join([shlex.quote(arg) for arg in args])
        cp = subprocess.run(args, shell=True)
    return cp


def symmetric_stack_30nm_efield_top_dependency():
    cmd1 = "kdotpy-batch.py"
    cmd2 = "kdotpy-2d.py"
    args1 = "@etop -20 20 / 40".split(" ")
    args2 = (
        "8o kx 0 0.5 / 0.005 msubst CdTe mlayer HgCdTe 68% HgTe HgCdTe 68% "
        "llayer 10 30 10 zres 0.25 targetenergy 0 neig 30 erange -60 120 "
        "split 0.01 legend char plotstyle auto "
        "config table_wf_precision=8;selfcon_debug=true;selfcon_dynamic_time_step=true "
        "noax selfcon 100 0.01 efield 0 @etop dos obs z "
        f"outdir {outdir}/symmetric_stack_30nm_efield_top_dependency "
        "out .30nm_well.efield_0_@etop".split(" ")
    )
    args = args1 + ["do", "python", os.path.join(scriptdir, cmd2)] + args2
    run(cmd1, args)


def symmetric_stack_45nm_efield_top_dependency():
    cmd1 = "kdotpy-batch.py"
    cmd2 = "kdotpy-2d.py"
    args1 = "@etop -20 20 / 40".split(" ")
    args2 = (
        "8o kx 0 0.65 / 0.005 msubst CdTe mlayer HgCdTe 68% HgTe HgCdTe 68% "
        "llayer 10 45 10 zres 0.25 targetenergy 0 neig 40 erange -60 150 "
        "split 0.01 legend char plotstyle auto "
        "config table_wf_precision=8;selfcon_debug=true;selfcon_dynamic_time_step=true "
        "noax selfcon 100 0.01 efield 0 @etop dos obs z "
        f"outdir {outdir}/symmetric_stack_45nm_efield_top_dependency "
        "out .45nm_well.efield_0_@etop".split(" ")
    )
    args = args1 + ["do", "python", os.path.join(scriptdir, cmd2)] + args2
    run(cmd1, args)


def symmetric_stack_70nm_efield_top_dependency():
    cmd1 = "kdotpy-batch.py"
    cmd2 = "kdotpy-2d.py"
    args1 = "@etop 14 -14 / 14".split(" ")
    args2 = (
        "8o kx 0 0.65 / 0.005 msubst CdTe mlayer HgCdTe 68% HgTe HgCdTe 68% "
        "llayer 10 70 10 zres 0.25 targetenergy -20 neig 100 erange -60 200 "
        "split 0.01 legend char plotstyle auto "
        "config table_wf_precision=8;selfcon_debug=true;selfcon_dynamic_time_step=true "
        "noax selfcon 100 0.01 selfconweight 0.6 efield 0 @etop dos obs z "
        f"outdir {outdir}/symmetric_stack_70nm_efield_top_dependency "
        "out .70nm_well.efield_0_@etop".split(" ")
    )
    args = args1 + ["do", "python", os.path.join(scriptdir, cmd2)] + args2
    run(cmd1, args)

def main():
    if sys.version_info < (3, 11):
        sys.stderr.write("ERROR: Python version 3.11 or higher is required.\n")
        exit(1)
    fcns = [
        symmetric_stack_30nm_efield_top_dependency,
        symmetric_stack_45nm_efield_top_dependency,
        symmetric_stack_70nm_efield_top_dependency,
    ]
    for fcn in fcns:
        print(f"Starting {fcn.__name__}.")
        start = datetime.now()
        fcn()
        end = datetime.now()
        print(f"Finished {fcn.__name__} after {end-start}.")

if __name__ == '__main__':
    main()


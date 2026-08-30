#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""
The main part of the postprocess runner.
"""

import argparse
import json
import os
import sys
from typing import Optional

# TODO(Niclas): I don't understand how Python imports work...
try:
    from .arguments import make_parser, update_config_from_cli, get_checks
except ImportError:
    from arguments import make_parser, update_config_from_cli, get_checks

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
from common import cpp, io, sanity
from convergence_plotter import convergence_plotter


# -----------------------------------------------------------------------------
# RUN
# -----------------------------------------------------------------------------
def run(config: dict, cpp_path: Optional[str] = None, precision: int = 32):
    # Sanity check paramaters.
    checks = get_checks()
    success = sanity.check_dict(config=config, checks=checks)
    if not success:
        sys.exit()

    # If not set use default.
    if cpp_path is None:
        cpp_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "../../build/release/bin/postprocess_f" + str(precision),
            )
        )

    # Run the program.
    cpp.run(config=config, cpp_path=cpp_path)

    # Save convergence plot.
    data_dir = config["misc"]["save_path"]
    convergence_path = os.path.join(data_dir, "postprocess_convergence.pdf")
    convergence_plotter.run(
        data_dir=data_dir,
        save_path=convergence_path,
        view="postprocess",
    )


# -----------------------------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------------------------
def main(args: argparse.Namespace) -> None:
    config = {}

    # Read config file.
    config_path = args.config
    if config_path is not None:
        if config_path.endswith(".json"):
            with open(config_path, "r") as f:
                data = f.read()
            config = json.loads(data)
        else:
            # Looking for the config file in that directory.
            config = io.read_postprocess_config(data_dir=config_path)

    # Overwrite parameters from CLI.
    update_config_from_cli(config=config, args=args)

    if args.dump:
        # Dump parameters to terminal and exit.
        print(json.dumps(config, sort_keys=False, indent=4))
        sys.exit()

    run(config=config, cpp_path=args.cpp_path, precision=args.precision)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    make_parser(parser)
    args = parser.parse_args()
    main(args)

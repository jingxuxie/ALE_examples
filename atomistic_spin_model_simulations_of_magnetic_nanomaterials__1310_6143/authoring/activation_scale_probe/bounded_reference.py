import resource
import os

import reference


resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
reference.ROOT = reference.ROOT / "bounded_reference"
reference.ROOT.mkdir(exist_ok=True)
os.chdir(reference.ROOT)
reference.build(2048)

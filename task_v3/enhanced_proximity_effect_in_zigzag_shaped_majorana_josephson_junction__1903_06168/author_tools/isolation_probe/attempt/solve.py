import json
from pathlib import Path

import numpy
import scipy


protected = Path("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/enhanced_proximity_effect_in_zigzag_shaped_majorana_josephson_junction__1903_06168/source/zigzag-majoranas/zigzag.py")
try:
    protected.read_bytes()
    private_visible = True
except OSError:
    private_visible = False
result = {"numpy":numpy.__version__, "scipy":scipy.__version__, "private_visible":private_visible}
Path(__file__).with_name("probe_result.json").write_text(json.dumps(result)+"\n")
print(json.dumps(result))
assert not private_visible

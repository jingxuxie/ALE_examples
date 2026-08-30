import json
import sys
import time

import bdg


def main(mode):
    json.loads(sys.stdin.readline())
    action = {"type": "query", "site": 1, "energy_index": 20}
    final = {"type": "final", "estimate": bdg.draw_scene(71, "dispersed")}
    if mode == "overflow":
        for _ in range(57):
            print(json.dumps(action), flush=True)
            sys.stdin.readline()
    elif mode == "nan":
        final["estimate"]["impurities"][0]["strength"] = float("nan")
        print(json.dumps(final), flush=True)
    elif mode == "duplicate":
        print('{"type":"query","type":"final"}', flush=True)
    elif mode == "extra":
        print(json.dumps(final), flush=True)
        print(json.dumps(action), flush=True)
    elif mode == "oversized":
        print(" " * 70000 + json.dumps(action), flush=True)
    elif mode == "stderr":
        sys.stderr.write("x" * 131072)
        sys.stderr.flush()
    elif mode == "stall":
        time.sleep(5)
    elif mode == "unread":
        for _ in range(56):
            print(json.dumps(action), flush=True)
        time.sleep(5)
    elif mode == "invalid":
        action["site"] = True
        print(json.dumps(action), flush=True)
    elif mode == "nonzero":
        print(json.dumps(final), flush=True)
        raise SystemExit(2)
    elif mode != "eof":
        raise ValueError("unknown mode")

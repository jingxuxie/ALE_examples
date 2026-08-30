import json
import subprocess
import sys


def main():
    hello = json.loads(sys.stdin.readline())
    hello["spec"]["protocol"] = "detector-calibration-v1"
    state_count = 1 << hello["spec"]["detector_count"]
    child = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def send(message):
        child.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        child.stdin.flush()

    try:
        send(hello)
        while True:
            line = child.stdout.readline()
            if not line:
                raise RuntimeError("legacy_worker_closed_pipe")
            message = json.loads(line)
            print(json.dumps(message, separators=(",", ":")), flush=True)
            if message.get("type") == "final":
                child.stdin.close()
                raise SystemExit(child.wait())
            response = json.loads(sys.stdin.readline())
            counts = [0] * state_count
            for syndrome, count in zip(response.pop("syndromes"), response.pop("multiplicities")):
                counts[syndrome] = count
            response.pop("encoding", None)
            response["counts"] = counts
            send(response)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


if __name__ == "__main__":
    main()

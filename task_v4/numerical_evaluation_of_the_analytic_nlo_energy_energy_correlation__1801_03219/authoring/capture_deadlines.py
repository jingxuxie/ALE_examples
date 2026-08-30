import datetime
import hashlib
import json
from pathlib import Path
import time

from static_artifact import read_regular


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {"concept_2":"witness.json","concept_3":"design.json"}
ATTEMPTS = [(concept,attempt) for concept in ARTIFACTS for attempt in [3,4]]


def main():
    remaining = set(ATTEMPTS)
    cache = {}
    while remaining:
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        for identity in list(remaining):
            concept,attempt = identity
            basename = ROOT/concept/"attempts"/f"v_{attempt}"
            try:
                record = json.loads(basename.with_suffix(".run.json").read_text())
            except (OSError,json.JSONDecodeError):
                continue
            deadline = datetime.datetime.fromisoformat(record["started_utc"]).timestamp()+record["time_limit_seconds"]
            if record.get("status") == "finished" and not record.get("timed_out"):
                remaining.remove(identity)
                continue
            if now < deadline:
                artifact = basename/ARTIFACTS[concept]
                try:
                    payload,after = read_regular(artifact)
                    captured = datetime.datetime.now(datetime.timezone.utc).timestamp()
                    if captured <= deadline:
                        cache[identity] = (payload,captured,after.st_mtime)
                except (OSError,ValueError):
                    pass
                continue
            destination = basename.with_name(basename.name+"_deadline")
            destination.mkdir(exist_ok=True)
            payload,captured,modified = cache.get(identity,(None,None,None))
            if payload is not None:
                (destination/ARTIFACTS[concept]).write_bytes(payload)
            receipt = {"deadline_utc_timestamp":deadline,"captured_utc_timestamp":captured,
                       "artifact_mtime":modified,"artifact_present":payload is not None,
                       "sha256":hashlib.sha256(payload).hexdigest() if payload is not None else None,
                       "poll_interval_seconds":0.25,"quality_feedback_to_agent":False}
            (destination/"capture.json").write_text(json.dumps(receipt,indent=2)+"\n")
            print(json.dumps({"concept":concept,"attempt":attempt,**receipt}),flush=True)
            remaining.remove(identity)
        time.sleep(0.25)


if __name__ == "__main__":
    main()

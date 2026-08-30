import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import resource
import signal
import stat
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from hidden import exact


BYTE_LIMIT = 16384
SECONDS_LIMIT = 180
MEMORY_LIMIT = 2 * 1024 ** 3
TASK_ID = "pal_huse_spectral_center_falsification_g2_v1"


class ProtocolCommitmentError(RuntimeError):
    pass


def reject_constant(value):
    raise ValueError("nonfinite JSON constants are forbidden")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON keys are forbidden")
        result[key] = value
    return result


def load_witness(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("witness must be a regular file, not a directory, pipe, or device")
        if metadata.st_size > BYTE_LIMIT:
            raise ValueError("witness exceeds 16384 bytes")
        contents = source.read(BYTE_LIMIT + 1)
    if len(contents) > BYTE_LIMIT:
        raise ValueError("witness exceeds 16384 bytes")
    witness = json.loads(contents.decode("utf-8"), parse_constant=reject_constant,
                         object_pairs_hook=unique_object)
    exact.validate_witness(witness)
    return witness, hashlib.sha256(contents).hexdigest(), len(contents)


def timeout_handler(signum, frame):
    raise TimeoutError("evaluator exceeded 180 seconds")


def invalid_report(reason):
    return {"valid": False, "pass": False, "core": None, "worst_family": None,
            "worst_family_name": None, "reason": reason}


def evaluate(path):
    started = time.monotonic()
    cpu_started = time.process_time()
    counter = {"diagonalizations": 0}
    digest = None
    size = None
    protocol_bytes = b""
    protocol = {"task_id": TASK_ID}
    commitment_verified = False
    previous_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(SECONDS_LIMIT)
    try:
        try:
            protocol_bytes = (ROOT / "hidden" / "protocol.json").read_bytes()
            commitment = json.loads((ROOT / "hidden" / "commitment.json").read_text())
            actual = hashlib.sha256(protocol_bytes).hexdigest()
            if not hmac.compare_digest(actual, commitment["private_protocol_sha256"]):
                raise ProtocolCommitmentError("private protocol commitment mismatch")
            protocol = json.loads(protocol_bytes)
            exact.validate_protocol(protocol)
            if protocol["case_set"] != "private_replication":
                raise ProtocolCommitmentError("public calibration cannot be the grading bank")
            commitment_verified = True
        except ProtocolCommitmentError:
            protocol = {"task_id": TASK_ID}
            raise
        except Exception as error:
            protocol = {"task_id": TASK_ID}
            raise RuntimeError("trusted protocol unavailable") from error
        witness, digest, size = load_witness(path)
        report = exact.assess(witness, protocol, counter=counter)
    except (ValueError, TypeError, OverflowError, UnicodeError, RecursionError) as error:
        report = invalid_report("invalid_witness:" + str(error))
    except (TimeoutError, MemoryError) as error:
        report = invalid_report("resource_limit:" + type(error).__name__)
    except OSError as error:
        report = invalid_report("witness_io_error:" + str(error))
    except Exception as error:
        report = invalid_report("evaluator_error:" + type(error).__name__)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
    report["schema_version"] = 1
    report["task_id"] = protocol["task_id"]
    report["protocol_sha256"] = hashlib.sha256(protocol_bytes).hexdigest()
    report["protocol_commitment_verified"] = commitment_verified
    report["case_set"] = "private_replication"
    report["witness_sha256"] = digest
    actual_limit = resource.getrlimit(resource.RLIMIT_AS)[0]
    report["resource"] = {"wall_seconds": time.monotonic() - started,
                          "cpu_seconds": time.process_time() - cpu_started,
                          "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                          "diagonalizations": counter["diagonalizations"],
                          "witness_bytes": size, "byte_limit": BYTE_LIMIT,
                          "wall_limit_seconds": SECONDS_LIMIT, "address_space_limit_bytes": actual_limit,
                          "workers": 1, "blas_threads": 1}
    report["core_score"] = report["core"]
    report["worst_family_score"] = report["worst_family"]
    report["passed"] = report["pass"]
    report["evaluator_valid"] = not report["reason"].startswith("evaluator_error:")
    report["runtime_seconds"] = report["resource"]["wall_seconds"]
    within_limits = (report["runtime_seconds"] <= SECONDS_LIMIT
                     and counter["diagonalizations"] <= 129
                     and size is not None and size <= BYTE_LIMIT)
    report["resource_score"] = 1.0 if report["valid"] and within_limits else 0.0
    report.pop("members", None)
    return report


def main():
    parser = argparse.ArgumentParser(description="Evaluate static witness JSON; never execute participant code.")
    parser.add_argument("witness", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    current_soft, current_hard = resource.getrlimit(resource.RLIMIT_AS)
    limits = [MEMORY_LIMIT] + [value for value in (current_soft, current_hard) if value >= 0]
    resource.setrlimit(resource.RLIMIT_AS, (min(limits), current_hard))
    report = evaluate(arguments.witness)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output is not None:
        arguments.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()

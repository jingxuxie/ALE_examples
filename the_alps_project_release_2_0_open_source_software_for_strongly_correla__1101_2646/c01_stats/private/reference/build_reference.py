import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "upstream"
PIN = "fccd5403b08c4e5c450229714d28be5ca4a07229"


def main():
    source_names = ["batch", "covariance", "variance", "mean", "propagation", "galois", "util"]
    sources = [UPSTREAM / "alea" / "src" / (name + ".cpp") for name in source_names]
    includes = sorted(UPSTREAM.glob("*/include")) + [ROOT / "eigen"]
    command = ["g++", "-std=c++14", "-O1", "-DNDEBUG", "-DBOOST_BIND_GLOBAL_PLACEHOLDERS",
               "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections"]
    command += ["-I" + str(path) for path in includes]
    command += [str(ROOT / "oracle.cpp")] + [str(path) for path in sources]
    command += ["-o", str(ROOT / "alea_oracle")]
    with (ROOT / "build.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    provenance = {
        "repository": "https://github.com/ALPSCore/ALPSCore",
        "commit": PIN,
        "release": "v2.3.2",
        "source_archive_sha256": hashlib.sha256((ROOT / "ALPSCore-fccd540.tar.gz").read_bytes()).hexdigest(),
        "eigen_archive_sha256": hashlib.sha256((ROOT / "eigen-3.3.9.tar.gz").read_bytes()).hexdigest(),
        "upstream_sources": {str(path.relative_to(UPSTREAM)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sources},
        "command": command,
        "implementation": "Unmodified upstream batch_acc, batch_result, jackknife_prop, covariance; thin JSON/expression adapter.",
    }
    (ROOT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(ROOT / "alea_oracle")


if __name__ == "__main__":
    main()

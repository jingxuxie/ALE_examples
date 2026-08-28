import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def capture():
    reference = Path(__file__).resolve().parent
    sources = reference.parents[2] / "private/sources"
    repository = sources / "Juqst.jl"
    source = repository / "src/marginal.jl"
    correction = "08101ff532626926d40393bec771ebd09035c068"
    patch = subprocess.check_output(["git", "-C", str(repository), "show", correction, "--", "src/marginal.jl"], text=True)
    head = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    remote = subprocess.check_output(["git", "-C", str(repository), "remote", "get-url", "origin"], text=True).strip()
    (reference / "juqst_08101ff.patch").write_text(patch)
    manifest = {
        "primary_paper": {"id": "1907.13022v2", "url": "https://arxiv.org/abs/1907.13022v2",
                          "evidence": ["Methods, Gibbs Random Fields", "Figure 4, chains up to 100 qubits", "Supplement IV, Scalable Estimations"]},
        "adjacent_paper": {"id": "2303.00780v1", "url": "https://arxiv.org/abs/2303.00780v1",
                           "evidence": ["Appendix F, equations F1-F10", "Code and data availability statement"],
                           "code_or_data_obtained": False, "availability": "request-only; not an executable code oracle"},
        "juqst": {"remote": remote, "checkout": head, "file": "src/marginal.jl",
                  "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "cmi_fix": correction,
                  "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
                  "actual_change": "getSummand stride changes size(jpYZ)[1] to size(jpXZ)[1]",
                  "runtime_available": shutil.which("julia") is not None,
                  "use": "Python translation of fixed grouped CMI; independently checked by entropy/enumeration, not a Julia execution claim"},
        "authors_data": "All benchmark probabilities, factors and references are newly generated synthetic data",
    }
    pdf = sources / "1907.13022.pdf"
    if pdf.exists():
        manifest["primary_paper"]["local_pdf_sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    common = reference.parents[2] / "private/evaluation_sandbox.py"
    manifest["shared_sandbox_sha256"] = hashlib.sha256(common.read_bytes()).hexdigest()
    (reference / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    capture()

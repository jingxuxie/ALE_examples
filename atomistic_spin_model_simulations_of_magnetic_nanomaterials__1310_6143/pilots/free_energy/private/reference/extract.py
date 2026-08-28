import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT.parents[1] / "authoring" / "vampire"


def function_text(text, signature):
    start = text.index(signature)
    opening = text.index("{", start)
    depth = 1
    ending = opening + 1
    while depth:
        depth += (text[ending] == "{") - (text[ending] == "}")
        ending += 1
    return text[start:ending] + "\n"


def install(path, content):
    relative = str(path.relative_to(ROOT))
    patch = "*** Begin Patch\n*** Add File: " + relative + "\n"
    patch += "".join("+" + line + "\n" for line in content.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch", patch], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


records = {}
for original, signature, output in [
    ("src/montecarlo/cmc.cpp", "int cmc_step(){", "official_cmc.inc"),
    ("src/montecarlo/mc_moves.cpp", "void mc_angle(const std::vector<double>& old_spin", "official_angle.inc"),
]:
    raw = (SOURCE / original).read_bytes()
    extracted = function_text(raw.decode(), signature)
    install(ROOT / "private" / "reference" / output, extracted)
    records[original] = {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "extracted_sha256": hashlib.sha256(extracted.encode()).hexdigest(),
        "signature": signature,
        "first_line": raw.decode()[:raw.decode().index(signature)].count("\n") + 1,
        "destination": output,
        "transformation": "Unchanged function body and signature; namespace/dependency shims external.",
    }
for filename in ["BSD_licence", "license"]:
    install(ROOT / "private" / "reference" / ("VAMPIRE_" + filename), (SOURCE / filename).read_text())
records["commit"] = subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
records["repository"] = "https://github.com/richard-evans/vampire"
records["method"] = "https://arxiv.org/abs/1006.3507, algorithm III and Appendix A, Eq. A11"
(ROOT / "private" / "reference" / "provenance.json").write_text(json.dumps(records, indent=2) + "\n")

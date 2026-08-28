import base64
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "private" / "sources" / "supplement_audit"


def main():
    inventory = []
    for path in sorted((BASE / "target_ancillary").glob("*.vtl")):
        document = ElementTree.parse(path).getroot()
        content = base64.b64decode(document.attrib["vtcontent"], validate=True)
        archive_members = []
        if zipfile.is_zipfile(io.BytesIO(content)):
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                archive_members = archive.namelist()
                content = archive.read("vistrail")
        workflow = ElementTree.fromstring(content)
        modules = sorted({entry.get("name") for entry in workflow.iter("module") if entry.get("name")})
        annotations = sorted({entry.get("value") for entry in workflow.iter("annotation")
                              if entry.get("key") == "__desc__"})
        remote = sorted({value for entry in workflow.iter() for value in entry.attrib.values()
                         if re.match(r"https?://", value)})
        inventory.append({"file": path.name, "bytes": path.stat().st_size,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "format": "vtlink XML with base64-encoded vistrail provenance",
                          "embedded_zip_members": archive_members,
                          "workflow_version": workflow.get("version"), "modules": modules,
                          "annotations": annotations, "remote_inputs": remote,
                          "actions": len(list(workflow.iter("action"))), "executed": False})
    (BASE / "target_ancillary_inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    paper = (BASE / "alps20.tex").read_text()
    relevant = {str(number): line.strip() for number, line in enumerate(paper.splitlines(), 1)
                if "jackknife" in line and not line.startswith("%")}
    qualification = {
        "target_paper": "1101.2646", "source": "private/sources/supplement_audit/alps20.tex",
        "original_paper_already_includes_jackknife_and_cross_correlations": True,
        "evidence_lines": relevant,
        "consequence": "c01 is an authored deficient adapter with a participant-hidden later-library oracle, not evidence that jackknife or cross-correlation handling was absent from ALPS 2.0.",
        "ancillary_workflows": inventory,
        "execution_note": "Only XML/base64 was parsed. Embedded workflow code and remote database connections were not executed."}
    (BASE / "target_source_audit.json").write_text(json.dumps(qualification, indent=2) + "\n")
    ledger_path = ROOT / "private" / "source_ledger.json"
    ledger = json.loads(ledger_path.read_text())
    for entry in ledger:
        if entry.get("file") in {"paper.pdf", "ALPS_20110523_subset.tar"}:
            entry["file"] = "private/sources/" + entry["file"]
    alea_directory = ROOT / "c01_stats" / "private" / "reference"
    alea_provenance = json.loads((alea_directory / "provenance.json").read_text())
    assert all(hashlib.sha256((alea_directory / "upstream" / path).read_bytes()).hexdigest() == digest
               for path, digest in alea_provenance["upstream_sources"].items())
    ledger = [entry for entry in ledger if entry.get("repository") != "ALPSCore"]
    ledger.append({"repository": "ALPSCore", "source": alea_provenance["repository"],
                   "pin": alea_provenance["commit"], "release": alea_provenance["release"],
                   "source_archive_sha256": alea_provenance["source_archive_sha256"],
                   "unchanged_upstream_file_hashes_verified": True,
                   "provenance": "c01_stats/private/reference/provenance.json"})
    metadata = json.loads((BASE / "figshare_1092509.json").read_text())
    author_archive = BASE / "mps_author_examples.tar.gz"
    archive_metadata = metadata["files"][0]
    expected_md5 = archive_metadata["computed_md5"]
    actual_md5 = hashlib.md5(author_archive.read_bytes()).hexdigest()
    assert actual_md5 == expected_md5
    additions = [
        (BASE / "alps_paper_source.tar", {"source": "https://arxiv.org/src/1101.2646"}),
        (author_archive, {"source": archive_metadata["download_url"], "doi": metadata["doi"],
                          "license": metadata["license"], "md5_verified": actual_md5}),
        (ROOT / "research_mps" / "evidence" / "mps_source.tar", {"source": "https://arxiv.org/src/1407.0872"}),
    ]
    for path, attribution in additions:
        relative = str(path.relative_to(ROOT))
        entry = {"file": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                 "bytes": path.stat().st_size, **attribution}
        ledger = [existing for existing in ledger if existing.get("file") != relative]
        ledger.append(entry)
    assert all(hashlib.sha256((ROOT / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]
               for entry in ledger if "file" in entry)
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
    print(json.dumps({"ancillary_files": len(inventory), "archive_md5_verified": actual_md5,
                      "workflow_modules": {item["file"]: item["modules"] for item in inventory}}, indent=2))


if __name__ == "__main__":
    main()

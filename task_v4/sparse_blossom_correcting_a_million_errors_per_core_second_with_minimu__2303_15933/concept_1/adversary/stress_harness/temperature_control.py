import ctypes
import json
import subprocess
import time

from common import SIDE, write_json
import numpy as np
from models import load_model


def main():
    directory = SIDE / "temperature_controls"
    directory.mkdir(exist_ok=True)
    source = (SIDE / "native_diagnostics/decoder.cpp").read_text()
    source = source.replace("bool force_list = false;", "bool force_list = false;\n    std::array<int, 8> temperature_labels{};")
    source = source.replace("return label;", "temperature_labels.fill(label);\n                return label;", 1)
    anchor = "int chosen = std::max_element(masses.begin(), masses.end()) - masses.begin();"
    insertion = """
        const std::array<double, 8> temperatures{0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 10.0};
        for (int control = 0; control < 8; control++) {
            std::array<double, 16> values{};
            for (auto& entry : candidates) values[entry.second.first] += std::exp(temperatures[control] * (best - entry.second.second));
            temperature_labels[control] = std::max_element(values.begin(), values.end()) - values.begin();
        }
    """
    if source.count(anchor) != 1 or "std::array<int, 8> temperature_labels" not in source:
        raise ValueError("Instrumentation anchor changed")
    source = source.replace(anchor, anchor + insertion)
    source += """
extern "C" void run_temperatures(void* handle, int shots, const uint8_t* syndromes, uint8_t* output, int ensemble) {
    auto& decoder = *static_cast<Decoder*>(handle);
    for (int shot = 0; shot < shots; shot++) {
        decoder.decode(syndromes + shot * decoder.detectors, 40, 40, ensemble);
        for (int control = 0; control < 8; control++) output[shot * 8 + control] = decoder.temperature_labels[control];
    }
}
"""
    if (directory / "decoder.cpp").exists():
        raise ValueError("Temperature control already exists")
    patch = "*** Begin Patch\n*** Add File: " + str(directory / "decoder.cpp") + "\n" + "".join("+" + line + "\n" for line in source.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)
    subprocess.run(["/usr/bin/g++", "-O3", "-std=c++17", "-fPIC", "-march=native", "-shared", str(directory / "decoder.cpp"), "-o", str(directory / "decoder.so")], check=True)
    library = ctypes.CDLL(str(directory / "decoder.so"))
    library.create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    library.create.restype = ctypes.c_void_p
    library.destroy.argtypes = [ctypes.c_void_p]
    library.run_temperatures.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    suite = SIDE / "corpora/ratchet2_confirm_128"
    records = []
    for spec in json.loads((SIDE / "ratchet2_selected.json").read_text())["specs"]:
        case_id = spec["case_id"]
        model = load_model(suite / "models" / case_id)
        matrix = np.ascontiguousarray(model["detector_matrix"], dtype=np.uint8)
        logical = np.ascontiguousarray(model["observable_matrix"], dtype=np.uint8)
        probabilities = np.ascontiguousarray(model["probabilities"], dtype=np.float64)
        with np.load(suite / "private" / (case_id + ".npz"), allow_pickle=False) as data:
            syndromes = np.ascontiguousarray(data["syndromes"])
            labels = data["labels"] @ (1 << np.arange(4))
        with np.load(SIDE / "private_sweeps/ratchet2_confirm_champion_128" / (case_id + "__champion.npz"), allow_pickle=False) as data:
            expected = data["predictions"] @ (1 << np.arange(4))
        output = np.zeros((len(syndromes), 8), dtype=np.uint8)
        started = time.process_time()
        handle = library.create(*matrix.shape, matrix.ctypes.data, logical.ctypes.data, probabilities.ctypes.data)
        try:
            library.run_temperatures(handle, len(syndromes), syndromes.ctypes.data, output.ctypes.data, 2 if model["rounds"] > 1 else 8)
        finally:
            library.destroy(handle)
        elapsed = time.process_time() - started
        np.testing.assert_array_equal(output[:, 3], expected)
        record = dict(case_id=case_id, shots=len(syndromes), failures=(output != labels[:, None]).sum(axis=0).tolist(),
            temperatures=[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2, 10], cpu_seconds=elapsed, baseline_equal=True)
        np.savez_compressed(directory / (case_id + ".npz"), predictions=output)
        records.append(record)
        write_json(directory / "report.json", dict(complete=False, records=records))
        print(json.dumps(record), flush=True)
    write_json(directory / "report.json", dict(complete=True, records=records, exploratory=True, official_score=False,
        caveat="Temperature is a cheap reranking knob; this deliberately checks for an obvious baseline weakness, not a new solution."))


if __name__ == "__main__":
    main()

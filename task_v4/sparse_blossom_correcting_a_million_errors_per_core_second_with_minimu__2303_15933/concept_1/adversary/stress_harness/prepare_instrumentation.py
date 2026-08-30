import subprocess

from common import SIDE, digest_file, write_json


def main():
    source_path = SIDE / "snapshots/confirmed_generation_1/code/decoder.cpp"
    source = source_path.read_text()

    def replace_once(before, after):
        nonlocal source
        if source.count(before) != 1:
            raise ValueError("Unexpected champion source layout")
        source = source.replace(before, after, 1)

    replace_once("    int detectors, variables, words;", """    int detectors, variables, words;
    bool force_list = false;
    int diagnostic_fast = 0;
    double diagnostic_gap = -1;
    double diagnostic_candidates = 0;
    double diagnostic_best = 0;
    double diagnostic_margin = 0;""")
    replace_once("    int decode(const uint8_t* syndrome, int iterations, int order, int ensemble) {", """    int decode(const uint8_t* syndrome, int iterations, int order, int ensemble) {
        diagnostic_fast = 0;
        diagnostic_gap = -1;
        diagnostic_candidates = 0;
        diagnostic_best = 0;
        diagnostic_margin = 0;""")
    replace_once("            if (valid && trial == 0) {", """            if (valid && trial == 0 && !force_list) {
                diagnostic_fast = 1;
                diagnostic_margin = 1e30;
                for (int variable = 0; variable < variables; variable++) {
                    diagnostic_margin = std::min(diagnostic_margin, double(std::abs(posterior[variable])));
                    if (hard[variable]) diagnostic_best += prior[variable];
                }""")
    replace_once("        return std::max_element(masses.begin(), masses.end()) - masses.begin();", """        int chosen = std::max_element(masses.begin(), masses.end()) - masses.begin();
        double runner_up = 0;
        for (int label = 0; label < 16; label++) if (label != chosen) runner_up = std::max(runner_up, masses[label]);
        diagnostic_gap = std::min(100.0, std::log((masses[chosen] + 1e-300) / (runner_up + 1e-300)));
        diagnostic_candidates = candidates.size();
        diagnostic_best = best;
        return chosen;""")
    if not source.endswith("}\n"):
        raise ValueError("Unexpected source terminator")
    source = source[:-2] + """
void run_diagnostics(void* handle, int shots, const uint8_t* syndromes, uint8_t* output, double* diagnostics,
                     int iterations, int order, int ensemble, int force_list) {
    auto& decoder = *static_cast<Decoder*>(handle);
    decoder.force_list = force_list != 0;
    for (int shot = 0; shot < shots; shot++) {
        int label = decoder.decode(syndromes + shot * decoder.detectors, iterations, order, ensemble);
        for (int bit = 0; bit < 4; bit++) output[shot * 4 + bit] = (label >> bit) & 1;
        diagnostics[shot * 5] = decoder.diagnostic_fast;
        diagnostics[shot * 5 + 1] = decoder.diagnostic_gap;
        diagnostics[shot * 5 + 2] = decoder.diagnostic_candidates;
        diagnostics[shot * 5 + 3] = decoder.diagnostic_best;
        diagnostics[shot * 5 + 4] = decoder.diagnostic_margin;
    }
}
}
"""
    destination = SIDE / "native_diagnostics/decoder.cpp"
    destination.parent.mkdir(parents=True, exist_ok=True)
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n" + "".join("+" + line + "\n" for line in source.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)
    subprocess.run(["/usr/bin/g++", "-O3", "-std=c++17", "-fPIC", "-shared", str(destination), "-o", str(destination.with_suffix(".so"))], check=True)
    subprocess.run(["/usr/bin/g++", "-O3", "-march=native", "-std=c++17", "-fPIC", "-shared", str(destination), "-o", str(destination.with_name("decoder_native.so"))], check=True)
    write_json(SIDE / "native_diagnostics/provenance.json", dict(source_sha256=digest_file(source_path),
               instrumentation="Private per-shot fast-path/list-gap/count/cost/margin observations, with optional forced-list control",
               prediction_equivalence="Must be checked empirically against original compiled champion before interpretation",
               public_baseline_changed=False))


if __name__ == "__main__":
    main()

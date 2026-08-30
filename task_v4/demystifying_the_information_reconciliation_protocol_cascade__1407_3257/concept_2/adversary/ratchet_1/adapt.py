import difflib
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT.parents[1] / "champions/generation_1/submission"


def substitute(source, before, after, count=1):
    observed = source.count(before)
    if observed != count:
        raise ValueError(f"expected {count} occurrences, found {observed}: {before!r}")
    return source.replace(before, after)


def adapt_sources():
    output = ROOT / "sources"
    output.mkdir(exist_ok=True)
    metadata = {}
    for name in ("bp_search", "group_search"):
        original = (ARCHIVE / f"{name}.cpp").read_text()
        source = substitute(original, "constexpr int length = 2048;\nconstexpr int checks = 384;", '#include "geometry.hpp"')
        source = substitute(source, "std::array<uint64_t, 6>", "std::array<uint64_t, syndrome_words>")
        source = substitute(source, "word < 6", "word < syndrome_words")
        if name == "bp_search":
            source = substitute(source, "std::array<std::array<int, 32>, checks> members;", "std::array<std::array<int, max_block_size>, checks> members;\nstd::array<int, checks> check_sizes{};")
            source = substitute(source, "selected.size() >= 379", "selected.size() >= matrix_rank")
            source = substitute(source, "std::array<float, length * 6>", "std::array<float, checks * max_block_size>", 2)
            source = substitute(source, "index < 32", "index < check_sizes[check]", 2)
            source = substitute(source, "check * 32", "check * max_block_size", 3)
            source = substitute(source, '    std::ifstream input("blocks.txt");', '    if (argc > 2) generator.seed(std::stoul(argv[2]));\n    std::ifstream input("blocks.txt");')
            source = substitute(source, "pass * 64 + group", "check_offsets[pass] + group")
            source = substitute(source, "    std::vector<std::pair<int, std::vector<int>>> impulses;", "    check_sizes = counts;\n    std::vector<std::pair<int, std::vector<int>>> impulses;")
            source = substitute(source, "    auto start = std::chrono::steady_clock::now();", '    std::cout << "CONFIG n " << length << " checks " << checks << " rank " << matrix_rank << " impulses " << impulses.size() << std::endl;\n    auto start = std::chrono::steady_clock::now();')
            source = substitute(source, "if (++trial % 100 == 0)", "if (++trial % 10 == 0)")
            source = substitute(source, "            if (elapsed > seconds) return 0;", '            if (elapsed > seconds) {\n                std::cout << "END trials " << trial << " elapsed " << elapsed << std::endl;\n                return 0;\n            }')
        else:
            source = substitute(source, "constexpr int words = length / 64;", "constexpr int words = (length + 63) / 64;")
            source = substitute(source, "std::array<std::array<int, 32>, 64> groups;", "std::vector<std::vector<int>> groups;")
            source = substitute(source, "int best = 20;", "#ifndef INITIAL_BEST\n#define INITIAL_BEST 20\n#endif\nint best = INITIAL_BEST;")
            source = substitute(source, "    std::array<int, 64> counts{};", "    groups.resize(group_counts[grouping_pass]);")
            source = substitute(source, "64 * pass + group", "check_offsets[pass] + group")
            source = substitute(source, "groups[group][counts[group]++] = position;", "groups[group].push_back(position);")
            source = substitute(source, "std::array<int, 64> group_order;", "std::vector<int> group_order(groups.size());")
            source = substitute(source, "        std::shuffle(order.begin() + chosen_groups * 32, order.end(), generator);", "        int retained_positions = 0;\n        for (int group_index = 0; group_index < chosen_groups; ++group_index) retained_positions += groups[group_order[group_index]].size();\n        std::shuffle(order.begin() + retained_positions, order.end(), generator);")
            source = substitute(source, "rank == 379", "rank == matrix_rank")
            source = substitute(source, "group < 64", "group < int(groups.size())")
            source = substitute(source, "first_index < 32", "first_index < int(groups[group].size())")
            source = substitute(source, "    auto start = std::chrono::steady_clock::now();", '    if (chosen_groups < 0 || chosen_groups > int(groups.size())) return 2;\n    std::cout << "CONFIG n " << length << " checks " << checks << " rank " << matrix_rank << " pass " << grouping_pass << " groups " << chosen_groups << " initial_best " << best << std::endl;\n    auto start = std::chrono::steady_clock::now();')
            source = substitute(source, "if (trial % 100 == 0)", "if (trial % 10 == 0)")
            source = substitute(source, "        if (elapsed > seconds) return 0;", '        if (elapsed > seconds) {\n            std::cout << "END trials " << trial + 1 << " elapsed " << elapsed << std::endl;\n            return 0;\n        }')
        (output / f"{name}.cpp").write_text(source)
        (output / f"{name}.patch").write_text("".join(difflib.unified_diff(original.splitlines(True), source.splitlines(True), fromfile=f"archived/{name}.cpp", tofile=f"adapted/{name}.cpp")))
        metadata[name] = {
            "archived_sha256": hashlib.sha256(original.encode()).hexdigest(),
            "adapted_sha256": hashlib.sha256(source.encode()).hexdigest(),
        }
    original = (ARCHIVE / "sat_search.py").read_text()
    source = substitute(original, "output = Path(__file__).resolve().parent", "output = Path.cwd()")
    source = substitute(source, "Path('/tmp/cascade-c2-v1-lrzw9x7v/participant/input/deployment.json')", "Path('deployment.json')")
    source = substitute(source, "import time", "import time\nimport re")
    source = substitute(source, "set_config(config, b'timeout', str(arguments.seconds * 1000).encode())", "set_config(config, b'timeout', str(arguments.seconds * 1000).encode())\nset_global = api('Z3_global_param_set', None, ctypes.c_char_p, ctypes.c_char_p)\nset_global(b'sat.random_seed', str(arguments.seed).encode())")
    source = substitute(source, "    print(text, flush=True)", "    print(text, flush=True)\n    support = sorted(int(position) for position in re.findall(r'x(\\d+)\\s*->\\s*true', text))\n    (output / 'sat_core.json').write_text(json.dumps({'errors': support}) + '\\n')")
    (output / "sat_search.py").write_text(source)
    (output / "sat_search.patch").write_text("".join(difflib.unified_diff(original.splitlines(True), source.splitlines(True), fromfile="archived/sat_search.py", tofile="adapted/sat_search.py")))
    metadata["sat_search"] = {"archived_sha256": hashlib.sha256(original.encode()).hexdigest(), "adapted_sha256": hashlib.sha256(source.encode()).hexdigest()}
    (ROOT / "adaptations.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    adapt_sources()

import subprocess

from common import SIDE, write_json


def main():
    source = (SIDE / "native_diagnostics/decoder.cpp").read_text()
    source = source.replace("    double diagnostic_margin = 0;", """    double diagnostic_margin = 0;
    vector<std::array<int, 3>> marginal_triplets;
    vector<std::array<float, 4>> marginal_costs;
    vector<int> marginal_alias_first, marginal_alias_second;""", 1)
    source = source.replace("            hashes[var] = hash ^ (hash >> 31);", """            hashes[var] = hash ^ (hash >> 31);
            if (!marginal_alias_first.empty() && marginal_alias_first[var] >= 0) {
                hashes[var] = hashes[marginal_alias_first[var]] ^ hashes[marginal_alias_second[var]];
            }""", 1)
    before = """        auto insert = [&](uint64_t hash, int label, float score) {
            candidates.emplace(hash, std::make_pair(label, score));
        };"""
    after = """        auto insert = [&](uint64_t hash, int label, float score, const vector<int>* first = nullptr, const vector<int>* second = nullptr) {
            if (first) for (int variable : *first) base[variable] ^= 1;
            if (second) for (int variable : *second) base[variable] ^= 1;
            float adjusted = score;
            for (int group = 0; group < int(marginal_triplets.size()); group++) {
                const auto& indices = marginal_triplets[group];
                int physical = (base[indices[0]] ^ base[indices[2]]) | ((base[indices[1]] ^ base[indices[2]]) << 1);
                adjusted += marginal_costs[group][physical];
                for (int variable : indices) if (base[variable]) adjusted -= prior[variable];
            }
            if (first) for (int variable : *first) base[variable] ^= 1;
            if (second) for (int variable : *second) base[variable] ^= 1;
            candidates.emplace(hash, std::make_pair(label, adjusted));
        };"""
    if source.count(before) != 1:
        raise ValueError("Unexpected insertion function")
    source = source.replace(before, after, 1)
    source = source.replace("insert(base_hash ^ hash, base_logical ^ label, base_score + score);",
                            "insert(base_hash ^ hash, base_logical ^ label, base_score + score, &flip);")
    source = source.replace("insert(base_hash ^ fliphashes[left] ^ fliphashes[right], base_logical ^ fliplabels[left] ^ fliplabels[right], score);",
                            "insert(base_hash ^ fliphashes[left] ^ fliphashes[right], base_logical ^ fliplabels[left] ^ fliplabels[right], score, &flips[left], &flips[right]);")
    source = source.replace("insert(base_hash ^ fliphashes[index], base_logical ^ fliplabels[index], base_score + score);",
                            "insert(base_hash ^ fliphashes[index], base_logical ^ fliplabels[index], base_score + score, &flips[index]);")
    source = source[:-2] + """
void set_triplets(void* handle, int groups, const int* triplets) {
    auto& decoder = *static_cast<Decoder*>(handle);
    decoder.marginal_triplets.clear();
    decoder.marginal_costs.clear();
    decoder.marginal_alias_first.assign(decoder.variables, -1);
    decoder.marginal_alias_second.assign(decoder.variables, -1);
    for (int group = 0; group < groups; group++) {
        int first = triplets[group * 3], second = triplets[group * 3 + 1], third = triplets[group * 3 + 2];
        double prob_x = 1 / (1 + std::exp(double(decoder.prior[first])));
        double prob_z = 1 / (1 + std::exp(double(decoder.prior[second])));
        double prob_y = 1 / (1 + std::exp(double(decoder.prior[third])));
        std::array<double, 4> probabilities{};
        probabilities[0] = (1 - prob_x) * (1 - prob_z) * (1 - prob_y) + prob_x * prob_z * prob_y;
        probabilities[1] = prob_x * (1 - prob_z) * (1 - prob_y) + (1 - prob_x) * prob_z * prob_y;
        probabilities[2] = (1 - prob_x) * prob_z * (1 - prob_y) + prob_x * (1 - prob_z) * prob_y;
        probabilities[3] = prob_x * prob_z * (1 - prob_y) + (1 - prob_x) * (1 - prob_z) * prob_y;
        std::array<float, 4> costs{};
        for (int state = 0; state < 4; state++) costs[state] = -std::log(probabilities[state] / probabilities[0]);
        decoder.marginal_triplets.push_back({first, second, third});
        decoder.marginal_costs.push_back(costs);
        decoder.marginal_alias_first[third] = first;
        decoder.marginal_alias_second[third] = second;
    }
}
}
"""
    destination = SIDE / "marginal_portfolio/decoder.cpp"
    destination.parent.mkdir(parents=True, exist_ok=True)
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n" + "".join("+" + line + "\n" for line in source.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)
    subprocess.run(["/usr/bin/g++", "-O3", "-march=native", "-std=c++17", "-fPIC", "-shared", str(destination), "-o", str(destination.with_suffix(".so"))], check=True)
    write_json(SIDE / "marginal_portfolio/method.json", dict(method="Partial exact marginalization of disjoint X/Z/Y mechanism-gauge fibers before logical-class list summation",
               proposal="Original champion BP/OSD proposals, with gauge-invariant configuration hashing and four-state local factor weights",
               caveat="Exploratory structural portfolio, not exact logical Bayes or a claimed passing solution; local probabilities inherit native float-logit precision"))


if __name__ == "__main__":
    main()

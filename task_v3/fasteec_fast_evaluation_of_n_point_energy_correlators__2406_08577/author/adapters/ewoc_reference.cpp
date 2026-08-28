#include <fastjet/ClusterSequence.hh>

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::size_t max_events = 100000;
constexpr std::size_t max_bins = 65536;
constexpr std::size_t max_rows_per_jet = 4096;
constexpr std::size_t max_rows = 10000000;
constexpr std::size_t max_lines = 20000000;
constexpr std::uint64_t max_ordered_terms = 50000000;
const double pi = std::acos(-1.0);

struct Options {
    std::string events_file;
    std::size_t nevents;
    bool proton_collision;
    std::string algorithm;
    double radius;
    bool mass;
    double kappa;
    double log_min;
    std::size_t bins;
    std::string output_file;
};

std::uint64_t unsigned_value(const std::string& text, const std::string& name) {
    std::uint64_t value = 0;
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), value);
    if (text.empty() || parsed.ec != std::errc() ||
        parsed.ptr != text.data() + text.size()) {
        throw std::invalid_argument(name + " must be an unsigned decimal integer");
    }
    return value;
}

double real_value(const std::string& text, const std::string& name) {
    std::size_t consumed = 0;
    double value = 0.0;
    try {
        value = std::stod(text, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument(name + " must be a finite double");
    }
    if (consumed != text.size() || !std::isfinite(value)) {
        throw std::invalid_argument(name + " must be a finite double");
    }
    return value;
}

Options parse_options(int argc, char* argv[]) {
    if (argc != 11) {
        throw std::invalid_argument(
            "usage: ewoc_reference events_file nevents geometry algorithm radius "
            "observable kappa log_min bins output_file");
    }
    const auto nevents = unsigned_value(argv[2], "nevents");
    const auto bins = unsigned_value(argv[9], "bins");
    const std::string geometry = argv[3];
    const std::string algorithm = argv[4];
    const std::string observable = argv[6];
    if (nevents == 0 || nevents > max_events) {
        throw std::invalid_argument("nevents must be in [1, 100000]");
    }
    if (bins < 3 || bins > max_bins) {
        throw std::invalid_argument("bins must be in [3, 65536], including both flow bins");
    }
    if (geometry != "pp" && geometry != "ee") {
        throw std::invalid_argument("geometry must be pp or ee");
    }
    if (algorithm != "ca" && algorithm != "kt" && algorithm != "antikt") {
        throw std::invalid_argument("algorithm must be ca, kt, or antikt");
    }
    if (observable != "mass" && observable != "angular") {
        throw std::invalid_argument("observable must be mass or angular");
    }
    Options options{argv[1], static_cast<std::size_t>(nevents), geometry == "pp",
                    algorithm, real_value(argv[5], "radius"), observable == "mass",
                    real_value(argv[7], "kappa"), real_value(argv[8], "log_min"),
                    static_cast<std::size_t>(bins), argv[10]};
    if (options.radius < 1e-6 || options.radius > pi) {
        throw std::invalid_argument("radius must be in [1e-6, pi]");
    }
    if (options.kappa <= 0.0 || options.kappa > 8.0) {
        throw std::invalid_argument("kappa must be in (0, 8]");
    }
    const double log_max = options.mass ? 4.0 : std::log10(pi);
    if (options.log_min < -12.0 || options.log_min >= log_max) {
        throw std::invalid_argument("log_min must be >= -12 and below the fixed log_max");
    }
    std::error_code filesystem_error;
    if (options.events_file == options.output_file ||
        std::filesystem::equivalent(options.events_file, options.output_file,
                                    filesystem_error)) {
        throw std::invalid_argument("input and output must be different files");
    }
    return options;
}

fastjet::JetDefinition subjet_definition(const Options& options) {
    if (!options.proton_collision) {
        const double power = options.algorithm == "kt" ? 1.0 :
                             options.algorithm == "antikt" ? -1.0 : 0.0;
        return fastjet::JetDefinition(fastjet::ee_genkt_algorithm, options.radius,
                                      power, fastjet::E_scheme);
    }
    const auto algorithm = options.algorithm == "kt" ? fastjet::kt_algorithm :
                           options.algorithm == "antikt" ? fastjet::antikt_algorithm :
                           fastjet::cambridge_algorithm;
    return fastjet::JetDefinition(algorithm, options.radius, fastjet::E_scheme);
}

std::vector<double> finite_edges(const Options& options) {
    const double log_max = options.mass ? 4.0 : std::log10(pi);
    std::vector<double> edges(options.bins - 1);
    for (std::size_t edge = 0; edge < edges.size(); ++edge) {
        edges[edge] = std::pow(10.0, options.log_min +
            (log_max - options.log_min) * static_cast<double>(edge) /
            static_cast<double>(options.bins - 2));
    }
    edges.back() = options.mass ? 10000.0 : pi;
    for (std::size_t edge = 1; edge < edges.size(); ++edge) {
        if (!(edges[edge] > edges[edge - 1])) {
            throw std::invalid_argument("finite histogram edges must be distinct doubles");
        }
    }
    return edges;
}

double physical_mass(const fastjet::PseudoJet& momentum) {
    const double mass_squared = momentum.m2();
    const double tolerance = 64.0 * std::numeric_limits<double>::epsilon() *
                             momentum.e() * momentum.e();
    if (!std::isfinite(mass_squared) || mass_squared < -tolerance) {
        throw std::runtime_error("non-finite or materially spacelike subjet momentum");
    }
    return std::sqrt(std::max(0.0, mass_squared));
}

double opening_angle(const fastjet::PseudoJet& first,
                     const fastjet::PseudoJet& second) {
    const double norm = std::sqrt(first.modp2()) * std::sqrt(second.modp2());
    if (!(norm > 0.0) || !std::isfinite(norm)) {
        throw std::runtime_error("ee angular requires nonzero spatial subjet momenta");
    }
    const double cosine = (first.px() * second.px() + first.py() * second.py() +
                           first.pz() * second.pz()) / norm;
    return std::acos(std::clamp(cosine, -1.0, 1.0));
}

void accumulate_jet(const std::vector<fastjet::PseudoJet>& particles,
                    const Options& options, const fastjet::JetDefinition& definition,
                    const std::vector<double>& edges, std::vector<double>& histogram,
                    std::uint64_t& ordered_terms) {
    double total_weight = 0.0;
    for (const auto& particle : particles) {
        total_weight += options.proton_collision ? particle.pt() : particle.e();
    }
    if (!(total_weight > 0.0) || !std::isfinite(total_weight)) {
        throw std::runtime_error("each supplied jet must have positive finite scalar weight");
    }
    const fastjet::ClusterSequence sequence(particles, definition);
    const auto subjets = options.proton_collision ?
        fastjet::sorted_by_pt(sequence.inclusive_jets(0.0)) :
        fastjet::sorted_by_E(sequence.inclusive_jets(0.0));
    const std::uint64_t subjet_count = subjets.size();
    const std::uint64_t terms = subjet_count * subjet_count;
    if (subjets.empty() || terms > max_ordered_terms - ordered_terms) {
        throw std::runtime_error("empty clustering or 50000000 ordered-term limit exceeded");
    }
    ordered_terms += terms;
    std::vector<double> fractions;
    fractions.reserve(subjets.size());
    for (const auto& subjet : subjets) {
        if (!options.proton_collision && !options.mass && !(subjet.modp2() > 0.0)) {
            throw std::runtime_error("ee angular requires nonzero spatial subjet momenta");
        }
        fractions.push_back((options.proton_collision ? subjet.pt() : subjet.e()) /
                             total_weight);
    }
    for (std::size_t first = 0; first < subjets.size(); ++first) {
        for (std::size_t second = first; second < subjets.size(); ++second) {
            const bool contact = first == second;
            const double weight = (contact ? 1.0 : 2.0) *
                std::pow(fractions[first] * fractions[second], options.kappa);
            if (weight == 0.0) {
                continue;
            }
            double value = 0.0;
            if (options.mass) {
                value = physical_mass(contact ? subjets[first] :
                                               subjets[first] + subjets[second]);
            } else if (!contact) {
                value = options.proton_collision ? subjets[first].delta_R(subjets[second]) :
                                                   opening_angle(subjets[first], subjets[second]);
            }
            if (!std::isfinite(value) || value < 0.0 || !std::isfinite(weight)) {
                throw std::runtime_error("non-finite EWOC contribution");
            }
            const auto bin = static_cast<std::size_t>(
                std::upper_bound(edges.begin(), edges.end(), value) - edges.begin());
            histogram[bin] += weight;
        }
    }
}

std::vector<double> evaluate(const Options& options) {
    const auto definition = subjet_definition(options);
    const auto edges = finite_edges(options);
    std::vector<double> histogram(options.bins, 0.0);
    std::ifstream input(options.events_file);
    input.imbue(std::locale::classic());
    if (!input) {
        throw std::runtime_error("cannot open events_file");
    }
    std::vector<fastjet::PseudoJet> particles;
    std::uint64_t event_id = 0;
    std::uint64_t ordered_terms = 0;
    std::size_t processed = 0;
    std::size_t jet_rows = 0;
    std::size_t total_rows = 0;
    std::size_t line_number = 0;
    bool have_event = false;
    std::array<char, 4097> buffer{};
    while (input.getline(buffer.data(), static_cast<std::streamsize>(buffer.size()))) {
        if (++line_number > max_lines) {
            throw std::runtime_error("20000000 input-line limit exceeded");
        }
        const auto line_size = static_cast<std::size_t>(input.gcount()) -
                               (input.eof() ? 0U : 1U);
        const std::string line(buffer.data(), line_size);
        if (line.find('\0') != std::string::npos) {
            throw std::runtime_error("NUL byte in input on line " + std::to_string(line_number));
        }
        std::istringstream row(line);
        row.imbue(std::locale::classic());
        std::string id_text;
        if (!(row >> id_text) || id_text.front() == '#') {
            continue;
        }
        std::string pt_text, rapidity_text, phi_text, extra;
        if (!(row >> pt_text >> rapidity_text >> phi_text) || (row >> extra)) {
            throw std::runtime_error("expected event_id pt rapidity phi on line " +
                                     std::to_string(line_number));
        }
        const auto next_id = unsigned_value(id_text, "event_id");
        const double pt = real_value(pt_text, "pt");
        const double rapidity = real_value(rapidity_text, "rapidity");
        const double phi = real_value(phi_text, "phi");
        if (pt < 0.0 || pt > 1e9 || (pt > 0.0 && pt < 1e-12) ||
            std::abs(rapidity) > 10.0) {
            throw std::runtime_error("row outside bounded pt/rapidity domain on line " +
                                     std::to_string(line_number));
        }
        if (have_event && next_id != event_id) {
            if (next_id < event_id) {
                throw std::runtime_error("event IDs must increase between jet blocks");
            }
            accumulate_jet(particles, options, definition, edges, histogram, ordered_terms);
            if (++processed == options.nevents) {
                break;
            }
            particles.clear();
            jet_rows = 0;
        }
        have_event = true;
        event_id = next_id;
        if (++jet_rows > max_rows_per_jet || ++total_rows > max_rows) {
            throw std::runtime_error("4096 rows per jet or 10000000 total-row limit exceeded");
        }
        if (pt == 0.0) {
            continue;
        }
        const double azimuth = std::remainder(phi, 2.0 * pi);
        const double px = pt * std::cos(azimuth);
        const double py = pt * std::sin(azimuth);
        const double pz = pt * std::sinh(rapidity);
        const double energy = std::sqrt(px * px + py * py + pz * pz);
        particles.emplace_back(px, py, pz, energy);
    }
    if (input.bad() || (input.fail() && !input.eof())) {
        throw std::runtime_error("input read failure or line longer than 4096 bytes");
    }
    if (processed < options.nevents && have_event) {
        accumulate_jet(particles, options, definition, edges, histogram, ordered_terms);
        ++processed;
    }
    if (processed != options.nevents) {
        throw std::runtime_error("events_file contains fewer than nevents complete jets");
    }
    for (auto& value : histogram) {
        value /= static_cast<double>(processed);
    }
    return histogram;
}

}

int main(int argc, char* argv[]) {
    try {
        const auto options = parse_options(argc, argv);
        fastjet::ClusterSequence::set_fastjet_banner_stream(nullptr);
        const auto histogram = evaluate(options);
        std::ofstream output(options.output_file);
        output.imbue(std::locale::classic());
        if (!output) {
            throw std::runtime_error("cannot open output_file");
        }
        output << std::scientific << std::setprecision(std::numeric_limits<double>::max_digits10);
        for (std::size_t bin = 0; bin < histogram.size(); ++bin) {
            if (bin != 0) {
                output << ' ';
            }
            output << histogram[bin];
        }
        output << '\n';
        output.close();
        if (!output) {
            throw std::runtime_error("cannot finish writing output_file");
        }
        return 0;
    } catch (const fastjet::Error& error) {
        std::cerr << "ewoc_reference: FastJet: " << error.message() << '\n';
    } catch (const std::exception& error) {
        std::cerr << "ewoc_reference: " << error.what() << '\n';
    }
    return 1;
}

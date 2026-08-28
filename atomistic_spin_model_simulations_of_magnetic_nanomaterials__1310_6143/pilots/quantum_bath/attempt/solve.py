#!/usr/bin/env python3
"""Deterministic finite-memory thermal spin dynamics.

The native kernel is embedded so this file is a complete submission.  Its
temporary build and, when necessary, the noise backing file live beside the
requested output, never in the submission or the participant workspace.
"""

import os

for _variable in (
    "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_variable] = "1"

import ctypes
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np


NATIVE_SOURCE = r"""
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <exception>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

constexpr double tableau[15][12] = {
    {},
    {5.26001519587677318785587544488e-2},
    {1.97250569845378994544595329183e-2, 5.91751709536136983633785987549e-2},
    {2.95875854768068491816892993775e-2, 0, 8.87627564304205475450678981324e-2},
    {2.41365134159266685502369798665e-1, 0, -8.84549479328286085344864962717e-1, 9.24834003261792003115737966543e-1},
    {3.7037037037037037037037037037e-2, 0, 0, 1.70828608729473871279604482173e-1, 1.25467687566822425016691814123e-1},
    {3.7109375e-2, 0, 0, 1.70252211019544039314978060272e-1, 6.02165389804559606850219397283e-2, -1.7578125e-2},
    {3.70920001185047927108779319836e-2, 0, 0, 1.70383925712239993810214054705e-1, 1.07262030446373284651809199168e-1, -1.53194377486244017527936158236e-2, 8.27378916381402288758473766002e-3},
    {6.24110958716075717114429577812e-1, 0, 0, -3.36089262944694129406857109825, -8.68219346841726006818189891453e-1, 2.75920996994467083049415600797e1, 2.01540675504778934086186788979e1, -4.34898841810699588477366255144e1},
    {4.77662536438264365890433908527e-1, 0, 0, -2.48811461997166764192642586468, -5.90290826836842996371446475743e-1, 2.12300514481811942347288949897e1, 1.52792336328824235832596922938e1, -3.32882109689848629194453265587e1, -2.03312017085086261358222928593e-2},
    {-9.3714243008598732571704021658e-1, 0, 0, 5.18637242884406370830023853209, 1.09143734899672957818500254654, -8.14978701074692612513997267357, -1.85200656599969598641566180701e1, 2.27394870993505042818970056734e1, 2.49360555267965238987089396762, -3.0467644718982195003823669022},
    {2.27331014751653820792359768449, 0, 0, -1.05344954667372501984066689879e1, -2.00087205822486249909675718444, -1.79589318631187989172765950534e1, 2.79488845294199600508499808837e1, -2.85899827713502369474065508674, -8.87285693353062954433549289258, 1.23605671757943030647266201528e1, 6.43392746015763530355970484046e-1},
    {5.42937341165687622380535766363e-2, 0, 0, 0, 0, 4.45031289275240888144113950566, 1.89151789931450038304281599044, -5.8012039600105847814672114227, 3.1116436695781989440891606237e-1, -1.52160949662516078556178806805e-1, 2.01365400804030348374776537501e-1, 4.47106157277725905176885569043e-2},
    {0.1312004499419488073250102996e-1, 0, 0, 0, 0, -0.1225156446376204440720569753e1, -0.4957589496572501915214079952, 0.1664377182454986536961530415e1, -0.3503288487499736816886487290, 0.3341791187130174790297318841, 0.8192320648511571246570742613e-1, -0.2235530786388629525884427845e-1},
    {5.42937341165687622380535766363e-2-0.244094488188976377952755905512, 0, 0, 0, 0, 4.45031289275240888144113950566, 1.89151789931450038304281599044, -5.8012039600105847814672114227, 3.1116436695781989440891606237e-1-0.733846688281611857341361741547, -1.52160949662516078556178806805e-1, 2.01365400804030348374776537501e-1, 4.47106157277725905176885569043e-2-0.220588235294117647058823529412e-1}
};
constexpr double stage_times[12] = {
    0, 0.526001519587677318785587544488e-1, 0.789002279381515978178381316732e-1,
    0.118350341907227396726757197510, 0.281649658092772603273242802490,
    1.0/3, 0.25, 4.0/13, 0.651282051282051282051282051282, 0.6, 6.0/7, 1
};

struct Material {
    double noise_scale, anisotropy, drive, omega, gamma, memory_scale;
};

struct Solver {
    int count, species_count;
    size_t spin_size, state_size;
    std::vector<int32_t> species, neighbors;
    std::vector<Material> materials;
    std::vector<double> weights, state, trial, stage;
    std::vector<double> derivatives[12];
    double applied[3], time, next_step, relative_tolerance, absolute_tolerance;
    bool first_valid;
    uint64_t accepted, rejected, evaluations;

    Solver(int atoms, int kinds, const double* spins, const int32_t* assignments,
           const int32_t* adjacency, const double* parameters,
           const double* exchange, const double* field, bool equilibrated,
           double initial_step, double rtol, double atol)
        : count(atoms), species_count(kinds), spin_size(size_t(atoms)*3),
          state_size(spin_size*3), species(assignments, assignments+atoms),
          neighbors(adjacency, adjacency+size_t(atoms)*6), materials(kinds),
          weights(size_t(atoms)*6), state(state_size), trial(state_size),
          stage(state_size), time(0), next_step(initial_step),
          relative_tolerance(rtol), absolute_tolerance(atol), first_valid(false),
          accepted(0), rejected(0), evaluations(0) {
        std::copy(field, field+3, applied);
        std::copy(spins, spins+spin_size, state.begin());
        for (auto& derivative : derivatives) derivative.resize(state_size);
        double frequency_scale = 1;
        for (int kind=0; kind<kinds; ++kind) {
            const double* values = parameters+6*kind;
            Material& material = materials[kind];
            material.noise_scale = 1/std::sqrt(values[0]);
            material.anisotropy = 2*values[1]/values[0];
            material.drive = values[2]/values[3];
            material.omega = values[3];
            material.gamma = values[4];
            material.memory_scale = values[2] > 0 ? values[2]/(values[3]*values[3]) : 1;
            frequency_scale = std::max(frequency_scale, std::max(values[3], values[4]));
        }
        next_step = std::min(next_step, 0.1/frequency_scale);
        for (int atom=0; atom<count; ++atom) {
            int kind = species[atom];
            for (int bond=0; bond<6; ++bond) {
                size_t edge = size_t(atom)*6+bond;
                weights[edge] = exchange[kind*kinds+species[neighbors[edge]]]/parameters[kind*6];
            }
            if (equilibrated) {
                double displacement = parameters[kind*6+2]/std::pow(parameters[kind*6+3], 2);
                for (int component=0; component<3; ++component)
                    state[spin_size+size_t(atom)*3+component] = displacement*spins[size_t(atom)*3+component];
            }
        }
    }

    void rhs(const double* values, double* result, double fraction,
             const double* noise_left, const double* noise_right) {
        ++evaluations;
        double left_fraction = 1-fraction;
        for (int atom=0; atom<count; ++atom) {
            size_t offset = size_t(atom)*3;
            const Material& material = materials[species[atom]];
            double spin_x = values[offset], spin_y = values[offset+1], spin_z = values[offset+2];
            double field_x = applied[0] + values[spin_size+offset]
                + material.noise_scale*(left_fraction*noise_left[offset]+fraction*noise_right[offset]);
            double field_y = applied[1] + values[spin_size+offset+1]
                + material.noise_scale*(left_fraction*noise_left[offset+1]+fraction*noise_right[offset+1]);
            double field_z = applied[2] + values[spin_size+offset+2] + material.anisotropy*spin_z
                + material.noise_scale*(left_fraction*noise_left[offset+2]+fraction*noise_right[offset+2]);
            for (int bond=0; bond<6; ++bond) {
                size_t edge = size_t(atom)*6+bond;
                size_t neighbor = size_t(neighbors[edge])*3;
                double weight = weights[edge];
                field_x += weight*values[neighbor];
                field_y += weight*values[neighbor+1];
                field_z += weight*values[neighbor+2];
            }
            result[offset] = spin_y*field_z-spin_z*field_y;
            result[offset+1] = spin_z*field_x-spin_x*field_z;
            result[offset+2] = spin_x*field_y-spin_y*field_x;
            for (int component=0; component<3; ++component) {
                size_t index = offset+component;
                result[spin_size+index] = material.omega*values[2*spin_size+index];
                result[2*spin_size+index] = material.drive*values[index]
                    -material.omega*values[spin_size+index]-material.gamma*values[2*spin_size+index];
            }
        }
    }

    template<int row, int term=0>
    inline double combination(size_t index) const {
        if constexpr (term == 12) return 0;
        else if constexpr (tableau[row][term] == 0) return combination<row, term+1>(index);
        else return tableau[row][term]*derivatives[term][index]+combination<row, term+1>(index);
    }

    template<int stage_number>
    void evaluate_stages(double step, double left_time, double coarse_dt,
                         const double* noise_left, const double* noise_right) {
        for (size_t index=0; index<state_size; ++index)
            stage[index] = state[index]+step*combination<stage_number>(index);
        rhs(stage.data(), derivatives[stage_number].data(),
            (time+step*stage_times[stage_number]-left_time)/coarse_dt, noise_left, noise_right);
        if constexpr (stage_number < 11)
            evaluate_stages<stage_number+1>(step, left_time, coarse_dt, noise_left, noise_right);
    }

    void advance(double target, double left_time, double coarse_dt,
                 const double* noise_left, const double* noise_right) {
        bool preceding_rejection = false;
        while (time < target) {
            double remaining = target-time;
            double step = std::min(next_step, remaining);
            if (!(step > 0) || time+step == time)
                throw std::runtime_error("Adaptive integrator step underflow");
            if (!first_valid) {
                rhs(state.data(), derivatives[0].data(), (time-left_time)/coarse_dt, noise_left, noise_right);
                first_valid = true;
            }
            evaluate_stages<1>(step, left_time, coarse_dt, noise_left, noise_right);
            for (size_t index=0; index<state_size; ++index)
                trial[index] = state[index]+step*combination<12>(index);
            double error = 0;
            for (size_t block=0; block<3; ++block) {
                for (int atom=0; atom<count; ++atom) {
                    double floor = absolute_tolerance*(block == 0 ? 1 : materials[species[atom]].memory_scale);
                    for (int component=0; component<3; ++component) {
                        size_t index = block*spin_size+size_t(atom)*3+component;
                        double error_fifth = combination<13>(index);
                        double error_third = combination<14>(index);
                        if (!std::isfinite(error_fifth) || !std::isfinite(error_third) || !std::isfinite(trial[index])) {
                            error = std::numeric_limits<double>::infinity();
                            continue;
                        }
                        double denominator = std::sqrt(error_fifth*error_fifth+0.01*error_third*error_third);
                        if (!std::isfinite(denominator)) {
                            error = std::numeric_limits<double>::infinity();
                            continue;
                        }
                        double difference = denominator > 0 ? step*std::abs(error_fifth)*(std::abs(error_fifth)/denominator) : 0;
                        double scale = floor+relative_tolerance*std::max(std::abs(state[index]), std::abs(trial[index]));
                        double ratio = std::abs(difference)/scale;
                        if (!std::isfinite(ratio))
                            throw std::runtime_error("Non-finite integration state");
                        error = std::max(error, ratio);
                    }
                }
            }
            if (error <= 1) {
                ++accepted;
                state.swap(trial);
                for (int atom=0; atom<count; ++atom) {
                    size_t offset = size_t(atom)*3;
                    double norm = std::sqrt(state[offset]*state[offset]+state[offset+1]*state[offset+1]
                        +state[offset+2]*state[offset+2]);
                    state[offset] /= norm;
                    state[offset+1] /= norm;
                    state[offset+2] /= norm;
                }
                time = step == remaining ? target : time+step;
                rhs(state.data(), derivatives[0].data(), (time-left_time)/coarse_dt, noise_left, noise_right);
                double factor = error == 0 ? 5 : std::min(5.0, std::max(0.2, 0.9*std::pow(error, -0.125)));
                if (preceding_rejection) factor = std::min(1.0, factor);
                next_step = step*factor;
                preceding_rejection = false;
            } else {
                ++rejected;
                next_step = step*std::max(0.1, 0.9*std::pow(error, -0.125));
                preceding_rejection = true;
            }
        }
    }

    void snapshot(double* mean) const {
        std::fill(mean, mean+3*species_count, 0.0);
        std::vector<int> populations(species_count, 0);
        for (int atom=0; atom<count; ++atom) {
            int kind = species[atom];
            ++populations[kind];
            for (int component=0; component<3; ++component)
                mean[3*kind+component] += state[size_t(atom)*3+component];
        }
        for (int kind=0; kind<species_count; ++kind)
            if (populations[kind])
                for (int component=0; component<3; ++component)
                    mean[3*kind+component] /= populations[kind];
    }

    void output(double* spins, double* memory) const {
        std::copy(state.begin(), state.begin()+spin_size, spins);
        for (int atom=0; atom<count; ++atom) {
            double omega = materials[species[atom]].omega;
            for (int component=0; component<3; ++component) {
                memory[size_t(atom)*6+component] = state[spin_size+size_t(atom)*3+component];
                memory[size_t(atom)*6+3+component] = omega*state[2*spin_size+size_t(atom)*3+component];
            }
        }
    }
};

static std::string last_error;
extern "C" {
const char* spin_error() { return last_error.c_str(); }
void* spin_create(int count, int kinds, const double* spins, const int32_t* material,
                  const int32_t* neighbors, const double* parameters, const double* exchange,
                  const double* field, int equilibrated, double step, double rtol, double atol) {
    try {
        return new Solver(count, kinds, spins, material, neighbors, parameters, exchange,
                          field, equilibrated != 0, step, rtol, atol);
    } catch (const std::exception& error) { last_error=error.what(); return nullptr; }
}
int spin_advance(void* handle, double target, double left_time, double coarse_dt,
                 const double* noise_left, const double* noise_right) {
    try {
        static_cast<Solver*>(handle)->advance(target, left_time, coarse_dt, noise_left, noise_right);
        return 0;
    } catch (const std::exception& error) { last_error=error.what(); return -1; }
}
void spin_snapshot(void* handle, double* mean) { static_cast<Solver*>(handle)->snapshot(mean); }
void spin_output(void* handle, double* spins, double* memory) { static_cast<Solver*>(handle)->output(spins, memory); }
void spin_stats(void* handle, uint64_t* stats) {
    Solver* solver = static_cast<Solver*>(handle);
    stats[0] = solver->accepted; stats[1] = solver->rejected; stats[2] = solver->evaluations;
}
void spin_destroy(void* handle) { delete static_cast<Solver*>(handle); }
}
"""


def initialize(case):
    shape = tuple(case["shape"])
    grid = np.indices(shape)
    count = int(np.prod(shape))
    material = np.asarray(
        (grid.sum(axis=0) % len(case["materials"])).ravel(), dtype=np.int32
    )
    lattice = np.arange(count, dtype=np.int32).reshape(shape)
    neighbors = np.stack([
        np.roll(lattice, direction, axis=axis).ravel()
        for axis in range(3) for direction in (-1, 1)
    ], axis=1)
    random = np.random.default_rng(case["initial_seed"])
    spins = random.normal(size=(count, 3)) * case["disorder"]
    for index, values in enumerate(case["materials"]):
        spins[material == index] += np.asarray(values["initial_direction"])
    if case.get("twist", 0):
        angle = case["twist"] * grid[0].ravel() / shape[0]
        original = spins.copy()
        spins[:, 0] = np.cos(angle)*original[:, 0]+np.sin(angle)*original[:, 2]
        spins[:, 2] = -np.sin(angle)*original[:, 0]+np.cos(angle)*original[:, 2]
    spins /= np.linalg.norm(spins, axis=1)[:, None]
    parameters = np.array([
        [values[key] for key in ("mu", "K", "A", "omega0", "Gamma", "T")]
        for values in case["materials"]
    ], dtype=np.float64)
    return spins, material, np.ascontiguousarray(neighbors), parameters


def bath_spectrum(case):
    coarse_dt = float(case["dt"])*int(case["decimation"])
    nfft = int(case["nfft"])
    frequencies = 2*np.pi*np.arange(nfft//2+1, dtype=np.float64)/(nfft*coarse_dt)
    power = np.empty((len(case["materials"]), len(frequencies)), dtype=np.float64)
    thermostat = case["thermostat"]
    for index, material in enumerate(case["materials"]):
        temperature = float(material["T"])
        strength = float(material["A"])
        omega = float(material["omega0"])
        gamma = float(material["Gamma"])
        if thermostat == "classical":
            numerator = np.full_like(frequencies, 2*temperature)
        elif thermostat in ("quantum", "nozero"):
            thermal = np.zeros_like(frequencies)
            if temperature > 0:
                thermal[0] = 2*temperature
                active = (frequencies > 0) & (frequencies < 700*temperature)
                thermal[active] = 2*frequencies[active]/np.expm1(frequencies[active]/temperature)
            numerator = thermal+frequencies if thermostat == "quantum" else thermal
        else:
            raise ValueError("Unknown thermostat: "+str(thermostat))
        denominator = (omega*omega-frequencies*frequencies)**2 + (gamma*frequencies)**2
        power[index] = strength*gamma*numerator/denominator
    multipliers_squared = 2*power/coarse_dt
    lags = np.asarray(case["lags"], dtype=np.int64) % nfft
    covariance = np.fft.irfft(multipliers_squared, n=nfft, axis=-1)[:, lags].copy()
    return np.sqrt(multipliers_squared), covariance


class NoiseRecord:
    def __init__(self, case, material, multipliers, directory, memory_limit=320*1024**2):
        self.count = len(material)
        self.nfft = int(case["nfft"])
        self.length = int(case["steps"])//int(case["decimation"])+2
        if (int(case["steps"]) % int(case["decimation"])) == 0:
            self.length -= 1
        self.length = min(self.nfft, max(1, self.length))
        self.file = None
        if not np.any(multipliers):
            self.values = np.broadcast_to(
                np.zeros((self.count, 3), dtype=np.float64),
                (self.length, self.count, 3),
            )
            return
        total_bytes = self.length*self.count*3*8
        if total_bytes <= memory_limit:
            self.values = np.empty((self.length, self.count, 3), dtype=np.float64)
        else:
            self.values = None
            self.file = tempfile.TemporaryFile(dir=directory)
            self.file.truncate(total_bytes)
        random = np.random.default_rng(case["noise_seed"])
        batch_size = max(1, min(self.count, (16*1024**2)//(3*self.nfft*8)))
        for start in range(0, self.count, batch_size):
            stop = min(self.count, start+batch_size)
            white = random.standard_normal((stop-start, 3, self.nfft))
            transformed = np.fft.rfft(white, axis=-1)
            del white
            transformed *= multipliers[material[start:stop], None, :]
            filtered = np.fft.irfft(transformed, n=self.nfft, axis=-1)
            del transformed
            if self.values is not None:
                self.values[:, start:stop, :] = filtered[:, :, :self.length].transpose(2, 0, 1)
            else:
                cropped = np.ascontiguousarray(filtered[:, :, :self.length].transpose(2, 0, 1))
                for knot in range(self.length):
                    data = memoryview(cropped[knot]).cast("B")
                    offset = (knot*self.count+start)*3*8
                    while data:
                        written = os.pwrite(self.file.fileno(), data, offset)
                        if written <= 0:
                            raise OSError("Failed to write the noise backing file")
                        offset += written
                        data = data[written:]
            del filtered

    def knot(self, index):
        index %= self.nfft
        if self.values is not None:
            return self.values[index]
        size = self.count*3*8
        data = bytearray(size)
        view = memoryview(data)
        offset = index*size
        while view:
            chunk = os.pread(self.file.fileno(), len(view), offset)
            if not chunk:
                raise OSError("Incomplete noise backing file")
            view[:len(chunk)] = chunk
            offset += len(chunk)
            view = view[len(chunk):]
        return np.frombuffer(data, dtype=np.float64).reshape(self.count, 3)

    def close(self):
        if self.file is not None:
            self.file.close()


def compile_kernel(directory):
    source = Path(directory)/"spin_kernel.cpp"
    library = Path(directory)/"spin_kernel.so"
    source.write_text(NATIVE_SOURCE)
    compilation = subprocess.run([
        "g++", "-O3", "-std=c++17", "-march=native", "-fPIC", "-shared",
        str(source), "-o", str(library),
    ], env=dict(os.environ, TMPDIR=str(directory)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if compilation.returncode:
        raise RuntimeError("Native compilation failed: "+compilation.stderr.decode())
    native = ctypes.CDLL(str(library))
    pointer = ctypes.c_void_p
    integer = ctypes.c_int
    real = ctypes.c_double
    native.spin_error.argtypes = []
    native.spin_error.restype = ctypes.c_char_p
    native.spin_create.argtypes = [integer, integer]+[pointer]*6+[integer, real, real, real]
    native.spin_create.restype = pointer
    native.spin_advance.argtypes = [pointer, real, real, real, pointer, pointer]
    native.spin_advance.restype = integer
    native.spin_snapshot.argtypes = [pointer, pointer]
    native.spin_snapshot.restype = None
    native.spin_output.argtypes = [pointer, pointer, pointer]
    native.spin_output.restype = None
    native.spin_stats.argtypes = [pointer, pointer]
    native.spin_stats.restype = None
    native.spin_destroy.argtypes = [pointer]
    native.spin_destroy.restype = None
    return native


def solve(case, directory, rtol=1e-8, atol=1e-10, noise_memory_limit=320*1024**2):
    spins, material, neighbors, parameters = initialize(case)
    multipliers, covariance = bath_spectrum(case)
    exchange = np.ascontiguousarray(case["exchange"], dtype=np.float64)
    field = np.ascontiguousarray(case["field"], dtype=np.float64)
    sample_steps = np.asarray(case["sample_steps"], dtype=np.int64)
    trace = np.empty((len(sample_steps), len(parameters), 3), dtype=np.float64)
    memory = np.empty((len(spins), 6), dtype=np.float64)
    dt = float(case["dt"])
    decimation = int(case["decimation"])
    steps = int(case["steps"])
    coarse_dt = dt*decimation
    if np.any(sample_steps < 0) or np.any(sample_steps > steps):
        raise ValueError("Sample step outside the integration interval")
    with tempfile.TemporaryDirectory(prefix=".spin_solver_", dir=directory) as scratch:
        native = compile_kernel(scratch)
        record = NoiseRecord(case, material, multipliers, scratch, noise_memory_limit)
        handle = native.spin_create(
            len(spins), len(parameters), spins.ctypes.data, material.ctypes.data,
            neighbors.ctypes.data, parameters.ctypes.data, exchange.ctypes.data,
            field.ctypes.data, case["initial_memory"] == "equilibrated", dt, rtol, atol,
        )
        if not handle:
            record.close()
            raise RuntimeError(native.spin_error().decode())
        try:
            snapshots = {}
            for index, step in enumerate(sample_steps):
                snapshots.setdefault(int(step), []).append(index)
            boundaries = sorted(set(range(decimation, steps+1, decimation)) | set(snapshots) | {0, steps})
            current_knot = -1
            noise_left = noise_right = None
            current_step = 0
            for target_step in boundaries:
                if target_step > current_step:
                    knot = current_step//decimation
                    if knot != current_knot:
                        noise_left = noise_right if knot == current_knot+1 and noise_right is not None else record.knot(knot)
                        noise_right = record.knot(knot+1)
                        current_knot = knot
                    status = native.spin_advance(
                        handle, target_step*dt, knot*coarse_dt, coarse_dt,
                        noise_left.ctypes.data, noise_right.ctypes.data,
                    )
                    if status:
                        raise RuntimeError(native.spin_error().decode())
                    current_step = target_step
                for index in snapshots.get(target_step, ()):
                    native.spin_snapshot(handle, trace[index].ctypes.data)
            native.spin_output(handle, spins.ctypes.data, memory.ctypes.data)
            if os.environ.get("SPIN_SOLVER_STATS"):
                stats = np.empty(3, dtype=np.uint64)
                native.spin_stats(handle, stats.ctypes.data)
                print("steps=%d rejected=%d rhs=%d" % tuple(stats), file=sys.stderr)
        finally:
            native.spin_destroy(handle)
            record.close()
    result = dict(spins=spins, memory=memory, trace=trace, covariance=covariance)
    for name, values in result.items():
        if values.dtype != np.float64 or not np.all(np.isfinite(values)):
            raise RuntimeError("Invalid output array: "+name)
    return result


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solve.py CASE.json OUTPUT.npz")
    with open(sys.argv[1], encoding="utf-8") as source:
        case = json.load(source)
    output = Path(sys.argv[2]).resolve()
    result = solve(case, output.parent)
    with open(output, "wb") as destination:
        np.savez(destination, **result)


if __name__ == "__main__":
    main()

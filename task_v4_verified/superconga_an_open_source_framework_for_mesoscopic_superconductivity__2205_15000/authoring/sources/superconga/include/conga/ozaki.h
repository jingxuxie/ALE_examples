#ifndef CONGA_OZAKI_H_
#define CONGA_OZAKI_H_

#include <algorithm>
#include <utility>
#include <vector>

/* Wrapper of dsygv from FORTRAN LAPACK
 * Documentation: http://www.netlib.org/lapack/explore-html/d5/d2e/dsygv_8f.html
 * Requires compilation flags:
 *     GCC:       -lgfortran -llapack -lblas
 *     Intel/MKL: -lgfortran -lmkl_intel_ilp64 -lmkl_sequential -lmkl_core
 * -lpthread -lm -ldl -DMKL_ILP64 -m64
 */
extern "C" {
void dsygv_(int64_t *ITYPE, char *JOBZ, char *UPLO, int64_t *N, double *A,
            int64_t *LDA, double *B, int64_t *LDB, double *W, double *WORK,
            int64_t *LWORK, int64_t *INFO);
}

namespace conga {
namespace ozaki {
/// @brief Compute the number of Ozaki poles needed. If more than 200 is
/// needed the exact number is approximated.
/// @tparam T Float or double.
/// @param inTemperature The temperature (in units of Tc).
/// @param inEnergyCutoff The energy cutoff (in units of 2*pi*kB*Tc).
/// @return The number of poles.
template <typename T>
int computeNumEnergies(const T inTemperature, const T inEnergyCutoff) {
  // A vector of the largest Ozaki pole with n+1 poles computed, where n is the
  // index of the vector.
  const std::vector<double> maxOzakiPole = {
      3.464101615138,      13.043193723013,    27.182805923222,
      46.319508681820,     70.526709814647,    99.819209820145,
      134.201334576035,    173.674723843717,   218.240115243641,
      267.897882477874,    322.648232120917,   382.491286239281,
      447.427120870950,    517.455785454923,   592.577313298030,
      672.791727521291,    758.099044591524,   848.499276499387,
      943.992432147387,    1044.578518259219,  1150.257539991102,
      1261.029501351330,   1376.894405494319,  1497.852254930454,
      1623.903051677801,   1755.046797373544,  1891.283493357799,
      2032.613140735255,   2179.035740424027,  2330.551293191541,
      2487.159799683865,   2648.861260447426,  2815.655675948037,
      2987.543046583090,   3164.523372695167,  3346.596654578822,
      3533.762892490810,   3726.022086653727,  3923.374237262044,
      4125.819344486381,   4333.357408476837,  4545.988429367131,
      4763.712407272654,   4986.529342298375,  5214.439234539534,
      5447.442084074518,   5685.537890980710,  5928.726655323640,
      6177.008377162879,   6430.383056551208,  6688.850693540401,
      6952.411288172675,   7221.064840486898,  7494.811350521523,
      7773.650818306208,   8057.583243876886,  8346.608627256021,
      8640.726968470750,   8939.938267543248,  9244.242524494641,
      9553.639739344733,   9868.129912114642,  10187.713042813368,
      10512.389131458542,  10842.158178074462, 11177.020182659693,
      11516.975145232140,  11862.023065802561, 12212.163944387836,
      12567.397780986943,  12927.724575614844, 13293.144328276247,
      13663.657038985704,  14039.262707740532, 14419.961334558257,
      14805.752919440674,  15196.637462387956, 15592.614963412661,
      15993.685422515518,  16399.848839707749, 16811.105214993084,
      17227.454548365906,  17648.896839834808, 18075.432089412709,
      18507.060297090567,  18943.781462892035, 19385.595586789594,
      19832.502668811354,  20284.502708945201, 20741.595707203986,
      21203.781663584734,  21671.060578106339, 22143.432450728560,
      22620.897281488116,  23103.455070385800, 23591.105817420932,
      24083.849522596051,  24581.686185888688, 25084.615807335540,
      25592.638386922201,  26105.753924657907, 26623.962420530934,
      27147.263874548138,  27675.658286698381, 28209.145657019460,
      28747.725985486431,  29291.399272088380, 29840.165516850884,
      30394.024719756279,  30952.976880822123, 31517.022000048237,
      32086.160077425615,  32660.391112956720, 33239.715106652184,
      33824.132058499723,  34413.641968492826, 35008.244836653459,
      35607.940662971036,  36212.729447455276, 36822.611190103285,
      37437.585890915667,  38057.653549855168, 38682.814167005199,
      39313.067742276238,  39948.414275748975, 40588.853767362038,
      41234.386217142870,  41885.011625110244, 42540.729991207598,
      43201.541315517512,  43867.445597926955, 44538.442838554773,
      45214.533037321766,  45895.716194298584, 46581.992309429610,
      47273.361382657822,  47969.823414089085, 48671.378403742987,
      49378.026351488850,  50089.767257488224, 50806.601121605097,
      51528.527943908797,  52255.547724346325, 52987.660462994907,
      53724.866159820733,  54467.164814822114, 55214.556427974414,
      55967.040999261437,  56724.618528703817, 57487.289016365059,
      58255.052462227519,  59027.908866262900, 59805.858228478566,
      60588.900548765567,  61377.035827283733, 62170.264063961804,
      62968.585258870233,  63771.999411872166, 64580.506523058772,
      65394.106592470736,  66212.799620066056, 67036.585605816275,
      67865.464549688913,  68699.436451832487, 69538.501312039167,
      70382.659130497530,  71231.909907065638, 72086.253641840856,
      72945.690334811923,  73810.219985944655, 74679.842595227819,
      75554.558162766305,  76434.366688360693, 77319.268172226453,
      78209.262614181425,  79104.350014321433, 80004.530372739711,
      80909.803689260734,  81820.169963918539, 82735.629196799040,
      83656.181387807985,  84581.826537007699, 85512.564644378072,
      86448.395710174183,  87389.319733820099, 88335.336715730969,
      89286.446655858366,  90242.649554185831, 91203.945410558954,
      92170.334225223487,  93141.815998147023, 94118.390728990082,
      95100.058418232264,  96086.819065539064, 97078.672670988453,
      98075.619234544327,  99077.658756581528, 100084.791236587014,
      101097.016674872531, 102114.335071418158};

  // The value to compare with in the poles data.
  const double val =
      2.0 * M_PI * static_cast<double>(inEnergyCutoff / inTemperature);

  // Get the pointer to the value of the first element larger than 'val'.
  const auto upper =
      std::upper_bound(maxOzakiPole.begin(), maxOzakiPole.end(), val);

  if (upper != maxOzakiPole.end()) {
    // The value was found, so we can compute the index, and thus the number
    // of needed poles.
    const int idx =
        static_cast<int>(std::distance(maxOzakiPole.begin(), upper));
    return idx + 1;
  } else {
#ifndef NDEBUG
    std::cerr << "-- WARNING! The temperature (cutoff) is too low (high). Will "
                 "approximate the number of Ozaki poles using a polynomial fit."
              << std::endl;
#endif
    // These parameters were obtained by fitting a second degree polynomial to
    // the poles data in Matlab. The fit is very good.
    const double c2 = 2.5465;
    const double c1 = 1.2744;
    const double c0 = 0.4651;

    // Loop until we find the approximate needed number of poles.
    int i = static_cast<int>(maxOzakiPole.size()) - 1;
    bool success = false;
    while (!success) {
      i++;
      const double x = static_cast<double>(i);
      const double approxVal = x * (c2 * x + c1) + c0;
      success = approxVal >= val;
    }
    return i;
  }
}

/// @brief Compute the Ozaki energies and residues.
/// @tparam T Float or double.
/// @param inTemperature The temperature (in units of Tc).
/// @param inNumEnergies The number of energies.
/// @return The pair {energies, residues}.
template <typename T>
std::pair<std::vector<T>, std::vector<T>>
computeEnergiesAndResidues(const T inTemperature, const int inNumEnergies) {
  // Dimension of matrices is 2*poles due to positive and negative poles
  int64_t N = 2 * inNumEnergies;

  // Ozaki matrices from PRB 75, 035123, (2007)
  // Note that A and B have switched place in relation to the paper.
  // This is a trick so dsygv can actually find a solution.
  // Paper (i start at 1):
  // Diagonal matrix A, A_ii = -(2*i-1)
  // Off-diagonal matrix B, B_i,i+1 = B_i,i-1 = -1/2
  // This implementation (i starts at 0):
  // Diagonal matrix B, B_ii = (2*i+1)
  // Off-diagonal matrix A, A_i,i+1 = A_i,i-1 = -1/2
  std::vector<double> A(N * N, 0.0);
  std::vector<double> B(N * N, 0.0);

  for (int i = 0; i < N; ++i) {
    B[i * N + i] = i * 2.0 + 1.0;

    if (i < N - 1) {
      A[N * i + (i + 1)] = -0.5;
      A[N * (i + 1) + i] = -0.5;
    }
  }

  int64_t LDA = N;       // Dimension of A: N*N
  int64_t LDB = N;       // Dimension of B: N*N
  int64_t LWORK = 3 * N; // Working dimension: (3*N)*(3*N)

  // ITYPE 1: Generalized eigenvalue problem of type A*x = (lambda)*B*x
  int64_t ITYPE = 1;
  char JOBZ = 'V';  // Compute eigenvalues and eigenvectors
  char UPLO = 'U';  // Upper triangles of A and B are stored
  int64_t INFO = 0; // Storage for info returned from dsygv

  std::vector<double> W(N, 0.0);        // Eigenvalue storage
  std::vector<double> WORK(LWORK, 0.0); // Work storage

  dsygv_(&ITYPE, &JOBZ, &UPLO, &N, A.data(), &LDA, B.data(), &LDB, W.data(),
         WORK.data(), &LWORK, &INFO);

  std::vector<T> ozakiEnergies;
  std::vector<T> ozakiResidues;

  for (int i = 0; i < inNumEnergies; ++i) {
    const double pole = -1.0 / W[i];
    const double residueSqrt = 0.5 * A[N * i] * pole;

    const T ozakiEnergy =
        static_cast<T>(pole) * inTemperature / static_cast<T>(2.0 * M_PI);
    ozakiEnergies.push_back(ozakiEnergy);

    const T ozakiResidue = static_cast<T>(residueSqrt * residueSqrt);
    ozakiResidues.push_back(ozakiResidue);
  }

  return {ozakiEnergies, ozakiResidues};
}

/// @brief Compute the Ozaki energies and residues.
/// @tparam T Float or double.
/// @param inTemperature The temperature (in units of Tc).
/// @param inEnergyCutoff The energy cutoff (in units of 2*pi*kB*Tc).
/// @return The pair {energies, residues}.
template <typename T>
std::pair<std::vector<T>, std::vector<T>>
computeEnergiesAndResidues(const T inTemperature, const T inEnergyCutoff) {
  const int numEnergies = computeNumEnergies(inTemperature, inEnergyCutoff);
  return computeEnergiesAndResidues(inTemperature, numEnergies);
}

} // namespace ozaki
} // namespace conga

#endif // CONGA_OZAKI_H_

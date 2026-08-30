//===---------------- arg.h - Macro for struct parameters. ----------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Macro for adding parameters to struct. Adapted from PyTorch C++ API:
/// torch/csrc/api/include/torch/arg.h
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_ARG_H_
#define CONGA_ARG_H_

#include <utility>

#define CONGA_ARG(T, name)                                                     \
public:                                                                        \
  inline auto name(const T &new_##name)->decltype(*this) { /* NOLINT */        \
    this->m_##name = new_##name;                                               \
    return *this;                                                              \
  }                                                                            \
  inline auto name(T &&new_##name)->decltype(*this) { /* NOLINT */             \
    this->m_##name = std::move(new_##name);                                    \
    return *this;                                                              \
  }                                                                            \
  inline const T &name() const noexcept { /* NOLINT */                         \
    return this->m_##name;                                                     \
  }                                                                            \
  inline T &name() noexcept { /* NOLINT */                                     \
    return this->m_##name;                                                     \
  }                                                                            \
                                                                               \
private:                                                                       \
  T m_##name /* NOLINT */

#endif // CONGA_ARG_H_

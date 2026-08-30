# Scientific seed

Dennis, Hope and Johnsson, *XMDS2: Fast, scalable simulation of coupled stochastic
partial differential equations*, arXiv:1204.4255v2, is the seed for the coupled
field / spectral integration / atom-optics setting. The control benchmark,
uncertainty envelope and target thresholds are new design choices, not reported
results from that paper. This task requires no stochastic forcing.

- Paper: `https://arxiv.org/abs/1204.4255`
- Original repository: `https://github.com/GrahamDennis/xpdeint`
- Fourier geometry, IP operators, refinement diagnostics:
  `https://xmds.sourceforge.net/reference_elements.html`
- Examples: `https://xmds.sourceforge.net/worked_examples.html`

The included simulator is independently implemented with NumPy/SciPy. It uses
exact spectral kinetic evolution in a symmetric split method; it is not an
XMDS2 installation or an assertion of identical XMDS integration algorithms.

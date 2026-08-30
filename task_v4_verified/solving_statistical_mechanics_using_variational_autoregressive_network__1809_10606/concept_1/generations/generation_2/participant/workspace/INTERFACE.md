# Interface

Input JSON fields: `n` (integer), `couplings` (symmetric zero-diagonal n-by-n
matrix), `fields` (length n). Parameters already include inverse temperature:
`log p(s) = 0.5*s.T@couplings@s + fields@s - log Z`, for spins -1/+1.
Couplings may be dense or sparse, positive or negative; fields may be zero.

Output JSON has exactly `mixing`, `weights`, `biases`, `orders`.
For M components, their shapes are `(M,)`, `(M,n,n)`, `(M,n)`, `(M,n)`.
Mixing weights are strictly positive and sum to one within 1e-10. Every order is
a permutation of 0,...,n-1. `weights[m,i,j]` must be exactly zero unless j precedes
i in `orders[m]`. All real parameters must be finite; for every conditional,
`abs(biases[m,i])+sum_j(abs(weights[m,i,j])) <= 60`.

In original site coordinates the conditional logit is
`biases[m,i]+sum_j(weights[m,i,j]*s[j])`. Its probability of +1 is the logistic
function of that logit. Component probabilities are products of conditionals;
the model is the mixture of those normalized joint distributions. There are no
additional runtime callbacks or tables. The JSON file must be at most 1 MiB.

All quality metrics use complete enumeration and natural logarithms:
`KL(q||p) = sum_s q(s)*(log q(s)-log p(s))` and
`ESS = 1/sum_s exp(2*log p(s)-log q(s))`. ESS here is a population fraction, not
the potentially optimistic ESS of a finite sample. Family scores average KL
within each family. The public examples are distinct from hidden instances.

`python baseline/solve.py input/example_quartets.json output.json` is runnable from
the participant root. All required implementation files must be in the submitted
directory; code may additionally import the provided workspace through PYTHONPATH.

# Sheet identity versus physical identifiability

## Why sheet names are not scored

The parent identified a legitimate distinction between local parameter
identifiability and discrete label ambiguity. Version 2.1 therefore matches
the active sheet spectra up to **one permutation per case**, shared by all
14 windows. The target is an unordered set of normalized, finite-resolution
sheet spectra, not an orbital naming convention. Input data, finite resolution,
noise, window tolerances, and aggregate pass limits are unchanged from v2.
Only the matching rule changed, before any fresh concept_3 scientific attempt.

Even without this rule, the distinct positive probe factors generically anchor
sheet names in the exact model. If sheet Green functions are linearly
independent, equality of probe 0 after a permutation forces the corresponding
weights to permute. Equality of probe 1 then requires P_b/P_pi(b) to be the
same positive constant for every b. Following a permutation cycle forces this
constant to be one, so distinct P values rule out a nonidentity permutation.
Coincident sheet functions are a degenerate exception but have coincident
spectra. This argument is **not** a finite-noise guarantee and is not used to
justify scoring an ordering. The permutation-invariant contract removes the
issue even in near-degenerate cases.

`global_identifiability.py` explicitly tries every nonidentity permutation of
each audit system's complete sheet functions, and optimizes the unknown mixing
coordinates from a grid of 3 or 9 starts across their full disclosed domain.
This enlarged test even allows permutations that might violate the sampler's
sheet-dependent gap/phase domains. True latents are used only to define these
explicit alias diagnostics, never as a predictive initialization.

## The remaining blind-unmixing problem

Permutation invariance does not resolve general blind unmixing. With three
arbitrary sheet functions and only two mixed probes, even known weights leave
a functional nullspace. There is no model-free uniqueness claim. Predictions
must exploit the **disclosed finite-dimensional causal family** and its prior;
the model is not closed under arbitrary functional nullspace perturbations.

The global audit separately initializes models from an independent public-seed
bank, considers every topology-compatible family, and performs three bounded
fits per family. The inference function receives only observed features,
their noise, and the public sheet count. Fits within delta chi-square <=9 of
the best fit are compared pairwise in exact noise-whitened feature distance
and permutation-invariant target distance. A feature separation <=2 with
target separation >2 score units is flagged as a collision warning. Saved
fitted parameters permit independent inspection and additional searches.

This is a finite global search, not a certificate. The search can miss narrow
or low-prior-volume branches, and local Gaussian-prior uncertainty is near the
score scale for some three-sheet cases. Conversely, one adversarial pair alone
would not establish an aggregate Bayes-risk lower bound for the disclosed
sampling distribution. See `hidden/global_identifiability.json` for actual
results and `hidden/global_fit_models.npz` for the fitted alternatives.

The expensive feature-only audit and local diagnostics are kept distinct:
truth-initialized derivatives and label replay never count as evidence of a
passing predictor. The task remains `hard_open_candidate` until a genuinely
predictive full-batch solution meets both accuracy and runtime gates.

import jax
import jax.numpy as jnp
from flax import nnx
from ..fourier import FourierMeta
from ..utils import Const, ShapeInfo
from .base import ApplyBijection
from .affine_complex import complex_affine_apply

class SpectrumScaling(ApplyBijection):
    r"""Diagonal scaling transformation in Fourier space.

    Applies element-wise scaling to the Fourier transform of real-valued fields,
    implementing diagonal transformations in momentum space. This is particularly
    useful for implementing free field theories and spectral preconditioning.

    Type: $\mathbb{R}^{H \times W \times C} \to \mathbb{R}^{H \times W \times C}$
    Transform: $\mathcal{F}^{-1}[s(\mathbf{k}) \mathcal{F}[\mathbf{x}]]$

    The scaling factors correspond to momentum-dependent transformations, with
    the log-Jacobian computed from FFT multiplicities to handle real FFT symmetries.

    Args:
        scaling: Scaling factors with shape matching rFFT output.
            If not an nnx.Variable/nnx.Param, by default treated as constant.
        channel_dim: Number of channel dimensions.
        space_dim: Number of spatial dimensions. If None, inferred from the
            rank of ``scaling``, which assumes a single spectrum shared by
            all channels. Must be given explicitly for a per-channel
            spectrum (and whenever ``scaling`` is None).

    Note:
        The spatial part of the scaling array must have the same shape as the
        output of ``jnp.fft.rfftn`` over the space axes. With ``channel_dim > 0``
        the scaling may either have rank ``space_dim`` (one spectrum shared by
        all channels) or rank ``space_dim + channel_dim`` (per-channel spectra).

    Note:
        Those rFFT entries whose conjugate partner is also stored in the
        rFFT grid are constrained, and they must satisfy
        ``s[copy_to] == conj(s[copy_from])`` for the index pairs of
        :meth:`FourierMeta.create(space_shape) <FourierMeta.create>` (plain
        equality for a real spectrum). For a real spectrum the condition is vacuous in
        one dimension (no such pairs exist). It is separate from the other
        requirement that the spectrum is symmetric under $k \to -k$ everywhere.

        Violating it fails silently: ``mr + mi`` vanishes on every ``copy_to``
        entry, so the log-Jacobian weights assume the symmetry rather
        than check it. The map then stops being invertible *and* the reported
        log-density change is wrong. Use :func:`~bijx.fourier.spectrum_asymmetry`
        to check the precondition.

        Any real function of :func:`~bijx.fourier.fft_momenta` satisfies this
        automatically, since those momenta are folded into the first Brillouin zone
        and are therefore related by $k \to -k$ across each conjugate pair,
        as is a spectrum parametrised per $|k|^2$ class through
        ``FourierMeta.unique_unfold``.

        A complex spectrum carries a second condition: it must be real at
        self-conjugate modes (``mr & ~mi``), where the field carries no
        imaginary degree of freedom. See :func:`~bijx.fourier.spectrum_asymmetry`.

    Example:
        >>> # Create momentum-dependent scaling
        >>> k = fft_momenta((8, 8))
        >>> scaling = jnp.exp(-0.1 * jnp.sum(k**2, axis=-1))
        >>> bijection = SpectrumScaling(scaling)
        >>> y, log_det = bijection.forward(phi, log_density)
    """

    def __init__(
        self,
        scaling: jax.Array | nnx.Variable,
        channel_dim: int = 0,
        space_dim: int | None = None,
    ):
        self.channel_dim = channel_dim

        if not isinstance(scaling, nnx.Variable):
            scaling = Const(scaling)
        self.scaling_var = scaling
        if space_dim is None:
            value = scaling.get_value()
            if value is None:
                raise ValueError(
                    "space_dim must be given explicitly if scaling is None"
                )
            # bare spectrum: rank is the number of space dimensions
            space_dim = jnp.ndim(value)
        self.shape_info = ShapeInfo(space_dim=space_dim, channel_dim=channel_dim)

    @property
    def scaling(self):
        return self.scaling_var.get_value()

    def _broadcast_scaling(self, scaling, shape_info):
        """Align scaling with the rFFT event shape ``(*rfft_shape, *channels)``."""
        space_dim = shape_info.space_dim
        channel_dim = shape_info.channel_dim
        rank = jnp.ndim(scaling)
        if rank == space_dim:
            # one spectrum shared by all channels
            scaling = jnp.reshape(scaling, jnp.shape(scaling) + (1,) * channel_dim)
        elif rank != space_dim + channel_dim:
            raise ValueError(
                f"scaling rank {rank} matches neither space_dim={space_dim} "
                f"(shared spectrum) nor space_dim + channel_dim="
                f"{space_dim + channel_dim} (per-channel spectrum)"
            )
        return scaling

    def apply(self, x, log_density, reverse=False, **kwargs):
        _, shape_info = self.shape_info.process_event(x.shape)
        meta = FourierMeta.create(shape_info.space_shape)
        scaling = self._broadcast_scaling(self.scaling, shape_info)

        # full rFFT event shape: spectrum axes followed by channel axes
        event_shape = meta.mr.shape + shape_info.channel_shape
        # weight = number of independent real DoF per rFFT mode (0, 1 or 2)
        weight = (meta.mr.astype(int) + meta.mi.astype(int)).reshape(
            meta.mr.shape + (1,) * shape_info.channel_dim
        )
        # broadcast before summing: a shared spectrum acts on every channel,
        # so its contribution to log|det J| is counted once per channel
        log_scaling = jnp.broadcast_to(jnp.log(jnp.abs(scaling)), event_shape)
        delta_ld = jnp.sum(weight * log_scaling)

        x_k = jnp.fft.rfftn(x, shape_info.space_shape, shape_info.space_axes)
        x_k, log_density = complex_affine_apply(
            x_k,
            log_density,
            scale=scaling,
            delta_ld=delta_ld,
            invert=reverse,
        )
        x = jnp.fft.irfftn(x_k, shape_info.space_shape, shape_info.space_axes)
        return x, log_density

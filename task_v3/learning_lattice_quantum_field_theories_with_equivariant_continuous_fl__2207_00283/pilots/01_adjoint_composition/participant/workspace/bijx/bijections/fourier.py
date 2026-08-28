import jax
import jax.numpy as jnp
from flax import nnx
from ..fourier import FourierMeta
from ..utils import Const, ShapeInfo
from .base import ApplyBijection

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

    Note:
        The scaling array must have the same shape as the output of jnp.fft.rfftn
        to ensure proper broadcasting during the Fourier-space multiplication.

    Example:
        >>> # Create momentum-dependent scaling
        >>> k = fft_momenta((8, 8))
        >>> scaling = jnp.exp(-0.1 * jnp.sum(k**2, axis=-1))
        >>> bijection = SpectrumScaling(scaling)
        >>> y, log_det = bijection.forward(phi, log_density)
    """

    def __init__(self, scaling: jax.Array | nnx.Variable, channel_dim: int = 0):
        self.channel_dim = channel_dim

        if not isinstance(scaling, nnx.Variable):
            scaling = Const(scaling)
        self.scaling_var = scaling
        self.shape_info = ShapeInfo(
            space_dim=len(scaling.shape), channel_dim=channel_dim
        )

    @property
    def scaling(self):
        return self.scaling_var.get_value()

    def scale(self, r, reverse=False):
        """Apply Fourier-space scaling transformation.

        Transforms the input through FFT, applies scaling, and transforms back.
        Computes the log-Jacobian contribution from the scaling factors.

        Args:
            r: Input array to transform.
            reverse: If True, apply inverse scaling (division).

        Returns:
            Tuple of (transformed_array, log_jacobian_contribution).
        """
        _, shape_info = self.shape_info.process_event(r.shape)
        meta = FourierMeta.create(shape_info.space_shape)
        r = jnp.fft.rfftn(r, shape_info.space_shape, shape_info.space_axes)
        r = r / self.scaling if reverse else r * self.scaling
        r = jnp.fft.irfftn(r, shape_info.space_shape, shape_info.space_axes)

        factor = meta.mr.astype(int) + meta.mi.astype(int)
        delta_ld = jnp.sum(factor * jnp.log(jnp.abs(self.scaling)))

        return r, delta_ld

    def apply(self, x, log_density, reverse=False, **kwargs):
        x, delta = self.scale(x, reverse=reverse)
        return x, log_density - delta if reverse else log_density + delta

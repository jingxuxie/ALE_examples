import typing as tp
import jax
import jax.numpy as jnp
from ..solvers import odeint_rk4
from .base import Bijection


class ContFlowRK4(Bijection):
    r"""Continuous normalizing flow using fixed-step RK4 solver.

    Wraps around a vector field to turn it into the bijection defined by
    solving the corresponding ODE, using a fixed-step RK4 solver.
    The vector field function should return both the velocity and the
    log-density time derivative for the instantaneous change of variables.

    The integration uses a uniform time grid with fixed step size.
    Gradients are always computed using backward solving (adjoint sensitivity).
    Consider :class:`ContFlowDiffrax` for more flexibility and advanced solvers.

    Args:
        vf: Vector field function with signature
            ``(t, x, **kwargs) -> (dx/dt, d(log_density)/dt)``.
        t_start: Integration start time.
        t_end: Integration end time.
        steps: Number of integration steps.

    Example:
        >>> def vector_field(t, x):
        ...     return -x, jnp.sum(x, axis=-1, keepdims=True)  # Linear flow
        >>> flow = ContFlowRK4(vector_field, steps=50)
        >>> y, log_det = flow.forward(x, log_density)
    """

    def __init__(
        self,
        # (t, x, **kwargs) -> dx/dt, d(log_density)/dt
        vf: tp.Callable,
        *,
        t_start: float = 0,
        t_end: float = 1,
        steps: int = 20,
    ):
        self.vf = vf
        self.t_start = t_start
        self.t_end = t_end
        self.steps = steps

    def solve_flow(
        self,
        x,
        log_density,
        *,
        # integration parameters
        t_start=None,
        t_end=None,
        steps=None,
        # arguments to vector field
        **kwargs,
    ):
        """Solve the ODE flow using RK4 integration.

        Args:
            x: Initial state array.
            log_density: Initial log density values.
            t_start: Override integration start time.
            t_end: Override integration end time.
            steps: Override number of integration steps.
            **kwargs: Additional arguments passed to vector field.

        Returns:
            Final state tuple (x_final, log_density_final).
        """
        t_start = t_start if t_start is not None else self.t_start
        t_end = t_end if t_end is not None else self.t_end
        steps = steps if steps is not None else self.steps

        delta_t = t_end - t_start
        sgn = jnp.where(delta_t < 0, -1.0, 1.0)

        def vf(s, state, args):
            x, log_density = state
            t = t_start + s * delta_t
            dx_dt, dld_dt = jax.tree.map(
                lambda x: sgn * x,
                self.vf(t, x, **args),
            )
            return dx_dt, dld_dt

        y0 = (x, log_density)
        y_final = odeint_rk4(
            vf,
            y0,
            1.0,
            kwargs,
            step_size=1.0 / steps,  # cannot be a jax tracer here
            start_time=0.0,
        )
        return y_final

    def forward(self, x, log_density, **kwargs):
        return self.solve_flow(x, log_density, **kwargs)

    def reverse(self, x, log_density, **kwargs):
        return self.solve_flow(
            x,
            log_density,
            t_start=self.t_end,
            t_end=self.t_start,
            **kwargs,
        )

import numpy as np
import skimage.segmentation
import sparse
import kwant
from kwant.continuum import discretize
from copy import deepcopy
from itertools import product
import scipy.sparse as sp
import scipy.sparse.linalg as sla
import scipy.spatial.distance as ssd
import scipy
from scipy import constants
import warnings

warnings.filterwarnings("ignore")

sigma_0 = np.eye(2)
sigma_x = np.array([[0, 1], [1, 0]])
sigma_y = np.array([[0, -1j], [1j, 0]])
sigma_z = np.array([[1, 0], [0, -1]])
_kinetic = "(t * (k_y^2 + k_x^2)) * kron(sigma_0, sigma_z)"
_soc = "- alpha * (kron(sigma_y, sigma_z) * k_x + kron(sigma_x, sigma_z) * k_y)"
TEMPLATE_STRING = _kinetic + _soc


def site_color_fn(syst, masks):
    in_sc = masks["sc_top"] + masks["sc_bot"]
    shape = masks["sc_top"].shape

    def site_color(ind):
        return "gold" if in_sc[mask_ind(ind, shape)] else "grey"

    return site_color


def system(X, Y, infinite=False):
    xs = np.sort(np.unique(X))
    ys = np.sort(np.unique(Y))
    a_x, a_y = xs[1] - xs[0], ys[1] - ys[0]
    lat = kwant.lattice.Monatomic([[a_x, 0], [0, a_y]], norbs=4, offset=(0, np.min(ys)))
    template = discretize(TEMPLATE_STRING, coords=("x", "y"), grid=lat)
    syst = kwant.Builder(
        kwant.TranslationalSymmetry([np.max(X) + a_x, 0]) if infinite else None
    )
    syst.fill(
        template,
        lambda s: np.any(np.isclose(xs, s.pos[0])) * np.any(np.isclose(ys, s.pos[1])),
        (xs[0], ys[0]),
    )
    if infinite:
        syst = kwant.wraparound.wraparound(syst)
    syst = syst.finalized()
    return syst


def mask_ind(site_ind, shape):
    return np.unravel_index(site_ind, shape, order="F")


def kwant_ind(inds, shape):
    return np.ravel_multi_index(inds, shape, order="F")


def kron_along_zero_axis(A, B):
    i, j, k = A.shape
    l, m = B.shape
    C = A[:, :, :, None, None] * B[None, None, None, :, :]
    return C.swapaxes(2, 3).reshape((i, j * l, k * m))


def _prep_matrices(N, inds):
    shape = (len(inds), N, N)
    coords = [range(len(inds)), inds, inds]
    return shape, coords


def sc_matrices(N, inds, which_sc, params):
    """TODO: This function can probably be more efficient"""
    shape, coords = _prep_matrices(N, inds)
    phases = [(-1) ** int(sc == "sc_top") * params["phase"] / 2 for sc in which_sc]
    re, im = zip(*[(np.cos(p), np.sin(p)) for p in phases])
    re_sc = sparse.COO(coords, re, shape=shape)
    im_sc = sparse.COO(coords, im, shape=shape)
    sc = kron_along_zero_axis(re_sc, np.kron(sigma_0, sigma_x))
    return sc + kron_along_zero_axis(im_sc, np.kron(sigma_0, sigma_y))


def zeeman_matrices(N, inds, params):
    shape, coords = _prep_matrices(N, inds)
    data = [params["E_Z"]] * len(inds)
    zeeman = sparse.COO(coords, data, shape=shape)
    return kron_along_zero_axis(zeeman, np.kron(sigma_x, sigma_0))


def onsite_matrices(N, inds, values):
    shape, coords = _prep_matrices(N, inds)
    mu = sparse.COO(coords, values, shape=shape)
    return kron_along_zero_axis(mu, np.kron(sigma_0, sigma_z))


def system_hamiltonian(syst, masks, params):
    """Adds missing Zeeman, superconductivity and chemical potential terms"""
    N = len(syst.sites)
    shape = masks["sc_top"].shape

    # Masks and inces for each material
    in_sc = masks["sc_top"] + masks["sc_bot"]
    in_normal = ~in_sc
    sc_inds = [i for i in range(N) if in_sc[mask_ind(i, shape)]]
    normal_inds = [i for i in range(N) if in_normal[mask_ind(i, shape)]]
    onsite_inds = sc_inds + normal_inds

    # Chemical potential values for each material
    mu_vals = [-params["mu_sc"]] * len(sc_inds) + [-params["mu_normal"]] * len(
        normal_inds
    )
    np.random.seed(params["disorder_seed"])
    disorder_vals = np.random.uniform(
        -params["disorder_strength"],
        params["disorder_strength"],
        len(sc_inds) + len(normal_inds),
    )
    onsite_vals = np.array(mu_vals) + np.array(disorder_vals)

    # Build matrices
    which_sc = [
        "sc_top" if masks["sc_top"][mask_ind(i, shape)] else "sc_bot" for i in sc_inds
    ]
    sc = sc_matrices(N, sc_inds, which_sc, params).sum(axis=0)
    zeeman = zeeman_matrices(N, normal_inds, params).sum(axis=0)
    mu = onsite_matrices(N, onsite_inds, onsite_vals).sum(axis=0)
    base_h = syst.hamiltonian_submatrix(params=params, sparse=True)

    return (base_h + sc + zeeman + mu).tocsr()


def boundary_sites(masks):
    cross = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    inner_masks, outer_masks = {}, {}
    for material in masks:
        mask = np.zeros_like(masks[material], dtype="bool")
        mask[masks[material]] = 1
        inner_masks[material] = skimage.segmentation.boundaries.dilation(
            ~(mask == 1), cross
        ) ^ ~(mask == 1)
        outer_masks[material] = skimage.segmentation.boundaries.dilation(
            mask == 1, cross
        ) ^ (mask == 1)
    return inner_masks, outer_masks


def perturbations(X, Y, masks, min_dist, mirror_sym=True):
    assert X.shape[1] % 2 == 1
    inner_boundary, outer_boundary = boundary_sites(masks)
    shape = masks["sc_top"].shape
    mid_ind = int(np.floor(shape[1] / 2))
    materials = ("sc_top", "sc_bot")

    perts = []
    for mat, add_site in product(materials, [True, False]):
        boundary = outer_boundary if add_site else inner_boundary
        boundary = np.copy(boundary[mat])
        if mirror_sym:
            boundary = boundary[:, : mid_ind + 1]
        yi, xi = np.where(boundary)

        # Sort along x and remove x = 0
        asrt = np.argsort(xi)
        yi, xi = yi[asrt], xi[asrt]
        yi, xi = yi[xi != 0], xi[xi != 0]
        sites = kwant_ind([yi, xi], shape)
        if mirror_sym:
            # Position of mirror symmetric partner
            partner_xi = shape[-1] - xi

            # Compute perturbations
            partner_sites = kwant_ind([yi, partner_xi], shape)
            perts.append(
                [
                    [(mat, mat), add_site, (s1, s2)]
                    for s1, s2 in zip(sites, partner_sites)
                ]
            )
        else:
            perts.append([[(mat,), add_site, (s1,)] for s1 in sites])

    # Add sites at the mirror plane
    mat = "sc_top"
    other_mat = "sc_bot"

    for add_site in [True, False]:
        boundaries = outer_boundary if add_site else inner_boundary
        sites = []
        boundary = np.copy(boundaries[mat])
        other_boundary = np.copy(boundaries[other_mat])
        yi = np.where(boundary[:, 0])[0]
        if len(yi):
            yi = yi[0]
        else:
            continue
        other_yi = np.max(np.where(other_boundary[:, 0])[0])
        sites += [kwant_ind([yi, 0], shape), kwant_ind([other_yi, 0], shape)]
        if mirror_sym:
            perts.append([[tuple(materials), add_site, tuple(sites)]])
        else:
            perts.append([[(materials[0],), add_site, (sites[0],)]])
            perts.append([[(materials[1],), add_site, (sites[1],)]])

    perts = sum(perts, [])
    perts = list(set([tuple(p) for p in perts]))
    return prune_perturbations(X, Y, masks, perts, min_dist)


def prune_perturbations(X, Y, masks, perturbations, min_dist, kind="sc"):
    """Remove perturbations which decrease distance between superconductorsbelow min_dist"""
    """TODO: make more efficient; no need to recompute the entire mask for each perturbation"""
    m1, m2 = f"{kind}_top", f"{kind}_bot"
    valid_perts = []
    for pert in perturbations:
        new_masks = update_masks(masks, pert)
        if minimum_mask_distance(X, Y, new_masks[m1], new_masks[m2]) >= min_dist:
            valid_perts.append(pert)
    return valid_perts


def minimum_mask_distance(X, Y, m1, m2):
    inner_bnd, _ = boundary_sites({"m1": m1, "m2": m2})
    m1_pos = np.dstack((X[inner_bnd["m1"]], Y[inner_bnd["m1"]]))[0]
    m2_pos = np.dstack((X[inner_bnd["m2"]], Y[inner_bnd["m2"]]))[0]
    # cdist is slightly faster than using np.linalg.norm
    return np.min((ssd.cdist(m1_pos, m2_pos)))


def update_masks(base_masks, pert_description):
    new_masks = deepcopy(base_masks)
    materials, bool_val, inds = pert_description
    shape = base_masks["sc_top"].shape
    for material, ind in zip(materials, inds):
        new_masks[material][mask_ind(ind, shape)] = bool_val
    return new_masks


def mumps_eigsh(matrix, k, sigma, **kwargs):
    """Call sla.eigsh with mumps support.

    Please see scipy.sparse.linalg.eigsh for documentation.
    """

    class LuInv(sla.LinearOperator):
        def __init__(self, matrix):
            instance = kwant.linalg.mumps.MUMPSContext()
            instance.analyze(matrix, ordering="pord")
            instance.factor(matrix)
            self.solve = instance.solve
            sla.LinearOperator.__init__(self, matrix.dtype, matrix.shape)

        def _matvec(self, x):
            return self.solve(x.astype(self.dtype))

    opinv = LuInv(matrix - sigma * sp.identity(matrix.shape[0]))
    es, wfs = sla.eigsh(matrix, k, sigma=sigma, OPinv=opinv, **kwargs)
    # Make sure eigenvectors are orthogonal in the presence of degeneracies
    orth_wfs = np.linalg.qr(wfs)[0]
    es = np.diag(orth_wfs.T.conj() @ matrix @ orth_wfs).real
    return es, orth_wfs


def effective_hamiltonians(h0, wfs, perturbations):
    h_psi = sparse.tensordot(perturbations, wfs, axes=((2), (0)), return_type="COO")
    psi_h_psi = sparse.tensordot(wfs.conj(), h_psi, axes=((0), (1)))
    return h0[None, :, :] + psi_h_psi.swapaxes(0, 1)


def dispersion(k_x, X, Y, masks, params):
    syst = system(X, Y, infinite=True)
    h = system_hamiltonian(syst, masks, dict(params, k_x=k_x))
    return mumps_eigsh(h, 8, 0)


def ehams_at_k(perts, e_wf_k, eham_k, params):
    _, wf = e_wf_k
    N = wf.shape[0] // 4  # number of sites
    phams = []
    for (materials, bool_val, inds) in perts:
        sign = 1 if bool_val else -1
        if "sc" in materials[0]:
            zeeman_mat = zeeman_matrices(N, inds, params).sum(axis=0)
            sc_mat = sc_matrices(N, inds, materials, params).sum(axis=0)
            onsite_vals = [-params["mu_sc"] + params["mu_normal"]] * len(inds)
            onsite_mat = onsite_matrices(N, inds, onsite_vals).sum(axis=0)
            phams.append(sign * (onsite_mat + sc_mat - zeeman_mat))
        else:
            onsite_vals = [-params["V"]] * len(inds)
            onsite_mat = onsite_matrices(N, inds, onsite_vals).sum(axis=0)
            phams.append(sign * onsite_mat)
    return effective_hamiltonians(eham_k, wf, sparse.stack(phams))


def gaps_at_k(ehams):
    return np.min(np.abs(np.linalg.eigvalsh(ehams)), axis=1)


def chunks(lst, n):
    """
    Yield successive n-sized chunks from lst.
    From https://stackoverflow.com/a/312464
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def _prep_masks(L_x, L_y, a_x, a_y):
    x = np.arange(0, L_x, a_x, dtype=float)
    y = np.arange(-L_y / 2, L_y / 2 + a_y, a_y, dtype=float)
    X, Y = np.meshgrid(x, y)
    base_mask = np.zeros((len(y), len(x)), dtype=int)
    masks = {
        "sc_top": np.zeros_like(base_mask, dtype=bool),
        "sc_bot": np.zeros_like(base_mask, dtype=bool),
    }
    return X, Y, masks


def straight_geometry(L_x, L_y, a_x, a_y, W):
    X, Y, masks = _prep_masks(L_x, L_y, a_x, a_y)
    masks["sc_top"][Y > W / 2] = True
    masks["sc_bot"][Y < -W / 2] = True
    return X, Y, masks


def zigzag_geometry(L_x, L_y, a_x, a_y, W, z_y):
    X, Y, masks = _prep_masks(L_x, L_y, a_x, a_y)

    def curve(x):
        if x % L_x < L_x / 2:
            return 4 * z_y / L_x * (x % (L_x / 2)) - z_y
        else:
            return -4 * z_y / L_x * (x % (L_x / 2)) + z_y

    curve = np.vectorize(curve)
    y_offset = W / np.cos(np.arctan(4 * z_y / L_x)) if z_y != 0 else W
    masks["sc_top"][Y >= curve(X) + y_offset / 2] = True
    masks["sc_bot"][Y <= curve(X) - y_offset / 2] = True
    return X, Y, masks

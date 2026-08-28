import utils
import numpy as np
from matplotlib import pyplot as plt
from copy import deepcopy
from IPython.display import clear_output
from scipy import ndimage
import pickle


def live_plot(actual_gaps, predicted_gaps, masks):
    """
    Plot optimization progress.
    taken from https://github.com/ziofil/live_plot/blob/master/live_plot_example.ipynb
    """
    clear_output(wait=True)
    fig, ax = plt.subplots(1, 2, figsize=(10, 5))
    ax[0].plot(range(len(actual_gaps)), actual_gaps, label="Exact")
    ax[0].plot(
        range(1, len(predicted_gaps) + 1), predicted_gaps, label="Perturbation theory"
    )
    ax[0].set_xlabel("Epoch")
    ax[0].set_ylabel("Gap")
    ax[0].legend()
    color_masks = 1*masks["sc_top"] - 1*masks["sc_bot"]
    ax[1].imshow(color_masks, cmap="RdBu_r", origin="lower")
    ax[1].axis("off")
    plt.tight_layout()
    plt.show()


def geometry_optimization(client, **optimization_pars):
    # Read parameters
    X = optimization_pars["X"]
    Y = optimization_pars["Y"]
    start_masks = optimization_pars["start_masks"]
    num_epochs = optimization_pars["num_epochs"]
    num_iters = optimization_pars["num_iters"]
    min_dist = optimization_pars["min_dist"]
    ham_params = optimization_pars["ham_params"]
    ks = optimization_pars["ks"]
    mu_range = optimization_pars.get(
        "mu_range", [ham_params["mu_normal"], ham_params["mu_normal"]]
    )
    EZ_range = optimization_pars.get("EZ_range", [ham_params["E_Z"], ham_params["E_Z"]])
    filter_epoch = optimization_pars.get("filter_epoch", np.inf)
    filter_settings = optimization_pars.get("filter_settings", {})
    parameter_seed = optimization_pars.get("parameter_seed", 0)
    disorder_seed = optimization_pars.get("disorder_seed", lambda epoch: epoch)
    filename = optimization_pars.get("filename", None)
    mirror_sym = optimization_pars.get("mirror_sym", True)
    homogeneous_mu = optimization_pars.get("homogeneous_mu", True)

    # Initialize optimization variables
    masks = deepcopy(start_masks)
    masks_by_epoch = [masks]
    actual_gaps, predicted_gaps = [], []
    np.random.seed(parameter_seed)

    for epoch in range(num_epochs):
        epoch_params = dict(ham_params)
        if homogeneous_mu:
            epoch_params["mu_normal"] = epoch_params["mu_sc"] = np.random.uniform(*mu_range)
        else:
            epoch_params["mu_normal"] = np.random.uniform(*mu_range)
        epoch_params["E_Z"] = np.random.uniform(*EZ_range)
        epoch_params["disorder_seed"] = disorder_seed(epoch)

        def wrapped_dispersion(k):
            return utils.dispersion(k, X, Y, masks, epoch_params)

        es_wfs = client.map(wrapped_dispersion, ks)
        lowest_band = client.map(lambda es_wfs: np.min(np.abs(es_wfs[0])), es_wfs)

        # Main optimization loop
        current_ehams_k = client.map(lambda e_wf: np.diag(e_wf[0]), es_wfs)
        for iteration in range(num_iters):
            # Get all perturbations, already pruned
            perts = utils.perturbations(
                X, Y, masks, min_dist, mirror_sym=mirror_sym
            )

            # Compute perturbed es in the cluster
            def wrapped_ehams(e_wf_k, eham_k):
                return utils.ehams_at_k(perts, e_wf_k, eham_k, epoch_params)

            p_ehams_k = client.map(wrapped_ehams, es_wfs, current_ehams_k)

            # Compute gap for each perturbation
            gap_at_k = client.map(utils.gaps_at_k, p_ehams_k)
            dispersion_gap = client.submit(
                lambda x: np.min(x, axis=0), gap_at_k
            ).result()
            selected_pert = np.argmax(dispersion_gap)

            # Update optimization variables and free up memory in the cluster
            masks = utils.update_masks(masks, perts[selected_pert])
            current_ehams_k = client.map(lambda eham: eham[selected_pert], p_ehams_k)
            [[task.release() for task in job] for job in [gap_at_k, p_ehams_k]]

        if epoch > 0 and epoch % filter_epoch == 0:
            for region in ["sc_top", "sc_bot"]:
                masks[region] = ndimage.median_filter(masks[region], **filter_settings)

        predicted_gaps.append(dispersion_gap[selected_pert])
        actual_gaps.append(np.min(client.gather(lowest_band)))
        masks_by_epoch.append(deepcopy(masks))

        # Free up memory in the cluster
        [task.release() for task in es_wfs]

        live_plot(actual_gaps, predicted_gaps, masks)
        if filename:
            with open(filename, "wb") as f:
                data = {
                    "predicted_gaps": predicted_gaps,
                    "actual_gaps": actual_gaps,
                    "masks_by_epoch": masks_by_epoch,
                }
                pickle.dump(data, f)

    return predicted_gaps, actual_gaps, masks_by_epoch

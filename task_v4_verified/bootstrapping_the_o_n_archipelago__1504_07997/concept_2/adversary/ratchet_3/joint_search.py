import concurrent.futures
import json
import os

import numpy as np

import search


def main():
    cases, witnesses, validations = [], [], []
    for serial in range(8):
        instance, witness, specification = search.candidate("spin_aliases", serial, seed_offset=900001)
        identifier = "joint_%02d" % serial
        instance["id"] = witness["id"] = identifier
        instance["family"] = "joint_alias_cancellation"
        vectors = np.asarray([atom["ope"] for atom in witness["atoms"]])
        magnitudes = np.linalg.norm(vectors, axis=1)
        vectors[:, 0] = magnitudes * np.sqrt(0.5)
        vectors[:, 1] = magnitudes * np.sqrt(0.5) * np.where(np.arange(len(vectors)) % 2, -1, 1)
        vectors[0, 0] = 0.73
        for atom, vector in zip(witness["atoms"], vectors):
            atom["ope"] = vector.tolist()
        support = [atom["index"] for atom in witness["atoms"]]
        products = np.stack([vectors[:, 0] ** 2, vectors[:, 0] * vectors[:, 1], vectors[:, 1] ** 2], axis=1)
        target = np.asarray(instance["design"])[:, support] @ products
        instance["target"] = target.tolist()
        instance["scales"] = np.maximum(0.15, np.abs(target)).tolist()
        instance["trace_budget"] = float(np.sum(vectors ** 2) * 1.03)
        validations.append(dict(search.validate(instance, witness), id=identifier, specification=specification))
        cases.append(instance)
        witnesses.append(witness)
    search.write(search.HERE / "joint_candidates.json", {"instances": cases})
    search.write(search.HERE / "joint_witnesses.json", {"cases": witnesses})
    search.write(search.HERE / "joint_validation.json", {"cases": validations})
    cpus = sorted(os.sched_getaffinity(0))[-40:-32]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(search.run, instance, 60, cpus[index], "joint_screening") for index, instance in enumerate(cases)]
        records = [future.result() for future in futures]
    search.write(search.HERE / "joint_screening_results.json", {"records": records})
    failures = [record for record in records if not record["valid"] and record["reason"] == "moment residual"
                and record["exit_code"] == 0 and not record["timed_out"] and record["continuous_attempted"] and not record["stage_errors"]]
    failures.sort(key=lambda record: record["residual"], reverse=True)
    instances = {instance["id"]: instance for instance in cases}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(search.run, instances[record["id"]], 300, cpus[index], "confirmation")
                   for index, record in enumerate(failures[:4])]
        confirmed = [future.result() for future in futures]
    search.write(search.HERE / "joint_confirmation_results.json", {"records": confirmed})


if __name__ == "__main__":
    main()

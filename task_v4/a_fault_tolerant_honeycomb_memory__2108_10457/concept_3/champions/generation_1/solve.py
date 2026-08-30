import csv
import os
import sys
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
sys.dont_write_bytecode = True
if 'TASK_ROOT' in os.environ:
    sys.path.insert(0, str(Path(os.environ['TASK_ROOT']) / 'workspace'))
elif len(sys.argv) > 1:
    sys.path.insert(0, str(Path(sys.argv[1]).resolve().parent.parent / 'workspace'))

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp


def read_rows(path):
    with open(path, newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for field in ('noise', 'code_distance', 'num_shots', 'num_correct'):
            if field in row:
                row[field] = float(row[field])
        if 'num_shots' in row:
            row['failures'] = row['num_shots'] - row['num_correct']
    return rows


def family(row):
    observable = row['preserved_observable']
    if row['circuit_style'].startswith('surface'):
        observable = 'symmetric'
    return row['circuit_style'], row['decoder'], observable


def probability_from_latent(latent):
    hazard = np.exp(np.clip(latent, -60, 6))
    return -0.5 * np.expm1(-2 * hazard)


def latent_from_probability(probability):
    return np.log(-0.5 * np.log1p(-2 * np.clip(probability, 1e-25, .499)))


def binomial_loss(latent, shots, failures):
    hazard = np.exp(np.clip(latent, -60, 6))
    probability = -0.5 * np.expm1(-2 * hazard)
    loss = -np.sum(failures * np.log(probability) + (shots-failures) * np.log1p(-probability))
    derivative = (shots * probability - failures) / (probability * (1-probability))
    derivative *= hazard * np.exp(-2 * hazard)
    return loss, derivative


def fit_linear(matrix, shots, failures, offset=None, penalty=None, initial=None, bounds=None):
    if offset is None:
        offset = np.zeros(len(shots))
    if penalty is None:
        penalty = np.zeros(matrix.shape[1])
    if initial is None:
        target = latent_from_probability((failures+.1) / (shots+.2)) - offset
        weights = np.sqrt(np.minimum(failures+.1, 1000))
        initial = np.linalg.lstsq(matrix * weights[:, None], target * weights, rcond=None)[0]
    if bounds is None:
        bounds = [(-100, 100)] * matrix.shape[1]
    scale = max(float(np.sum(failures)), 1)

    def objective(coefficients):
        loss, derivative = binomial_loss(matrix @ coefficients + offset, shots, failures)
        loss += np.sum(penalty * coefficients**2)
        gradient = matrix.T @ derivative + 2 * penalty * coefficients
        return loss / scale, gradient / scale

    result = minimize(objective, initial, jac=True, method='L-BFGS-B', bounds=bounds,
                      options={'maxiter': 1000, 'ftol': 1e-12, 'gtol': 1e-8})
    if not np.all(np.isfinite(result.x)):
        raise ValueError('Nonfinite fitted coefficients')
    return result.x


class DistanceModel:
    def __init__(self, style, curvature):
        self.beta = 1.1 if style.startswith('surface') else 0.0
        self.curvature = curvature

    def features(self, rows):
        distance = np.array([row['code_distance'] / 4 for row in rows])
        noise = np.log(np.array([row['noise'] for row in rows]) / .001)
        curved_noise = np.exp(noise / 2) if self.curvature == 'sqrt' else noise**2
        matrix = np.column_stack([np.ones(len(rows)), noise, curved_noise,
                                  distance, distance * noise, distance * curved_noise,
                                  np.log(distance)])
        return matrix, self.beta * np.log(distance)

    def fit(self, rows):
        matrix, offset = self.features(rows)
        shots = np.array([row['num_shots'] for row in rows])
        failures = np.array([row['failures'] for row in rows])
        self.coefficients = fit_linear(matrix, shots, failures, offset,
                                       np.array([.01] * 6 + [10]))
        self.max_distance = max(row['code_distance'] for row in rows)
        self.corrections = {}
        for noise in sorted({row['noise'] for row in rows}):
            indexes = [index for index, row in enumerate(rows) if row['noise'] == noise]
            distances = np.array([(rows[index]['code_distance'] - self.max_distance) / 4
                                  for index in indexes])
            local_matrix = np.column_stack([np.ones(len(indexes)), distances])
            prior = matrix[indexes] @ self.coefficients + offset[indexes]
            self.corrections[noise] = fit_linear(
                local_matrix, shots[indexes], failures[indexes], prior,
                np.array([100., 100.]), np.zeros(2), [(-3, 3)] * 2)
        return self

    def predict(self, rows):
        matrix, offset = self.features(rows)
        latent = matrix @ self.coefficients + offset
        for index, row in enumerate(rows):
            if row['noise'] in self.corrections:
                correction = self.corrections[row['noise']]
                latent[index] += correction[0] + correction[1] * (row['code_distance'] - self.max_distance) / 4
        return probability_from_latent(latent)


class LowNoiseModel:
    def fit(self, rows):
        self.models = {}
        for distance in sorted({row['code_distance'] for row in rows}):
            selected = [row for row in rows if row['code_distance'] == distance]
            levels = sorted({row['noise'] for row in selected})
            useful = [noise for noise in levels
                      if sum(row['failures'] for row in selected if row['noise'] == noise) >= 20]
            cutoff = levels[min(2, len(levels)-1)]
            if useful:
                cutoff = max(cutoff, useful[min(2, len(useful)-1)])
            selected = [row for row in selected if row['noise'] <= cutoff]
            reference = min(row['noise'] for row in selected)
            noise = np.log(np.array([row['noise'] for row in selected]) / reference)
            shots = np.array([row['num_shots'] for row in selected])
            failures = np.array([row['failures'] for row in selected])
            matrix = np.column_stack([np.ones(len(selected)), noise])
            power_coefficients = fit_linear(matrix, shots, failures, bounds=[(-100, 100), (.5, 12)])
            style, decoder, observable = family(selected[0])
            if style.startswith('surface'):
                leading_power = (distance+1) / 2
            elif style.endswith('EM3_v2'):
                leading_power = distance / 4
            elif observable == 'H':
                leading_power = max(2, distance / 2 - 1)
            else:
                leading_power = distance / 2
            powers = np.array([leading_power, leading_power+1])
            series_matrix = noise[:, None] * powers[None, :]
            initial_probability = np.mean(((failures+.1) / (shots+.2))[noise == 0])
            initial = np.full(2, np.log(initial_probability / 2))
            scale = max(float(np.sum(failures)), 1)

            def objective(coefficients):
                terms = series_matrix + coefficients[None, :]
                latent = logsumexp(terms, axis=1)
                loss, derivative = binomial_loss(latent, shots, failures)
                ratios = np.exp(terms-latent[:, None])
                return loss / scale, ratios.T @ derivative / scale

            result = minimize(objective, initial, jac=True, method='L-BFGS-B', bounds=[(-80, 5)] * 2,
                              options={'maxiter': 700, 'ftol': 1e-12, 'gtol': 1e-8})
            if not np.all(np.isfinite(result.x)):
                raise ValueError('Nonfinite fitted series')
            self.models[distance] = reference, power_coefficients, powers, result.x
        return self

    def predict(self, rows):
        predictions = []
        for row in rows:
            reference, coefficients, powers, series = self.models[row['code_distance']]
            noise = np.log(row['noise'] / reference)
            power_probability = probability_from_latent(coefficients[0] + coefficients[1] * noise)
            series_probability = probability_from_latent(logsumexp(powers * noise + series))
            predictions.append(np.exp(.25 * np.log(power_probability) + .75 * np.log(series_probability)))
        return np.array(predictions)


def predict(training, queries):
    predictions = np.zeros(len(queries))
    probability_floor = max(1e-15, .5 / max(row['num_shots'] for row in training))
    for group in sorted({family(row) for row in queries}):
        selected = [row for row in training if family(row) == group]
        query_indexes = [index for index, row in enumerate(queries) if family(row) == group]
        distance_models = [DistanceModel(group[0], curvature).fit(selected)
                           for curvature in ('sqrt', 'quadratic')]
        low_noise_model = LowNoiseModel().fit(selected)
        minimum_noise = min(row['noise'] for row in selected)
        noise_levels = sorted({row['noise'] for row in selected}
                              | {queries[index]['noise'] for index in query_indexes})
        for distance in sorted({queries[index]['code_distance'] for index in query_indexes}):
            indexes = [index for index in query_indexes if queries[index]['code_distance'] == distance]
            prototype = queries[indexes[0]]
            grid = [{**prototype, 'noise': noise} for noise in noise_levels]
            log_predictions = np.mean([np.log(model.predict(grid)) for model in distance_models], axis=0)
            if distance in low_noise_model.models:
                low_indexes = [index for index, noise in enumerate(noise_levels) if noise < minimum_noise]
                if low_indexes:
                    log_predictions[low_indexes] = np.log(low_noise_model.predict([grid[index] for index in low_indexes]))
            monotone = np.maximum.accumulate(np.exp(log_predictions))
            lookup = dict(zip(noise_levels, monotone))
            for index in indexes:
                predictions[index] = lookup[queries[index]['noise']]
    return np.clip(predictions, probability_floor, .5)


def main():
    if len(sys.argv) != 4:
        raise SystemExit('Usage: python solve.py TRAIN_CSV QUERY_CSV OUTPUT_CSV')
    training_path, query_path, output_path = sys.argv[1:]
    training = read_rows(training_path)
    queries = read_rows(query_path)
    probabilities = predict(training, queries)
    with open(output_path, 'w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['query_id', 'p_failure'])
        for row, probability in zip(queries, probabilities):
            writer.writerow([row['query_id'], format(float(probability), '.17g')])


if __name__ == '__main__':
    main()

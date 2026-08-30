from investigate import *
import itertools

random = np.random.default_rng(81726)
best = 0
rotation = ROTATION_NUMERATORS/5
for trial in range(200000):
    if trial % 10 == 0:
        rotation, triangular = np.linalg.qr(random.normal(size=(4,4)))
    if min(rotation[:,0]**2) < .01:
        continue
    first, second, third = rotation[:,:3].T
    plateau = max(first**-2*second**2)*random.uniform(1.001,3)
    positive = 10**random.uniform(-1,2)
    slope = random.uniform(-2,2)*np.sqrt(plateau)
    determinant_curve = positive*(plateau-slope**2)
    if determinant_curve <= 0:
        continue
    width = np.sqrt(plateau/determinant_curve)
    curvature = positive*(second-slope*first)**2+(plateau-slope*slope)*third**2
    centers = (plateau*first-slope*second)*third/curvature
    score = min(abs(centers))/width
    if score > best:
        best = score
        print('BEST',trial, score, plateau, positive, slope, centers, width, rotation.tolist(),flush=True)
        Path('geometry_best.json').write_text(json.dumps(dict(score=score, plateau=plateau, positive=positive, slope=slope, centers=centers.tolist(), width=width, rotation=rotation.tolist())))
print('DONE',best)

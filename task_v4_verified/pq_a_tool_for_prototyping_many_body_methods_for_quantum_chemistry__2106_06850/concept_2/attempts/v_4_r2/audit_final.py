import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from api import CONSTRAINTS,robust_screen
from oracle import DeterminantCC

filename=Path('submission.json')
raw=filename.read_bytes()
source=json.loads(raw)
assert set(source)=={'schema_version','orbital_energies','pair_matrix','amplitudes'}
assert source['schema_version']==1
assert source['orbital_energies']==CONSTRAINTS['orbital_energies']
assert len(raw)<=CONSTRAINTS['artifact_bytes_max']
matrix=np.array(source['pair_matrix'])
amplitudes=np.array(source['amplitudes'])
assert matrix.shape==(15,15) and amplitudes.shape==(18,)
assert np.isfinite(matrix).all() and np.isfinite(amplitudes).all()
oracle=DeterminantCC()
hamiltonian,one_body,tensor=oracle.hamiltonian(source['orbital_energies'],matrix)
cluster=np.einsum('k,kij->ij',amplitudes,oracle.generators)
positive=expm(cluster)
inverse=expm(-cluster)
transformed=inverse@hamiltonian@positive
commutators=np.array([transformed@generator-generator@transformed for generator in oracle.generators])
jacobian=commutators[:,oracle.targets,oracle.reference].T
gradient=commutators[:,oracle.reference,oracle.reference]
multipliers=np.linalg.solve(jacobian.T,-gradient)
left_row=oracle.ref.copy()
left_row[oracle.targets]=multipliers
left=left_row@inverse
right=positive[:,oracle.reference]
density=oracle.rdm(left,right)
occupations=np.linalg.eigvalsh((density+density.T)/2)
energies,vectors=np.linalg.eigh(hamiltonian)
exact_density=oracle.rdm(vectors[:,0],vectors[:,0])
right_density=oracle.rdm(right,right)/(right@right)
fock=one_body+sum(tensor[:,occupied,:,occupied] for occupied in range(3))
audit={
    'artifact_sha256':hashlib.sha256(raw).hexdigest(),
    'artifact_bytes':len(raw),
    'independent_expm_cc_residual':float(max(abs(transformed[oracle.targets,oracle.reference]))),
    'independent_expm_lambda_residual':float(max(abs(gradient+jacobian.T@multipliers))),
    'independent_expm_energy_error':float(abs(transformed[oracle.reference,oracle.reference]-energies[0])),
    'independent_expm_dad':float(np.linalg.norm(density-density.T)/np.sqrt(3)),
    'independent_expm_population_violation':float(max(-occupations[0],occupations[-1]-1,0)),
    'lambda_occupations':occupations.tolist(),
    'exact_occupations':np.linalg.eigvalsh(exact_density).tolist(),
    'right_occupations':np.linalg.eigvalsh(right_density).tolist(),
    'biorthogonal_norm':float(left@right),
    'density_trace':float(np.trace(density)),
    'canonical_fock_error':float(np.max(abs(fock-np.diag(source['orbital_energies'])))),
    'hamiltonian_hermiticity_error':float(np.max(abs(hamiltonian-hamiltonian.T))),
}
assert audit['independent_expm_cc_residual']<2e-9
assert audit['independent_expm_lambda_residual']<2e-9
assert abs(audit['biorthogonal_norm']-1)<2e-8
assert abs(audit['density_trace']-3)<2e-8
assert audit['canonical_fock_error']<2e-10
assert audit['hamiltonian_hermiticity_error']<2e-10
report=robust_screen(matrix,amplitudes,oracle)
Path('submission.validation.json').write_text(json.dumps(report,indent=2))
audit['robust_summary']={key:value for key,value in report.items() if key not in ['points','adaptive_response']}
audit['adaptive_gradient_norm']=report['adaptive_response']['norm']
audit['required_population_violation']=CONSTRAINTS['population_violation_min']
Path('final_audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps(audit,indent=2),flush=True)

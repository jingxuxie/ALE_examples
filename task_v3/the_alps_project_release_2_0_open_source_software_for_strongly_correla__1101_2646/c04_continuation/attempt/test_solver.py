import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import subprocess
import sys
import unittest
from pathlib import Path
import numpy as np
import scipy.linalg as la
from solve import solve, pack, unpack
from research import generated, green_from_spectrum


def request_from_case(case):
    return {'iw':case['iw'].tolist(), 'G_iw':pack(case['data']),
            'moments':[pack(moment) for moment in case['moments']],
            'h0':pack(case['bare']), 'omega':case['omega'].tolist(),
            'eta':case['eta'], 'support':case['support'], 'absolute_data_error':2e-13}


class ReconstructionTests(unittest.TestCase):
    def verify_physics(self,request,result):
        green = unpack(result['G_retarded'])
        sigma = unpack(result['Sigma_retarded'])
        dimension = len(request['h0']['real'])
        self.assertEqual(green.shape,(len(request['omega']),dimension,dimension))
        self.assertEqual(sigma.shape,green.shape)
        self.assertTrue(np.all(np.isfinite(green)))
        self.assertTrue(np.all(np.isfinite(sigma)))
        spectral = -(green-green.conj().swapaxes(-1,-2))/(2j*np.pi)
        self.assertGreater(np.min(np.linalg.eigvalsh(spectral)),-1e-10)
        points = np.asarray(request['omega'])+1j*request['eta']
        expected = points[:,None,None]*np.eye(dimension)-unpack(request['h0'])-np.linalg.inv(green)
        np.testing.assert_allclose(sigma,expected,rtol=2e-12,atol=2e-12)
        return green

    def test_finite_noncommuting_spectra(self):
        for seed,dimension in [(1,2),(2,3),(4,4)]:
            with self.subTest(dimension=dimension):
                case = generated('finite',seed,dimension,error=2e-13)
                request = request_from_case(case)
                prediction = self.verify_physics(request,solve(request))
                self.assertLess(la.norm(prediction-case['target'])/la.norm(case['target']),2e-4)

    def test_dyson_static_shift(self):
        case = generated('finite',6,2,error=0)
        case['bare'] = case['bare']+np.array([[.7,.2j],[-.2j,-.4]])
        request = request_from_case(case)
        prediction = self.verify_physics(request,solve(request))
        self.assertLess(la.norm(prediction-case['target'])/la.norm(case['target']),1e-4)

    def test_no_dynamic_self_energy(self):
        bare = np.array([[.2,.3+.4j],[.3-.4j,-.8]])
        iw = np.geomspace(.07,60,90)
        omega = np.linspace(-2,2,161)
        identity = np.eye(2)
        request = {'iw':iw.tolist(),'G_iw':pack(np.linalg.inv(1j*iw[:,None,None]*identity-bare)),
                   'moments':[pack(identity),pack(bare),pack(bare@bare)],'h0':pack(bare),
                   'omega':omega.tolist(),'eta':.08,'support':[-2,2],'absolute_data_error':2e-13}
        prediction = self.verify_physics(request,solve(request))
        expected = np.linalg.inv((omega+.08j)[:,None,None]*identity-bare)
        np.testing.assert_allclose(prediction,expected,rtol=1e-11,atol=1e-11)

    def test_continuous_bands(self):
        for kind,seed,dimension,eta in [('scalarband',3,2,.06),('band',1,3,.12),('band2',2,4,.12)]:
            with self.subTest(kind=kind):
                case = generated(kind,seed,dimension,error=0,eta=eta)
                request = request_from_case(case)
                prediction = self.verify_physics(request,solve(request))
                tolerance = .12 if kind=='band2' else 2e-5
                self.assertLess(la.norm(prediction-case['target'])/la.norm(case['target']),tolerance)

    def test_larger_matrix_bath(self):
        rng = np.random.default_rng(193)
        dimension = 4
        total = 32
        hamiltonian = rng.normal(size=(total,total))+1j*rng.normal(size=(total,total))
        hamiltonian = (hamiltonian+hamiltonian.conj().T)/12
        energies,vectors = la.eigh(hamiltonian)
        residues = np.einsum('ia,ja->aij',vectors[:dimension],vectors[:dimension].conj())
        iw = np.geomspace(.04,80,110)
        omega = np.linspace(energies[0]-.3,energies[-1]+.3,181)
        data = green_from_spectrum(1j*iw,energies,residues)
        data += 2e-14*(rng.uniform(-1,1,data.shape)+1j*rng.uniform(-1,1,data.shape))
        moments = [np.eye(dimension),hamiltonian[:dimension,:dimension],(hamiltonian@hamiltonian)[:dimension,:dimension]]
        case = dict(iw=iw,omega=omega,data=data,moments=moments,bare=moments[1],eta=.1,support=[energies[0]-.1,energies[-1]+.1])
        request = request_from_case(case)
        prediction = self.verify_physics(request,solve(request))
        expected = green_from_spectrum(omega+.1j,energies,residues)
        self.assertLess(la.norm(prediction-expected)/la.norm(expected),5e-4)

    def test_band_contour_integral(self):
        from bandfit import band_green,band_green_exact
        rng = np.random.default_rng(709)
        matrices = rng.normal(size=(5,3,3))+1j*rng.normal(size=(5,3,3))
        matrices = (matrices+matrices.conj().swapaxes(-1,-2))*.12
        nodes = np.linspace(-2,2,31)+.13j
        exact = band_green_exact(nodes,matrices[0],matrices[1:])
        quadrature = band_green(nodes,matrices[0],matrices[1:],count=4096)
        np.testing.assert_allclose(exact,quadrature,rtol=1e-10,atol=1e-10)

    def test_unitary_covariance(self):
        case = generated('finite',3,3,error=0)
        request = request_from_case(case)
        original = unpack(solve(request)['G_retarded'])
        rng = np.random.default_rng(91)
        unitary,_ = la.qr(rng.normal(size=(3,3))+1j*rng.normal(size=(3,3)))
        case['data'] = unitary.conj().T@case['data']@unitary
        case['moments'] = [unitary.conj().T@moment@unitary for moment in case['moments']]
        case['bare'] = unitary.conj().T@case['bare']@unitary
        rotated = unpack(solve(request_from_case(case))['G_retarded'])
        np.testing.assert_allclose(rotated,unitary.conj().T@original@unitary,rtol=1e-5,atol=1e-6)

    def test_cli(self):
        directory = Path(__file__).resolve().parent
        case = generated('finite',2,2,error=0)
        source = directory/'test_request.json'
        destination = directory/'test_result.json'
        request = request_from_case(case)
        source.write_text(json.dumps(request))
        subprocess.run([sys.executable,str(directory/'solve.py'),'--input',str(source),'--output',str(destination)],check=True,timeout=120)
        self.verify_physics(request,json.loads(destination.read_text()))


if __name__=='__main__':
    unittest.main()

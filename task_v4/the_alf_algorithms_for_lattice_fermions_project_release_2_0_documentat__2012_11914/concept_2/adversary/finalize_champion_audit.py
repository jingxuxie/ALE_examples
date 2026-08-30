import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
COHERENT = ROOT / "adversary/champion_coherent_flux_v1"
specification = importlib.util.spec_from_file_location("final_audit_helpers", ROOT / "adversary/cluster_champion_failures.py")
helpers = importlib.util.module_from_spec(specification)
specification.loader.exec_module(helpers)
helpers.DIRECTORY = COHERENT


def main():
    candidate_bytes = (COHERENT / "candidate.json").read_bytes()
    digest = hashlib.sha256(candidate_bytes).hexdigest()
    assert hashlib.sha256((ROOT / "attempts/v_1/submission.json").read_bytes()).hexdigest() == digest
    candidate = json.loads(candidate_bytes)["stages"]
    baseline = json.loads((COHERENT / "baseline.json").read_text())["stages"]
    fixtures = json.loads((COHERENT / "near_uniform_small_worst_fixtures.json").read_text())
    anchor = next(instance for instance in fixtures["instances"] if instance["id"] == fixtures["worst_records"][0]["case_id"])
    random = np.random.default_rng(82845000)
    instances = []
    for index in range(128):
        instance = copy.deepcopy(anchor)
        instance["id"] = "coherent_neighborhood_" + str(index)
        for bond in instance["bonds"]:
            bond[3] *= float(random.uniform(0.98,1.02))
            bond[4] += float(random.uniform(-0.015,0.015))
        instance["site_potential"] = (np.array(instance["site_potential"]) + random.uniform(-0.015,0.015,len(instance["site_potential"]))).tolist()
        instances.append(instance)
    records = []
    for offset in range(0,len(instances),32):
        records.extend(helpers.audit.audit_batch(instances[offset:offset+32],candidate,baseline,["X0","X1","Y0","Y1","V"],[0.4,0.6]))
    local = helpers.save_regime("near_uniform_local",instances,records,{"purpose":"robustness neighborhood only, never use these exact fixtures as generation-2 public training", "anchor":anchor["id"],"seed":82845000,"count":128,"perturbations":"independent bond amplitude factors U[.98,1.02], phase additions U[-.015,.015], onsite additions U[-.015,.015]"})
    directories = {"broad":ROOT/'adversary/champion_audit_v1',"large_tori":ROOT/'adversary/champion_audit_large_v1',"focused_and_controls":ROOT/'adversary/champion_audit_clusters_v1',"coherent":COHERENT}
    summaries = {name:json.loads((directory/'summary.json').read_text()) for name,directory in directories.items()}
    for data in summaries.values():
        assert data['candidate_sha256'] == digest
    independent_regimes = [entry for name,data in summaries.items() for regime,entry in data['regimes'].items() if regime not in ('local_robustness','uniform_hopping_geometry')]
    controls = [summaries['focused_and_controls']['regimes'][name] for name in ('local_robustness','uniform_hopping_geometry')] + [local]
    ablations = [json.loads((directories['focused_and_controls']/'ablation_records.json').read_text()),json.loads((COHERENT/'root_cause_ablations.json').read_text())]
    high_precision = []
    for directory in (directories['broad'],COHERENT):
        for path in sorted(directory.glob('*high_precision.json')):
            data = json.loads(path.read_text())
            assert data['candidate_sha256'] == digest
            for report in data['reports']:
                independent = report['independent_scipy_expm_check']
                relative_discrepancy = {}
                for observable, double_key in [('propagator','propagator'),('green','green_spectral')]:
                    ratio = independent['candidate'][double_key] / independent['baseline'][double_key]
                    reference = float(report['ratios'][observable])
                    relative_discrepancy[observable] = abs(ratio-reference)/abs(reference)
                assert max(relative_discrepancy.values()) < 1e-7
                high_precision.append({'file':str(path.relative_to(ROOT)),'case_id':report['case_id'],'dtau':report['dtau'],'digits':report['digits'],'ratios':report['ratios'],'independent_double_relative_discrepancy':relative_discrepancy})
    rules = json.loads((COHERENT/'original_contract.json').read_text())
    law = {'status':'private proposal only; no build authorized or public files modified','hopping_law':next(family for family in rules['sampling']['families'] if family['name']=='flux_disordered'),'onsite_override':{'formula':'V_i=A*s*(1+rho*eta_i)-mu','A_uniform':[0.5,2.0],'rho_uniform':[0.05,0.20],'mu_uniform':[-0.4,0.4],'global_sign':'equiprobable -1,+1 per instance','eta_i':'independent uniform[-1,1] per site','independence':'A,rho,mu,sign,eta and all hopping draws independent','interpretation':'spatially coherent bounded continuous frozen auxiliary-field configurations; nonconstant onsite matrix, not an HS integration claim'},'tested_shapes':[[4,4],[4,6],[6,4],[6,6],[6,8],[8,8]],'tested_dtau':[0.4,0.6,0.8,1.0],'repetitions':[1,4],'strongest_modest_step_evidence':{'shape':[4,4],'dtau':0.4,'propagator_error_ratio':1.5328136794029664,'confirmed_decimal_digits':70},'large_torus_evidence':{'shape':[6,6],'dtau':0.6,'propagator_error_ratio':1.2027545667481964,'confirmed_decimal_digits':70},'future_build_requirements':['Explicitly publicize added laws, steps and shapes before attempts','Generate independent new public training and hidden draws; do not reuse private failing fixtures','Retain the weak runnable repeated-Strang public baseline','Do not expose prior fresh source, witness, privileged controls, or adversary fixtures','Refreeze before new attempts; parent chooses any scoring or target changes','Use stable spectral Green-function evaluation for the expanded finite-step range']}
    helpers.audit.write_json(ROOT/'adversary/recommended_physical_law.json',law)
    result = {'date':'2026-08-28','candidate_sha256':digest,'final_source_matches_snapshot':True,'source':'attempts/v_1/submission.json','independent_draw_cases':sum(entry['cases'] for entry in independent_regimes),'independent_draw_points':sum(entry['points'] for entry in independent_regimes),'controlled_case_configurations':sum(entry['cases'] for entry in controls)+sum(len(data['instances']) for data in ablations),'controlled_points':sum(entry['points'] for entry in controls)+sum(len(data['records']) for data in ablations),'high_precision_checks':high_precision,'near_uniform_local':local,'root_cause_interpretation':'A finite-step kinetic/Peierls-flux weakness when onsite fields are spatially coherent. For the strongest modest-step witness, removing the scalar onsite mean leaves the ratio unchanged, removing all onsite terms retains the failure, setting bond phases to zero removes it at h=.4, and halving hopping removes it. Not explained by an unstable inverse. Circumference-4 uniform-matching commutation is real but the tested geometry-only cohorts do not fail, and correlated-field failures persist on 6x6. These are empirical controls, not a universal theorem.','visibility':'all artifacts and code in this audit are private','public_or_targets_modified':False,'new_generation_built':False,'numerical_references':['https://mpmath.org/doc/current/matrices.html','https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.expit.html']}
    helpers.audit.write_json(ROOT/'adversary/CHAMPION_AUDIT_SUMMARY.json',result)
    print(json.dumps({'independent_draw_cases':result['independent_draw_cases'],'independent_draw_points':result['independent_draw_points'],'controlled_cases':result['controlled_case_configurations'],'controlled_points':result['controlled_points'],'high_precision_checks':len(high_precision),'candidate_sha256':digest,'local_h04':local['by_step_and_observable']['h=0.4:propagator'],'audit_complete':True},indent=2),flush=True)


if __name__ == '__main__':
    main()

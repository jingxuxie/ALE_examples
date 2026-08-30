""" 
This script contains all of the code listings from the paper preprint
"Probing quantum processor performance with pyGSTi".  It was created
to run on Python 3.7 and with pyGSTi version 0.9.9.1.  Each code listing
from the paper is in a "run_listingX" function, which can be set to run
by un-commenting it within the "main" block at the end of this script.
"""
import pygsti
import numpy as np


def simulate_data(model_to_depolarize, data_template_to_replace):
    datagen_model = model_to_depolarize.depolarize(
        op_noise=0.05, spam_noise=0.1)
    return pygsti.io.fill_in_empty_dataset_with_fake_data(
        datagen_model, data_template_to_replace, nSamples=1000, seed=8675309)


def simulate_nq_data(model_to_add_random_errors_to, data_template_to_replace):
    v = model_to_add_random_errors_to.to_vector()
    randvec = 0.001 * (np.random.rand(len(v)) - 0.5)
    datagen_model = model_to_add_random_errors_to.copy()
    datagen_model.from_vector(v + randvec)
    return pygsti.io.fill_in_empty_dataset_with_fake_data(
        datagen_model, data_template_to_replace, nSamples=1000, seed=8675309)


def simulate_nq_circuits(model_to_add_random_errors_to, output_dataset_name, circuits):
    v = model_to_add_random_errors_to.to_vector()
    randvec = 0.001 * (np.random.rand(len(v)) - 0.5)
    datagen_model = model_to_add_random_errors_to.copy()
    datagen_model.from_vector(v + randvec)
    dataset = pygsti.construction.generate_fake_data(
        datagen_model, circuits, nSamples=1000, seed=8675309)
    pygsti.io.write_dataset(output_dataset_name, dataset)
    return dataset


def simulate_rb_data(processor_spec, data_template_to_replace):
    model = processor_spec.get_std_model('TP')
    template_dataset = pygsti.io.load_dataset(data_template_to_replace,
                                              ignoreZeroCountLines=False, withTimes=False)
    circuits = list(template_dataset.keys())
    return simulate_nq_circuits(model, data_template_to_replace, circuits)


def simulate_timedependent_data(model_to_depolarize, data_template_to_replace):
    datagen_model = model_to_depolarize.depolarize(
        op_noise=0.05, spam_noise=0.1)
    datagen_model.set_simtype('map')  # only map-type can generate time-dep data
    return pygsti.io.fill_in_empty_dataset_with_fake_data(
        datagen_model, data_template_to_replace, nSamples=1, seed=8675309, times=range(100))


def run_listing1():
    # BEGIN LISTING: Running GST and then generating a report
    from pygsti.modelpacks import smq1Q_XYI
    exp_design = smq1Q_XYI.get_gst_experiment_design(max_max_length=64)
    pygsti.io.write_empty_protocol_data(exp_design, 'ExampleGSTDataDir', clobber_ok=True)

    # USER FILLS IN ExampleGSTDataDir/data/dataset.txt and starts new Python session
    simulate_data(smq1Q_XYI.target_model(), "ExampleGSTDataDir/data/dataset.txt")

    gst_data = pygsti.io.load_data_from_dir('ExampleGSTDataDir')
    gst_protocol = pygsti.protocols.StandardGST('TP,CPTP,Target')
    results = gst_protocol.run(gst_data)

    report = pygsti.report.construct_standard_report(results, title='GST Example Report')
    report.write_html('exampleReportDir')
    # END LISTING


def run_listing2():
    # BEGIN LISTING: GST for two qubits using fiducial pair reduction
    from pygsti.modelpacks import smq2Q_XYICNOT
    exp_design = smq2Q_XYICNOT.get_gst_experiment_design(max_max_length=16, fpr=True)
    pygsti.io.write_empty_protocol_data(exp_design, 'FPR2QGSTData', clobber_ok=True)

    # USER FILLS IN FPR2QGSTData/data/dataset.txt and starts new Python session
    simulate_data(smq2Q_XYICNOT.target_model(), "FPR2QGSTData/data/dataset.txt")

    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    GB = (1024)**3

    gst_data = pygsti.io.load_data_from_dir('FPR2QGSTData', comm=comm)
    gst_protocol = pygsti.protocols.StandardGST('TP,CPTP,Target', advancedOptions={'all': {'maxIterations': 1}})  #TODO: remove advancedOptions
    results = gst_protocol.run(gst_data, memlimit=5*GB, comm=comm)

    report = pygsti.report.construct_standard_report(
                 results, title='GST 2Q Example Report w/FPR', comm=comm)
    report.write_html('exampleReportDirFPR2Q')
    # END LISTING


def run_listing3():
    # BEGIN CONTEXT
    GB = (1024)**3
    # END CONTEXT
    
    # BEGIN LISTING: GST on 4 qubits
    from mpi4py import MPI
    comm = MPI.COMM_WORLD

    model = pygsti.construction.build_localnoise_model(
        nQubits=4, gate_names=['Gxpi2','Gypi2','Gcnot'],
        availability={'Gcnot': [(0,1),(1,2),(2,3)]}, parameterization='H+S')

    singleQfiducials = [(), ('Gxpi2',), ('Gypi2',)]
    circuit_struct = pygsti.construction.create_standard_localnoise_sequences(
        nQubits=4, maxLengths=[1,2,4], singleQfiducials=singleQfiducials,
        gate_names=['Gxpi2','Gypi2','Gcnot'], availability={'Gcnot': [(0,1),(1,2),(2,3)]}, comm=comm)
    exp_design = pygsti.protocols.StructuredGSTDesign(model, circuit_struct)
    pygsti.io.write_empty_protocol_data(exp_design, "4Q_GST", clobber_ok=True)

    # USER CREATES DATASET FILE 4Q_GST/data/dataset.txt
    simulate_nq_data(model, "4Q_GST/data/dataset.txt")

    data = pygsti.io.load_data_from_dir("4Q_GST")
    gst_protocol = pygsti.protocols.GST(model, gaugeopt_suite=None, verbosity=4)
    results = gst_protocol.run(data, memlimit=5*GB, comm=comm)

    report = pygsti.report.construct_nqnoise_report(results, title="GST 4Q Example Report")
    report.write_html("example4QReportDir")
    # END LISTING


def run_listing4():
    # BEGIN CONTEXT
    ws = pygsti.report.Workspace()
    # ws.init_notebook_mode(autodisplay=True)  #do this in a notebook for inline display
    # END CONTEXT

    # BEGIN LISTING: Clifford randomized benchmarking on 1 qubit
    nQubits = 1
    gate_names = ['Gxpi2', 'Gxmpi2', 'Gypi2', 'Gympi2']
    pspec = pygsti.obj.ProcessorSpec(nQubits, gate_names, qubit_labels=['Q0'])
    depths = [0, 2, 4, 8, 16, 32, 64]  # circuit depths (in Clifford operations) minus 2.
    k = 40  # number of random circuits at each length

    exp_design = pygsti.protocols.CliffordRBDesign(pspec, depths, k)
    pygsti.io.write_empty_protocol_data(exp_design, '1QCliffordRB', clobber_ok=True)

    # USER FILLS IN 1QCliffordRB/data/dataset.txt
    simulate_rb_data(pspec, "1QCliffordRB/data/dataset.txt")

    rb_data = pygsti.io.load_data_from_dir('1QCliffordRB')
    rb_protocol = pygsti.protocols.RB()
    results = rb_protocol.run(rb_data)
    ws.RandomizedBenchmarkingPlot(results)
    # END LISTING


def run_listing5():
    # BEGIN LISTING: Direct randomized benchmarking of each pair of qubits in a 5-qubit ring
    nQubits = 5
    qubit_labels = ('Q0', 'Q1', 'Q2', 'Q3', 'Q4')
    gate_names = ['Gcnot', 'Gxpi2', 'Gxmpi2', 'Gypi2', 'Gympi2']
    connections = [('Q0','Q1'), ('Q1','Q2'), ('Q2','Q3'), ('Q3','Q4'), ('Q4', 'Q0')]
    pspec = pygsti.obj.ProcessorSpec(nQubits, gate_names, qubit_labels=qubit_labels,
    				availability={'Gcnot':connections})
    depths = [0, 2, 4, 8, 16, 32, 64]
    k = 40  # number of random circuits at each length

    designs = {Qs: pygsti.protocols.DirectRBDesign(pspec, depths, k, qubit_labels=Qs,
                                                   add_default_protocol=True)
               for Qs in connections + [qubit_labels]}
    comb_design = pygsti.protocols.CombinedExperimentDesign(designs)
    pygsti.io.write_empty_protocol_data(comb_design, 'AllPairsDirectRB', clobber_ok=True)

    # USER FILLS IN AllPairsDirectRB/data/dataset.txt
    simulate_rb_data(pspec, "AllPairsDirectRB/data/dataset.txt")

    rb_data = pygsti.io.load_data_from_dir('AllPairsDirectRB')
    protocol = pygsti.protocols.DefaultRunner()
    results = protocol.run(rb_data)
    # END LISTING


def run_listing6():

    # BEGIN CONTEXT
    from pygsti.modelpacks import smq1Q_XYI
    exp_design = smq1Q_XYI.get_gst_experiment_design(max_max_length=64)
    pygsti.io.write_empty_protocol_data(exp_design, 'ExampleGSTDataDir', clobber_ok=True)
    simulate_data(smq1Q_XYI.target_model(), "ExampleGSTDataDir/data/dataset.txt")
    gst_data = pygsti.io.load_data_from_dir('ExampleGSTDataDir')
    # END CONTEXT

    # BEGIN LISTING: Model testing and report generation
    # define variables from Listing 1 up until filling in 'data/dataset.txt'

    model_to_test = smq1Q_XYI.target_model().depolarize(op_noise=0.07, spam_noise=0.07)
    mt_protocol = pygsti.protocols.ModelTest(model_to_test)
    results = mt_protocol.run(gst_data)

    report = pygsti.report.construct_standard_report(results, title='Model Test Report')
    report.write_html('exampleMTReportDir')
    # END LISTING


def run_listing7():
    # BEGIN LISTING: Bolting on drift analysis to GST
    from pygsti.modelpacks import smq1Q_XYI
    exp_design = smq1Q_XYI.get_gst_experiment_design(max_max_length=16)
    pygsti.io.write_empty_protocol_data(exp_design, 'DriftExample', clobber_ok=True)

    # USER FILLS IN DriftExample/data/dataset.txt WITH TIME SERIES DATA
    simulate_timedependent_data(smq1Q_XYI.target_model(), "DriftExample/data/dataset.txt")

    gst_data = pygsti.io.load_data_from_dir('DriftExample')
    stability_protocol = pygsti.protocols.StabilityAnalysis()
    results = stability_protocol.run(gst_data)

    report = pygsti.report.construct_drift_report(results, title='GST Drift Report')
    report.write_html('DriftReport')
    # END LISTING


def run_listing8():
    # BEGIN CONTEXT
    from pygsti.modelpacks import smq1Q_XYI
    exp_design = smq1Q_XYI.get_gst_experiment_design(max_max_length=64)
    pygsti.io.write_empty_protocol_data(exp_design, 'ExampleGSTDataDir', clobber_ok=True)
    simulate_data(smq1Q_XYI.target_model(), "ExampleGSTDataDir/data/dataset.txt")
    gst_data = pygsti.io.load_data_from_dir('ExampleGSTDataDir')
    gst_protocol = pygsti.protocols.StandardGST('TP,CPTP,Target')
    results = gst_protocol.run(gst_data)
    # END CONTEXT

    # BEGIN LISTING: Extracting and computing with gates from GST result
    dataset = results.dataset
    gst_estimate = results.estimates["CPTP"].models['stdgaugeopt']
    ideal_model = results.estimates["CPTP"].models['target']

    Gx_matrix = gst_estimate[('Gxpi2',0)].todense()  # numpy array
    Gx_idealmatrix = ideal_model[('Gxpi2',0)].todense()  # numpy array

    infidelity = pygsti.tools.entanglement_infidelity(Gx_matrix, Gx_idealmatrix)

    nSigma = pygsti.tools.two_delta_logl_nsigma(
                gst_estimate, dataset)
    # END LISTING


def run_listing9():
    # BEGIN CONTEXT
    from pygsti.modelpacks import smq1Q_XYI
    exp_design = smq1Q_XYI.get_gst_experiment_design(max_max_length=64)
    pygsti.io.write_empty_protocol_data(exp_design, 'ExampleGSTDataDir', clobber_ok=True)
    simulate_data(smq1Q_XYI.target_model(), "ExampleGSTDataDir/data/dataset.txt")
    gst_data = pygsti.io.load_data_from_dir('ExampleGSTDataDir')
    gst_protocol = pygsti.protocols.StandardGST('TP,CPTP,Target')
    results = gst_protocol.run(gst_data)
    # END CONTEXT

    # BEGIN LISTING: Generate a report as a Jupyter notebook
    report = pygsti.report.construct_standard_report(results, title="GST Report Example")
    report.write_notebook("myReport.ipynb")
    # END LISTING


def run_listing10():
    # BEGIN CONTEXT
    from math import sin, cos
    model1 = pygsti.construction.build_explicit_model(
        [('Q0', 'Q1')], ['Gi', ('Gxpi2','Q0'), ('Gypi2','Q0'), ('Gxpi2','Q1'), ('Gypi2','Q1'), ('Gcnot','Q0','Q1')],
        ["I(Q0):I(Q1)", "I(Q0):X(pi/2,Q1)", "I(Q0):Y(pi/2,Q1)",
         "X(pi/2,Q0):I(Q1)", "Y(pi/2,Q0):I(Q1)", "CNOT(Q0,Q1)"],
        effectLabels=['00', '01', '10', '11'], effectExpressions=["0", "1", "2", "3"])
    
    model2 = model1.copy()
    theta = np.pi/2 - 0.1
    U = np.array([[1, 0, 0, 0],
                  [0, 1, 0, 0],
                  [0, 0, cos(theta), sin(theta)],
                  [0, 0, sin(theta), -cos(theta)]], 'd')
    model2[('Gcnot','Q0','Q1')] = pygsti.tools.unitary_to_pauligate(U)

    model3 = model1.copy()
    theta = np.pi/2 - 0.1
    U = np.array([[1, 0, 0, 0],
                  [0, 1, 0, 0],
                  [0, 0, cos(theta), sin(theta)],
                  [0, 0, sin(theta), -cos(theta)]], 'd')
    model3[('Gcnot','Q0','Q1')] = pygsti.tools.unitary_to_pauligate(U)

    circuit_list = pygsti.construction.circuit_list([
        [('Gcnot','Q0','Q1')]*reps for reps in [1,2,4,6,8,10]
    ], line_labels=('Q0','Q1'))

    dataset = pygsti.construction.generate_fake_data(
        model1, circuit_list, nSamples=1000, seed=100)
    # END CONTEXT

    # BEGIN LISTING: Choosing the best-fit among several hand-picked models
    nSigmas = []
    nSigmas.append(pygsti.tools.two_delta_logl_nsigma(
                        model1, dataset, circuit_list))
    nSigmas.append(pygsti.tools.two_delta_logl_nsigma(
                        model2, dataset, circuit_list))
    nSigmas.append(pygsti.tools.two_delta_logl_nsigma(
                        model3, dataset, circuit_list))
    best_model_index = nSigmas.index(min(nSigmas))
    # END LISTING


def run_listing11():
    # BEGIN CONTEXT
    dataset = pygsti.objects.DataSet(outcomeLabels=["{0:04b}".format(x) for x in range(16)])
    c1 = pygsti.obj.Circuit([('Gcnot',0,1), ('Gcnot',2,3)], line_labels=(0,1,2,3))
    c2 = pygsti.obj.Circuit([('Gxpi2',1),('Gcnot',0,1)], line_labels=(0,1,2,3))
    dataset.add_count_dict(c1, {'0000': 1000})
    dataset.add_count_dict(c2, {'0000': 490, '0100': 510})
    # END CONTEXT

    # BEGIN LISTING: Testing a 4-qubit model
    model_to_test = pygsti.construction.build_localnoise_model(
        nQubits=4, gate_names=['Gxpi2','Gypi2','Gcnot'])

    nSigma = pygsti.tools.two_delta_logl_nsigma(model_to_test, dataset)
    # END LISTING


def run_listing12():
    # BEGIN LISTING: Circuit simulation on a 4-qubit model
    model = pygsti.construction.build_localnoise_model(
                nQubits=4, gate_names=['Gxpi2','Gypi2','Gcnot'], geometry='line')

    c1 = pygsti.obj.Circuit('[Gxpi2:0Gypi2:1][Gcnot:0:1][Gcnot:1:2][Gxpi2:0Gcnot:2:3]@(0,1,2,3)')
    c2 = pygsti.obj.Circuit([ [('Gxpi2',0),('Gypi2',1)], ('Gcnot',0,1),
                               ('Gcnot',1,2), [('Gxpi2',0),('Gcnot',2,3)] ], line_labels=(0,1,2,3))
    outcome_probs = model.probs(c1)
    outcome_probs2 = model.probs(c2)

    print(outcome_probs.get('0100',0.0))
    # END LISTING


def run_listing13():
    # BEGIN CONTEXT
    from pygsti.modelpacks import smq1Q_XY
    # END CONTEXT

    # BEGIN LISTING: Robust phase estimation on 1 qubit
    from pygsti.modelpacks import smq1Q_Xpi2_rpe
    exp_design = smq1Q_Xpi2_rpe.get_rpe_experiment_design(max_max_length=2**6)

    pygsti.io.write_empty_protocol_data(exp_design, 'RPEData', clobber_ok=True)

    # USER FILLS IN RPEData/data/dataset.txt
    simulate_data(smq1Q_XY.target_model(), "RPEData/data/dataset.txt")

    rpe_data = pygsti.io.load_data_from_dir('RPEData')
    rpe_protocol = pygsti.protocols.RPE()
    results = rpe_protocol.run(rpe_data)

    print(results)
    # END LISTING


def run_listing14():
    # BEGIN CONTEXT
    from pygsti.modelpacks import smq1Q_XYI
    mdl1 = smq1Q_XYI.target_model().depolarize(op_noise=0.01)
    mdl2 = smq1Q_XYI.target_model().depolarize(op_noise=0.04, spam_noise=0.01)
    cstruct = smq1Q_XYI.get_gst_circuits_struct(max_max_length=4)
    sim_ds1 = pygsti.construction.generate_fake_data(
        mdl1, cstruct.allstrs, nSamples=1000, seed=100)
    sim_ds2 = pygsti.construction.generate_fake_data(
        mdl2, cstruct.allstrs, nSamples=1000, seed=100)
    pygsti.io.write_dataset("Dataset1.txt", sim_ds1)
    pygsti.io.write_dataset("Dataset2.txt", sim_ds2)
    # END CONTEXT

    # BEGIN LISTING: Comparing datasets that should be the same.
    ds1 = pygsti.io.load_dataset("Dataset1.txt")
    ds2 = pygsti.io.load_dataset("Dataset2.txt")

    comparator = pygsti.objects.DataComparator([ds1, ds2])
    comparator.implement()

    comparator.get_worst_circuits(10)
    # END LISTING


def run_listing15():
    # BEGIN CONTEXT
    from pygsti.modelpacks import smq1Q_XYZI
    exp_design = smq1Q_XYZI.get_gst_experiment_design(max_max_length=4)
    dataset = pygsti.construction.generate_fake_data(
        smq1Q_XYZI.target_model().depolarize(0.02),
        exp_design.all_circuits_needing_data, nSamples=1000, seed=100)
    gst_data = pygsti.protocols.ProtocolData(exp_design, dataset)
    # END CONTEXT

    # BEGIN LISTING: GST using a model with customized a parameterization
    from pygsti.modelpacks import smq1Q_XYZI
    initial_model = smq1Q_XYZI.target_model()

    # Change all of initial_model's operations to having a CPTP-constrained parameterization.
    initial_model.set_all_parameterizations("CPTP")

    # Replace the CPTP-constrained Z-gate with an always-perfect (0 parameter, "static") Z-gate.
    gate_matrix = initial_model[('Gzpi2',0)].todense()
    initial_model[('Gzpi2',0)] = pygsti.objects.StaticDenseOp(gate_matrix)

    # Run GST (on existing gst_data)
    results = pygsti.protocols.GST(initial_model, gaugeopt_suite=None).run(gst_data)
    # END LISTING


def run_listing16and17():
    # BEGIN CONTEXT
    from pygsti.modelpacks import smq1Q_XYI
    exp_design = smq1Q_XYI.get_gst_experiment_design(max_max_length=16)
    dataset = pygsti.construction.generate_fake_data(
        smq1Q_XYI.target_model().depolarize(0.03),
        exp_design.all_circuits_needing_data, nSamples=1000, seed=100)
    gst_data = pygsti.protocols.ProtocolData(exp_design, dataset)
    # END CONTEXT

    # BEGIN LISTING: Defining a custom operator object
    class MyXPi2Operator(pygsti.obj.DenseOperator):
        def __init__(self):
            # initialize with no noise
            super().__init__(np.identity(4,'d'), "densitymx")
            self.from_vector([0, 0])

        def num_params(self):
            return 2  # we have two parameters

        def to_vector(self):
            return np.array([self.depol_amt, self.over_rotation], 'd')

        def from_vector(self, v, close=False, nodirty=False):
            # initialize from parameter vector v
            self.depol_amt = v[0]
            self.over_rotation = v[1]

            theta = (np.pi/2 + self.over_rotation)/2
            a = 1.0-self.depol_amt
            b = a*2*np.cos(theta)*np.sin(theta)
            c = a*(np.sin(theta)**2 - np.cos(theta)**2)

            # .base is a member of DenseOperator and is a numpy array that is
            # the dense Pauli transfer matrix of this operator
            self.base[:,:] = np.array([[1,   0,   0,   0],
                                       [0,   a,   0,   0],
                                       [0,   0,   c,  -b],
                                       [0,   0,   b,   c]], 'd')
            if not nodirty: self.dirty = True

        def transform(self, S):
            # Update self with inverse(S) * self * S (used in gauge optimization)
            raise NotImplementedError("MyXPi2Operator cannot be transformed!")
    # END LISTING

    # BEGIN LISTING: Performing GST with a model containing a custom operator
    from pygsti.modelpacks import smq1Q_XYI
    model = smq1Q_XYI.target_model()
    model.operations[('Gxpi2',0)] = MyXPi2Operator()

    # Run GST *without* gauge optimization
    gst_protocol = pygsti.protocols.GST(model, gaugeopt_suite=None)
    results = gst_protocol.run(gst_data)
    # END LISTING

if __name__ == "__main__":
    # Run listings (uncomment the ones you want to run)
    print("Uncomment the lines corresponding to listings you want to run")
    #run_listing1()
    #run_listing2() # LONG!
    #run_listing3() # LONG! 
    #run_listing4()
    #run_listing5()
    #run_listing6()
    #run_listing7()
    #run_listing8()
    #run_listing9()
    #run_listing10()
    #run_listing11()
    #run_listing12()
    #run_listing13()
    #run_listing14()
    #run_listing15()
    #run_listing16and17()

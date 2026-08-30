"""Utility classes for the full-crosstalk models
"""

import numpy as np
import sys

import pygsti
from pygsti.objects import operation as _op
from pygsti.objects import opfactory as _opfactory
from pygsti.objects.label import Label as _Lbl
from pygsti.objects import labeldicts as _ld
from pygsti.objects.localnoisemodel import LocalNoiseModel as _LocalNoiseModel, _SimpleCompLayerRules
from pygsti.objects.qubitgraph import QubitGraph as _QubitGraph


# Note for Erik: I'm not 100% satisfied with this inheritance, but it's definitely the easiest path to solution.
# I tried composition with the LocalNoiseModel instead, but it was difficult to manage
# copying all the blks dicts over properly (I got something that was independent,
# but not sure it was wired up properly internally w.r.t sharing gates between layers)
class ComposedCrosstalkModel(_LocalNoiseModel):
    """Like LocalNoiseModel but potentially non-local crosstalk noise happens after
    all local gates in a layer.
    """
    def __init__(self, num_qubits, gatedict, crosstalk_gates,
                 prep_layers=None, povm_layers=None, availability=None,
                 qubit_labels=None, geometry="line", evotype="densitymx",
                 simulator="auto", on_construction_error='raise',
                 independent_gates=False, ensure_composed_gates=False,
                 global_idle=None, padded_idle=None):
        """Create a crosstalk noise model from a local noise model, where crosstalk is applied
        as a composed operation after all local operations.

        Almost all parameters passed straight through to LocalNoiseModel, so not repeating docstring here.

        Parameters
        ----------
        crosstalk_gates: dict
            Keys are gate labels, values are (label, op) for noisy crosstalk operations.
            Crosstalk labels are needed for the state space labels of the crosstalk
            (which are likely a larger set than the "local" gates).
        
        padded_idle: str, optional
            Operation name that will be applied to all idle qubits in a layer.
            Crosstalk-affected qubits are not included when deciding whether a qubit is idle,
            and only the local portion of the padded_idle operation is applied.
            The padded idle operation is applied with all other local operations,
            i.e. before any crosstalk noise operations.
        """
        # Initialize base local noise model    
        super().__init__(num_qubits, gatedict,
                 prep_layers=prep_layers, povm_layers=povm_layers, availability=availability,
                 qubit_labels=qubit_labels, geometry=geometry, evotype=evotype,
                 simulator=simulator, on_construction_error=on_construction_error,
                 independent_gates=independent_gates, ensure_composed_gates=ensure_composed_gates,
                 global_idle=global_idle)

        # Overwrite crosstalk rules
        self._layer_rules = _ComposedCrosstalkLayerRules()

        # Handle initialization of crosstalk gates
        flags = {'auto_embed': False, 'match_parent_dim': False,
                 'match_parent_evotype': True, 'cast_to_type': None}
        self.operation_blks['crosstalk layers'] = _ld.OrderedMemberDict(self, None, None, flags)
        self.factories['crosstalk layers'] = _ld.OrderedMemberDict(self, None, None, flags)
    
        self.padded_idle = padded_idle

        # Embed crosstalk layers for each available local gate layer
        # Note that the keys are that of the LOCAL gate layer for easy lookup
        # and the crosstalk label is only needed to know how to embed the crosstalk op
        for op_label in self.operation_blks['layers'].keys():
            op_label = _Lbl(op_label)
            # Try to find op (with state space labels)
            ct_label, ct_gate = crosstalk_gates.get(op_label, (None, None))
            
            # If op not found, let's try name only
            if ct_gate is None:
                ct_label, ct_gate = crosstalk_gates.get(op_label.name, (None, None))
            
            # If still not found, no crosstalk layer to be built
            if ct_gate is None:
                continue

            # Embed crosstalk gate into the full space
            ct_label = _Lbl(ct_label)
            inds = ct_label.sslbls

            if isinstance(ct_gate, _opfactory.OpFactory):
                if inds == tuple(self.qubit_labels):
                    embedded_op = ct_gate
                else:
                    embedded_op = _opfactory.EmbeddedOpFactory(self.state_space_labels, inds, ct_gate, False)
                
                self.factories['crosstalk layers'][op_label] = embedded_op
            else:
                if inds == tuple(self.qubit_labels):
                    embedded_op = ct_gate
                else:
                    embedded_op = _op.EmbeddedOp(self.state_space_labels, inds, ct_gate)

                self.operation_blks['crosstalk layers'][op_label] = embedded_op
    
        # TODO: Hack to match StateSpaceLabels overflow handling
        if self.dim >= float(sys.maxsize):
            self.dim == np.inf
    
    
class _ComposedCrosstalkLayerRules(_SimpleCompLayerRules):
    """Same prep/povm layer rules as LocalNoiseModel, just update the operation layer rules
    to append the crosstalk layers. Padding idle operations are applied before crosstalk.
    """
    def operation_layer_operator(self, model, layerlbl, caches):
        """
        Create the operator corresponding to `layerlbl`.

        Parameters
        ----------
        layerlbl : Label
            A circuit layer label.

        Returns
        -------
        LinearOperator
        """
        if layerlbl in caches['complete-layers']: return caches['complete-layers'][layerlbl]
        # For now, don't force dense (since I want to use with CHP)
        dense = False
        Composed = _op.ComposedOp
        components = layerlbl.components
        bHasGlobalIdle = bool(_Lbl('globalIdle') in model.operation_blks['layers'])

        # Exclude empty layer here for proper padding idle logic
        if isinstance(layerlbl, pygsti.objects.CircuitLabel) and len(components) != 0:
            circuit_op = self._create_op_for_circuitlabel(model, layerlbl, dense)
            caches['complete-layers'][layerlbl] = circuit_op
            return circuit_op

        gblIdle = [model.operation_blks['layers'][_Lbl('globalIdle')]] if bHasGlobalIdle else []

        local_layers = [self._layer_component_operation(model, l, caches['op-layers'], dense) for l in components]

        crosstalk_layers = [self._layer_crosstalk_operation(model, l, caches['op-crosstalk layers']) for l in components]
        crosstalk_layers = [layer for layer in crosstalk_layers if layer is not None] # Strip out failed crosstalk layer creations

        # Add padding operation to all idle qubits
        idle_layers = []
        if model.padded_idle is not None:
            # Go through all labels and find idle qubits
            idle_qubits = set(model.state_space_labels.labels[0]) # First tensor prod block only
            for complbl in components:
                idle_qubits -= set(complbl.sslbls) # Local qubit support
            
            idle_labels = [_Lbl(model.padded_idle, [iq]) for iq in idle_qubits]
            idle_layers = [self._layer_component_operation(model, l, caches['op-layers'], dense) for l in idle_labels]

        all_layers = gblIdle + local_layers + idle_layers + crosstalk_layers

        # TODO: Hack to deal with overflow
        for layer in all_layers:
            
            if layer.dim >= float(sys.maxsize):
                layer.dim = np.inf

        #Note: OK if len(components) == 0, as it's ok to have a composed gate with 0 factors
        ret = Composed(all_layers, dim=model.dim, evotype=model.evotype)
        model._init_virtual_obj(ret)  # so ret's gpindices get set

        caches['complete-layers'][layerlbl] = ret  # cache the final label value
        return ret

    def _layer_component_operation(self, model, complbl, cache, dense):
        """
        Retrieves the operation corresponding to one component of a layer operation.

        Parameters
        ----------
        complbl : Label
            A component label of a larger layer label.

        dense : bool
            Whether to create dense operators or not.

        Returns
        -------
        LinearOperator
        """
        if complbl in cache:
            return cache[complbl]

        #Note: currently we don't cache complbl because it's not the final
        # label being created, but we could if it would improve performance.
        if isinstance(complbl, pygsti.objects.CircuitLabel):
            ret = self._create_op_for_circuitlabel(model, complbl, dense)
        elif complbl in model.operation_blks['layers']:
            ret = model.operation_blks['layers'][complbl]
        else:
            ret = _opfactory.op_from_factories(model.factories['layers'], complbl)
        return ret
    
    def _layer_crosstalk_operation(self, model, complbl, cache):
        if complbl in cache:
            return cache[complbl]
        
        if complbl in model.operation_blks['crosstalk layers']:
            ret = model.operation_blks['crosstalk layers'][complbl]
        else:
            try:
                ret = _opfactory.op_from_factories(model.factories['crosstalk layers'], complbl)
            except KeyError:
                # No crosstalk layer specified, so catch error and return no layer
                ret = None
        
        return ret
(* ::Package:: *)

Begin["`Private`"];


(* ::Subsection:: *)
(*Core Tensor routines*)


(* ::Subsubsection::Closed:: *)
(*LScalarQ*)


LScalarQ::set = "Cannot set LScalarQ[`1`] to `2`; the lhs argument must be a symbol and the rhs must be True or False.";


LScalarQ[expr_] := 
  Block[{LDot, LTensor},
  LDot[_,_]:=LDot;
  LTensor[_,___List] := LDot;
  (*With[{res=expr, list=Append[X`Private`$LScalarList,LDot]}, Internal`WouldBeNumericQ[res, list]]*)
	Internal`WouldBeNumericQ @@ {expr, Append[X`Private`$LScalarList,LDot]}
  ];


LScalarQ /: HoldPattern[(Set|SetDelayed)[LScalarQ[symb:Except[_Symbol]],bool_]] := CompoundExpression[Message[LScalarQ::set,symb,bool],Null];
LScalarQ /: HoldPattern[(Set|SetDelayed)[LScalarQ[symb_],bool:Except[True|False]]] := CompoundExpression[Message[LScalarQ::set,symb,bool],Null];

LScalarQ /: HoldPattern[(Set|SetDelayed)[LScalarQ[symb_],True]] := If[!MemberQ[Attributes[symb],Protected], $LScalarList=DeleteDuplicates[Append[$LScalarList,symb]];True, Message[Set::wrsym,symb]; True];
LScalarQ /: HoldPattern[(Set|SetDelayed)[LScalarQ[symb_],False]] := If[!MemberQ[Attributes[symb],Protected], $LScalarList=DeleteCases[$LScalarList,symb];False, Message[Set::wrsym,symb]; False];


AppendTo[$LScalarList, Dim];


(* ::Subsubsection::Closed:: *)
(*LDot*)


LDot /: Inactive[LDot]:=LDot;
LDot::args = "LDot called with `1` arguments; exactly 2 are needed to construct four-vector dot product.";
LDot::symb = LTensor::symb = "Cannot identify Lorentz vector/tensor in product '`1`'.  Disambiguate by declaring 'LScalarQ[\!\(\*StyleBox[\"symb\", \"TI\"]\)] = True' for all \!\(\*StyleBox[\"symb\", \"TI\"]\) that are not vectors/tensors.";
LDot[a_,b_,c__]:=CompoundExpression[Message[LDot::args,Length[{c}]+2],Hold[LDot[a,b,c]]];


LDot[0, _] := 0;

HoldPattern[LDot[a_,b_Times]] :=
  With[
   {pos=Position[b,PatternTest[_,!LScalarQ[#]&],1,Heads->False]},
   MapAt[LDot[a,#]&,b,pos]/;(Length[pos]==1 || Message[LDot::symb,b])
  ];

LDot[a_,b_Plus] := Distribute[List[a,b],Plus,List,Plus,LDot];


(*This defines the behavior of Clear[LDot]*)

$defaultLDotDownValues = DownValues[LDot];
$defaultLDotMessages = Messages[LDot];
$defaultLDotAttributes = {Orderless,ReadProtected};

Unprotect[Clear,ClearAll];
  Clear[LDot] := (DownValues[LDot]=$defaultLDotDownValues;);
  ClearAll[LDot] := (DownValues[LDot]=$defaultLDotDownValues; Messages[LDot]=$defaultLDotMessages; Attributes[LDot]=$defaultLDotAttributes;);
  Clear[left___,LDot,right___] := (Clear[LDot];Clear[left,right];);
  ClearAll[left___,LDot,right___] := (ClearAll[LDot];ClearAll[left,right];);
Protect[Clear,ClearAll];

SetAttributes[{$defaultLDotDownValues,$defaultLDotMessages,$defaultLDotAttributes},{Protected,ReadProtected,Locked}];


(* ::Subsubsection::Closed:: *)
(*LTensor*)


SetAttributes[LTensor,NHoldRest];


LTensor /: Inactive[LTensor]:=LTensor;


LTensor[0, __] := 0;
HoldPattern[LTensor[__,{0},___]] := 0;

(*Distribute over multiplication, pulling out numeric/scalar objets which cannot stand for four-vectors.*)
LTensor[a_Plus,idx_Symbol] := Distribute[List[a,idx],Plus,List,Plus,LTensor];

(*Pull out constant in constant times four-vectors contracted into tensors*)
LTensor[tensorLeft__,List[ker_Times],right___] :=
  With[
   {pos=Position[ker,PatternTest[_,!LScalarQ[#]&],1,Heads->False]},
   MapAt[LTensor[tensorLeft,{#},right]&,ker,pos]/;Length[pos]<=1
  ];

(*constructs such as k_{k} should go to k.k*)
LTensor[vec1_,vec2_List] := LDot[vec1,First[vec2]];

LTensor[ker_Times,idx__]:=
  With[
   {pos=Position[ker,PatternTest[_,!LScalarQ[#]&],1,Heads->False]},
   MapAt[LTensor[#,idx]&,ker,pos]/;Length[pos]<=1
  ];

LTensor[ker_Times,idx__]:=Null/;Message[LTensor::symb,ker];


(*
The reason LTensor is protected is because making downvalues interferes with Contract.
In particular, the user might want to set k_mu = 0 because in his example,
it is contracted with polarization vector LeviCivitaE(k)_mu.  However, in the process of contracting,
k_mu p_mu which doesn't vanish may appear with mu as a dummy index, but will inadvertently be
set to zero in the process of contracting.
*)


(*This defines the behavior of Clear[LTensor]*)

$defaultLTensorDownValues = DownValues[LTensor];
$defaultLTensorMessages = Messages[LTensor];
$defaultLTensorAttributes = {NHoldRest,ReadProtected};

Unprotect[Clear,ClearAll];
  Clear[LTensor] := (DownValues[LTensor]=$defaultLTensorDownValues;);
  ClearAll[LTensor] := (DownValues[LTensor]=$defaultLTensorDownValues; Messages[LTensor]=$defaultLTensorMessages; Attributes[LTensor]=$defaultLTensorAttributes;);
  Clear[left___,LTensor,right___] := (Clear[LTensor];Clear[left,right];);
  ClearAll[left___,LTensor,right___] := (ClearAll[LTensor];ClearAll[left,right];);
Protect[Clear,ClearAll];

SetAttributes[{$defaultLTensorDownValues,$defaultLTensorMessages,$defaultLTensorAttributes},{Protected,ReadProtected,Locked}];

LTensor::set = "Cannot assign to `1`.  The lhs argument must be a fully contracted tensor without free or dummy indices.";

LTensor/:HoldPattern[(Set|SetDelayed)[lhs_LTensor,rhs_]]:=
  If[MatchQ[Unevaluated[lhs],LTensor[_Symbol,__List]],
	PrependTo[DownValues[LTensor],HoldPattern[lhs]:>rhs];rhs,
	Message[LTensor::set,HoldForm[lhs]]];


(* ::Subsubsection::Closed:: *)
(*Metric and Levi-Civita Symbols*)


SetAttributes[MetricG, Constant];
MetricG::indices="Metric tensor `1` has `2` indices; 2 indices are expected.";

(*Metric tensor symmetry*)
MetricG /: LTensor[MetricG,mu_,nu_] := LTensor[MetricG,nu,mu]/;!OrderedQ[{mu,nu}];

(*Self-contracted metric tensor*)
MetricG /: LTensor[MetricG,idx_Symbol,idx_] := Dim;

(*constructs such as MetricG_ \[Mu]{k} should go to k_ \[Mu]*)
MetricG /: LTensor[MetricG,idx_,vec_List] := pair[idx,vec];

(*Wrong number of indices*)
MetricG /: e: Except[LTensor[MetricG,_,_],LTensor[MetricG,idx__]] := Null /; Message[MetricG::indices,HoldForm[e],Length[{idx}]];


SetAttributes[LeviCivitaE, Constant];
LeviCivitaE::indices="Levi-Civita symbol `1` has `2` indices; `3` indices are expected.";

(*Levi-Civita symbol antisymmetry*)
LeviCivitaE /: HoldPattern[LTensor[LeviCivitaE,idx__]] := Signature[{idx}]LTensor@@Prepend[Sort[{idx}],LeviCivitaE]/;!OrderedQ[{idx}];
LeviCivitaE /: HoldPattern[LTensor[LeviCivitaE,___,b_,___,b_,___]] := 0;

(*Wrong number of indices*)
LeviCivitaE /: e: Except[LTensor[LeviCivitaE,_,_,_,_],LTensor[LeviCivitaE,idx__]] := Null /; Message[LeviCivitaE::indices,HoldForm[e],Length[{idx}],4];


(* ::Subsubsection::Closed:: *)
(*Uncontract*)


(*Utility function not used internally*)
X`Utilities`Uncontract[expr_,k_]:=
  Catch[
	softUncontract[expr,k,False]/.HoldPattern[LDot[a_,p:k]|LDot[p:k,a_]]^n_.:>Switch[Positive[n],True,Product[(LTensor[a,#]LTensor[p,#])&[Unique[]],{i,1,n}],False,LDot[p,a]^n]
  ,DiracMatrix,messageInvalidDiracMatrix[X`Utilities`Uncontract]];


(*Lightweight version of FermionLineExpand.  Used in softUncontract
  Does this in basis observed by FermionLineExpand option.
  No Chisholm expansion, no sorting*)

softUncontractDiracMatrixExpand[expr_,optDiracAlgebra_] := 
  Module[{optChiralBasis, result},
	optChiralBasis=If[OptionValue[FermionLineExpand,ChiralBasis]===Automatic, !FreeQ[expr,DiracPL|DiracPR], OptionValue[FermionLineExpand,ChiralBasis]];

	result = expr/.diracMatrixExpansionRule[False,optChiralBasis && optDiracAlgebra, optDiracAlgebra, False, False];

	(*This also organizes by tensor structures*)
	X`Utilities`ClearDuplicatedTensors[result]
  ];

(*Used in helper function numeratorProcessor for LoopIntegrate.  It is "soft" because it does not uncontract out of LDot*)
softUncontract[expr_,k_,optDiracAlgebra_]:=
  (*Must call internalFermionLineExpand to expand out FermionLine and DiracMatrix*)
	softUncontractDiracMatrixExpand[expr,optDiracAlgebra] //. 
	{(*Rule #1: uncontract out of high rank tensors*)
	  HoldPattern[LTensor[Except[MetricG,tensor_],idx__]]^n1_. :> 
		With[{vecsPos=Position[{idx},x_List?(Not[FreeQ[#,k]]&),1]},
		  If[Positive[n1],
			(*True,*)
			Internal`InheritedBlock[{LTensor},
			  Unprotect[LTensor];
			  Unset[LTensor[a_Plus,b_Symbol]];
			  Unset[LTensor[tensorLeft__,List[ker_Times],right___]];
			  Unset[LTensor[ker_Times,b__]];
			  (*Block LTensor from pulling out constants from added/subtracted vectors*)
			  (Expand[(Plus@@(ReplacePart[MapAt[List,#,vecsPos+1],1->tensor]&/@Distribute[FlattenAt[LTensor[Symbol,idx],vecsPos+1],Plus,LTensor,List,LTensor]))^n1] /. 
				(HoldPattern[LTensor[tensor,left___,{p:k},right___]]^n2_. :> Product[(LTensor[p,#]LTensor[tensor,left,#,right])&[Unique[]],{i,1,n2}]))
			],
			(*False,*)
			LTensor[tensor,idx]^n1
		  ]/;vecsPos=!={}
		],
		(*Rule #2: uncontract out of DiracMatrix*)
		(mtxHead:DiracMatrix|Spur|Inactive[Spur])[left___,LDot[vec_,p:k],right___] :> (*With[{idx=Unique[]},mtxHead[left,LTensor[vec,idx],right]LTensor[p,idx]]*)(mtxHead[left,LTensor[vec,#],right]LTensor[p,#]&)[Unique[]],
		(mtxHead:DiracMatrix|Spur|Inactive[Spur])[left___,LTensor[tensor_,l___,{p:k},r___],right___] :> (*With[{idx=Unique[]},mtxHead[left,LTensor[tensor,l,idx,r],right]LTensor[p,idx]]*)(mtxHead[left,LTensor[tensor,l,#,r],right]LTensor[p,#]&)[Unique[]]
		(*If DiracMatrix is inside FermionLine (or FermionLineProduct), 
			This relies on the DownValue rule for FermionLine and FermionLineProduct
			to pull the uncontracted vector (viewed as constants) outside of FermionLine and FermionLineProduct*)
	};


(* ::Subsubsection::Closed:: *)
(*Contract*)


elementaryContractionRules=
{
  (*Contraction of ordinary metric tensors and vectors.*)
  HoldPattern[Power[LTensor[MetricG, _Symbol, _Symbol],2]]:>Dim,
  HoldPattern[Power[LTensor[v_, _Symbol],2]]:>LDot[v,v],
  HoldPattern[LTensor[MetricG, PatternSequence[a_,b_]|PatternSequence[b_,a_]] LTensor[MetricG, PatternSequence[a_,c_]|PatternSequence[c_,a_]]]:>LTensor[MetricG,b,c],
  HoldPattern[LTensor[MetricG, PatternSequence[a_,b_]|PatternSequence[b_,a_]] LTensor[v_,a_Symbol]]:>LTensor[v,b],
  HoldPattern[LTensor[v_, a_Symbol] LTensor[w_, a_Symbol]]:>LDot[v,w]
};

elementaryContract=Expand[#,_LTensor]//.elementaryContractionRules& ;


highRankTensorContractionRules=
{
  (*Just in case there there is another Levi-Civita in coefficient c, should expand in LTensor*)
  HoldPattern[c_. LTensor[LeviCivitaE,idx1__]*LTensor[LeviCivitaE,idx2__]] :> Expand[-c Det[Outer[pair,{idx1},{idx2},1,1]],_LTensor],
  HoldPattern[c_. LTensor[LeviCivitaE,idx1__]^2] :> Expand[-c Det[Outer[pair,{idx1},{idx1},1,1]],_LTensor],
  (*Contract vectors into tensors*)
  HoldPattern[LTensor[Except[DiracG,v_], a_Symbol] LTensor[Except[DiracG,tensor_],left___,a_,right___]] :>LTensor[tensor,left,{v},right],
  (*Contract metric tensors into tensors*)
  HoldPattern[LTensor[MetricG, PatternSequence[a_,b_]|PatternSequence[b_,a_]] LTensor[left__,a_Symbol,right___]]:>LTensor[left,b,right]
};
highRankTensorContract=Expand[#,_LTensor]//.highRankTensorContractionRules& ;


(*Used in internalLoopIntegrate if option DiracAlgebra is set to False; does not involve contracting Levi-Civita tensor*)
elementaryFermionLineContractionRules=
{
  (*Contractions into FermionLineProduct*)
  LTensor[v_,a_Symbol] FermionLineProduct[leftFL___,FermionLine[wBar_,w_,mtx_DiracMatrix],rightFL___] :> 
	Block[{$patternMatched}, With[{result = FermionLineProduct[leftFL,FermionLine[wBar,w,mtx/.{LTensor[left__,a,right___]:>($patternMatched=True; LTensor[left,{v},right])}],rightFL]}, result /; $patternMatched]],
  HoldPattern[LTensor[MetricG,PatternSequence[a_Symbol, b_]|PatternSequence[b_, a_Symbol]] FermionLineProduct[leftFL___,FermionLine[wBar_,w_,mtx_DiracMatrix],rightFL___]] :> 
	Block[{$patternMatched}, With[{result = FermionLineProduct[leftFL,FermionLine[wBar,w,mtx/.{LTensor[left__,a,right___]:>($patternMatched=True; LTensor[left,b,right])}],rightFL]}, result /; $patternMatched]],

  (*Contractions into FermionLine*)
  LTensor[v_,a_Symbol] (fl: FermionLine|Inactive[FermionLine])[wBar_,w_,(mtx: _DiracMatrix|Blank[Inactive[DiracMatrix]])] :> 
	Block[{$patternMatched}, With[{result = fl[wBar,w,mtx/.{LTensor[left__,a,right___]:>($patternMatched=True; LTensor[left,{v},right])}]}, result /; $patternMatched]],
  HoldPattern[LTensor[MetricG,PatternSequence[a_Symbol, b_]|PatternSequence[b_, a_Symbol]] (fl: FermionLine|Inactive[FermionLine])[wBar_,w_,(mtx: _DiracMatrix|Blank[Inactive[DiracMatrix]])]] :> 
	Block[{$patternMatched}, With[{result = fl[wBar,w,mtx/.{LTensor[left__,a,right___]:>($patternMatched=True; LTensor[left,b,right])}]}, result /; $patternMatched]],

  (*Contractions into DiracMatrix*)
  HoldPattern[LTensor[v_,a_Symbol] (mtx: DiracMatrix[__]|Inactive[DiracMatrix][__]|Spur[__]|Inactive[Spur][__])(*(mtx: _DiracMatrix|Blank[Inactive[DiracMatrix]]|_Spur|Blank[Inactive[Spur]])*)] :> 
	Block[{$patternMatched}, With[{result = mtx/.{LTensor[left__,a,right___]:>($patternMatched=True; LTensor[left,{v},right])}}, result /; $patternMatched]],
  HoldPattern[LTensor[MetricG,PatternSequence[a_Symbol, b_]|PatternSequence[b_, a_Symbol]] (mtx: DiracMatrix[__]|Inactive[DiracMatrix][__]|Spur[__]|Inactive[Spur][__])(*(mtx: _DiracMatrix|Blank[Inactive[DiracMatrix]]|_Spur|Blank[Inactive[Spur]])*)] :> 
	Block[{$patternMatched}, With[{result = mtx/.{LTensor[left__,a,right___]:>($patternMatched=True; LTensor[left,b,right])}}, result /; $patternMatched]]      
};
elementaryFermionLineContract=Expand[#,_LTensor|_FermionLine|Blank[Inactive[FermionLine]]|_FermionLineProduct]//.elementaryFermionLineContractionRules& ;


With[{leviCivitaContractionRules=
  {mtxHead_[left___,LTensor[DiracG,idx1:Except[_List|_Integer, a|b|c|d]],LTensor[DiracG,idx2:Except[_List|_Integer, a|b|c|d]],LTensor[DiracG,idx3:Except[_List|_Integer, a|b|c|d]],LTensor[DiracG,idx4:Except[_List|_Integer, a|b|c|d]],right___]:>With[{idxList={a,b,c,d}/.{idx1->1,idx2->2,idx3->3,idx4->4}}, $patternMatched=True; Signature[idxList]*24*I*mtxHead[left,DiracG5,right]],
   mtxHead_[left___,LTensor[DiracG,idx1:Except[_List|_Integer, a|b|c|d]],LTensor[DiracG,idx2:Except[_List|_Integer, a|b|c|d]],LTensor[DiracG,idx3:Except[_List|_Integer, a|b|c|d]],right___]:>With[{idxList={a,b,c,d}/.{idx1->1,idx2->2,idx3->3}}, $patternMatched=True; -Signature[idxList]*6*I*mtxHead[left,LTensor[DiracG,Sort[idxList][[4]]],DiracG5,right]],
   mtxHead_[left___,LTensor[DiracS,idx1:Except[_List|_Integer, a|b|c|d],idx2:Except[_List|_Integer, a|b|c|d]],right___]:>With[{idxList={a,b,c,d}/.{idx1->1,idx2->2}}, $patternMatched=True; Signature[idxList]*-2I*mtxHead[left,LTensor[DiracS,Sequence@@(Sort[idxList][[3;;4]])],DiracG5,right]],
   mtxHead_[left___,LTensor[DiracG,idx1:Except[_List|_Integer, a|b|c|d]],LTensor[DiracG,idx2:Except[_List|_Integer, a|b|c|d]],right___]:>With[{idxList={a,b,c,d}/.{idx1->1,idx2->2}}, $patternMatched=True; Signature[idxList]*-2*mtxHead[left,LTensor[DiracS,Sequence@@(Sort[idxList][[3;;4]])],DiracG5,right]]}
  },

epsFermionLineContractionRules=
{
  (*Contractions into FermionLineProduct*)
  RuleDelayed@@Hold[LTensor[LeviCivitaE,a_,b_,c_,d_] FermionLineProduct[leftFL___,FermionLine[wBar_,w_,mtx_DiracMatrix],rightFL___],
	Block[{$patternMatched}, With[{result=FermionLineProduct[leftFL,FermionLine[wBar,w,Replace[mtx,leviCivitaContractionRules]],rightFL]},result/;$patternMatched]]],
  (*Contractions into FermionLine*)
  RuleDelayed@@Hold[LTensor[LeviCivitaE,a_,b_,c_,d_] (fl: FermionLine|Inactive[FermionLine])[wBar_,w_,(mtx: _DiracMatrix|Blank[Inactive[DiracMatrix]])],
	Block[{$patternMatched},With[{result=fl[wBar,w,Replace[mtx,leviCivitaContractionRules]]},result/;$patternMatched]]],
  (*Contractions into DiracMatrix*)
  RuleDelayed@@Hold[HoldPattern[LTensor[LeviCivitaE,a_,b_,c_,d_] (mtx: DiracMatrix[__]|Inactive[DiracMatrix][__]|Spur[__]|Inactive[Spur][__])(*(mtx: _DiracMatrix|Blank[Inactive[DiracMatrix]]|_Spur|Blank[Inactive[Spur]])*)],
	Block[{$patternMatched}, With[{result=Replace[mtx,leviCivitaContractionRules]},result/;$patternMatched]]]
};

fermionLineContract=
  With[{contractionRules=Join[epsFermionLineContractionRules,elementaryFermionLineContractionRules]},
    Expand[#,_LTensor|_FermionLine|Blank[Inactive[FermionLine]]|_FermionLineProduct]//.contractionRules&
  ];

inertSpurContractionRules=
{RuleDelayed@@Hold[LTensor[LeviCivitaE,a_,b_,c_,d_]*(mtx_InertSpur),
	Block[{$patternMatched}, With[{result=Replace[mtx,leviCivitaContractionRules]},result/;$patternMatched]]],
  LTensor[v_,a_Symbol]*mtx_InertSpur:> 
	Block[{$patternMatched}, With[{result = mtx/.{LTensor[left__,a,right___]:>($patternMatched=True; LTensor[left,{v},right])}}, result /; $patternMatched]],
  LTensor[MetricG,a_Symbol, b_Symbol]*mtx_InertSpur:> 
	Block[{$patternMatched}, With[{result = mtx/.{LTensor[left__,a,right___]:>RuleCondition@($patternMatched=True; LTensor[left,b,right])}}, result /; $patternMatched]],
  LTensor[MetricG,a_Symbol, b_Symbol]*mtx_InertSpur:> 
	Block[{$patternMatched}, With[{result = mtx/.{LTensor[left__,b,right___]:>RuleCondition@($patternMatched=True; LTensor[left,a,right])}}, result /; $patternMatched]]
};

inertSpurContract=Expand[#,_LTensor|_InertSpur]//.inertSpurContractionRules&;

];


InertSpur[___,0,___] := 0;
InertSpur[left___, c_?(FreeQ[#,Dirac1|DiracG5|DiracPL|DiracPR|LDot[DiracG,_]|LTensor[DiracG|DiracS,__]|_DiracMatrix|_Projector[__]]&) Pattern[mtx,Dirac1|DiracG5|DiracPL|DiracPR|LDot[DiracG,_]|LTensor[DiracG|DiracS,__]|_DiracMatrix|_Projector[__]], right___] := c InertSpur[left, mtx, right];
InertSpur[left___, Dirac1, right___] := InertSpur[left, right];
Default[InertSpur] = Dirac1;
InertSpur[left___,DiracMatrix[middle___],right___]:=InertSpur[left,middle,right];

SetAttributes[Contract,HoldAll];
Contract[expr_]:=
Module[
  (*Need hold to prevent vector sums from automatically expanding*)
  {currExpr=Hold[expr]/.{Inactive[LoopIntegrate]:>Inactive[LoopIntegrate],Inactive[Spur]:>Inactive[Spur],LoopIntegrate:>InertLoopIntegrate,Spur:>InertSpur}},

  Which[
	(*If there is LoopIntegrate*)
	!FreeQ[currExpr,_InertLoopIntegrate] && FreeQ[Unevaluated[currExpr], _X`LoopRefine],

	  currExpr = currExpr/. InertLoopIntegrate[num_,k_,den__]*tensor_. /; FreeQ[tensor,k] :> RuleCondition[InertLoopIntegrate[Contract[num*tensor],k,den]];
	  currExpr = ReleaseHold[currExpr /. InertLoopIntegrate->LoopIntegrate],

	(*If there is Spur*)	
	!FreeQ[currExpr,_InertSpur] && FreeQ[Unevaluated[currExpr], _X`LoopRefine],

	  Internal`InheritedBlock[{LTensor, LDot},
	  (*block LTensor and LDot to keep indices and dot products from distributing across added vectors (Plus).*)

		Unprotect[LTensor];
		Unset[LTensor[a_Plus,idx_Symbol]];
		Unset[LTensor[tensorLeft__,List[ker_Times],right___]];
		Unset[LTensor[ker_Times,idx__]];

		Unset[LDot[a_,b_Plus]];
		Unset[LDot[a_,b_Times]];

		currExpr=inertSpurContract[ReleaseHold[currExpr]/.prefactor_. sp_InertSpur:>elementaryContract[prefactor]*elementaryContract[sp]];

	  (*If there are products of Spur, then use contraction formulae across spur.
		===Insert code here when complete===*)

		currExpr=currExpr /. InertSpur :> Spur
	  ],

	(*Otherwise, convert back to LoopIntegrate and Spur.*)
	True,
	  currExpr=ReleaseHold[currExpr]/.{InertLoopIntegrate:>LoopIntegrate,InertSpur:>Spur}
  ];

  If[!FreeQ[currExpr,Inactive[LoopIntegrate]],
	currExpr = Expand[currExpr, Inactive[LoopIntegrate]] /. Inactive[LoopIntegrate][num_,k_,den__]*tensor_ /; FreeQ[tensor,k] :> (Inactive[LoopIntegrate][Contract[num*tensor],k,den])
  ];

  Sow[True,"Contract"];

  (*First, contract higher rank tensors (including Levi-Civita tensors)*)
  If[!FreeQ[currExpr, LTensor[Except[MetricG|DiracS],_,__]],
	currExpr = highRankTensorContract[currExpr]
  ];

  (*There should be no active Spur or LoopIntegrate or LoopRefine.
    Check if there is a DiracMatrix (which is also included in FermionLine and FermionLineProduct),
	or Inactive[Spur]*)
  If[!FreeQ[currExpr,_DiracMatrix|Blank[Inactive[DiracMatrix]]|_Spur|Blank[Inactive[Spur]]],
	If[$DiracAlgebra,
	  currExpr = fermionLineContract[currExpr],
	  currExpr = elementaryFermionLineContract[currExpr]
	]
  ];

  (*Expand out tensors that are contracted into vector sums*)
  currExpr=ReplaceRepeated[currExpr, HoldPattern[LTensor[Except[DiracS,ten_],left___,List[Plus[vecs__]],right___]]:>Plus@@(LTensor[ten,left,{#},right]&/@{vecs})];

  (*Perform elementary contraction rules*)
  currExpr=elementaryContract[currExpr]
];

LHS_Contract:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,1];Fail];


(* ::Subsubsection::Closed:: *)
(*Tensor structures*)


X`Utilities`TensorStructures[e_List] := Flatten[X`Utilities`TensorStructures /@ e];

X`Utilities`TensorStructures[e_]:=
  If[#==={},{1},#]& @
	(With[{expr=Expand[e/.HoldPattern[LTensor[Except[DiracG|DiracS,_],__List]]->1,_LTensor|_DiracMatrix|_Spur|Blank[Inactive[Spur]]|_FermionLine|_FermionLineProduct]},
	  DeleteDuplicates[
		  Switch[Head[#],
			Times,DeleteCases[#,IgnoringInactive[Except[_LTensor|_Spur|_DiracMatrix|_FermionLine|_FermionLineProduct]]],
			IgnoringInactive[LTensor|Spur|DiracMatrix|FermionLine|FermionLineProduct],#,
			_,Unevaluated[Sequence[]]]&/@Switch[Head[expr],Plus,List@@expr,_,List@expr]
		]]);


SetAttributes[X`Utilities`CollectByTensorStructures,Listable];

X`Utilities`CollectByTensorStructures[e_, f_:Identity]:=
  With[{expr=Expand[e,_LTensor|_DiracMatrix|_Spur|Blank[Inactive[Spur]]|_FermionLine|_FermionLineProduct]},
	Collect[expr,If[#==={},{1},#],f]& @
	(DeleteDuplicates[
		  Switch[Head[#],
			Times,DeleteCases[#,IgnoringInactive[Except[_LTensor|_Spur|_DiracMatrix|_FermionLine|_FermionLineProduct]]],
			IgnoringInactive[LTensor|Spur|DiracMatrix|FermionLine|FermionLineProduct],#,
			_,Unevaluated[Sequence[]]]&/@(Switch[Head[expr],Plus,List@@expr,_,List@expr]/.HoldPattern[LTensor[Except[DiracG|DiracS,_],__List]]->1)
		  ])
  ];

X`Utilities`CollectByTensorStructures[e_, fC_, fT_]:=
  With[{expr=Expand[e,_LTensor|_DiracMatrix|_Spur|Blank[Inactive[Spur]]|_FermionLine|_FermionLineProduct]},
	Collect[Unevaluated[expr],If[#==={},{1},#],Hold]& @
	  (DeleteDuplicates[
		  Switch[Head[#],
			Times,DeleteCases[#,IgnoringInactive[Except[_LTensor|_Spur|_DiracMatrix|_FermionLine|_FermionLineProduct]]],
			IgnoringInactive[LTensor|Spur|DiracMatrix|FermionLine|FermionLineProduct],#,
			_,Unevaluated[Sequence[]]]&/@(Switch[Head[expr],Plus,List@@expr,_,List@expr]/.HoldPattern[LTensor[Except[DiracG|DiracS,_],__List]]->1)
		  ]) /. {a_. Hold[b_]:>fT[a]fC[b]}
  ];


(*Pattern1: In each monomial, set indices of tensors known symmetry with OrderLessPatternSequence, then replace symbols in the monomial which are dummy with their Pattern[...,Blank[Symbol]] counterparts*)
(*Pattern2: First replacement is same as Pattern1 for only indices with known symmetry, and the replacement of symbols is specifically targeted to its indices.*)
(*          Second replacement is same as Pattern1 but for all other tensors, and the replacement of symbols is everywhere.*)

If[$VersionNumber>=10.1,
  (*Use 'OrderlessPatternSequence' of version 10*)

  (*X`Utilities`ClearDuplicatedTensors[expr_]:=
  With[{oldTensors=X`Utilities`TensorStructures[expr]},
	With[{newTensorsAndReplacementRules=
	  Reap[DeleteDuplicates[oldTensors,
		(*I have to construct two patterns because reserved symbols like DiracS and DiracG may be used as dummy indices.*)
		With[{pattern1=HoldPattern[#2]/.HoldPattern[LTensor[lten:LeviCivitaE|MetricG|DiracS,idx__]]:>LTensor[lten,OrderlessPatternSequence[idx]]/.(#:>Pattern[#,Blank[Symbol]]&/@X`Utilities`DummyIndices[#2]),
			  pattern2=HoldPattern[#2]/.With[{dummyIdxRepRules=#:>Pattern[#,Blank[Symbol]]&/@X`Utilities`DummyIndices[#2]},{LTensor[lten:LeviCivitaE|MetricG|DiracS,idx__]:>RuleCondition[LTensor[HoldPattern[lten],OrderlessPatternSequence[idx]/.dummyIdxRepRules]],LTensor[ker_,idx__]:>RuleCondition[LTensor[HoldPattern[ker],PatternSequence[idx]/.dummyIdxRepRules]]}]},
		  If[MatchQ[#1,pattern2], Sow[Rule[#2,#1/.(pattern1:>#2)],"DuplicatedTensors"];True,False]]&
		],"DuplicatedTensors"]},

	  If[newTensorsAndReplacementRules[[2]]==={},
		X`Utilities`CollectByTensorStructures[expr],
		Collect[Expand[expr,_LTensor|_DiracMatrix|_Spur|Blank[Inactive[Spur]]|_FermionLine|_FermionLineProduct]/.First[newTensorsAndReplacementRules[[2]]],newTensorsAndReplacementRules[[1]]]
	  ]
	]
  ];*)

  X`Utilities`ClearDuplicatedTensors[expr_]:=
  With[{oldTensors=X`Utilities`TensorStructures[expr]},
	With[{newTensorsAndReplacementRules=
	  Reap[DeleteDuplicates[oldTensors,
		With[{dummyIdxToPattRule=(#:>Pattern[#,Blank[Symbol]]&/@X`Utilities`DummyIndices[#2])},
		  With[{pattern=HoldPattern[#2]/.HoldPattern[LTensor[lten_,idx__]]:>RuleCondition[LTensor[HoldPattern[lten],Switch[lten,LeviCivitaE|MetricG|DiracS,OrderlessPatternSequence[idx],_,PatternSequence[idx]]/.dummyIdxToPattRule]]},
			If[MatchQ[#1,pattern], Sow[Rule[#2,#1/.(pattern:>#2)],"DuplicatedTensors"];True,False]]
		  ]&
		],"DuplicatedTensors"]},

	  If[newTensorsAndReplacementRules[[2]]==={},
		X`Utilities`CollectByTensorStructures[expr],
		Collect[Expand[expr,_LTensor|_DiracMatrix|_Spur|Blank[Inactive[Spur]]|_FermionLine|_FermionLineProduct]/.First[newTensorsAndReplacementRules[[2]]],newTensorsAndReplacementRules[[1]]]
	  ]
	]
  ];
,
  
  X`Utilities`ClearDuplicatedTensors[expr_]:=
  With[{oldTensors=X`Utilities`TensorStructures[expr]},
	With[{newTensorsAndReplacementRules=
	  Reap[DeleteDuplicates[oldTensors,
		(*I have to construct two patterns because reserved symbols like DiracS and DiracG may be used as dummy indices.*)
		With[{pattern1=HoldPattern[#2]/.HoldPattern[LTensor[lten:LeviCivitaE|MetricG|DiracS,idx__]]:>(Alternatives@@Map[LTensor[lten,Sequence@@#]&,Permutations[{idx}]])/.(#:>Pattern[#,Blank[Symbol]]&/@X`Utilities`DummyIndices[#2]),
			  pattern2=HoldPattern[#2]/.With[{dummyIdxRepRules=#:>Pattern[#,Blank[Symbol]]&/@X`Utilities`DummyIndices[#2]},{LTensor[lten:LeviCivitaE|MetricG|DiracS,idx__]:>RuleCondition[Alternatives@@Map[LTensor[HoldPattern[lten],Sequence@@#]&,Permutations[{idx}/.dummyIdxRepRules]]],LTensor[ker_,idx__]:>RuleCondition[LTensor[HoldPattern[ker],PatternSequence[idx]/.dummyIdxRepRules]]}]},
		  If[MatchQ[#1,pattern2], Sow[Rule[#2,#1/.(pattern1:>#2)],"DuplicatedTensors"];True,False]]&
		],"DuplicatedTensors"]},

	  If[newTensorsAndReplacementRules[[2]]==={},
		X`Utilities`CollectByTensorStructures[expr],
		Collect[Expand[expr,_LTensor|_DiracMatrix|_Spur|Blank[Inactive[Spur]]|_FermionLine|_FermionLineProduct]/.First[newTensorsAndReplacementRules[[2]]],newTensorsAndReplacementRules[[1]]]
	  ]
	]
  ]
];


X`Utilities`DummyIndices::mon = "`1` is not a monomial.";
X`Utilities`DummyIndices[Except[_Plus,expr_]] := Cases[Tally[Cases[expr,LTensor[ker_,stuff__]:>stuff,Infinity,Heads->True]],{symb_Symbol,2}:>symb,1];
X`Utilities`DummyIndices[expr_] := Null /; Message[X`Utilities`DummyIndices::mon,expr];


X`Utilities`FreeIndices[expr_Plus]:=X`Utilities`FreeIndices[expr[[1]]];
X`Utilities`FreeIndices[expr_]:=Cases[Tally[Cases[expr,LTensor[ker_,stuff__]:>stuff,Infinity,Heads->True]],{symb_Symbol,1}:>symb,1];


(* ::Subsection::Closed:: *)
(*Longitudinal / Transverse*)


Longitudinal::vec="Input tensor built from more than 1 vector: `1`.  Specify projection vector.";
Longitudinal::novec="No vectors were found inside input tensor.  Specify projection vector.";
Longitudinal::idx="Input tensor appears to be of rank greater than 2: `1`. Specify projection indices.";
Longitudinal::rank="Too few indices.  Rank of input tensor must be of rank 2 or higher.";

Longitudinal[expr_] :=
  With[{vec=DeleteDuplicates[Cases[Variables[expr],LTensor[v_,_]:>v]],
		idx=DeleteDuplicates[Cases[Variables[expr],LTensor[_,x___]:>x]]},
	With[{projector=(LTensor[vec[[1]],idx[[1]]]LTensor[vec[[1]],idx[[2]]]/LDot[vec[[1]],vec[[1]]])},
	  Contract[projector*expr]
	] /; Check[validLTproj[Longitudinal,vec,idx]; True, False]
  ];

Longitudinal[expr_, vec_Symbol] :=
  With[{idx=DeleteDuplicates[Cases[Variables[expr],LTensor[_,x___]:>x]]},
	With[{projector=(LTensor[vec,idx[[1]]]LTensor[vec,idx[[2]]]/LDot[vec,vec])},
			Contract[projector*expr]
		] /; Check[validLTproj[Longitudinal,{vec},idx]; True, False]
  ];

Longitudinal[expr_, vec_Symbol, idx:{_Symbol,_Symbol}] :=
  With[{projector=(LTensor[vec,idx[[1]]]LTensor[vec,idx[[2]]]/LDot[vec,vec])},
	Contract[projector*expr]
  ];

LHS_Longitudinal:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,3];Fail];


Transverse::vec="Input tensor built from more than 1 vector: `1`.  Specify projection vector.";
Transverse::novec="No vectors were found inside input tensor.  Specify projection vector.";
Transverse::idx="Input tensor appears to be of rank greater than 2: `1`. Specify projection indices.";
Transverse::rank="Too few indices.  Rank of input tensor must be of rank 2 or higher.";

Transverse[expr_] :=
  With[{vec=DeleteDuplicates[Cases[Variables[expr],LTensor[v_,_]:>v]],
	    idx=DeleteDuplicates[Cases[Variables[expr],LTensor[_,x___]:>x]]},
	With[{projector=1/(Dim-1) (LTensor[MetricG,idx[[1]],idx[[2]]]-LTensor[vec[[1]],idx[[1]]]LTensor[vec[[1]],idx[[2]]]/LDot[vec[[1]],vec[[1]]])},
	  Contract[projector*expr]
	] /; Check[validLTproj[Transverse,vec,idx]; True, False]
  ];

Transverse[expr_, vec_Symbol] :=
  With[{idx=DeleteDuplicates[Cases[Variables[expr],LTensor[_,x___]:>x]]},
	With[{projector=1/(Dim-1) (LTensor[MetricG,idx[[1]],idx[[2]]]-LTensor[vec,idx[[1]]]LTensor[vec,idx[[2]]]/LDot[vec,vec])},
	  Contract[projector*expr]
	] /; Check[validLTproj[Transverse,{vec},idx]; True, False]
  ];

Transverse[expr_, vec_Symbol, idx:{_Symbol,_Symbol}] :=
  With[{projector=1/(Dim-1) (LTensor[MetricG,idx[[1]],idx[[2]]]-LTensor[vec,idx[[1]]]LTensor[vec,idx[[2]]]/LDot[vec,vec])},
	Contract[projector*expr]
  ];

LHS_Transverse:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,3];Fail];


validLTproj[head_,vec_,idx_] := 
  (If[Length[vec]>1,Message[head::vec,vec]];
   If[Length[vec]==0,Message[head::novec]];
   If[Length[idx]>2,Message[head::idx,idx]];
   If[Length[idx]<2,Message[head::rank,idx]];);


(* ::Subsection::Closed:: *)
(*MandelstamRelations*)


MandelstamRelations::opts = "Value of option Eliminate -> `1` is not one of `2` or None.";
MandelstamRelations::arg = "Expecting a rule of the form \!\(\*RowBox[{\(\*RowBox[{\"{\",RowBox[{\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),\"1\"]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),\"2\"]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),\"3\"]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),\"4\"]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),\"1\"]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),\"2\"]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),\"3\"]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),\"4\"]\)}],\"}\"}]\),\"\[Rule]\",RowBox[{\"{\",RowBox[{\(\*StyleBox[\"s\",\"TI\"]\),\",\",\(\*StyleBox[\"t\",\"TI\"]\),\",\",\(\*StyleBox[\"u\",\"TI\"]\)}],\"}\"}]}]\), with nonzero monomials \!\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\), \(1\)]\), \!\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\), \(2\)]\), \!\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\), \(3\)]\), and \!\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\), \(4\)]\).";
 
MandelstamRelations[{c1_. p1_Symbol,c2_. p2_Symbol,c3_. p3_Symbol,c4_. p4_Symbol,m1_,m2_,m3_,m4_}->{s_,t_,u_}, OptionsPattern[MandelstamRelations]]/;LScalarQ[c1]&&LScalarQ[c2]&&LScalarQ[c3]&&LScalarQ[c4]&&!LScalarQ[p1]&&!LScalarQ[p2]&&!LScalarQ[p3]&&!LScalarQ[p4] :=
  With[
	{eliminationRule = 
	  Switch[
		OptionValue[Eliminate],
		None, {},
		s|t|u, {OptionValue[Eliminate]->(-#1-#2+m1^2+m2^2+m3^2+m4^2)&@@DeleteCases[{s,t,u},OptionValue[Eliminate]]},
		_, Message[MandelstamRelations::optvg,Eliminate,OptionValue[Eliminate],"one of "<>ToString[DeleteCases[{s,t,u},0]]];{}
	  ]},

	If[p1=!=p2=!=p3=!=p4=!=0,
	  ReplaceAll[{LDot[p1,p1]->m1^2/c1^2, LDot[p2,p2]->m2^2/c2^2,
				  LDot[p3,p3]->m3^2/c3^2, LDot[p4,p4]->m4^2/c4^2,
				  LDot[p1,p2]->1/(2 c1 c2) (s-m1^2-m2^2), LDot[p3,p4]->1/(2 c3 c4) (s-m3^2-m4^2),
				  LDot[p1,p3]->1/(2 c1 c3) (-t+m1^2+m3^2), LDot[p2,p4]->1/(2 c2 c4) (-t+m2^2+m4^2),
				  LDot[p1,p4]->1/(2 c1 c4) (-u+m1^2+m4^2), LDot[p2,p3]->1/(2 c2 c3) (-u+m2^2+m3^2),
				  LTensor@@Prepend[Sort[{{p1},{p2},{p4},{p3}}],LeviCivitaE]->0}, eliminationRule],
	  {}]

  ];

MandelstamRelations[{p1_,p2_,p3_,p4_,m1_,m2_,m3_,m4_}->{s_,t_,u_}, OptionsPattern[MandelstamRelations]] := {} /; Check[Map[LTensor[#,Symbol]&,{p1,p2,p3,p4}];True,True];
MandelstamRelations[Except[Rule[{Except[_Plus],Except[_Plus],Except[_Plus],Except[_Plus],_,_,_,_},{_,_,_}]], OptionsPattern[MandelstamRelations]]  := Null /; Message[MandelstamRelations::arg];

LHS_MandelstamRelations:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,1];Fail];


(* ::Subsection::Closed:: *)
(*PVX*)


HoldPattern[PVX[args: PatternSequence[_,_]]] := PVA[args];
HoldPattern[PVX[args: PatternSequence[_,_,_,_,_]]] := PVB[args];
HoldPattern[PVX[args: PatternSequence[_,_,_,_,_,_,_,_,_]]] := PVC[args];
HoldPattern[PVX[args: PatternSequence[_,_,_,_,_,_,_,_,_,_,_,_,_,_]]] := PVD[args];

h_PVX := Null/;If[!argsCheckPVX[Length[Unevaluated[h]]],Message[PVX::hdiv,Unevaluated[h]]];


(* ::Subsection:: *)
(*LoopIntegrate*)


(* ::Subsubsection::Closed:: *)
(*Series and Derivatives*)


Unprotect[Inactive];

(*Derivative wrt mass*)
Derivative[0,0,left___,{0,n_Integer?Positive,0},right___][Inactive[LoopIntegrate]][num_,intVec_,denomSpecs__]:=
  With[{newDenomSpecs=MapAt[#+{0,0,1}&,{denomSpecs},Length[{left}]+1]},
	2*{denomSpecs}[[Length[{left}]+1,3]]*{denomSpecs}[[Length[{left}]+1,2]]*Inactive[LoopIntegrate][num,intVec,Sequence@@newDenomSpecs]
  ];

Derivative[0,0,left___,{0,n_Integer?Positive},right___][Inactive[LoopIntegrate]][num_,intVec_,denomSpecs__]:=
  With[{newDenomSpecs=MapAt[Append[#,2]&,{denomSpecs},Length[{left}]+1]},
	2*{denomSpecs}[[Length[{left}]+1,2]]*Inactive[LoopIntegrate][num,intVec,Sequence@@newDenomSpecs]
 ];

(*Derivatives used in series*)
Inactive/:HoldPattern[D[li:Inactive[LoopIntegrate][numerator_,intVar_,denom__List,opt:OptionsPattern[]],x_Symbol|{x_Symbol,1},NonConstants->{LoopIntegrate}]] (*/; x=!=intVar*) := 
	MapAt[D[#,x,NonConstants->{LoopIntegrate}]&,li,1]+
	Total@MapIndexed[-#1[[3]]*Inactive[LoopIntegrate][numerator*D[LDot[#1[[1]],#1[[1]]]-(#1[[2]])^2,x],intVar,Sequence@@ReplacePart[{denom},#2->(#1/.{q_,m_,w_}:>{q,m,w+1})],opt]&,PadRight[{denom},{Length[{denom}],3},1]];

Inactive/:HoldPattern[D[li:Inactive[LoopIntegrate][numerator_,intVar_,denom__List,opt:OptionsPattern[]],{x_Symbol,0},NonConstants->{LoopIntegrate}]] (*/; x=!=intVar*) := li;

Inactive/:HoldPattern[D[li:Inactive[LoopIntegrate][numerator_,intVar_,denom__List,opt:OptionsPattern[]],{x_Symbol,n_Integer},NonConstants->{LoopIntegrate}]] (*/; x=!=intVar*) := 
	D[MapAt[D[#,x,NonConstants->{LoopIntegrate}]&,li,1],{x,n-1},NonConstants->{LoopIntegrate}]+
	D[Total@MapIndexed[-#1[[3]]*Inactive[LoopIntegrate][numerator*D[LDot[#1[[1]],#1[[1]]]-(#1[[2]])^2,x],intVar,Sequence@@ReplacePart[{denom},#2->(#1/.{q_,m_,w_}:>{q,m,w+1})],opt]&,PadRight[{denom},{Length[{denom}],3},1]],{x,n-1},NonConstants->{LoopIntegrate}];

Protect[Inactive];


Unprotect[System`Private`InternalSeries];
HoldPattern[System`Private`InternalSeries[expr: Inactive[LoopIntegrate][numerator_,intVar_,denom:PatternSequence[___,Except[_Rule,_]],opts:OptionsPattern[LoopIntegrate]?(X`Internal`ValidOptionsQ[LoopIntegrate])],{x_,x0_,nn_Integer}]] /; !FreeQ[expr,x]:=
  Module[{res},
	Internal`InheritedBlock[{$LScalarList, Inactive},

	  Unprotect[Inactive]; Inactive[LoopIntegrate][0,___]:=0; Protect[Inactive];
	  $LScalarList=DeleteDuplicates[Append[$LScalarList,x]];

	  If[Catch[Check[validLoopIntegrateDenominators[intVar,{denom}];True,False] && x=!=intVar, LoopIntegrate],
	  
		res=(Sum[(D[expr,{x,i},NonConstants->{LoopIntegrate}]/.x->x0)(x-x0)^i/i!,{i,0,nn}]);
		System`SeriesDump`SafeSeries[res,{x,x0,nn}],

		$Failed

	  ]

	]
  ];
Protect[System`Private`InternalSeries];


(* ::Subsubsection::Closed:: *)
(*Partial fraction expansion*)


reInsert[list_,pos_]:=With[{insPos=MapIndexed[Subtract[#1,#2]&,pos]+1},  Insert[list,0,insPos]];


minBy[list_,f_,n_]:=list[[Ordering[f/@list,n]]];
partialFractionExpansionRule=dl_DenomSpec:>
With[{ns=NullSpace[Transpose[Last[CoefficientArrays[List@@dl[[All,1]], DeleteCases[Variables[List@@dl[[All,1]]],_?LScalarQ]]]]]},
  With[{den=List@@dl,nullVec=First[minBy[ns,Count[#,Except[0]]&,1]]},
  With[{squareOfDenominators=LDot[#[[1]],#[[1]]]-Power[#[[2]],2]& /@ den},
  With[{(*The sum, giving f*)
		f=Simplify[Dot[nullVec,squareOfDenominators]],
		(*List of weights of denominators involved in partial fraction expansion*)
		weightList=Pick[den[[All,3]],nullVec,Except[0|_List]]},
  With[{minWeight=Min[weightList]},

  Module[{positionOfZeros=Position[nullVec,0,{1,1},Heads->False], allExponents},

	If[PossibleZeroQ[f],

	  Module[{critDenomJ, newDen},
		critDenomJ=Position[nullVec,Except[0],{1,1},1,Heads->False];
		(*List of weights of denominators with the critical denominator removed.*)
		(*allExponents returns list of lists containing all combinations of exponents involved in multinomial expansion, except for the critical denominator*)
		(*Since multinomial expansion generates a homogenous polynomial of order exponent, need to get all permutations of exponents.*)
		allExponents=Flatten[Map[Permutations,PowersRepresentations[minWeight,Length[weightList]-1,1]],1];

		(*The critical denominator will get an additive contribution of Min[weightList]*)
		positionOfZeros=Union[positionOfZeros,critDenomJ];
		(*All Exponents with zeros inserted for those denominators not involved in partial fraction expansion or critical denominator*)
		allExponents=reInsert[#,positionOfZeros]&/@allExponents;

		(*Add the exponent to the critical denominator*)
		newDen=MapAt[#+minWeight&,den,{critDenomJ[[1,1]],3}];
		(-1)^minWeight/nullVec[[critDenomJ[[1,1]]]] Multinomial@@#*Inner[pow,nullVec,#,Times]DeleteCases[DenomSpec@@MapThread[(#1-{0,0,#2})&,{newDen,#}],{_,_,0}]&/@allExponents
	  ]
	,
		(*allExponents returns list of lists containing all combinations of exponents involved in multinomial expansion*)
		(*Since multinomial expansion generates a homogenous polynomial with all possible exponent distributions, need to get all permutations of exponents.*)
		allExponents=Flatten[Map[Permutations,PowersRepresentations[minWeight,Length[weightList],1]],1];

		(*All Exponents with zeros inserted for those denominators not involved in partial fraction expansion*)
		allExponents=reInsert[#,positionOfZeros]&/@allExponents;
		
		1/f^minWeight Multinomial@@#*Inner[pow,nullVec,#,Times]DeleteCases[DenomSpec@@MapThread[(#1-{0,0,#2})&,{den,#}],{_,_,0}]& /@ allExponents

	]

  ]]]]]/;ns=!={}
];


partialFractionExpand[numerator_,intVar_,sortedDenom_(*List*),optCancel_,dim_(*Integer*)]:=
  Module[{res={DenomSpec@@Map[MapAt[intVar+#&,#,1]&,sortedDenom]} (*HERE*) },

	res=res//.partialFractionExpansionRule/.intVar->0; (*HERE*)

	res=Total[res,Infinity];

	If[optCancel,
	  res/.DenomSpec:>(cancelDenominators[numerator,intVar,{##},dim]&),
	  res/.DenomSpec:>(covariantDecomposition[numerator,intVar,{##},dim]&)
	]
  ];


(* ::Subsubsection::Closed:: *)
(*Cancel denominators*)


(*Helper functions for partial fraction expansion*)
finiteDerivative[indices_(*List*)][coeffRules_(*List*)]:=
  DeleteCases[(*Remove terms with negative exponents*)
	Map[(*1.  For each monomial...*)
	  MapAt[(*2.  Subtract 'indices' from exponents*)
		Function[Plus[#1,-indices]],#,1]&,
	  coeffRules],
	Except[Rule[{__?NonNegative},_]]
];

(*After performing the finiteDerivative w.r.t. D1,D2,..., the next step is to evaluate this at the arguments.
  Some of the arguments may be zero, and if they are raised to a positive power, that term vanishes.
  Therefore these terms MUST be removed.  If they are not removed, the next step of taking the
  finite derivative w.r.t D0 will occur before evaluation at arguement which is wrong.**)
(*removeZeros takes a single List of CoefficientRules as its argument, and the evaluation arguments,
  and returns a new list of CoefficientRules where terms corresponding to 0^n are deleted.*)
removeZeros[rules_(*List*),args_(*List*)]:=DeleteCases[rules,Rule[expList_,_]/;Count[Pick[Rest@expList,Rest@args,0], _?Positive]>0];

performShift[coeffRule_] := 
  With[{listOfExponents=coeffRule[[1]],coefficient=coeffRule[[2]]},
	  (Prepend[(*g1^i1 g2^i2 ...*)##, (*D0^(n0+n1+...-i1-i2-...)*)Total[listOfExponents]-Total[#]]->
		(*coeff*(n1Ci1)(n2Ci2)...*)coefficient*Times@@Binomial[Rest[listOfExponents],#]) & /@ 
	    Tuples[Range[0,#]&/@Rest[listOfExponents]]
	];

(*finiteDerivativeWithShift returns the numerator of scalar product cancel formula*)
finiteDerivativeWithShift[indices:{k0_,rest___}][coeffRules_(*List*)][args_(*List*)]:=
  (*4. Express polynomial in standard form*)
  X`Internal`FromCoefficientRules[
	(*3. Perform a final final derivative w.r.t. D0*)
	finiteDerivative[PadRight[{k0},Length[indices]]]
	  [(*2. Convert expression D0^4 D1^5 D2^2 -> (D0^4)(D0+g1)^5(D0+g2)^2.  *)
		Flatten@ (*Need to flatten because performShift generates a list of terms from binomial expansion*)
		(performShift/@ (*only acts on single rule, so must be mapped over list*)
		  (*1.  Obtain the necessary finite derivatives w.r.t. D1,D2,...*)
		  removeZeros[finiteDerivative[{0,rest}][coeffRules],args])]
  ,args];


cancelDenominators[numerator_,intVar_,{}, dim_]:=0;

If[$VersionNumber >= 10.1,

(*In version 10.0+, can use GroebnerBasis`BasisAndConversionMatrix*)
cancelDenominators[numerator_,intVar_,sortedDenom_(*List*), dim_(*Integer*)]:=
  Module[{pList,mList,wList,canonicalizedNumerator,
			newVars,varsToBasic,basicToVars,toDenominators,p,m,d,
			polynomCoefficients,
			internalBasis,internalConversionMatrix},

	(*Transform external vectors to canonical form, defined by one denominator having zero external momenta flowing through it*)
	pList=Delete[sortedDenom[[All,1]]-sortedDenom[[1,1]],1];
	(*List of masses and weights*)
	mList=sortedDenom[[All,2]];
	wList=sortedDenom[[All,3]];

	(*Shift the numerator so that numerator is written in terms of external vectors in canonical form.*)
	canonicalizedNumerator = ReplaceAll[numerator, intVar->intVar-sortedDenom[[1,1]]];

	If[pList==={},
	  {internalBasis,internalConversionMatrix}={{},{{}}};
	  basicToVars={m[i_]:>mList[[i+1]]};
	  varsToBasic={},

	  {internalBasis,internalConversionMatrix}=GroebnerBasis`BasisAndConversionMatrix[pList,DeleteCases[Variables[pList], _?LScalarQ],Cases[Variables[pList], _?LScalarQ]];
	  basicToVars=(Thread[Array[p,Length[pList]]->pList] ~Join~ {m[i_]:>mList[[i+1]]});
	  varsToBasic=(Rule[LDot[#1,intVar],LDot[#2,intVar]]& @@@ (Thread[internalBasis->Dot[internalConversionMatrix,Array[p,Length[pList]]]]))
	];

	toDenominators={LDot[intVar,intVar]:>d[0]+m[0]^2,LDot[intVar,p[i_]]:>(d[i]-d[0]-m[0]^2-LDot[p[i],p[i]]+m[i]^2)/2};

	newVars = {LDot[intVar,intVar]-m[0]^2}~Join~Array[(2*LDot[intVar,p[#]]+LDot[p[#],p[#]]-m[#]^2+m[0]^2) &,Length[sortedDenom]-1]/.basicToVars;

	polynomCoefficients=X`Internal`CoefficientRules[canonicalizedNumerator/.varsToBasic/.toDenominators/.basicToVars, Array[d,Length[sortedDenom],0]];
	(*Print[polynomCoefficients];*)

	With[{canonDenom=Transpose[{Prepend[pList,0],mList,wList}]},
	  Total[covariantDecomposition[finiteDerivativeWithShift[#][polynomCoefficients][newVars(1-Unitize[wList-#])], 
		intVar,
		DeleteCases[MapThread[(#1-{0,0,#2})&,{canonDenom,#}],{_,_,_?NonPositive}],dim] & /@ 
		  Tuples[Range[0, #] & /@ wList]]
	]

  ],

cancelDenominators[numerator_,intVar_,sortedDenom_List,dim_Integer]:=
  Module[{pList,mList,wList,canonicalizedNumerator,
			momSymbs,newVars,varsToBasic,basicToVars,toDenominators,p,m,d,
			polynomCoefficients},

	(*Transform external vectors to canonical form, defined by one denominator having zero external momenta flowing through it*)
	pList=Delete[sortedDenom[[All,1]]-sortedDenom[[1,1]],1];
	(*List of masses and weights*)
	mList=sortedDenom[[All,2]];
	wList=sortedDenom[[All,3]];

	(*Shift the numerator so that numerator is written in terms of external vectors in canonical form.*)
	canonicalizedNumerator = ReplaceAll[numerator, intVar->intVar-sortedDenom[[1,1]]];

	(*Setup basis momentum symbols*)
	momSymbs=DeleteCases[Variables[pList], _?LScalarQ]; (*Extract just the momentum symbols*)

	(*vars are the user-input variables*)
	(*basicVars are the "basis" variables, p[1], p[2], ...*)
	varsToBasic=First[Quiet[Solve[Table[pList[[i]]==p[i],{i,1,Length[pList]}], momSymbs]]];
	basicToVars=First[Quiet[Solve[Equal@@@varsToBasic,Table[p[i],{i,1,Length[pList]}]]]] ~Join~ {m[i_]:>mList[[i+1]]};
	varsToBasic=Rule[LDot[#1,intVar],LDot[#2,intVar]]& @@@ varsToBasic;

	toDenominators={LDot[intVar,intVar]:>d[0]+m[0]^2,LDot[intVar,p[i_]]:>(d[i]-d[0]-m[0]^2-LDot[p[i],p[i]]+m[i]^2)/2};

	newVars = {LDot[intVar,intVar]-m[0]^2}~Join~Array[(2*LDot[intVar,p[#]]+LDot[p[#],p[#]]-m[#]^2+m[0]^2) &,Length[sortedDenom]-1]/.basicToVars;

	polynomCoefficients=X`Internal`CoefficientRules[canonicalizedNumerator/.varsToBasic/.toDenominators/.basicToVars, Array[d,Length[sortedDenom],0]];
	(*Print[polynomCoefficients];*)

	With[{canonDenom=Transpose[{Prepend[pList,0],mList,wList}]},
	  Total[covariantDecomposition[finiteDerivativeWithShift[#][polynomCoefficients][newVars(1-Unitize[wList-#])], 
		intVar,
		DeleteCases[MapThread[(#1-{0,0,#2})&,{canonDenom,#}],{_,_,_?NonPositive}],dim] & /@ 
		  Tuples[Range[0, #] & /@ wList]]
	]

  ]

];


(* ::Subsubsection::Closed:: *)
(*Passarino-Veltman tensor*)


X`Utilities`PassarinoVeltmanTensor::oddindex="There are `1` vectors, but `2` indices.  Cannot assign odd number of indices (`3`) to metric tensor.";
X`Utilities`PassarinoVeltmanTensor::negativeindex="There are `1` vectors, but only `2` indices to assign.";

X`Utilities`PassarinoVeltmanTensor[vecs:{{_,_Integer}...},{}]:=1;
X`Utilities`PassarinoVeltmanTensor[vecs:{{_,_Integer}...},indices:{_Symbol..}]/;MemberQ[vecs,{0,Except[0]}]:=0;

(*If indices are repeated, use recursion formula for PV-tensor contractions*)
X`Utilities`PassarinoVeltmanTensor[vecs:{{_,_Integer}...},indices:{_Symbol..}]:=
  With[{newIndices=Flatten@DeleteCases[Gather[indices],{_Symbol,_Symbol}],
		n=vecs[[All,2]],
		P=Length[indices],
		r=(Length[indices]-Total[vecs[[All,2]]])/2},

		pvTensorRecursion[Map[MapAt[vec,#,1]&,vecs,{1}],newIndices,(Length[indices]-Length[newIndices])/2] /; 
		  (If[r<0,Message[X`Utilities`PassarinoVeltmanTensor::negativeindex,Total[n],P];False,True] &&
		   If[!IntegerQ[r],Message[X`Utilities`PassarinoVeltmanTensor::oddindex,Total[n],P,2r];False,True])
  ];


(*usage: pvTensor[{p1,p2,...},{\[Mu]1,\[Mu]2,...}] gives the fully symmetrized Passarino-Veltman tensor,
  the indices \[Mu]1,\[Mu]2,... must all be unique.*)

pvTensor[vecs_List,{}]:=1;
pvTensor[vecs_List,indices_List]/;MemberQ[vecs,{0,Except[0]}]:=0;

(*Fully symmetric tensor built out of metric tensor only.*)
pvTensor[{}, indices_]:=
With[
  {P=Length[indices],
   r=Length[indices]/2,
   repPerm=Apply[Times,Map[Composition[Factorial,Length],Gather[indices]]]},
  With[{representative=Function@@{1/(r! 2^r) Product[pair[Slot[i],Slot[i+1]],{i,1,P,2}]}},

	If[IntegerQ[r],
	  (*If there are even number of indices*)
	  repPerm*Tr[representative@@@Permutations[indices]],
	  (*If there are odd number of indices*)
	  Return[0]
	]

  ]
];

(*General construction of Passarino-Veltman tensor with no repeated (self-contracted) indices*)
pvTensor[vecs_, indices_]:=
With[
  {sym=vecs[[All,1]],
   n=vecs[[All,2]],
   P=Length[indices],
   r=(Length[indices]-Total[vecs[[All,2]]])/2 (* = (P-Total[n])/2*),
   repPerm=Apply[Times,Map[Composition[Factorial,Length],Gather[indices]]]},

	With[{representative=
	  Function@@{
		Product[1/n[[j]]! Product[pair[sym[[j]], Slot[i]],{i,1+Sum[n[[k]],{k,1,j-1}],Sum[n[[k]],{k,1,j}]}],{j,1,Length[sym]}]*
			1/(r! 2^r) Product[pair[Slot[i],Slot[i+1]],{i,Total[n]+1,P,2}]}},

	repPerm*Tr[representative@@@Permutations[indices]]
  ]
];


(*usage: pvTensorRecursion[{p1,p2,...},{\[Mu]1,\[Mu]2,...},n] reduces the n self contracted pairs down to pvTensor.
  all indices \[Mu]1,\[Mu]2,... should be unique.*)

(*Recrusion relation for contracted PV tensors*)
pvTensorRecursion[vecs_,indices_List,0]:=pvTensor[DeleteCases[vecs,{_,0}],indices];

(*If there are no vectors*)
pvTensorRecursion[{},indices_List,n_]:=
 With[{P=Length[indices]+2n,nSum=0},
  If[P-nSum>0,(Dim+P-2+nSum)*pvTensorRecursion[{},indices,n-1],0]
];

pvTensorRecursion[vecs_,indices_List,n_]:=
 With[{len=Length[vecs],P=Length[indices]+2n,nSum=Total@Last@Transpose[vecs]},

  Sum[
   With[{ni=vecs[[i,2]]},
    If[ni*(ni-1)>0,pair[vecs[[i,1]],vecs[[i,1]]]*pvTensorRecursion[ReplacePart[vecs,{i,2}->ni-2],indices,n-1],0]
   ],
  {i,1,len}] +
  Sum[
   With[{ni=vecs[[i,2]],nj=vecs[[j,2]]},
    If[ni*nj>0,2*pair[vecs[[i,1]],vecs[[j,1]]]*pvTensorRecursion[ReplacePart[vecs,{{i,2}->ni-1,{j,2}->nj-1}],indices,n-1],0]
   ],
  {i,1,len}, {j,i+1,len}] +
  (*(d+P-2+n1+n2{p1n2,p2n2,...})*)
  If[P-nSum>0,(Dim+P-2+nSum)*pvTensorRecursion[vecs,indices,n-1],0]
];



(* ::Subsubsection::Closed:: *)
(*Covariant decomposition*)


TensorPVX::usage="X`Private`TensorPVX[idxvecList, n, {{p0,m0,w0}, {p1,m1,w1}, \[Ellipsis]}] represents the tensor loop function with 'n' pairs of self\[Hyphen]contracted loop momenta k.k multiplied by additional loop momentum vectors \!\(\*SubscriptBox[k,\[Mu]]\), \!\(\*SubscriptBox[k,\[Nu]]\), \[Ellipsis], \!\(k.p0\), \!\(k.p1\)\[Ellipsis] specified by 'idxvecList' in the numerator, and denominator factors \!\(\*SuperscriptBox[\((\*SuperscriptBox[\((k+p0)\),2]-\*SuperscriptBox[m0,2])\),w0]\*SuperscriptBox[\((\*SuperscriptBox[\((k+p1)\),2]-\*SuperscriptBox[m1,2])\),w1]\[Ellipsis]\) .";

(*Covariant tensor decomposition for A-functions*)
(*in canonical form*)
TensorPVX[indices_List,autoC_Integer,{{0,m0_,w0_:1}},dim_:4]:=
	With[{rank=Length[indices]+2*autoC, opts=Sequence@@DeleteCases[{Weights->{w0},Dimensions->dim},(Weights->{1..})|(Dimensions->4)]},
		pvTensorRecursion[{},indices,autoC]*X`PVA[rank/2,m0,(*Weights->{w0},Dimensions->dim*)opts]
	];
(*NOT in canonical form*)
TensorPVX[indices_List,autoC_Integer,{{p0_,m0_,w0_:1}},dim_:4]:=
	With[{rank=Length[indices]+2*autoC, opts=Sequence@@DeleteCases[{Weights->{w0},Dimensions->dim},(Weights->{1..})|(Dimensions->4)]},
		Sum[(-1)^(2n+Mod[rank,2]) pvTensorRecursion[{{vec[p0],2n+Mod[rank,2]}},indices,autoC] X`PVA[(rank-2n-Mod[rank,2])/2,m0, opts],{n,0,rank/2}]
	];

(*Covariant tensor decomposition for B-functions*)
(*in canonical form*)
TensorPVX[indices_List,autoC_Integer,{{0,m0_,w0_:1},{p1_,m1_,w1_:1}},dim_:4]:=
	With[{rank=Length[indices]+2*autoC, opts=Sequence@@DeleteCases[{Weights->{w0,w1},Dimensions->dim},(Weights->{1..})|(Dimensions->4)]},
		Sum[pvTensorRecursion[{{vec[p1],rank-2*indexR}},indices,autoC]*X`PVB[indexR,rank-2*indexR,LDot[p1,p1],m0,m1,opts],{indexR,0,rank/2}]
	];
(*NOT in canonical form*)
TensorPVX[indices_List,autoC_Integer,{{p0_,m0_,w0_:1},{p1_,m1_,w1_:1}},dim_:4]:=
	With[{rank=Length[indices]+2*autoC, opts=Sequence@@DeleteCases[{Weights->{w0,w1},Dimensions->dim},(Weights->{1..})|(Dimensions->4)]},
		Sum[(-1)^kdx Binomial[kdx,jdx]pvTensorRecursion[{{vec[p0],kdx},{vec[p1],rank-kdx-2r}},indices,autoC] X`PVB[r,rank-2r-jdx,LDot[(p1-p0),(p1-p0)],m0,m1,opts],{r,0,rank/2},{kdx,0,rank-2r},{jdx,0,kdx}]
	];

(*Covariant tensor decomposition for C-functions*)
(*in canonical form*)
TensorPVX[indices_List,autoC_Integer,{{0,m0_,w0_:1},{p1_,m1_,w1_:1},{p2_,m2_,w2_:1}},dim_:4]:=
	With[{P=Length[indices]+2*autoC, opts=Sequence@@DeleteCases[{Weights->{w0,w1,w2},Dimensions->dim},(Weights->{1..})|(Dimensions->4)]},
		Sum[With[{n2=P-2r-n1},pvTensorRecursion[{{vec[p1],n1},{vec[p2],n2}},indices,autoC]*X`PVC[r,n1,n2,LDot[p1,p1],LDot[(p2-p1),(p2-p1)],LDot[p2,p2],m0,m1,m2,opts]],{r,0,P/2},{n1,0,P-2r}]
	];
(*NOT in canonical form:*)
TensorPVX[indices_List,autoC_Integer,{{p0_,m0_,w0_:1},{p1_,m1_,w1_:1},{p2_,m2_,w2_:1}},dim_:4]:=
	With[{P=Length[indices]+2*autoC, opts=Sequence@@DeleteCases[{Weights->{w0,w1,w2},Dimensions->dim},(Weights->{1..})|(Dimensions->4)]},
		Sum[(-1)^n1*Multinomial[jdx,mdx,n1-mdx-jdx]*pvTensorRecursion[{{vec[p0],n1},{vec[p1],n2},{vec[p2],P-2r-n1-n2}},indices,autoC]*X`PVC[r,mdx+n2,P-2r-jdx-mdx-n2,LDot[p1-p0,p1-p0],LDot[p2-p1,p2-p1],LDot[p2-p0,p2-p0],m0,m1,m2,opts],{r,0,P/2},{n1,0,P-2r},{n2,0,P-2r-n1},{jdx,0,n1},{mdx,0,n1-jdx}]
	];

(*Covariant tensor decomposition for D-functions*)
(*in canonical form*)
TensorPVX[indices_List,autoC_Integer,{{0,m0_,w0_:1},{p1_,m1_,w1_:1},{p2_,m2_,w2_:1},{p3_,m3_,w3_:1}},dim_:4]:=
	With[{P=Length[indices]+2*autoC, opts=Sequence@@DeleteCases[{Weights->{w0,w1,w2,w3},Dimensions->dim},(Weights->{1..})|(Dimensions->4)]},
		Sum[With[{n3=P-2r-n1-n2},pvTensorRecursion[{{vec[p1],n1},{vec[p2],n2},{vec[p3],n3}},indices,autoC]*X`PVD[r,n1,n2,n3,LDot[p1,p1],LDot[(p2-p1),(p2-p1)],LDot[(p3-p2),(p3-p2)],LDot[p3,p3],LDot[p2,p2],LDot[p1-p3,p1-p3],m0,m1,m2,m3,opts]],{r,0,P/2},{n1,0,P-2r},{n2,0,P-2r-n1}]
	];
(*NOT in canonical form:*)
TensorPVX[indices_List,autoC_Integer,{{p0_,m0_,w0_:1},{p1_,m1_,w1_:1},{p2_,m2_,w2_:1},{p3_,m3_,w3_:1}},dim_:4]:=
	With[{P=Length[indices]+2*autoC, opts=Sequence@@DeleteCases[{Weights->{w0,w1,w2,w3},Dimensions->dim},(Weights->{1..})|(Dimensions->4)]},
		Sum[(-1)^n1*Multinomial[jdx,k2dx,k3dx,n1-jdx-k2dx-k3dx]*pvTensorRecursion[{{vec[p0],n1},{vec[p1],n2},{vec[p2],n3},{vec[p3],P-2r-n1-n2-n3}},indices,autoC]*X`PVD[r,k2dx+n2,k3dx+n3,P-2r-n2-n3-jdx-k2dx-k3dx,LDot[(p1-p0),(p1-p0)],LDot[(p2-p1),(p2-p1)],LDot[(p3-p2),(p3-p2)],LDot[(p3-p0),(p3-p0)],LDot[(p2-p0),(p2-p0)],LDot[(p3-p1),(p3-p1)],m0,m1,m2,m3,opts],{r,0,P/2},{n1,0,P-2r},{n2,0,P-2r-n1},{n3,0,P-2r-n1-n2},{jdx,0,n1},{k2dx,0,n1-jdx},{k3dx,0,n1-jdx-k2dx}]
	];


(*General case*)
TensorPVX[indices_List,autoC_Integer,denom:{{_,_,_:1}..},dim_:4]:=
  With[{momInv=
	Which[
	  OddQ[Length[denom]],   With[{k=Floor[Length[denom]/2]}, Sequence@@Flatten[Table[LDot[#1-#2,#1-#2]&[denom[[Mod[i+j,2k+1]+1,1]],denom[[Mod[j,2k+1]+1,1]]],{i,1,k},{j,0,2k}]]],
	  EvenQ[Length[denom]],  With[{k=Floor[Length[denom]/2]}, Sequence@@Join[Flatten[Table[LDot[#1-#2,#1-#2]&[denom[[Mod[i+j,2k]+1,1]],denom[[Mod[j,2k]+1,1]]],{i,1,k-1},{j,0,2k-1}]],Table[LDot[#1-#2,#1-#2]&[denom[[Mod[k+j,2k]+1,1]],denom[[Mod[j,2k+1]+1,1]]],{j,0,k-1}]]]
	],
	P=Length[indices]+2*autoC},
	Sum[Total[pvTensorRecursion[Transpose[{vec/@(denom[[2;;,1]]-denom[[1,1]]),#1}],indices,autoC]*X`PVX[r,Sequence@@#1,momInv,Sequence@@denom[[All,2]](*,Weights\[Rule]denom[[All,3]],Dimensions\[Rule]dim*)]&/@Flatten[Map[Permutations,Map[PadRight[#,Length[denom]-1]&,IntegerPartitions[P-2r,Length[denom]-1]]],1]],{r,0,P/2}]
  ];


(*covariantDecomposition performs the covariant decomposition for integrals in canonical form.*)

(*the inputPoly can only contain intVar in the form of LDot and LTensor.  All other forms must be uncontracted.*)
covariantDecomposition[inputPoly_,intVar_,{},dim_Integer]:=0;

covariantDecomposition[inputPoly_, intVar_, denom_List, dim_Integer]:=
  Module[{vars,expr},
	(*List of variables combinations involving integration variable to be converted*)
	vars=Prepend[Cases[Variables[inputPoly],HoldPattern[LTensor[intVar, _]]|HoldPattern[LDot[intVar, Except[intVar,_]]]],LDot[intVar,intVar]];
	(*Turn expression into a list of rules*)
	expr=X`Internal`CoefficientRules[inputPoly,vars];
	(*Dot products turn into vec, four-vectors turn into idx*)
	vars=vars/.{HoldPattern[LDot[intVar,Except[intVar,p_(*Symbol*)]]]:>vec[p], HoldPattern[LTensor[intVar,a_Symbol]]:>idx[a]};
	(*Convert list of rules into tensor decomposition*)
	Total[expr/.(Rule[expo_,coeff_]:>coeff*TensorPVX[Inner[ConstantArray[#1,#2]&,Rest[vars],Rest[expo],Join],First[expo],denom,dim])]

  ];


(* ::Subsubsection::Closed:: *)
(*FermionLine processing*)


(*Extract on shell conditions from arguments of vertex Projector*)

fermionLineOnShellRules[{p1_,m1_},{p2_,m2_}]:=
  Module[{momSymbs=DeleteCases[Variables[{p1,p2}],_?LScalarQ],
	numberOfIndepMom,indepMom,onShellConditions},

	(*If there are more than two symbols making up p1 and p2,
	  or if p1.p1 or p2.p2 is already defined,
	  can't automate on shell conditions*)
	If[Length[momSymbs]>2 || FreeQ[LDot[p1,p1], _LDot] || FreeQ[LDot[p2,p2], _LDot], Return[{}]];

	numberOfIndepMom=Length[GroebnerBasis[{p1,p2},Variables[momSymbs]]];
	indepMom=momSymbs[[1;;numberOfIndepMom]];

	onShellConditions=Quiet[Solve[{LDot[p1,p1]==m1^2,LDot[p2,p2]==m2^2},{LDot[indepMom[[1]],indepMom[[1]]],LDot[indepMom[[2]],indepMom[[2]]]}]];

	If[onShellConditions=!={},
	  First[onShellConditions],
	  Message[LoopIntegrate::kina,TraditionalForm[HoldForm[{LDot[p1,p1]==m1^2,LDot[p2,p2]==m2^2}]]];
	  {}
	]
];

(*Legacy v1.0 syntax*)
fermionLineOnShellRules[p1_,p2_,m1_,m2_]:=fermionLineOnShellRules[{p1,m1},{p2,m2}];


(* ::Subsubsection::Closed:: *)
(*internalLoopIntegrate*)


loopIntegrateOrganizationScheme = Function[{optionOrganization,expr,result},
  Switch[optionOrganization,
	Automatic, expr,
	None, {},
	LTensor, X`Utilities`TensorStructures[result],
	Function, {_PVA, _PVB, _PVC, _PVD}
  ],{HoldAll} (*Don't determine the tensor structures unless it's necessary*)
];


(*parsedDenom[[1]] = factors indep. of loop momentum (sterile);
  parsedDenom[[2]] = factors of negative weight (lifted);
  parsedDenom[[3]] = sortedDenom;  *)
internalLoopIntegrate[intVar_,parsedDenom_,optionApart_,optionCancel_,optDimensions_,optDiracAlgebra_,optionOrganization_,vertexProjectorPresentQ_,onShell_]:=
  Function[{parsedNumer},
  Module[{result},

	result=Which[
	  optionApart,  parsedDenom[[1]]*partialFractionExpand[parsedNumer*parsedDenom[[2]],intVar,parsedDenom[[3]],optionCancel,optDimensions],
	  optionCancel, parsedDenom[[1]]*cancelDenominators[parsedNumer*parsedDenom[[2]],intVar,parsedDenom[[3]],optDimensions],
	  True,         parsedDenom[[1]]*covariantDecomposition[parsedNumer*parsedDenom[[2]],intVar,parsedDenom[[3]],optDimensions]
	]/.onShell;


	(*BEGIN Post processing*)
	(*If there are higher rank tensors, contract them*)
	If[!FreeQ[result, LTensor[_,_,_,__]], result = highRankTensorContract[result]];
	If[!FreeQ[result, _DiracMatrix|_Spur|Blank[Inactive[Spur]]], 
	  If[optDiracAlgebra,
	    result = fermionLineContract[result],
		result = elementaryFermionLineContract[result]
	  ]
	];

	Which[
	  (*This is the case when a vertex projector is present*)
	  !optionCancel && vertexProjectorPresentQ,
		(*Print["There is projector"];*)
		If[optionOrganization=!=None, 
		  Collect[result,loopIntegrateOrganizationScheme[optionOrganization,{_PVB, _PVC},result],FactorSquareFree],
		  result],

	  optDiracAlgebra && !FreeQ[parsedNumer, _FermionLineProduct],
		internalFermionLineProductExpand[parsedNumer,X`Utilities`CollectByTensorStructures[fermionLineContract[result]]],

	  optDiracAlgebra && !FreeQ[parsedNumer, _FermionLine],
		internalFermionLineExpand[parsedNumer,X`Utilities`CollectByTensorStructures[fermionLineContract[result]]],

	  optDiracAlgebra && !FreeQ[result, _DiracMatrix|_Spur|Blank[Inactive[Spur]]],
		internalDiracMatrixExpand[parsedNumer,X`Utilities`CollectByTensorStructures[fermionLineContract[result]]],

	  True,
		Collect[Expand[result,_LTensor], loopIntegrateOrganizationScheme[optionOrganization,If[Length[parsedDenom[[3]]]<4, DeleteCases[X`Utilities`TensorStructures[result],1]~Join~{_PVA, _PVB, _PVC, _PVD}, {_PVA, _PVB, _PVC, _PVD}],result]]
	]

  ],Listable
  ];


(* ::Subsubsection::Closed:: *)
(*LoopIntegrate*)


LoopIntegrate::kina="Warning: Vertex projection with inconsistent kinematics `1` encountered.";
LoopIntegrate::idenom="Denominator specifier `1` does not have the form {momentum, mass} or {momentum, mass, weight}.";
LoopIntegrate::klindenom="Momentum `1` of denominator `2` is not linear in integration variable `3`.";
LoopIntegrate::wdenom="Weight `1` of denominator `2` is not a machine-sized integer.";
LoopIntegrate::kdenom="Unexpected integration variable `1` in position `2` of denominator specifier `3`.";
LoopIntegrate::nocancel="Warning: External vectors `1` are linearly dependent, scalar products involving integration variable `2` in the numerator cannot be canceled with denominator factors.  Set Apart->True to LoopIntegrate to permit canceling scalar products." (*Use linearly independent external vectors and make on-shell replacements on output.*);
LoopIntegrate::kinem="Invalid integration variable `1`;  atomic symbol expected.";
LoopIntegrate::iext="Invalid external momentum `1`.";
LoopIntegrate::intvar="Integration variable cannot appear beyond position 2.";
LoopIntegrate::poly="Numerator is not a polynomial in `1`.\!\(\*
StyleBox[\"vec\", \"TI\"]\), or \!\(\*SubscriptBox[\(`1`\),\!\(\*
StyleBox[\"idx\", \"TI\"]\)]\).";
(*LoopIntegrate::lindm = "Input expression is not linear in DiracMatrix.";
LoopIntegrate::linfl = "Input expression is not linear in FermionLine, or FermionLineProduct; \n possibly missing '\[CircleTimes]' (alias: [\!\(\*\nStyleBox[\"Esc\",\nFontWeight->\"Bold\"]\)] c * [\!\(\*\nStyleBox[\"Esc\",\nFontWeight->\"Bold\"]\)]).";*)
LoopIntegrate::mixfl = "Input is a mixed expression in DiracMatrix, FermionLine, FermionLineProduct.  Expecting only one type of object.";
LoopIntegrate::syntax="Integration variable `1` in numerator is not in form `2`, or `3`.";


(*Denominator parser takes user-input sequence of denominator specifiers,
  and processes it for input into cancelDenominators or covariantDecomposition*)
denominatorParser =
Function[{intVar,inputDenom},
  With[(*Pad with unit weights, and merge duplicate entries*)
	{(*paddedDenom=PadRight[inputDenom,{Length[inputDenom],3},1],*)
	 (*paddedAndMergedDenom{#[[1,1]],#[[1,2]],Total[#[[All,3]]]}&/@GatherBy[paddedDenom,#[[1;;2]]&]*)
	 paddedDenom={#[[1,1]],#[[1,2]],Total[#[[All,3]]]}&/@GatherBy[PadRight[inputDenom,{Length[inputDenom],3},1],#[[1;;2]]&],
	 intVarRescale=Function[{Expand[#[[1]]/(Coefficient[#[[1]],intVar,1])],#[[2]]/PowerExpand[Sqrt[(Coefficient[#[[1]],intVar,1])^2]],#[[3]]}]},
	With[(*Remove Non-positive weights or sterile denominators*)
	  {reducedDenom=DeleteCases[paddedDenom,{_,_,_Integer?NonPositive}|{_?(FreeQ[#,intVar]&),_,_}]},
	  With[
		 (*Construct constant factors 
			(if denominator is independent of integration variable, pull it out,
			 otherwise, pull out coefficient of integration momentum.) *)
		 {sterileFactors = Product[If[FreeQ[paddedDenom[[index,1]],intVar],(LDot[paddedDenom[[index,1]],paddedDenom[[index,1]]]-(paddedDenom[[index,2]])^2)^-paddedDenom[[index,3]], (Coefficient[paddedDenom[[index,1]],intVar,1]^2)^(-paddedDenom[[index,3]])],{index,1,Length[paddedDenom]}],
		 (*Construct factors that belong in numerator.*)
		 liftedFactors = Product[If[TrueQ[Negative[paddedDenom[[index,3]]]],(LDot[paddedDenom[[index,1]],paddedDenom[[index,1]]]-(paddedDenom[[index,2]])^2)^-paddedDenom[[index,3]],1],{index,1,Length[paddedDenom]}],
		 (*Rescale non-canonically normalized integration momentum,
		   kill integration variables (intVar->0), and
		   sort so 0 external momentum is first.*)
		 sortedDenom = 
			If[Length[reducedDenom]!=4,
				Sort[ReplaceAll[Map[intVarRescale,reducedDenom],intVar->0],OrderedQ[{#1[[1]],#2[[1]]}]&],
				ReplaceAll[Map[intVarRescale,reducedDenom],intVar->0]]}, (*HERE*)

		{sterileFactors, liftedFactors, sortedDenom}

	  ]
	]
  ]
];

vanishingDetZQ[vecs_(*List*)]:=Length[vecs] > 0 && PossibleZeroQ[Det[Outer[LDot,vecs,vecs]]];

(*Numerator processor takes the numerator data, and processes it:
  (*1*) If input numerator doesn't have Contract or Spur, then perform elementary contract;
  (*2*) then on each element of numerator (if a list), if there are high rank tensors or open fermion line,
	then try to uncontract integration variable out of them*)

numeratorProcessor=
Function[{numerData,intVar,optDiracAlgebra},
  Catch[Module[{expr=First[numerData]},
	Which[
	  optDiracAlgebra && !FreeQ[First[numerData],_FermionLineProduct],
		If[(*No contract in numerator*)Last[numerData][[1]]==={}, expr=Composition[elementaryContract,highRankTensorContract,fermionLineContract][expr]];
		expr=internalFermionLineProductExpand[First[numerData],expr,ChisholmExpand->False,GordonIdentity->False];
		(*Echo[Count[expr,_FermionLineProduct,Infinity]];*)
		softUncontract[expr,intVar,True],
	  optDiracAlgebra && !FreeQ[First[numerData],_FermionLine],
		If[(*No contract in numerator*)Last[numerData][[1]]==={}, expr=Composition[elementaryContract,highRankTensorContract,fermionLineContract][expr]];
		softUncontract[internalFermionLineExpand[First[numerData],expr,ChisholmExpand->False,GordonIdentity->False],intVar,True],
	  !FreeQ[expr, LTensor[Except[MetricG,_],PatternSequence[_,__]]|_DiracMatrix|_Spur|Blank[Inactive[Spur]]],
		If[(*No contract in numerator*)Last[numerData][[1;;2]]==={{},{}}, expr=elementaryContract[expr]];
		softUncontract[expr,intVar,optDiracAlgebra],
	  True, If[(*No contract in numerator*)Last[numerData][[1;;2]]==={{},{}}, expr=elementaryContract[expr], expr]	
	]
  ],DiracMatrix,messageInvalidDiracMatrix[LoopIntegrate]]
];

ldotInDenomOfNumerQ=
  Function[{parsedNumer},
	If[Head[parsedNumer]===Plus, !FreeQ[Denominator[List@@parsedNumer],LDot], !FreeQ[Denominator[parsedNumer],LDot]]
  ,Listable];


(*Uses Sow/Reap so that if user stores numerator using SetDelayed, the presence of Contract, Spur, and Projector can still be detected*)
(*Need to obtain on shell conditions so that singularity due to projections can be removed.*)

(*Needs HoldFirst so that LoopIntegrate can reap data from numerator.*)
SetAttributes[LoopIntegrate,HoldFirst];
LoopIntegrate[numerator_,intVar_,denom:PatternSequence[___,Except[_Rule,_]],opts:OptionsPattern[]?(X`Internal`ValidOptionsQ[LoopIntegrate])]:=
  With[{parsedDenom=denominatorParser[intVar,{denom}],
		numerData=Reap[numerator, {"Contract","Spur","Projector"}]},
	  (*First[result] = computed numerator,
		Last[result]  = reaped values,
				[[1]] = contract: {} or {{True}},
				[[2]] = spur: {} or {{True}},
				[[3]] = projector: {} or {{{{p1,m},{p2,m}}}}*)
	With[{parsedNumer = numeratorProcessor[numerData,intVar,OptionValue[DiracAlgebra]],
		  vertexProjectorPresentQ=(Last[numerData][[3]]=!={} && MatchQ[Last[numerData][[3,1,1]],(*New syntax*){{_,_},{_,_}}(*|(*legacy v1 .0 syntax*){_,_,_,_}*)])},
	  With[{(*If there is a vertex projector, and numerator is not in a list, then extract on shell conditions. [will not be used if numerator is a list]*)
			onShell=If[vertexProjectorPresentQ && (Head[parsedNumer]=!=List || (Length[Last[numerData][[3,1]]]==Length[parsedNumer] && SameQ@@Last[numerData][[3,1]])), fermionLineOnShellRules@@(Last[numerData][[3,1,1]]), {}],
			optionCancel =
			  With[{pList = If[Length[parsedDenom[[3]]]>0,Rest[parsedDenom[[3,All,1]]] - parsedDenom[[3,1,1]],{}]}, 
				Switch[OptionValue[Cancel],
				  (*Automatic: If the internal momenta are linearly dependent, or if there is a vertex projector, then don't Cancel common factors*)
				  Automatic, !(vertexProjectorPresentQ || (vanishingDetZQ[pList] && !OptionValue[Apart]) || Or@@ldotInDenomOfNumerQ[parsedNumer]),
				  (*True: If the internal momenta are linearly dependent, issue a message, and don't Cancel common factors*)
				  True, If[vanishingDetZQ[pList] && !OptionValue[Apart], Message[LoopIntegrate::nocancel,parsedDenom[[3,All,1]],intVar]; False, True],
				  False, False]]},
	  (*internalLoopIntegrate is a Listable function*)
	  internalLoopIntegrate[intVar,parsedDenom,OptionValue[Apart],optionCancel(*OptionValue[Cancel]*),OptionValue[Dimensions],OptionValue[DiracAlgebra],OptionValue[Organization],vertexProjectorPresentQ,onShell][parsedNumer]
	  
	]/;Catch[Check[validLoopIntegrateNumerator[parsedNumer,intVar,vertexProjectorPresentQ];True,False], LoopIntegrate]
  ]/;Catch[Check[validLoopIntegrateInput[intVar,parsedDenom[[3]],opts];True,False], LoopIntegrate]
]/;Catch[Check[validLoopIntegrateDenominators[intVar,{denom}];True,False], LoopIntegrate];


LHS_LoopIntegrate:=RuleCondition[X`Internal`CheckArgumentCount[LHS,3,Infinity];Fail];


validLoopIntegrateDenominators[intVar_,unparsedDenom_]:=
  (
	(*Check that denominator specifiers are length 2 or 3*)
	With[{(*badDenom=Position[Length/@unparsedDenom,Except[2|3],{1,1},1,Heads->False]*)
		  badDenom=Position[unparsedDenom,Except[{_,_}|{_,_,_}],{1},1,Heads->False]},
	  If[badDenom=!={},Message[LoopIntegrate::idenom, unparsedDenom[[First@First@badDenom]]]; Throw[False, LoopIntegrate]]
	];

	(*Check that four-vectors with product kernels are interpretable*)
	Check[Map[LTensor[#,Symbol]&,unparsedDenom[[All,1]]],Throw[False, LoopIntegrate]];

	(*Check that integration variable is an atomic symbol.*)
	If[Head[intVar]=!=Symbol, 
	  Message[LoopIntegrate::kinem, intVar],

	  (*If integration variable is atomic, 
	  check that integration variable does not appear in mass or weight slots of denominator specifier,*)
	  With[{badDenom = Position[unparsedDenom[[All,2;;]],_?(!FreeQ[#,intVar]&),{0,Infinity},1,Heads->True]},
		If[badDenom=!={},Message[LoopIntegrate::kdenom,intVar,First[badDenom][[2]]+1,unparsedDenom[[First@First@badDenom]]]]
	  ];

	  (*and check that momenta slots are at most linear in integration variable.*)
	  With[{badDenom = Position[unparsedDenom[[All,1]],_?((!PolynomialQ[#,intVar] || (Exponent[#,intVar]!=-\[Infinity] && Exponent[#,intVar]!=0 && Exponent[#,intVar]!=1))&),{1,1},1,Heads->False]},
		If[badDenom=!={}, Message[LoopIntegrate::klindenom, unparsedDenom[[First@First@badDenom,1]], unparsedDenom[[First@First@badDenom]], intVar]; Throw[False, LoopIntegrate]]
	  ]
	];

	(*Check that denominator weights are integers*)
	With[{badDenom=Position[PadRight[unparsedDenom,{Length[unparsedDenom],3},1][[All,3]],Except[_Integer],{1,1},1,Heads->False]},
	  If[badDenom=!={},Message[LoopIntegrate::wdenom, unparsedDenom[[First@First@badDenom,3]], unparsedDenom[[First@First@badDenom]]]; Throw[False, LoopIntegrate]]
	];
  );


Options[validLoopIntegrateInput]:=Options[LoopIntegrate];

validLoopIntegrateInput[intVar_, parsedDenom_, OptionsPattern[]]:=
  ((*Check options*)

	If[!MemberQ[{True,False},OptionValue[Apart]], Message[LoopIntegrate::opttf, Apart, OptionValue[Apart]]];
	If[!EvenQ[OptionValue[Dimensions]], Message[LoopIntegrate::optvg, Dimensions, OptionValue[Dimensions], "an even integer"]];
	If[!MemberQ[{Automatic,True,False},OptionValue[Cancel]], Message[LoopIntegrate::opttfa,Cancel,OptionValue[Cancel]]];
	If[!MemberQ[{Automatic,LTensor,Function,None},OptionValue[Organization]], Message[LoopIntegrate::optvg, Organization, OptionValue[Organization], "Automatic, LTensor, Function, or None"]];
	If[!MemberQ[{True,False},OptionValue[DiracAlgebra]], Message[LoopIntegrate::opttf, DiracAlgebra, OptionValue[DiracAlgebra]]];

	(*Check that none of the external momenta is a numeric quantity (except 0)*)
	With[{badExtMom=Position[parsedDenom[[All,1]],Except[0,_?LScalarQ],{1,1},1,Heads->False]},
	  If[badExtMom=!={},  Message[LoopIntegrate::iext, parsedDenom[[First@First@badExtMom,1]]]; Throw[False, LoopIntegrate] ]
	];
  );


validLoopIntegrateNumerator = 
  Function[{inputPoly,intVar,vertexProjectorPresentQ},

	If[inputPoly===$Failed,Throw[False,LoopIntegrate]];

	If[!vertexProjectorPresentQ (*only check for short inputs, otherwise this would take a long time*),

	  (*Check that numerator is a polynomial in integration variable*)
	  With[{flatPoly=inputPoly/.{LTensor[intVar,Except[intVar,_Symbol]]:>\[FormalA],LDot[intVar,intVar]:>\[FormalB],LDot[intVar,Except[intVar,_]]:>\[FormalC]}},
		If[If[$VersionNumber>8,!Internal`PolynomialFunctionQ[flatPoly,{\[FormalA],\[FormalB],\[FormalC]}],!PolynomialQ[flatPoly,{\[FormalA],\[FormalB],\[FormalC]}]],Message[LoopIntegrate::poly,intVar]];
		If[!FreeQ[{flatPoly},intVar],Message[LoopIntegrate::syntax,intVar,HoldForm[LDot[intVar,"\!\(\*StyleBox[\"vec\", \"TI\"]\)"]],HoldForm[LTensor[intVar,"\!\(\*StyleBox[\"idx\", \"TI\"]\)"]]]]
	  ];

	  validFermionLineExpandInputQ[inputPoly,LoopIntegrate];
	  validFermionLineExpandOptionsQ[OptionValue[FermionLineExpand,ChisholmExpand],OptionValue[FermionLineExpand,GordonIdentity],OptionValue[FermionLineExpand,ChiralBasis]]
	];

	True
  ,{Listable}];


(* ::Subsection::Closed:: *)
(*Finish*)


SetAttributes[{internalLoopIntegrate,TensorPVX,covariantDecomposition,partialFractionExpand,cancelDenominators},Unevaluated@{Protected, ReadProtected, Locked}];


(*Protecting Functions*)
SetAttributes[MandelstamRelations, Unevaluated@{Protected, ReadProtected}];
SetAttributes[LoopIntegrate, Unevaluated@{Protected, ReadProtected}];
SetAttributes[PVX, Unevaluated@{NHoldAll,Protected,ReadProtected}];
SetAttributes[LDot, Unevaluated@{ReadProtected}];
SetAttributes[LTensor, Unevaluated@{ReadProtected}];
SetAttributes[LScalarQ, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[Contract, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[Longitudinal, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[Transverse, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[Dim, Unevaluated@{Protected, ReadProtected}];
SetAttributes[MetricG, Unevaluated@{Protected, ReadProtected}];
SetAttributes[LeviCivitaE, Unevaluated@{Protected, ReadProtected}];

SetAttributes[{
	X`Utilities`Uncontract, X`Utilities`TensorStructures, X`Utilities`CollectByTensorStructures, 
	X`Utilities`ClearDuplicatedTensors, X`Utilities`PassarinoVeltmanTensor, X`Utilities`DisableFancyIO,
	X`Utilities`EnableFancyIO, X`Utilities`DummyIndices,X`Utilities`FreeIndices},

	Unevaluated@{Protected, ReadProtected, Locked}];


End[];


(*EndPackage[]*)

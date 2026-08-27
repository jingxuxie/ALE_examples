(* ::Package:: *)

Begin["`Private`"];


(* ::Subsection:: *)
(*Spinor space objects*)


(* ::Subsubsection::Closed:: *)
(*InternalSeries*)


(*Prevents series from acting on open fermion line structures*)

Unprotect[System`Private`InternalSeries];
System`Private`InternalSeries[dm_DiracMatrix,__]:=dm;
System`Private`InternalSeries[fl_FermionLine,__]:=fl;
System`Private`InternalSeries[flp_FermionLineProduct[x__],__]:=flp;
Protect[System`Private`InternalSeries];


(* ::Subsubsection::Closed:: *)
(*Gamma and Sigma*)


DiracG::indices="Dirac gamma `1` has `2` indices, only 1 index is expected.";
DiracG /: HoldPattern[LDot[DiracG,DiracG]] := Dim*Dirac1;
DiracG /: LDot[DiracG,0] := 0;
DiracG /: e: Except[LTensor[DiracG,_],LTensor[DiracG,idx__]] := Null/; Message[DiracG::indices,HoldForm[e],Length[{idx}]];


DiracS::indices="Gamma matrix commutator `1` has `2` indices, 2 indices are expected.";
DiracS /: HoldPattern[LTensor[DiracS, idx: PatternSequence[_,_]]] /;!OrderedQ[{idx}] := Signature[{idx}]LTensor[DiracS,Sequence@@Sort[{idx}]];
DiracS /: LTensor[DiracS,a_,a_] := 0;
DiracS /: e: Except[LTensor[DiracS,_,_],LTensor[DiracS,idx__]] := Null/;Message[DiracS::indices,HoldForm[e],Length[{idx}]];


(* ::Subsubsection::Closed:: *)
(*DiracMatrix*)


(*DiracMatrix can be nested; spur atomization opens it all up*)

General::symb="Expression '`1`' does not contain any recognized Dirac matrices;\n possibly missing Dirac unit matrix (alias: [\!\(\*\nStyleBox[\"Esc\",\nFontWeight->\"Bold\"]\)] 11 [\!\(\*\nStyleBox[\"Esc\",\nFontWeight->\"Bold\"]\)]).";
General::symbx="Product '`1`' contains too many Dirac matrices;\n possible comma missing, or may need to use DiracMatrix[].";

DiracMatrix[___,0,___] := 0;

DiracMatrix[left___, c_?(FreeQ[#,Dirac1|DiracG5|DiracPL|DiracPR|LDot[DiracG,_]|LTensor[DiracG|DiracS,__]|_DiracMatrix|_Projector[__]]&) Pattern[mtx,Dirac1|DiracG5|DiracPL|DiracPR|LDot[DiracG,_]|LTensor[DiracG|DiracS,__]|_DiracMatrix|_Projector[__]], right___] := c DiracMatrix[left, mtx, right];
DiracMatrix[left___, Dirac1, right___] := DiracMatrix[left, right];

Default[DiracMatrix] = Dirac1;
SetAttributes[DiracMatrix, {Flat}];


(* ::Subsubsection::Closed:: *)
(*FermionLine*)


FermionLine[u2_List, u1_List, 0] := 0;
FermionLine[u2_List, u1_List, c_ dm_] /; FreeQ[c, _DiracMatrix] := c FermionLine[u2, u1, dm];
FermionLine[u2_List, u1_List, h_Plus] := Distribute[List[u2, u1, h], Plus, List, Plus, FermionLine];


(* ::Subsubsection::Closed:: *)
(*FermionLineProduct*)


(*When user inputs product of FermionLine, bring them together under a common FermionLineProduct*)
FermionLine /: HoldPattern[Power[a: FermionLine[_, _, _],n_Integer?Positive]]:=FermionLineProduct@@ConstantArray[a,n];
FermionLine /: HoldPattern[Times[a: FermionLine[_, _, _],b: FermionLine[_, _, _]]]:=FermionLineProduct[a,b]; (*This is ESPECIALLY WAY too slow*)

FermionLineProduct /: HoldPattern[Times[a: FermionLineProduct[__],b: FermionLine[_,_,_]]] := Append[a, b];
FermionLineProduct /: HoldPattern[Times[a: FermionLineProduct[__],b: FermionLineProduct[__]]] := Join[a, b];


FermionLineProduct[c_FermionLine]:=c;
FermionLineProduct[___,0,___]:=0;
FermionLineProduct[left___,c_ fl_FermionLine,right___]:=c FermionLineProduct[left, fl, right];
FermionLineProduct[left___,h_Plus,right___]:=Distribute[List[left,h,right],Plus,List,Plus,FermionLineProduct];
HoldPattern[FermionLineProduct[left___,h_Times,right___]] /; !FreeQ[h,_FermionLine] := FermionLineProduct[left,Expand[h],right];
(*HoldPattern[FermionLineProduct[left___,h:Times[_Plus,_Plus,___],right___]]:=FermionLineProduct[left,Expand[h],right];*)

SetAttributes[FermionLineProduct,Flat];


(* ::Subsection:: *)
(*Dirac matrix parser*)


(* ::Subsubsection::Closed:: *)
(*homogeneous algebra (pushing DiracG5, DiracPL, DiracPR)*)


(*This is for parity basis*)
combineAndConvertPLPRtoG5 =
	str_dMtx /; !FreeQ[str,DiracPL|DiracPR] :> 
		With[{strWithOmittedGamma5=DeleteCases[str,DiracG5]},
			(*Form the list of effective position-differences, and check if they are all odd:*)
			(*Differences in positions of DiracPL and DiracPR should be even, so add one to DiracPL position.*)
			If[VectorQ[Flatten[Differences[Sort[Join[Position[strWithOmittedGamma5,DiracPL]+1,Position[strWithOmittedGamma5,DiracPR]]]]],OddQ],
			(*If they are all odd*)
				With[{newMtx=DeleteCases[str,DiracPL|DiracPR],
					  pos=Position[str,DiracPL|DiracPR,1,1][[1,1]]},
				  (*This is 1/2 \[PlusMinus] DiracG5/2 *)
				  1/2 newMtx + Switch[str[[pos]],DiracPL,-1,DiracPR,1]*1/2 Insert[newMtx,DiracG5,pos]
				],
			(*If there is an odd difference, then we have PL*PR=0 *)
			0]
		];

(*Combines and pushes DiracG5 to the right*)
combineAndPushG5 =
{
	dMtx[string___]/;EvenQ[Count[{string},DiracG5]]:>(-1)^Total[Flatten[Take[Differences[Position[{string},DiracG5]]-1,{1,-1,2}]]]*(dMtx@@DeleteCases[{string},DiracG5]),
	dMtx[string___]:>(-1)^Total[Flatten[(Position[Reverse[{string}],DiracG5,1,1]-1)~Join~Take[Differences[Position[{string},DiracG5]]-1,{1,-1,2}]]]*(dMtx5@@DeleteCases[{string},DiracG5])
};

(*Combines and pushes DiracG5 to the right, placing the appropriate spur rules [only for Spur]*) 
combinePushG5loadSpurRules = 
{
  str_dMtx/;OddQ[Length[DeleteCases[str,DiracG5]]] :> 0,
  str_dMtx/;EvenQ[Count[str,DiracG5]] :> 
		(-1)^Total[Take[Differences[Position[str,DiracG5]]-1,{1,-1,2}],2]*(Hold[ReplaceRepeated[#,spurRules]]&@DeleteCases[str,DiracG5]),
  str_dMtx(*/;OddQ[Count[{string},DiracG5]]*) :> 
		(-1)^Total[Take[Differences[Append[Position[str,DiracG5],{Length[str]+1}]]-1,{1,-1,2}],2]*(Hold[ReplaceRepeated[#,spur5Rules]]&@(dMtx5@@DeleteCases[str,DiracG5]))
};

clearG5PLPR[False] = Function[#/.combineAndConvertPLPRtoG5/.combineAndPushG5];


(*This is for chiral basis*)
(*Brings DiracG5 together, and converts the odd DiracG5 to PR-PL*)
combineG5andConvertToPLPR =
	{str_dMtx /; EvenQ[Count[str,DiracG5]] :> 
		With[{strWithoutPLPR=DeleteCases[str,DiracPL|DiracPR]},
			(-1)^Total[Take[Differences[Position[strWithoutPLPR,DiracG5]]-1,{1,-1,2}],2]*DeleteCases[str,DiracG5]],
	 str_dMtx(*/;OddQ[Count[str,DiracG5]]*) :> 
		With[{strWithoutPLPR=DeleteCases[str,DiracPL|DiracPR]},
			(-1)^Total[Take[Differences[Append[Position[strWithoutPLPR,DiracG5],{Length[strWithoutPLPR]+1}]]-1,{1,-1,2}],2]*(Append[DeleteCases[str,DiracG5],DiracPR]-Append[DeleteCases[str,DiracG5],DiracPL])]
	};

(*Brings left/right projectors together assuming no explicit DiracG5, and pushes it to the right*)
combineAndPushPLPR =
	{str_dMtx /; !FreeQ[str,DiracPL|DiracPR] :> 
		If[VectorQ[Flatten[Differences[Sort[Join[Position[str,DiracPL]+1,Position[str,DiracPR]]]]],OddQ],
			(*If they are all odd, they will merge leaving a remaining projector*)
				With[{newMtx=DeleteCases[str,DiracPL|DiracPR],
					  pos=Position[str,DiracPL|DiracPR,1,1][[1,1]]},
				  (*Push remaining projector to the very left (same as very right)*)
				  If[OddQ[Length[DeleteCases[str,DiracPL|DiracPR]]-pos],
					Switch[str[[pos]],DiracPL,dMtxL,DiracPR,dMtxR],
					Switch[str[[pos]],DiracPL,dMtxR,DiracPR,dMtxL]]@@newMtx
				],
			(*If there is an even difference, then we have PL*PR=0 *)
			0],
	 str_dMtx :> dMtxL@@str + dMtxR@@str};

clearG5PLPR[True] = Function[#/.combineG5andConvertToPLPR/.combineAndPushPLPR];


(* ::Subsubsection::Closed:: *)
(*diracMtxParser*)


X`Utilities`ValidDiracMatrixQ::usage = "\!\(X`Utilities`ValidDiracMatrixQ[\*StyleBox[\"diracmatrix\", \"TI\"]]\) yields True if \!\(\*StyleBox[\"diracmatrix\", \"TI\"]\) is a valid DiracMatrix, and yields False otherwise.";

SetAttributes[X`Utilities`ValidDiracMatrixQ,HoldFirst];

(*Not used at present*)
internalValidDiracMatrixQ[input__] := 
  With[{washedInput={input}/.{Dirac1|DiracG5|DiracPL|DiracPR|LDot[DiracG,Except[DiracG,_]]|LTensor[DiracG,_Symbol]|HoldPattern[LTensor[DiracS,Except[DiracG,_],Except[DiracG,_]]]|_Projector[__]:>"SpinorSpaceObject"}},	
	Scan[If[!MemberQ[FactorTermsList[#,"SpinorSpaceObject"],"SpinorSpaceObject"] || !FreeQ[#,DiracG|DiracS] ,Throw[False,"ValidDiracMatrixQ"]]&, Numerator[Together[washedInput]]];
	"SpinorSpaceObject"
  ];

X`Utilities`ValidDiracMatrixQ[expr_DiracMatrix]:=Catch[Replace[expr,dm_DiracMatrix:>internalValidDiracMatrixQ@@dm,{0,Infinity}];True,"ValidDiracMatrixQ"];

X`Utilities`ValidDiracMatrixQ[_] := False;

messageInvalidDiracMatrix[head_] := (If[#[[1]]<1, Message[head::symb,#[[2]]], Message[head::symbx,#[[2]]]]; $Failed)&;


atomizeRules=
{
  dMtx[a___,m_. Dirac1,b___]:>m dMtx[a,b],
  dMtx[a___,c_ o:(DiracG5|DiracPL|DiracPR(*|LTensor[DiracS,_,_]*)),b___]:>c dMtx[a,o,b],
  dMtx[a___,c_. LDot[DiracG,g2_],b___] :> c dMtx[a,vec[g2],b],
  dMtx[a___,c_. LTensor[DiracG,mu_],b___] :> c dMtx[a,idx[mu],b]
};


(*If there were any \[Sigma], need to contract the metric tensor*)

contractMetricIndMtx=
  ReplaceRepeated[#,
	{HoldPattern[LTensor[MetricG, PatternSequence[a_,b_]|PatternSequence[b_,a_]]*dMtx[left___,h_[a_],right___]]:>dMtx[left,h[b],right],
	 LTensor[Except[DiracG,v_], a_Symbol]*dMtx[left___,idx[a_],right___]:>dMtx[left,vec[v],right],
	 HoldPattern[LTensor[MetricG, PatternSequence[a_,b_]|PatternSequence[b_,a_]] LTensor[MetricG, PatternSequence[a_,c_]|PatternSequence[c_,a_]]]:>LTensor[MetricG,b,c],
	 HoldPattern[Power[LTensor[MetricG, _Symbol, _Symbol],2]]:>Dim}]&;


(*This is used in Spur and FermionLineExpand*)
(*Converts product of Dirac matrices to Package-X internal form, putting each term in a list*)

(*Gamma5, PL and PR are not converted*)

(*Output expression is a list of terms, with each element of the form:
	    constant*dMtx[idx[\[Mu]],vec[k],DiracG5,idx[\[Nu]],DiracPL...].*)

diracMtxParser[diracMtx_dMtx, expandSigma_:True]:=
  Module[{expression, internalDiracMatrix, sigmaMtxPresent=False},Block[{dMtx},

	(*Swallow all symbols (constants) multiplying DiracMatrix*)
	internalDiracMatrix /: HoldPattern[Times[internalDiracMatrix[mtx___],Longest[const__]]] := internalDiracMatrix[mtx,Times[const] Dirac1];
	SetAttributes[internalDiracMatrix,Flat];

	(*Convert all DiracMatrix into internalDiracMatrix*)
	expression=ReplaceAll[#,DiracMatrix->internalDiracMatrix]&/@diracMtx;

	(*Convert DiracS\[Mu]\[Nu] into internalDiracMatrix[]*)
	If[expandSigma,
	  expression=ReplaceAll[#,HoldPattern[c_. LTensor[DiracS, a_,b_]]:>(sigmaMtxPresent=True;(internalDiracMatrix[c*Dirac1 I,pair[{DiracG},a],pair[{DiracG},b]]-I*c* Dirac1 pair[a,b]))]&/@expression,
	  expression=ReplaceAll[#,HoldPattern[c_. LTensor[DiracS, a_,b_]]:>internalDiracMatrix[c*Dirac1 I/2,pair[{DiracG},a],pair[{DiracG},b]]-internalDiracMatrix[c*Dirac1 I/2,pair[{DiracG},b],pair[{DiracG},a]]]&/@expression
	];

	(*Distribute internalDiracMatrix[] over plus, and expand everything out.*)
	expression=Collect[ReplaceRepeated[#, internalDiracMatrix[mtx__]:>Distribute[internalDiracMatrix@@Expand[{mtx}]]],{Dirac1,DiracG5},Expand]&/@expression;

	(*Distribute dMtx over plus forming a list of terms, then flatten with respect to DiracMatrix*)
	expression=(Flatten[#,Infinity,internalDiracMatrix]&/@(Distribute[expression,Plus,dMtx,List,dMtx]));

	(*Checking for syntax errors*)
	Map[With[{ct=Count[#,Dirac1|DiracG5|DiracPL|DiracPR|LDot[DiracG,_]|HoldPattern[LTensor[DiracS,_,_]]|LTensor[DiracG,_Symbol],{0,1}]},If[ct!=1,Throw[{ct,#},DiracMatrix]]]&,Flatten[expression,1,dMtx]];

	(*Factor out constants, and in doing so convert gamma matrices into vec[] or idx[]*)
	expression= (#//.atomizeRules &) /@ expression;

	(*If sigma matrix was expanded, need to contract the metric tensor from anticommutation relation*)
	If[sigmaMtxPresent, contractMetricIndMtx/@expression, expression]
  ]];


(* ::Subsection:: *)
(*Spur*)


(* ::Subsubsection::Closed:: *)
(*Inhomogeneous algebra without DiracG5*)


(*dot products multiplied by mtx:
  pair(a,b)*mtx(c,d,e...)
 code to recontract if a or b appears in mtx.
*)

dotDMtx[a_vec,b_vec,mtx_(*dMtx|dMtx5|dMtxL|dMtxR*)]:=LDot[First[a],First[b]]*mtx;
dotDMtx[a_vec,b_idx,mtx_(*dMtx|dMtx5|dMtxL|dMtxR*)]:=(Switch[#1,{},LTensor[First[a],First[b]]*mtx,_,ReplacePart[mtx,#1:>a]]&)[Position[mtx,b,1,1,Heads->False]];
dotDMtx[b_idx,a_vec,mtx_(*dMtx|dMtx5|dMtxL|dMtxR*)]:=(Switch[#1,{},LTensor[First[a],First[b]]*mtx,_,ReplacePart[mtx,#1:>a]]&)[Position[mtx,b,1,1,Heads->False]];
dotDMtx[a_idx,b_idx,mtx_(*dMtx|dMtx5|dMtxL|dMtxR*)]:=(Switch[#1,{},Switch[#2,{},LTensor[MetricG,First[a],First[b]]*mtx,_,ReplacePart[mtx,First[#2]:>a]],_,ReplacePart[mtx,First[#1]:>b]]&)[Position[mtx,a,1,1,Heads->False],Position[mtx,b,1,1,Heads->False]];


  (*UnRepeated gamma SPur*)
  (*a is a string of idx[\[Mu]], vec[k]... enclosed typically in dMtx, 
  but for programming purposes it is convenient to allow any head. *)

  ursp[_[]]=4;
  ursp[a_(*dMtx*)]:=With[{n=Length[a]},Sum[(-1)^i pair[a[[1]],a[[i]]]ursp[Rest[Drop[a,{i}]]],{i,2,n}]];
  (*ursp=If[Length[#1]\[Equal]0,4,Sum[(-1)^i pair[#1[[1]],#1[[i]]]#0[Rest[Drop[#1,{i}]]],{i,2,Length[#1]}]]&;*)

  (*Rules to take traces without DiracG5*)
  spurRules=
	Dispatch@{
	  dMtx[]:>4,
	  dMtx[Dirac1]:>4,
	  dMtx[a_,b_]:>4*pair[a,b],
	  (*dMtx[a_,b_,c_,e_]:>4pair[a,b]pair[c,e]-4pair[a,c]pair[b,e]+4pair[a,e]pair[b,c],*)

      (*For each pattern, include cyclic possibility*)
	  dMtx[a___,x_,x_,b___]:>Switch[x,_idx,Dim*dMtx[a,b],_vec,pair[x,x]dMtx[a,b]],
	  dMtx[x_,b___,x_]:>Switch[x,_idx,Dim*dMtx[b],_vec,pair[x,x]dMtx[b]],

	  dMtx[a___,x_,b_,x_,c___]:>Switch[x,_idx,-(Dim-2)dMtx[a,b,c],_vec,2dotDMtx[x,b,dMtx[a,x,c]]-pair[x,x]dMtx[a,b,c]],
	  dMtx[b_,x_,c___,x_]:>Switch[x,_idx,-(Dim-2)dMtx[b,c],_vec,2dotDMtx[x,b,dMtx[x,c]]-pair[x,x]dMtx[b,c]],
	  dMtx[x_,c___,x_,b_]:>Switch[x,_idx,-(Dim-2)dMtx[c,b],_vec,2dotDMtx[x,b,dMtx[c,x]]-pair[x,x]dMtx[c,b]],

	  dMtx[a___,x_,b_,c_,x_,e___]:>Switch[x,_idx,4dotDMtx[b,c,dMtx[a,e]]-(4-Dim)dMtx[a,b,c,e],_vec,pair[x,x]dMtx[a,b,c,e]-2dotDMtx[x,b,dMtx[a,x,c,e]]+2dotDMtx[x,c,dMtx[a,x,b,e]]],
	  dMtx[b_,c_,x_,e___,x_]:>Switch[x,_idx,4dotDMtx[b,c,dMtx[e]]-(4-Dim)dMtx[b,c,e],_vec,pair[x,x]dMtx[b,c,e]-2dotDMtx[x,b,dMtx[x,c,e]]+2dotDMtx[x,c,dMtx[x,b,e]]],
	  dMtx[c_,x_,e___,x_,b_]:>Switch[x,_idx,4dotDMtx[b,c,dMtx[e]]-(4-Dim)dMtx[b,c,e],_vec,pair[x,x]dMtx[b,c,e]-2dotDMtx[x,b,dMtx[x,c,e]]+2dotDMtx[x,c,dMtx[x,b,e]]],
	  dMtx[x_,e___,x_,b_,c_]:>Switch[x,_idx,4dotDMtx[b,c,dMtx[e]]-(4-Dim)dMtx[b,c,e],_vec,pair[x,x]dMtx[b,c,e]-2dotDMtx[x,b,dMtx[x,c,e]]+2dotDMtx[x,c,dMtx[x,b,e]]],

	  dMtx[a___,x_,Shortest[b__],x_,c___]:>With[{n=Length[{b}]},(-1)^n pair[x,x]dMtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],Drop[dMtx[b,x,c,a],{m}]],{m,1,n}]],

	  (*Most general formula, without repeated DiracG-matrices, is in ursp*)
	  dMtx[a__]:>ursp[dMtx[a]]
  };


(* ::Subsubsection::Closed:: *)
(*Inhomogeneous algebra with DiracG5*)


(*Manifestly 4 dimensional code.  Trace of unrepeated Dirac matrices with gamma5*)

(*a is a string of idx[\[Mu]], vec[k]... enclosed typically in dMtx5, 
  but for programming purposes it is convenient to allow any head. *)

With[{head=If[Head[#]===idx,First[#],{First[#]}]&},
  ursp5[a_(*dMtx5*)]:=
	With[{n=Length[a]-1, restMtx=Rest[a]},
	  Sum[
		  I*(-1)^(jdx+kdx+ldx) *
		  LTensor[LeviCivitaE,head[First[a]],head[restMtx[[jdx]]],head[restMtx[[kdx]]],head[restMtx[[ldx]]]] *
		  ursp[Delete[restMtx,{{jdx},{kdx},{ldx}}]]
		,{jdx,3,n},{kdx,2,jdx-1},{ldx,1,kdx-1}]
	]
];




  (*Rules to take traces with DiracG5 in the very right position.*)

  spur5Rules=
	Dispatch@{
	  
	  dMtx5[]:>0,
	  dMtx5[_,_]:>0,

	  dMtx5[objects: PatternSequence[_,_,_,_]] :> 
	  -4*I LTensor@@Prepend[
        Table[
            Switch[{objects}[[r]],
            _idx,{objects}[[r,1]],
            _vec,{{objects}[[r,1]]}],
          {r,1,4}],
	  LeviCivitaE],

	  (*For each pattern, include cyclic possibility*)
	  dMtx5[a___,x_,x_,b___]:>Switch[x,_idx,Dim*dMtx5[a,b],_vec,pair[x,x]*dMtx5[a,b]],
	  dMtx5[x_,b___,x_]:>-1*Switch[x,_idx,Dim*dMtx5[b],_vec,pair[x,x]*dMtx5[b]],

	  dMtx5[a___,x_,b_,x_,c___] :> Switch[x,_idx,-(Dim-2)dMtx5[a,b,c],_vec,2dotDMtx[x,b,dMtx5[a,x,c]]-pair[x,x]dMtx5[a,b,c]],
	  dMtx5[b_,x_,c___,x_] :> -1*Switch[x,_idx,-(Dim-2)dMtx5[b,c],_vec,2dotDMtx[x,b,dMtx5[x,c]]-pair[x,x]dMtx5[b,c]],
	  dMtx5[x_,c___,x_,b_] :> Switch[x,_idx,-(Dim-2)dMtx5[b,c],_vec,2dotDMtx[x,b,dMtx5[x,c]]-pair[x,x]dMtx5[b,c]],

	  dMtx5[a___,x_,b_,c_,x_,e___] :> Switch[x,_idx,4dotDMtx[b,c,dMtx5[a,e]]-(4-Dim)dMtx5[a,b,c,e],_vec,pair[x,x]dMtx5[a,b,c,e]-2dotDMtx[x,b,dMtx5[a,x,c,e]]+2dotDMtx[x,c,dMtx5[a,x,b,e]]],
	  dMtx5[b_,c_,x_,e___,x_] :> -1*Switch[x,_idx,4dotDMtx[b,c,dMtx5[e]]-(4-Dim)dMtx5[b,c,e],_vec,pair[x,x]dMtx5[b,c,e]-2dotDMtx[x,b,dMtx5[x,c,e]]+2dotDMtx[x,c,dMtx5[x,b,e]]],
	  dMtx5[c_,x_,e___,x_,b_] :> Switch[x,_idx,4dotDMtx[b,c,dMtx5[e]]-(4-Dim)dMtx5[b,c,e],_vec,pair[x,x]dMtx5[b,c,e]-2dotDMtx[x,b,dMtx5[x,c,e]]+2dotDMtx[x,c,dMtx5[x,b,e]]],
	  dMtx5[x_,e___,x_,b_,c_] :> -1*Switch[x,_idx,4dotDMtx[b,c,dMtx5[e]]-(4-Dim)dMtx5[b,c,e],_vec,pair[x,x]dMtx5[b,c,e]-2dotDMtx[x,b,dMtx5[x,c,e]]+2dotDMtx[x,c,dMtx5[x,b,e]]],

	  (*Continue to push contracted DiracG until they meet*)
	  dMtx5[a___,x_,Shortest[b__],x_,c___] :> With[{n=Length[{b}]},(-1)^n pair[x,x]dMtx5[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],dMtx5[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]],

	  (*Most general formula, without repeated DiracG-matrices*)
	  dMtx5[a__] :> ursp5[{a}]
	};



(* ::Subsubsection::Closed:: *)
(*Direct product of two spur (under development)*)


(*dot products multiplied by two mtx:
  pair(a,b)*mtx(c,d,e...)*mtx(f,g,h...)
 code to recontract if a or b appears in either mtx.
*)

dotDMtxProd[a_vec,b_vec,mtxProd_(*flProd*)]:=LDot[First[a],First[b]]*mtxProd;

dotDMtxProd[a_vec,b_idx,mtxProd_(*flProd*)]:=
  With[{place=Position[mtxProd,b,{2,2},1,Heads->False]},
    Switch[place,
      {},LTensor[First[a],First[b]]*mtxProd,
      _, ReplacePart[mtxProd,place->a]
    ]];

dotDMtxProd[b_idx,a_vec,mtxProd_(*flProd*)]:=
  With[{place=Position[mtxProd,b,{2,2},1,Heads->False]},
    Switch[place,
    {},LTensor[First[a],First[b]]*mtxProd,
    _, ReplacePart[mtxProd,place->a]
    ]];

dotDMtxProd[a_idx,b_idx,mtxProd_(*flProd*)]:=
  With[{place1=Position[mtxProd,a,{2,2},1,Heads->False],
		place2=Position[mtxProd,b,{2,2},1,Heads->False]},
    Switch[place1,
    {}, Switch[place2,
        {},LTensor[MetricG,First[a],First[b]]*mtxProd,
        _, ReplacePart[mtxProd,First[place2]->a]
        ],
     _,ReplacePart[mtxProd,First[place1]->b]
  ]];


spurProductRules =
  {flProd[dMtx[left1___,idx[a_],right1___],dMtx[left2___,idx[a_],right2___]]:>
	With[{n1=Length[{right1,left1}],n2=Length[{right2,left2}]},
	  Sum[(-1)^(j+k)dotDMtxProd[{right1,left1}[[j]],{right2,left2}[[k]],flProd[Drop[dMtx[right1,left1],{j}],Drop[dMtx[right2,left2],{k}]]],{j,1,n1},{k,1,n2}]],

   flProd[mtx1_dMtx,mtx2_dMtx]:>Times[ursp[mtx1],ursp[mtx2]]
  };


(* ::Subsubsection::Closed:: *)
(*Spur*)


(* Called at end of Spur if there is a 'Projector'*)
fastContract = 
  ReplaceRepeated[
	Expand[ReplaceRepeated[Expand[#,_LTensor],highRankTensorContractionRules],_LTensor]
	,elementaryContractionRules
  ]& ;


SetAttributes[Spur,HoldAll];

Spur::symb="Expression '`1`' does not contain any recognized Dirac matrices;\n possibly missing Dirac unit matrix (alias: [\!\(\*\nStyleBox[\"Esc\",\nFontWeight->\"Bold\"]\)] 11 [\!\(\*\nStyleBox[\"Esc\",\nFontWeight->\"Bold\"]\)]).";
Spur::symbx="Product '`1`' contains too many Dirac matrices;\n possible comma missing, or may need to use DiracMatrix[].";
Spur::proj="Projector should not occupy a slot in Spur that is accompanied by other factors.";

Spur[] := 4;
Spur[___,0,___] := 0;

Spur[diracMtx__] /; $DiracAlgebra :=
  Module[{diracSequence,result,projectorPresent=False},
	Catch[
	  Sow[True,"Spur"];

	  (*Check if there is a Projector[][]*)
	  If[!FreeQ[{diracMtx},Projector[__][__]], 
		projectorPresent=True;
		(*diracSequence=ReplaceAll[{diracMtx}, insertProjectors];*)

		Block[{DiracMatrix},
		  (*Insert the projectors, and enclose in list*)
		  diracSequence = dMtx@@((DiracMatrix[diracMtx]) /. DiracMatrix[left___,proj: Projector[__][kin__],right___] :> (Sow[{kin},"Projector"];DiracMatrix[left,Replace[proj, insertProjectors],right]));
		];

		(*If the projector was multiplying something, it will not get replaced (does not match pattern): throw an error*)
		If[!FreeQ[diracSequence,Projector], Message[Spur::proj]; Return[$Failed]]
		,
		(*Just enclose in dMtx*)
		diracSequence=dMtx[diracMtx]
	  ];

	  result=diracMtxParser[diracSequence];

	  (*Push DiracG5 to the right, kill terms with odd number of gamma matrices; 
		combinePushG5loadSpurRules also inserts held rules to take traces.*)
	  (*Then, release the hold on spurRules and spurRules5 replacements*)
	  result = Total[ReleaseHold[result/.combineAndConvertPLPRtoG5/.combinePushG5loadSpurRules],Infinity];

	  (*Add everything together.*)

	  If[projectorPresent,
		(*Because there are parts in the Projector that go like 1*k_mu which doesn't readily contract with gamma_mu *)
		fastContract[result]
		,
		Expand[result]
	  ]

  ,DiracMatrix, messageInvalidDiracMatrix[Spur]]
];


(* ::Subsection::Closed:: *)
(*Self energy/vertex projectors (with v2.0 syntax)*)


Projector /: Spur[left___,Projector[l_List, idx___][kin__],right___] := Map[Spur[left,Projector[#,idx][kin],right]& ,l];


Projector::noexist="No `1` projector with name '`2`' exists.";
Projector::argx="`1` projector '`2`' requires `3` of the form {momentum, mass}.";

insertProjectors={
  (******SELF ENERGY FORM FACTORS******)
  Projector["Kinetic"|"A"][{p_,m_}](*|Projector["Kinetic"|"A"][p_,m_]*):>Sequence[LDot[DiracG,p]/(4*LDot[p,p])],
  Projector["Mass"|"B"][{p_,m_}](*|Projector["Mass"|"B"][p_,m_]*):>Sequence[Dirac1/(4*m)],
  Projector["AxialKinetic"|"C"][{p_,m_}](*|Projector["AxialKinetic"|"C"][p_,m_]*):>Sequence[DiracG5,LDot[DiracG,p]/(4*(*I**)LDot[p,p])],
  Projector["ImaginaryMass"|"E"][{p_,m_}](*|Projector["ImaginaryMass"|"E"][p_,m_]*):>Sequence[DiracG5/(4*I*m)],

  Projector["AL"][{p_,m_}](*|Projector["AL"][p_,m_]*) :> Sequence[DiracPL, LDot[DiracG,p]/(2*LDot[p,p])],
  Projector["BL"][{p_,m_}](*|Projector["BL"][p_,m_]*) :> Sequence[DiracPL/(2*m)],
  Projector["AR"][{p_,m_}](*|Projector["AR"][p_,m_]*) :> Sequence[DiracPR, LDot[DiracG,p]/(2*LDot[p,p])],
  Projector["BR"][{p_,m_}](*|Projector["BR"][p_,m_]*) :> Sequence[DiracPR/(2*m)],
  
  Projector[x_String][{_,_}](*|Projector[x_String][Except[_List,_],Except[_List,_]]*):>(Message[Projector::noexist,"self energy",x]; Return[$Failed,Module]),
  Projector[x : "FieldStrength"|"Kinetic"|"A"|"Mass"|"B"|"KineticMixing"|"C"|"ImaginaryMass"|"E"|"AL"|"BL"|"AR"|"BR"][arg___]:>(Message[Projector::argx,"Self energy",x,"1 kinematic argument"]; Return[$Failed,Module]),

  (******SCALAR/PSEUDOSCALAR FORM FACTORS******)
  Projector["S"|"Scalar"][{p1_,m1_},{p2_,m2_}](*|Projector["S"|"Scalar"][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],Dirac1*1/(4*(m1*m2+LDot[p1,p2])),m2 Dirac1+LDot[DiracG,p2]],
  Projector["P"|"Pseudoscalar"][{p1_,m1_},{p2_,m2_}](*|Projector["P"|"Pseudoscalar"][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],DiracG5*(-I)/(4*(m1*m2-LDot[p1,p2])),m2 Dirac1+LDot[DiracG,p2]],

  Projector[x_String][{_,_},{_,_}](*|Projector[x_String][_,_,_,_]*):>(Message[Projector::noexist,"scalar-vertex",x]; Return[$Failed,Module]),
  Projector[x : "S"|"Scalar"|"P"|"Pseudoscalar"][arg___]:>(Message[Projector::argx,"scalar-vertex", x, "2 kinematic arguments"]; Return[$Failed,Module]),
  
  (******VECTOR/AXIAL-VECTOR FORM FACTORS******)
  (*Projectors for elastic vector/axial-vector form factors*)
  Projector["F1"|"Dirac"|"Charge",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["F1"|"Dirac"|"Charge",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],(m (-1+Dim) Dirac1 (LTensor[p1, \[Mu]]+LTensor[p2, \[Mu]]))/(4 (-2+Dim) (m^2+LDot[p1,p2])^2)-LTensor[DiracG, \[Mu]]/(4 (-2+Dim) (m^2+LDot[p1,p2])),m Dirac1+LDot[DiracG,p2]],
  Projector["F2"|"Pauli"|"MDM",\[Mu]_][{p1_,0},{p2_,0}](*|Projector["F2"|"Pauli"|"MDM",\[Mu]_][p1_,p2_,0,0]*):>Sequence[0],
  Projector["F2"|"Pauli"|"MDM",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["F2"|"Pauli"|"MDM",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],(Dirac1 (-m^4 Dim+m^2 (-2+Dim) LDot[p1,p2]) (LTensor[p1, \[Mu]]+LTensor[p2, \[Mu]]))/(4 m (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2)+(m^2 LTensor[DiracG, \[Mu]])/(2 (-2+Dim) (m^4-LDot[p1,p2]^2)),m Dirac1+LDot[DiracG,p2]],
  Projector["F3",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["F3",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],(m Dirac1 (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(8 m^4-8 LDot[p1,p2]^2),m Dirac1+LDot[DiracG,p2]],
  Projector["G1"|"Anapole",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["G1"|"Anapole",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],-((m Dirac1 (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(4 (-2+Dim) (m^4-LDot[p1,p2]^2)))-LTensor[DiracG,\[Mu]]/(4 (-2+Dim) (m^2+LDot[p1,p2])),DiracG5,m Dirac1+LDot[DiracG,p2]],
  Projector["G2"|"EDM",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["G2"|"EDM",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],-((m DiracG5 (LTensor[p1, \[Mu]]+LTensor[p2, \[Mu]]))/(2 (2 m^4-2 LDot[p1,p2]^2))),m Dirac1+LDot[DiracG,p2]],
  Projector["G3",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["G3",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],(m DiracG5 (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(8 (m^2-LDot[p1,p2])^2),m Dirac1+LDot[DiracG,p2]],

  (*Special elastic form factors*)
  Projector["SachsElectric"|"SachsMagnetic",\[Mu]_][{p1_,0},{p2_,0}](*|Projector["SachsElectric"|"SachsMagnetic",\[Mu]_][p1_,p2_,0,0]*):>Sequence[DiracG.p1,-(Subscript[DiracG, \[Mu]]/(4 (-2+Dim) (p1.p2))),DiracG.p2], 
  Projector["SachsElectric",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["SachsElectric",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],(Dirac1 (LTensor[p1, \[Mu]]+LTensor[p2, \[Mu]]))/(4 m (2 m^2+2 LDot[p1,p2])),m Dirac1+LDot[DiracG,p2]],
  Projector["SachsMagnetic",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["SachsMagnetic",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],-((m Dirac1 (LTensor[p1, \[Mu]]+LTensor[p2, \[Mu]]))/(4 (-2+Dim) (m^4-LDot[p1,p2]^2)))+LTensor[DiracG, \[Mu]]/(4 (-2+Dim) (m^2-LDot[p1,p2])),m Dirac1+LDot[DiracG,p2]],

  (*Inelastic/transition vector/axial-vector form factors*)
  Projector["F1"|"Dirac",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["F1"|"Dirac",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],((m1-m2) Dirac1 (2 m1 m2 (-2+Dim)+m1^2 (-1+Dim)+m2^2 (-1+Dim)-2 LDot[p1,p2]) (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(16 (-2+Dim) (m1 m2-LDot[p1,p2]) (m1 m2+LDot[p1,p2])^2)+((m1+m2) (-1+Dim) Dirac1 (m1^2+m2^2-2 LDot[p1,p2]) (LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(16 (-2+Dim) (m1 m2-LDot[p1,p2]) (m1 m2+LDot[p1,p2])^2)-((m1^2+m2^2-2 LDot[p1,p2]) LTensor[DiracG,\[Mu]])/(8 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2)),m2 Dirac1+LDot[DiracG,p2]],
  Projector["F2"|"Pauli",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["F2"|"Pauli",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],-(((m1-m2) (m1+m2)^2 (-1+Dim) Dirac1 (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(16 (-2+Dim) (m1 m2-LDot[p1,p2]) (m1 m2+LDot[p1,p2])^2))-((m1+m2) Dirac1 (2 m1 m2+m1^2 (-1+Dim)+m2^2 (-1+Dim)-2 (-2+Dim) LDot[p1,p2]) (LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(16 (-2+Dim) (m1 m2-LDot[p1,p2]) (m1 m2+LDot[p1,p2])^2)+((m1+m2)^2 LTensor[DiracG,\[Mu]])/(8 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2)),m2 Dirac1+LDot[DiracG,p2]],
  Projector["F3",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["F3",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],((m1+m2) Dirac1 (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(8 (m1^2+m2^2-2 LDot[p1,p2]) (m1 m2+LDot[p1,p2])),m2 Dirac1+LDot[DiracG,p2]],
  Projector["G1"|"Anapole",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["G1"|"Anapole",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],-(((m1+m2) Dirac1 (-2 m1 m2 (-2+Dim)+m1^2 (-1+Dim)+m2^2 (-1+Dim)-2 LDot[p1,p2]) (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(16 (-2+Dim) (-m1 m2+LDot[p1,p2])^2 (m1 m2+LDot[p1,p2])))-((m1-m2) (-1+Dim) Dirac1 (m1^2+m2^2-2 LDot[p1,p2]) (LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(16 (-2+Dim) (-m1 m2+LDot[p1,p2])^2 (m1 m2+LDot[p1,p2]))-((m1^2+m2^2-2 LDot[p1,p2]) LTensor[DiracG,\[Mu]])/(8 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2)),DiracG5,m2 Dirac1+LDot[DiracG,p2]],
  Projector["G2"|"EDM",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["G2"|"EDM",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],-(((m1-m2) (m1+m2)^2 (-1+Dim) Dirac1 (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(16 (-2+Dim) (-m1 m2+LDot[p1,p2])^2 (m1 m2+LDot[p1,p2])))-((m1+m2) Dirac1 (-(m1+m2)^2+(m1^2+m2^2) Dim-2 (-2+Dim) LDot[p1,p2]) (LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(16 (-2+Dim) (-m1 m2+LDot[p1,p2])^2 (m1 m2+LDot[p1,p2]))+((-m1^2+m2^2) LTensor[DiracG,\[Mu]])/(8 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2)),DiracG5,m2 Dirac1+LDot[DiracG,p2]],
  Projector["G3",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["G3",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],((m1+m2) DiracG5 (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(8 (m1^2+m2^2-2 LDot[p1,p2]) (m1 m2-LDot[p1,p2])),m2 Dirac1+LDot[DiracG,p2]],

  (*Elastic in Chiral basis*)
  Projector["AL",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["AL",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],DiracMatrix[-(LTensor[DiracG,\[Mu]]/(2 (-2+Dim) (m^2+LDot[p1,p2]))),DiracPL]+(m DiracPR ((m^2 (-2+Dim)-Dim LDot[p1,p2]) LTensor[p1,\[Mu]]+(m^2 Dim-(-2+Dim) LDot[p1,p2]) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2)+(m DiracPL ((m^2 Dim-(-2+Dim) LDot[p1,p2]) LTensor[p1,\[Mu]]+(m^2 (-2+Dim)-Dim LDot[p1,p2]) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2),m Dirac1+LDot[DiracG,p2]],
  Projector["BL",\[Mu]_][{p1_,0},{p2_,0}](*|Projector["BL",\[Mu]_][p1_,p2_,0,0]*):>Sequence[0],  
  Projector["BL",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["BL",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],-((m^3 (-1+Dim) DiracPL (LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(2 (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2))+(DiracPR (-m^4+m^2 (-2+Dim) LDot[p1,p2]) (LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(2 m (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2)+(m^2 LTensor[DiracG,\[Mu]])/(2 (-2+Dim) (m^4-LDot[p1,p2]^2)),m Dirac1+LDot[DiracG,p2]],  
  Projector["CL",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["CL",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],(m^3 DiracPL (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(4 (m^2-LDot[p1,p2])^2 (m^2+LDot[p1,p2]))-(m DiracPR LDot[p1,p2] (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(4 (m^2-LDot[p1,p2])^2 (m^2+LDot[p1,p2])),m Dirac1+LDot[DiracG,p2]],
  Projector["AR",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["AR",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],DiracMatrix[-(LTensor[DiracG,\[Mu]]/(2 (-2+Dim) (m^2+LDot[p1,p2]))),DiracPR]+(m DiracPL ((m^2 (-2+Dim)-Dim LDot[p1,p2]) LTensor[p1,\[Mu]]+(m^2 Dim-(-2+Dim) LDot[p1,p2]) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2)+(m DiracPR ((m^2 Dim-(-2+Dim) LDot[p1,p2]) LTensor[p1,\[Mu]]+(m^2 (-2+Dim)-Dim LDot[p1,p2]) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2),m Dirac1+LDot[DiracG,p2]],
  Projector["BR",\[Mu]_][{p1_,0},{p2_,0}](*|Projector["BR",\[Mu]_][p1_,p2_,0,0]*):>Sequence[0],
  Projector["BR",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["BR",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],-((m^3 (-1+Dim) DiracPR (LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(2 (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2))+(DiracPL (-m^4+m^2 (-2+Dim) LDot[p1,p2]) (LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(2 m (-2+Dim) (m^2-LDot[p1,p2]) (m^2+LDot[p1,p2])^2)+(m^2 LTensor[DiracG,\[Mu]])/(2 (-2+Dim) (m^4-LDot[p1,p2]^2)),m Dirac1+LDot[DiracG,p2]],
  Projector["CR",\[Mu]_][{p1_,m_},{p2_,m_}](*|Projector["CR",\[Mu]_][p1_,p2_,m_,m_]*):>Sequence[m Dirac1+LDot[DiracG,p1],(m^3 DiracPR (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(4 (m^2-LDot[p1,p2])^2 (m^2+LDot[p1,p2]))-(m DiracPL LDot[p1,p2] (-LTensor[p1,\[Mu]]+LTensor[p2,\[Mu]]))/(4 (m^2-LDot[p1,p2])^2 (m^2+LDot[p1,p2])),m Dirac1+LDot[DiracG,p2]],

 (*Inelastic in Chiral basis*)
  Projector["AL",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["AL",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],DiracMatrix[-(((m1^2+m2^2-2 LDot[p1,p2]) LTensor[DiracG,\[Mu]])/(4 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2))),DiracPL]+(m2 DiracPR ((m1^2 m2^2 (-2+Dim)-(m1^2+m2^2) (-1+Dim) LDot[p1,p2]+Dim LDot[p1,p2]^2) LTensor[p1,\[Mu]]+(m1^2 (m2^2+m1^2 (-1+Dim))-2 m1^2 (-1+Dim) LDot[p1,p2]+(-2+Dim) LDot[p1,p2]^2) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (-m1^2 m2^2+LDot[p1,p2]^2)^2)+(m1 DiracPL ((m2^2 (m1^2+m2^2 (-1+Dim))-2 m2^2 (-1+Dim) LDot[p1,p2]+(-2+Dim) LDot[p1,p2]^2) LTensor[p1,\[Mu]]+(m1^2 m2^2 (-2+Dim)-(m1^2+m2^2) (-1+Dim) LDot[p1,p2]+Dim LDot[p1,p2]^2) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (-m1^2 m2^2+LDot[p1,p2]^2)^2),m2 Dirac1+LDot[DiracG,p2]],
  Projector["BL",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["BL",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],DiracMatrix[(m1 (m1+m2) LTensor[DiracG,\[Mu]])/(4 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2)),DiracPR]+DiracMatrix[(m2 (m1+m2) LTensor[DiracG,\[Mu]])/(4 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2)),DiracPL]-(m1 m2 (m1+m2) (-1+Dim) DiracPL ((m2^2-LDot[p1,p2]) LTensor[p1,\[Mu]]+(m1^2-LDot[p1,p2]) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (-m1^2 m2^2+LDot[p1,p2]^2)^2)-((m1+m2) DiracPR ((m1^2 m2^2-m2^2 (-1+Dim) LDot[p1,p2]+(-2+Dim) LDot[p1,p2]^2) LTensor[p1,\[Mu]]+(m1^2 m2^2-m1^2 (-1+Dim) LDot[p1,p2]+(-2+Dim) LDot[p1,p2]^2) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (-m1^2 m2^2+LDot[p1,p2]^2)^2),m2 Dirac1+LDot[DiracG,p2]],  
  Projector["CL",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["CL",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],-((m1 m2 (m1+m2) DiracPL (LTensor[p1,\[Mu]]-LTensor[p2,\[Mu]]))/(4 (m1^2+m2^2-2 LDot[p1,p2]) (m1^2 m2^2-LDot[p1,p2]^2)))+((m1+m2) DiracPR LDot[p1,p2] (LTensor[p1,\[Mu]]-LTensor[p2,\[Mu]]))/(4 (m1^2+m2^2-2 LDot[p1,p2]) (m1^2 m2^2-LDot[p1,p2]^2)),m2 Dirac1+LDot[DiracG,p2]],
  Projector["AR",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["AR",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],DiracMatrix[-(((m1^2+m2^2-2 LDot[p1,p2]) LTensor[DiracG,\[Mu]])/(4 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2))),DiracPR]+(m2 DiracPL ((m1^2 m2^2 (-2+Dim)-(m1^2+m2^2) (-1+Dim) LDot[p1,p2]+Dim LDot[p1,p2]^2) LTensor[p1,\[Mu]]+(m1^2 (m2^2+m1^2 (-1+Dim))-2 m1^2 (-1+Dim) LDot[p1,p2]+(-2+Dim) LDot[p1,p2]^2) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (-m1^2 m2^2+LDot[p1,p2]^2)^2)+(m1 DiracPR ((m2^2 (m1^2+m2^2 (-1+Dim))-2 m2^2 (-1+Dim) LDot[p1,p2]+(-2+Dim) LDot[p1,p2]^2) LTensor[p1,\[Mu]]+(m1^2 m2^2 (-2+Dim)-(m1^2+m2^2) (-1+Dim) LDot[p1,p2]+Dim LDot[p1,p2]^2) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (-m1^2 m2^2+LDot[p1,p2]^2)^2),m2 Dirac1+LDot[DiracG,p2]],
  Projector["BR",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["BR",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],DiracMatrix[(m1 (m1+m2) LTensor[DiracG,\[Mu]])/(4 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2)),DiracPL]+DiracMatrix[(m2 (m1+m2) LTensor[DiracG,\[Mu]])/(4 (-2+Dim) (m1^2 m2^2-LDot[p1,p2]^2)),DiracPR]-(m1 m2 (m1+m2) (-1+Dim) DiracPR ((m2^2-LDot[p1,p2]) LTensor[p1,\[Mu]]+(m1^2-LDot[p1,p2]) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (-m1^2 m2^2+LDot[p1,p2]^2)^2)-((m1+m2) DiracPL ((m1^2 m2^2-m2^2 (-1+Dim) LDot[p1,p2]+(-2+Dim) LDot[p1,p2]^2) LTensor[p1,\[Mu]]+(m1^2 m2^2-m1^2 (-1+Dim) LDot[p1,p2]+(-2+Dim) LDot[p1,p2]^2) LTensor[p2,\[Mu]]))/(4 (-2+Dim) (-m1^2 m2^2+LDot[p1,p2]^2)^2),m2 Dirac1+LDot[DiracG,p2]],
  Projector["CR",\[Mu]_][{p1_,m1_},{p2_,m2_}](*|Projector["CR",\[Mu]_][p1_,p2_,m1_,m2_]*):>Sequence[m1 Dirac1+LDot[DiracG,p1],-((m1 m2 (m1+m2) DiracPR (LTensor[p1,\[Mu]]-LTensor[p2,\[Mu]]))/(4 (m1^2+m2^2-2 LDot[p1,p2]) (m1^2 m2^2-LDot[p1,p2]^2)))+((m1+m2) DiracPL LDot[p1,p2] (LTensor[p1,\[Mu]]-LTensor[p2,\[Mu]]))/(4 (m1^2+m2^2-2 LDot[p1,p2]) (m1^2 m2^2-LDot[p1,p2]^2)),m2 Dirac1+LDot[DiracG,p2]],

  Projector[x_String,\[Mu]_][{_,_},{_,_}](*|Projector[x_String,\[Mu]_][_,_,_,_]*) :> (Message[Projector::noexist,"vector-vertex",x]; Return[$Failed,Module]),
  Projector[x_String,\[Mu]_][arg__] :> (Message[Projector::argx,"Vector-vertex",x,"2 kinematic arguments"]; Return[$Failed,Module])
};


(* ::Subsection:: *)
(*FierzRearrange*)


(* ::Subsubsection:: *)
(*FierzRearrange*)


FierzRearrange::usage="FierzRearrange[expr,{p1,p2}] gives the form of expr where spinors carrying momentum p1 and p2 in all FermionLineProduct objects are exchanged by applying the Fierz identity.
FierzRearrange[{p1,p2}] represents an operator form of FierzTransform that can be applied to an expression.";


Options[FierzRearrange]={ChiralBasis->Automatic};


FierzRearrange[expr_, {p1_, p2_}, opts:OptionsPattern[]] := Null;


(* ::Subsection:: *)
(*FermionLineExpand*)


(* ::Subsubsection::Closed:: *)
(*flProdTensorContract and Expansion-recontraction*)


flProd[___,0,___]:=0;
flProd[left___,c_ fl:(_dMtx|_dMtx5|_dMtxL|_dMtxR),right___] := c flProd[left,fl,right];
flProd[left___,h_Plus,right___] := Distribute[List[left,h,right],Plus,List,Plus,flProd];


With[
  {idxList4:={a,b,c,d}/.{idx1->1,idx2->2,idx3->3,idx4->4},
   idxList3:={a,b,c,d}/.{idx1->1,idx2->2,idx3->3},
   idxList2:={a,b,c,d}/.{idx1->1,idx2->2},
   idxList1:={a,b,c,d}/.{idx1->1},
   (*generates correct head vec/idx depending on what is contracted with epsilon tensor*)
   vecidx=Function[Switch[Head[#],List,vec@@#,_(*Symbol*),idx[#]]],
   (*New dMtx due to the insertion of gamma-5*)
   newMtx:=Switch[mtx,dMtx,dMtx5,dMtx5,dMtx,_(*dMtxL|dMtxR*),mtx],
   (*Sign due to anticommuting gamma-5 to the right and merging with DiracG5 or PL/PR*)
   gamma5sign=Function[Switch[mtx,dMtxL,-1,_(*dMtx|dMtx5|dMtxR*),1]*(-1)^Length[#]]},

  With[{
	leviCivitaContractionRules=
	{(*Contraction of all four indices*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___,idx[idx1:Except[_List|_Integer, a|b|c|d]],idx[idx2:Except[_List|_Integer, a|b|c|d]],idx[idx3:Except[_List|_Integer, a|b|c|d]],idx[idx4:Except[_List|_Integer, a|b|c|d]],right___],
	  $patternMatched=True; Signature[idxList4]*gamma5sign[{right}]*24*I*newMtx[left,right]],
	 (*Contraction of three indices*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___,idx[idx1:Except[_List|_Integer, a|b|c|d]],idx[idx2:Except[_List|_Integer, a|b|c|d]],idx[idx3:Except[_List|_Integer, a|b|c|d]],right___],
	  $patternMatched=True; -Signature[idxList3]*gamma5sign[{right}]*6*I*newMtx[left,vecidx[Sort[idxList3][[4]]],right]],
	 (*Contraction of two indices*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___,idx[idx1:Except[_List|_Integer, a|b|c|d]],idx[idx2:Except[_List|_Integer, a|b|c|d]],right___],
	  $patternMatched=True; With[{perms=Permutations[{1,2}]}, Dot[Map[Signature,perms], Apply[-(gamma5sign[{right}]*Signature[idxList2]*I*newMtx[left,#1,#2,right])&, Extract[vecidx/@(Sort[idxList2][[3;;4]]),List/@perms],{1}]]]],
	 (*Contraction of one index*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___,idx[idx1:a|b|c|d],right___] /; !FreeQ[{a,b,c,d}, Alternatives@@extSp[[Length[{l}]+1,All,2]]] || !FreeQ[{left,right},Except[_List|_Integer, a|b|c|d]],
	  $patternMatched=True; With[{perms=Permutations[{1,2,3}]}, Dot[Map[Signature,perms], Apply[(gamma5sign[{right}]*Signature[idxList1]*1/6*I*newMtx[left,#1,#2,#3,right])&, Extract[vecidx/@(Sort[idxList1][[2;;4]]),List/@perms],{1}]]]], 
	 (*Contraction of zero indices*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___] /; !FreeQ[{a,b,c,d}, Alternatives@@extSp[[Length[{l}]+1,All,2]]] || Length[Cases[{left},Except[_List|_Integer, a|b|c|d],2,2]]>1,
	  $patternMatched=True; With[{perms=Permutations[{1,2,3,4}]}, Dot[Map[Signature,perms], Apply[(gamma5sign[{}]*1/24*I*newMtx[left,#1,#2,#3,#4])&, Extract[vecidx/@{a,b,c,d},List/@perms],{1}]]]],
	 (*Contraction into metric tensor*)
	 RuleDelayed@@Hold[LTensor[MetricG,Except[_List|_Integer, a|b|c|d],a|b|c|d], $patternMatched=True; 0]}
	},

	With[{leviCivitaIdentificationRule=RuleDelayed@@Hold[
	  HoldPattern[LTensor[LeviCivitaE,a_,b_,c_,d_] flProd[l___,mtxExpr: (_dMtx|_dMtx5|_dMtxL|_dMtxR),r___]] ,
		Block[{$patternMatched}, With[{res= flProd[l, mtxExpr/.leviCivitaContractionRules, r] },  res/;$patternMatched]]
	]},

	  SetDelayed@@Hold[flProdTensorContract[expr_, extSp_],
		ReplaceAll[Expand[expr,_LTensor|_flProd],
		  {
			leviCivitaIdentificationRule,
			LTensor[v_,a_Symbol] flProd[left___,(mtx:dMtx|dMtx5|dMtxL|dMtxR)[l___,idx[a_],r___],right___] :> flProd[left,mtx[l,vec[v],r],right],
			HoldPattern[LTensor[MetricG,PatternSequence[a_Symbol, b_Symbol]|PatternSequence[b_Symbol, a_Symbol]] flProd[left___,(mtx:dMtx|dMtx5|dMtxL|dMtxR)[l___,idx[a_],r___],right___]] :> flProd[left,mtx[l,idx[b],r],right],
			dMtx[0] :> 0
		  }
		]
	  ]
	]
  ]
];


sirlinExpansionIterative[False(*ChiralBasis*)] = Function[# /. {
  (*Special cases of Sirlin's formula in Polar basis for FermionLineProducts*)
  (*2x3a,b*)
  flProd[left___,(mtxa:dMtx|dMtx5)[a_idx, b_idx],middle___,(mtxb:dMtx|dMtx5)[c: (a_idx|b_idx),free_,(a_idx|b_idx)],right___] :>
	With[{mtx5a=If[mtxa===dMtx,dMtx5,dMtx],mtx5b=If[mtxb===dMtx,dMtx5,dMtx], sgn=If[c===a,1,-1]},
	  -2 flProd[left,mtxa[],middle,mtxb[free],right] + 2 sgn flProd[left,mtx5a[a,free],middle,mtx5b[a],right] - 2 sgn flProd[left,mtx5a[],middle,mtx5b[free],right]],
  (*3x2a,b*)
  flProd[left___,(mtxb:dMtx|dMtx5)[c: (a_idx|b_idx),free_,(a_idx|b_idx)],middle___,(mtxa:dMtx|dMtx5)[a_idx, b_idx],right___] :>
	With[{mtx5a=If[mtxa===dMtx,dMtx5,dMtx],mtx5b=If[mtxb===dMtx,dMtx5,dMtx], sgn=If[c===a,1,-1]},
	  -2 flProd[left,mtxb[free],middle,mtxa[],right] + 2 sgn flProd[left,mtx5b[a],middle,mtx5a[a,free],right] - 2 sgn flProd[left,mtx5b[free],middle,mtx5a[],right]],

  (*3x3a,b*)
  flProd[left___,(mtxa:dMtx|dMtx5)[a_idx,free1_,b_idx],middle___,(mtxb:dMtx|dMtx5)[c: (a_idx|b_idx),free2_, (a_idx|b_idx)],right___] :> 
	With[{mtx5a=If[mtxa===dMtx,dMtx5,dMtx],mtx5b=If[mtxb===dMtx,dMtx5,dMtx], sgn=If[c===a,1,-1]},
	  2 pair[free1,free2] flProd[left,mtxa[a],middle,mtxb[a],right] + 2 flProd[left,mtxa[free2],middle,mtxb[free1],right] + 
	  2 sgn pair[free1,free2] flProd[left,mtx5a[a],middle,mtx5b[a],right] - 2 sgn flProd[left,mtx5a[free2],middle,mtx5b[free1],right]]}
  ];

sirlinExpansionIterative[True(*ChiralBasis*)] = Function[# /. {
  (*Special cases of Sirlin's formula for FermionLineProducts*)
  (*3x2a,b*)
  flProd[left___,(mtxb:dMtxL|dMtxR)[c: (a_idx|b_idx), (a_idx|b_idx)],middle___,(mtxa:dMtxL|dMtxR)[a_idx,free_,b_idx],right___] :>
	With[{sgn=If[(mtxa===mtxb&&c===a) ||(mtxa=!=mtxb&&c=!=a),-1,1]}, -2 flProd[left,If[sgn==1,mtxb[a,free],mtxb[free,a]],middle,mtxa[a],right]],
	
  (*3x2a,b*)
  flProd[left___,(mtxa:dMtxL|dMtxR)[a_idx,free_,b_idx],middle___,(mtxb:dMtxL|dMtxR)[c: (a_idx|b_idx), (a_idx|b_idx)],right___] :>
	With[{sgn=If[(mtxa===mtxb&&c===a) ||(mtxa=!=mtxb&&c=!=a),-1,1]}, -2 flProd[left,mtxa[a],middle,If[sgn==1,mtxb[a,free],mtxb[free,a]],right]],

  (*3x3a,b*)
  flProd[left___,(mtxa:dMtxL|dMtxR)[a_idx,free1_,b_idx],middle___,(mtxb:dMtxL|dMtxR)[c: (a_idx|b_idx),free2_, (a_idx|b_idx)],right___] :> 
	If[(mtxa===mtxb&&c===a) ||(mtxa=!=mtxb&&c=!=a),
	  4 pair[free1,free2] flProd[left,mtxa[a],middle,mtxb[a],right],
	  4 flProd[left,mtxa[free2],middle,mtxb[free1],right]],

  (*3x3c,d*)
  flProd[left___,(mtxa:dMtxL|dMtxR)[a_idx,b_idx,free1_],middle___,Except[mtxa_,mtxb_][a_idx|b_idx, a_idx|b_idx,free2_],right___] :> 
	4 flProd[left,mtxa[free1],middle,mtxb[free2],right],
  flProd[left___,(mtxa:dMtxL|dMtxR)[free1_,a_idx,b_idx],middle___,Except[mtxa_,mtxb_][free2_,a_idx|b_idx, a_idx|b_idx],right___] :> 
	4 flProd[left,mtxa[free1],middle,mtxb[free2],right],
  flProd[left___,(mtxa:dMtxL|dMtxR)[free1_,a_idx,b_idx],middle___,mtxa_[a_idx|b_idx, a_idx|b_idx,free2_],right___] :> 
	4 flProd[left,mtxa[free1],middle,mtxa[free2],right],
  flProd[left___,(mtxa:dMtxL|dMtxR)[a_idx,b_idx,free1_],middle___,mtxa_[free2_,a_idx|b_idx, a_idx|b_idx],right___] :> 
	4 flProd[left,mtxa[free1],middle,mtxa[free2],right]}
  ];

chisholmExpansionIterative[False(*ChiralBasis*)] = Function[# /. {
  (*General formula with three or more Dirac matrices*)
  mtxExpr:((head:dMtx|dMtx5)[_,_,__]):>With[{oppHead=If[head===dMtx,dMtx5,dMtx]},
	  ursp[mtxExpr] head[]/4+ 
	  With[{n=Length[mtxExpr]}, Sum[(-1)^(jdx+1)/4 Take[mtxExpr,{jdx}] ursp[Delete[mtxExpr,{{jdx}}]], {jdx,1,n}]] + 
	  With[{n=Length[mtxExpr]}, Sum[(-1)^(jdx+kdx+1) * -1/4* (head[mtxExpr[[jdx]],mtxExpr[[kdx]]] + head[]pair[mtxExpr[[jdx]],mtxExpr[[kdx]]]) ursp[Delete[mtxExpr,{{jdx},{kdx}}]], {jdx,1,n},{kdx,1,jdx-1}]] +
	  With[{dummyIndex=Unique[]},ursp5[Prepend[mtxExpr,idx[dummyIndex]]] oppHead[idx[dummyIndex]]/4] +
	  ursp5[mtxExpr] oppHead[]/4] }
  ];

chisholmExpansionIterative[True(*ChiralBasis*)] = Function[# /. {
  (*General formula with three or more Dirac matrices*)
  mtxExpr:((head:dMtxL|dMtxR)[_,_,__]):>With[{sign=If[head===dMtxL,-1,+1]},
	  ursp[mtxExpr] head[]/4+ 
	  With[{n=Length[mtxExpr]}, Sum[(-1)^(jdx+1)/4 Take[mtxExpr,{jdx}] ursp[Delete[mtxExpr,{{jdx}}]], {jdx, 1 , n}]] + 
	  With[{n=Length[mtxExpr]}, Sum[(-1)^(jdx+kdx+1) * -1/4* (head[mtxExpr[[jdx]],mtxExpr[[kdx]]] + head[]pair[mtxExpr[[jdx]],mtxExpr[[kdx]]]) ursp[Delete[mtxExpr,{{jdx},{kdx}}]], {jdx,1,n},{kdx,1,jdx-1}]] +
	  With[{dummyIndex=Unique[]},sign * ursp5[Prepend[mtxExpr,idx[dummyIndex]]] head[idx[dummyIndex]]/4] +
	  sign * ursp5[mtxExpr] head[]/4] }
  ];


fLineProdProcess[externalSpinors_,optChiral_,optChisholm_]:=
  Module[{result},

	(*Pair reduce, apply on shell conditions*)
	result = # /. fl_flProd :> Inner[Expand[ReplaceRepeated[#1,fLineRules[optChiral]@@#2]]&,fl,flProd@@externalSpinors,flProd];

	(*Contract external tensors into fermion line*)
	result = flProdTensorContract[result,externalSpinors];

	(*Contract external tensors with themselves*)
	result = elementaryContract[highRankTensorContract[result]];

	If[optChisholm,

	  (*Echo[result,"1"];*)
	  result = sirlinExpansionIterative[optChiral][result];
	  (*Echo[result,"2"];*)

	  result = result /. fl_flProd :> Inner[Expand[ReplaceRepeated[#1,fLineRules[optChiral]@@#2]]&,fl,flProd@@externalSpinors,flProd];

	  result = chisholmExpansionIterative[optChiral][result];
	  (*Contract external tensors with themselves, mainly to eliminate Levi-Civita symbols*)
	  elementaryContract[highRankTensorContract[result]]
	  ,
	  Expand[result]
	]
  ]&;


sigPair=Function[{a,b},
  With[{obja = Switch[a,_vec,{a[[1]]},_idx,a[[1]]],
		objb = Switch[b,_vec,{b[[1]]},_idx,b[[1]]]}, LTensor[DiracS,obja,objb]]];

flProdFinalTensorContract[expr_] := 
  expr //.
	{HoldPattern[LTensor[v_,a_Symbol] flProd[left___,(mtx:dMtx|dMtx5|dMtxL|dMtxR)[l___,idx[a_],r___],right___]] :> flProd[left,mtx[l,vec[v],r],right],
	 HoldPattern[LTensor[v_,a_Symbol] flProd[left___,(mtx:dMtx|dMtx5|dMtxL|dMtxR)[c_. LTensor[DiracS,ll___,a_Symbol,rr___]],right___]] :> c flProd[left,mtx[LTensor[DiracS,ll,{v},rr]],right],
	 HoldPattern[LTensor[MetricG,PatternSequence[a_Symbol, b_Symbol]|PatternSequence[b_Symbol, a_Symbol]] flProd[left___,(mtx:dMtx|dMtx5|dMtxL|dMtxR)[idx[a_]],right___]] :> flProd[left,mtx[idx[b]],right],
	 HoldPattern[LTensor[MetricG,PatternSequence[a_Symbol, b_Symbol]|PatternSequence[b_Symbol, a_Symbol]] flProd[left___,(mtx:dMtx|dMtx5|dMtxL|dMtxR)[LTensor[DiracS,ll___,a_Symbol,rr___]],right___]] :> flProd[left,mtx[LTensor[DiracS,ll,b,rr]],right],
	 dMtx[0] :> 0};

flProdSigmaRules[False(*Chiral*)] =
  {
	HoldPattern[flProd[left___,(mtx:dMtx|dMtx5)[LTensor[DiracS,a_Symbol,b_Symbol]],middle___,dMtx5[LTensor[DiracS,a_Symbol,b_Symbol]],right___]] :> 
	  With[{oppHead=If[head===dMtx,dMtx5,dMtx]},flProd[left,oppHead[LTensor[DiracS,a,b]],middle,dMtx[LTensor[DiracS,a,b]],right]]
  };

flProdSigmaRules[True(*Chiral*)] =
  {
	HoldPattern[flProd[left___,(mtx:dMtxL|dMtxR)[LTensor[DiracS,a_Symbol,b_Symbol]],middle___,Except[mtx_,dMtxL|dMtxR][LTensor[DiracS,a_Symbol,b_Symbol]],right___]] :> 0
  };


gammaToSigma[externalSpinors_,optChiral_]:=
  Module[{result},

	result = # /. flProd[left___,(mtx:dMtx|dMtx5|dMtxL|dMtxR)[a_,b_],right___] :> -I flProd[left,mtx[sigPair[a,b]],right] + pair[a,b] flProd[left,mtx[],right];
	result = result /. flProdSigmaRules[optChiral];
	result = flProdFinalTensorContract[result];
	result = elementaryContract[result];

	(*Pair reduce, apply on shell conditions*)
	result = result /. fl_flProd :> Inner[Expand[ReplaceRepeated[#1,fLineRules[optChiral]@@#2]]&,fl,flProd@@externalSpinors,flProd]
  ]&;


(*SolveValue[constraint_,variable_]:=variable/.First[Solve[constraint,variable]];

flProdPreKIrules[{FermionLine[{sgn1_,p1_,m1_},{sgn2_,p2_,m2_}],FermionLine[{sgn3_,p3_,m3_},{sgn4_,p4_,m4_}]},True] :=
  {
	flProd[(mtxa:dMtxL|dMtxR)[vec[p4]],(mtxb:dMtxL|dMtxR)[vec[p1]]] /; mtxa =!= mtxb :> flProd[SolveValue[$kinematicConstraint[mtxa],mtxa[vec[p4]]],mtxb[vec[p1]]],
	flProd[(mtxa:dMtxL|dMtxR)[vec[p3]],(mtxb:dMtxL|dMtxR)[vec[p2]]] /; mtxa =!= mtxb :> flProd[SolveValue[$kinematicConstraint[mtxa],mtxa[vec[p3]]],mtxb[vec[p2]]],
	flProd[(mtx:dMtxL|dMtxR)[vec[p3]],mtx_[vec[p1]]] :> flProd[SolveValue[$kinematicConstraint[mtx],mtx[vec[p3]]],mtx[vec[p1]]],
	flProd[(mtx:dMtxL|dMtxR)[vec[p4]],mtx_[vec[p2]]] :> flProd[SolveValue[$kinematicConstraint[mtx],mtx[vec[p4]]],mtx[vec[p2]]]
  };
flProdPreKIrules[{FermionLine[{sgn1_,p1_,m1_},{sgn2_,p2_,m2_}],FermionLine[{sgn3_,p3_,m3_},{sgn4_,p4_,m4_}]},False] :=
  {

  };

flProdKIrules[{FermionLine[{sgn1_,p1_,m1_},{sgn2_,p2_,m2_}],FermionLine[{sgn3_,p3_,m3_},{sgn4_,p4_,m4_}]},True] :=
  {
	flProd[(mtx:dMtxL|dMtxR)[vec[p4]],mtx_[vec[p1]]] :> 
	  With[{dummyIndex=Unique[],oppMtx=If[mtx===dMtxL,dMtxR,dMtxL]},
		LDot[p4,p1] flProd[mtx[idx[dummyIndex]],mtx[idx[dummyIndex]]] - 
		I/2 sgn1 m1 flProd[mtx[LTensor[DiracS,dummyIndex,{p4}]],mtx[idx[dummyIndex]]] +
		I/2 sgn4 m4 flProd[mtx[idx[dummyIndex]],oppMtx[LTensor[DiracS,dummyIndex,{p1}]]]],

	flProd[(mtx:dMtxL|dMtxR)[vec[p3]],mtx_[vec[p2]]] :>
	  With[{dummyIndex=Unique[],oppMtx=If[mtx===dMtxL,dMtxR,dMtxL]},
		LDot[p2,p3] flProd[mtx[idx[dummyIndex]],mtx[idx[dummyIndex]]] + 
		I/2 sgn2 m2 flProd[oppMtx[LTensor[DiracS,dummyIndex,{p3}]],mtx[idx[dummyIndex]]] -
		I/2 sgn3 m3 flProd[mtx[idx[dummyIndex]],mtx[LTensor[DiracS,dummyIndex,{p2}]]]],

	flProd[(mtxa:dMtxL|dMtxR)[vec[p3]],(mtxb:dMtxL|dMtxR)[vec[p1]]] /; mtxa =!= mtxb :> 
	  With[{dummyIndex=Unique[]},
		LDot[p2,p3] flProd[mtxa[idx[dummyIndex]],mtxb[idx[dummyIndex]]] - 
		I/2 sgn1 m1 flProd[mtxa[LTensor[DiracS,dummyIndex,{p3}]],mtxb[idx[dummyIndex]]] -
		I/2 sgn3 m3 flProd[mtxa[idx[dummyIndex]],mtxb[LTensor[DiracS,dummyIndex,{p1}]]]],

	flProd[(mtxa:dMtxL|dMtxR)[vec[p4]],(mtxb:dMtxL|dMtxR)[vec[p2]]] /; mtxa =!= mtxb :> 
	  With[{dummyIndex=Unique[]},
		LDot[p2,p4] flProd[mtxa[idx[dummyIndex]],mtxb[idx[dummyIndex]]] + 
		I/2 sgn2 m2 flProd[mtxa[LTensor[DiracS,dummyIndex,{p4}]],mtxb[idx[dummyIndex]]] +
		I/2 sgn4 m4 flProd[mtxa[idx[dummyIndex]],mtxb[LTensor[DiracS,dummyIndex,{p2}]]]]
  };

flProdKIrules[{FermionLine[{sgn1_,p1_,m1_},{sgn2_,p2_,m2_}],FermionLine[{sgn3_,p3_,m3_},{sgn4_,p4_,m4_}]},False] :=
  {
	
  };

flProdKinematicIdentities[externalSpinors_, optChiral_]:=
  Module[{result},
	result = # /. flProdPreKIrules[externalSpinors,optChiral];

	result = result /. fl_flProd :> Inner[Expand[ReplaceRepeated[#1,fLineRules[optChiral]@@#2]]&,fl,flProd@@externalSpinors,flProd];

	result = result /. flProdKIrules[externalSpinors,optChiral]

	(*result = result /. fl_flProd :> Inner[Expand[ReplaceRepeated[#1,fLineRules[optChiral]@@#2]]&,fl,flProd@@externalSpinors,flProd]*)
  ]&;*)


(* ::Subsubsection::Closed:: *)
(*generateFermionLineKinematics*)


(*FermionLine::proj="Projector should not be present inside FermionLine.";*)
FermionLineExpand::kina="Warning: On shell conditions implied by fermion line kinematics `1` are inconsistent .";
FermionLineExpand::kinb="Warning: On shell conditions implied by fermion line kinematics `1` are inconsistent with `2`.";


generateFermionLineKinematics[FermionLine[{sgn2_,p2_,m2_,___},{sgn1_,p1_,m1_,___}], ep_, idx_:1] :=
  Module[{momSymbs=DeleteCases[Variables[{p1,p2}],_?LScalarQ],
	consistent,numberOfIndepMom,indepMom,varsToBasic,basicToVars,onShellConditions},

	(*If there are more than two symbols making up p1 and p2, 
	  it is not possible to decide which to eliminate to form the 'basic' momentum variables*)
	If[Length[momSymbs]>2, Return[{{},{},{}}]];

	numberOfIndepMom=Length[GroebnerBasis[{p1,p2},Variables[momSymbs]]];
	indepMom=momSymbs[[1;;numberOfIndepMom]];

	(*Automate on shell conditions*)
	If[(*Check that p1.p1 and p2.p2 do not immediately evaluate*)
	  !FreeQ[LDot[p1,p1], _LDot] && !FreeQ[LDot[p2,p2], _LDot],
	  (*Solve for dot products.  If there is an inconsistency, Solve will return {}*)
	  If[consistent=((onShellConditions=Quiet[Solve[{LDot[p1,p1]==m1^2,LDot[p2,p2]==m2^2},{LDot[indepMom[[1]],indepMom[[1]]],LDot[indepMom[[2]],indepMom[[2]]]}]])=!={}),
		onShellConditions=First[onShellConditions],
		Message[FermionLineExpand::kina,TraditionalForm[HoldForm[{LDot[p2,p2]==m2^2,LDot[p1,p1]==m1^2}]]]
	  ],

	  (*If either p1.p1 or p2.p2 evaluates to something, can't automate on shell conditions*)
	  onShellConditions = {};
	  (*But check if fermion line kinematics are consistent with whatever p1.p1 and p2.p2 evaluate to*)
	  If[!(consistent = Implies[FreeQ[LDot[p1,p1], _LDot], PossibleZeroQ[LDot[p1,p1]-m1^2]] && Implies[FreeQ[LDot[p2,p2], _LDot], PossibleZeroQ[LDot[p2,p2]-m2^2]]),
		Which[
		  FreeQ[LDot[p1,p1], _LDot] && FreeQ[LDot[p2,p2], _LDot] && !PossibleZeroQ[LDot[p1,p1]-m1^2] && !PossibleZeroQ[LDot[p2,p2]-m2^2],
		  Message[FermionLineExpand::kinb,TraditionalForm[HoldForm[{LDot[p2,p2]==m2^2,LDot[p1,p1]==m1^2}]], "values set to "<>ToString[HoldForm[LDot[p1,p1]],StandardForm]<>" and "<>ToString[HoldForm[LDot[p2,p2]],StandardForm]],
		  FreeQ[LDot[p1,p1], _LDot] && !PossibleZeroQ[LDot[p1,p1]-m1^2],
		  Message[FermionLineExpand::kinb,TraditionalForm[HoldForm[{LDot[p2,p2]==m2^2,LDot[p1,p1]==m1^2}]], "the value set to "<>ToString[HoldForm[LDot[p1,p1]],StandardForm]],
		  True(*FreeQ[LDot[p2,p2], _LDot] && !PossibleZeroQ[LDot[p2,p2]-m2^2]*),
		  Message[FermionLineExpand::kinb,TraditionalForm[HoldForm[{LDot[p2,p2]==m2^2,LDot[p1,p1]==m1^2}]], "the value set to "<>ToString[HoldForm[LDot[p2,p2]],StandardForm]]
		]
	  ]
	];

	(*As long as the kinematics are consistent, it is possible to express in terms of more 'basic' momentum variables*)
	If[consistent,

	  varsToBasic=First[Quiet[Solve[Table[DeleteCases[{p2,p1},0][[i]]==ep[i+2(idx-1)], {i,1,numberOfIndepMom}], indepMom]]];
	  basicToVars=First[Quiet[Solve[Apply[Equal,varsToBasic,{1}], Table[ep[i+2(idx-1)], {i,1,numberOfIndepMom}]]]]
	  ,
	  varsToBasic={};
	  basicToVars={}
	];

	{varsToBasic,basicToVars,onShellConditions}
];

(*Returns a list of three lists:
  [[1]] is {{p2->$p[2],q->$p[1]-$p[2]}, {p1->$p[3],q->$p[3]-$p[4]}}
  [[2]] is {$p[1]->p2+q,$p[2]->p2,$p[3]->p1,$p[4]->p1-q} [Flattened],
  [[3]] is {p2.p2->mX^2, q.q->-2 p2.q, p1.p1->mX^2, q.q->2 p1.q} [Flattened] on shell conditions*)
generateFermionLineKinematics[l_List, ep_] := MapAt[Flatten,Transpose[(MapIndexed[generateFermionLineKinematics[#1,$p,First[#2]]&,l,1])],{{2},{3}}];


(* ::Subsubsection::Closed:: *)
(*fLineTensorContract*)


(* ISSUES: 
  For handling FermionLine, we aren't contracting metric tensors.
*)

(*The reason these leviCivitaContractionRules are more complicated is because the generated
  gamma-5 in the identities must also be pushed to the right.*)

With[
  {idxList4:={a,b,c,d}/.{idx1->1,idx2->2,idx3->3,idx4->4},
   idxList3:={a,b,c,d}/.{idx1->1,idx2->2,idx3->3},
   idxList2:={a,b,c,d}/.{idx1->1,idx2->2},
   idxList1:={a,b,c,d}/.{idx1->1},
   (*generates correct head vec/idx depending on what is contracted with epsilon tensor*)
   vecidx=Function[Switch[Head[#],List,vec@@#,_(*Symbol*),idx[#]]],
   (*New dMtx due to the insertion of gamma-5*)
   newMtx:=Switch[mtx,dMtx,dMtx5,dMtx5,dMtx,_(*dMtxL|dMtxR*),mtx],
   (*Sign due to anticommuting gamma-5 to the right and merging with DiracG5 or PL/PR*)
   gamma5sign=Function[Switch[mtx,dMtxL,-1,_(*dMtx|dMtx5|dMtxR*),1]*(-1)^Length[#]]},

  With[{
	leviCivitaContractionRules=
	{(*Contraction of all four indices*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___,idx[idx1:Except[_List|_Integer, a|b|c|d]],idx[idx2:Except[_List|_Integer, a|b|c|d]],idx[idx3:Except[_List|_Integer, a|b|c|d]],idx[idx4:Except[_List|_Integer, a|b|c|d]],right___],
	  $patternMatched=True; Signature[idxList4]*gamma5sign[{right}]*24*I*newMtx[left,right]],
	 (*Contraction of three indices*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___,idx[idx1:Except[_List|_Integer, a|b|c|d]],idx[idx2:Except[_List|_Integer, a|b|c|d]],idx[idx3:Except[_List|_Integer, a|b|c|d]],right___],
	  $patternMatched=True; -Signature[idxList3]*gamma5sign[{right}]*6*I*newMtx[left,vecidx[Sort[idxList3][[4]]],right]],
	 (*Contraction of two indices*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___,idx[idx1:Except[_List|_Integer, a|b|c|d]],idx[idx2:Except[_List|_Integer, a|b|c|d]],right___],
	  $patternMatched=True; With[{perms=Permutations[{1,2}]}, Dot[Map[Signature,perms], Apply[-(gamma5sign[{right}]*Signature[idxList1]*I*newMtx[left,#1,#2,right])&, Extract[vecidx/@(Sort[idxList2][[3;;4]]),List/@perms],{1}]]]],
	 (*Contraction of one index*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___,idx[idx1:a|b|c|d],right___] /; !FreeQ[{a,b,c,d},_$p] || !FreeQ[{left,right},Except[_List|_Integer, a|b|c|d]],
	  $patternMatched=True; With[{perms=Permutations[{1,2,3}]}, Dot[Map[Signature,perms], Apply[(gamma5sign[{right}]*Signature[idxList1]*1/6*I*newMtx[left,#1,#2,#3,right])&, Extract[vecidx/@(Sort[idxList1][[2;;4]]),List/@perms],{1}]]]],
	 (*Contraction of zero indices*)
	 RuleDelayed@@Hold[(mtx:dMtx|dMtx5|dMtxL|dMtxR)[left___] /; !FreeQ[{a,b,c,d},_$p] || Length[Cases[{left},Except[_List|_Integer, a|b|c|d],2,2]]>1,
	  $patternMatched=True; With[{perms=Permutations[{1,2,3,4}]}, Dot[Map[Signature,perms], Apply[(gamma5sign[{}]*1/24*I*newMtx[left,#1,#2,#3,#4])&, Extract[vecidx/@{a,b,c,d},List/@perms],{1}]]]],
	 (*Contraction into metric tensor*)
	 RuleDelayed@@Hold[LTensor[MetricG,Except[_List|_Integer, a|b|c|d],a|b|c|d], $patternMatched=True; 0]}
	},

	With[{leviCivitaIdentificationRule=RuleDelayed@@Hold[
	  HoldPattern[{otherTensorFactors_. LTensor[LeviCivitaE,a_,b_,c_,d_],res_}],
		Block[{$patternMatched}, With[{replacementResult= {otherTensorFactors, res/.leviCivitaContractionRules} },  replacementResult/;$patternMatched]]
	]},

	  SetDelayed@@Hold[fLineTensorContract[tensorCoeff_,result_],
		ReplaceAll[{tensorCoeff,result}, leviCivitaIdentificationRule]]
	]
  ]
];


(* ::Subsubsection::Closed:: *)
(*Pair contraction and spinor equations of motion*)


(*This combines paired gamma matrices*)
dMtxRules =
{(*Push contracted DiracG until they meet*)
  (mtx:dMtx|dMtx5|dMtxL|dMtxR)[a___,x_,Shortest[b___],x_,c___]:>
	With[{n=Length[{b}]},(-1)^n pair[x,x] mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]]
};


(******This combines paired gamma matrices, and applies the Dirac equation on slahsed momenta******)
(*Both external momenta vanishing*)
fLineRules[(*ChiralBasis*)False][{sig2_,0,m2_,___},{sig1_,0,m1_,___}]:=
{(*Push contracted DiracG until they meet*)
	(mtx:dMtx|dMtx5)[a___,x_,Shortest[b___],x_,c___] :> With[{n=Length[{b}]},(-1)^n pair[x,x]mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]]
};
fLineRules[(*ChiralBasis*)True][{sig2_,0,m2_,___},{sig1_,0,m1_,___}]:=
{(*Push contracted DiracG until they meet*)
	(mtx:dMtxL|dMtxR)[a___,x_,Shortest[b___],x_,c___]:>With[{n=Length[{b}]},(-1)^n pair[x,x]mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]]
};

(*Right momentum non-vanishing*)
fLineRules[(*ChiralBasis*)False][{sig2_,0,m2_,___},{sig1_,p1_,m1_,___}]:=
{(*Push contracted DiracG until they meet*)
	(mtx:dMtx|dMtx5)[a___,x_,Shortest[b___],x_,c___] :> With[{n=Length[{b}]},(-1)^n pair[x,x]mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]],
 (*Push p1-slash to the right to apply Dirac equation*)
	dMtx[a___,vec[p1],b___]:>With[{n=Length[{b}]},(-1)^n sig1 m1 dMtx[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p1],{b}[[m]],dMtx[a,Sequence@@Drop[{b},{m}]]],{m,1,n}]],
	dMtx5[a___,vec[p1],b___]:>With[{n=Length[{b}]},-(-1)^n sig1 m1 dMtx5[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p1],{b}[[m]],dMtx5[a,Sequence@@Drop[{b},{m}]]],{m,1,n}]]
};
fLineRules[(*ChiralBasis*)True][{sig2_,0,m2_,___},{sig1_,p1_,m1_,___}]:=
{(*Push contracted DiracG until they meet*)
	(mtx:dMtxL|dMtxR)[a___,x_,Shortest[b___],x_,c___]:>With[{n=Length[{b}]},(-1)^n pair[x,x]mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]],
 (*Push p1-slash to the right to apply Dirac equation*)
	dMtxL[a___,vec[p1],b___]:>With[{n=Length[{b}]},(-1)^n sig1 m1 dMtxR[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p1],{b}[[m]],dMtxL[a,Sequence@@Drop[{b},{m}]]],{m,1,n}]],
	dMtxR[a___,vec[p1],b___]:>With[{n=Length[{b}]},(-1)^n sig1 m1 dMtxL[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p1],{b}[[m]],dMtxR[a,Sequence@@Drop[{b},{m}]]],{m,1,n}]]
};

(*Left momentum non-vanishing*)
fLineRules[(*ChiralBasis*)False][{sig2_,p2_,m2_,___},{sig1_,0,m1_,___}]:=
{(*Push contracted DiracG until they meet*)
	(mtx:dMtx|dMtx5)[a___,x_,Shortest[b___],x_,c___] :> With[{n=Length[{b}]},(-1)^n pair[x,x]mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]],
 (*Push p2-slash to the left to apply Dirac equation*)
	dMtx[a___,vec[p2],b___]:>With[{n=Length[{a}]},(-1)^n sig2 m2 dMtx[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p2],{a}[[n+1-m]],Drop[dMtx[a,b],{n+1-m}]],{m,1,n}]],
	dMtx5[a___,vec[p2],b___]:>With[{n=Length[{a}]}, (-1)^n sig2 m2 dMtx5[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p2],{a}[[n+1-m]],Drop[dMtx5[a,b],{n+1-m}]],{m,1,n}]]
};
fLineRules[(*ChiralBasis*)True][{sig2_,p2_,m2_,___},{sig1_,0,m1_,___}]:=
{(*Push contracted DiracG until they meet*)
	(mtx:dMtxL|dMtxR)[a___,x_,Shortest[b___],x_,c___]:>With[{n=Length[{b}]},(-1)^n pair[x,x]mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]],
 (*Push p2-slash to the left to apply Dirac equation*)
	dMtxL[a___,vec[p2],b___]:>With[{n=Length[{a}]}, (-1)^n sig2 m2 dMtxL[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p2],{a}[[n+1-m]],dMtxL[Sequence@@Drop[{a},{n+1-m}],b]],{m,1,n}]],
	dMtxR[a___,vec[p2],b___]:>With[{n=Length[{a}]}, (-1)^n sig2 m2 dMtxR[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p2],{a}[[n+1-m]],dMtxR[Sequence@@Drop[{a},{n+1-m}],b]],{m,1,n}]]
};

(*Both momenta non-vanishing*)
fLineRules[(*ChiralBasis*)False][{sig2_,p2_,m2_,___},{sig1_,p1_,m1_,___}]:=
{(*Push contracted DiracG until they meet*)
	(mtx:dMtx|dMtx5)[a___,x_,Shortest[b___],x_,c___] :> With[{n=Length[{b}]},(-1)^n pair[x,x]mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]],
 (*Push p1-slash to the right or p2-slash to the left to apply Dirac equation*)
	dMtx[a___,vec[p1],b___]:>With[{n=Length[{b}]},(-1)^n sig1 m1 dMtx[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p1],{b}[[m]],dMtx[a,Sequence@@Drop[{b},{m}]]],{m,1,n}]],
	dMtx[a___,vec[p2],b___]:>With[{n=Length[{a}]},(-1)^n sig2 m2 dMtx[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p2],{a}[[n+1-m]],Drop[dMtx[a,b],{n+1-m}]],{m,1,n}]],
	dMtx5[a___,vec[p1],b___]:>With[{n=Length[{b}]},-(-1)^n sig1 m1 dMtx5[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p1],{b}[[m]],dMtx5[a,Sequence@@Drop[{b},{m}]]],{m,1,n}]],
	dMtx5[a___,vec[p2],b___]:>With[{n=Length[{a}]}, (-1)^n sig2 m2 dMtx5[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p2],{a}[[n+1-m]],Drop[dMtx5[a,b],{n+1-m}]],{m,1,n}]]
};
fLineRules[(*ChiralBasis*)True][{sig2_,p2_,m2_,___},{sig1_,p1_,m1_,___}]:=
{(*Push contracted DiracG until they meet*)
	(mtx:dMtxL|dMtxR)[a___,x_,Shortest[b___],x_,c___]:>With[{n=Length[{b}]},(-1)^n pair[x,x]mtx[a,b,c]+Sum[(-1)^(m-1)*2*dotDMtx[x,{b}[[m]],mtx[a,Sequence@@Drop[{b},{m}],x,c]],{m,1,n}]],
 (*Push p1-slash to the right or p2-slash to the left to apply Dirac equation*)
	dMtxL[a___,vec[p1],b___]:>With[{n=Length[{b}]},(-1)^n sig1 m1 dMtxR[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p1],{b}[[m]],dMtxL[a,Sequence@@Drop[{b},{m}]]],{m,1,n}]],
	dMtxR[a___,vec[p1],b___]:>With[{n=Length[{b}]},(-1)^n sig1 m1 dMtxL[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p1],{b}[[m]],dMtxR[a,Sequence@@Drop[{b},{m}]]],{m,1,n}]],
	dMtxL[a___,vec[p2],b___]:>With[{n=Length[{a}]}, (-1)^n sig2 m2 dMtxL[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p2],{a}[[n+1-m]],dMtxL[Sequence@@Drop[{a},{n+1-m}],b]],{m,1,n}]],
	dMtxR[a___,vec[p2],b___]:>With[{n=Length[{a}]}, (-1)^n sig2 m2 dMtxR[a,b]+Sum[(-1)^(m-1)*2*dotDMtx[vec[p2],{a}[[n+1-m]],dMtxR[Sequence@@Drop[{a},{n+1-m}],b]],{m,1,n}]]
};


(* ::Subsubsection::Closed:: *)
(*dMtxSort, Chisholm, Gordon*)


(*This sorts dMtx/5/L/R using the Clifford algebra,*)
(*FreeQ[mtx,_LTensor] is to test for absence of sigma matrix*)

dMtxSort[expr_] :=
  ReplaceAll[expr,
	mtx:(_dMtx|_dMtx5|_dMtxL|_dMtxR) /; (*FreeQ[mtx,_LTensor] &&*) !OrderedQ[mtx] :>
	  ReplaceRepeated[mtx,
		Head[mtx][left___,a_,b_,right___]/;!OrderedQ[{a,b}]:>-Head[mtx][left,b,a,right]+2 pair[a,b]*Head[mtx][left,right]
	  ]
	];


chisholmExpansion[False(*ChiralBasis*)] = Function[# /. {
  (*Special cases for shorter chains*)
  (mtx:dMtx|dMtx5)[] :> mtx[],
  (mtx:dMtx|dMtx5)[a_] :> mtx[a],
  (mtx:dMtx|dMtx5)[a_,b_] :> pair[a,b] mtx[] - I mtx[sigPair[a,b]],

  (*General formula with arbitrary number of Dirac matrices*)
  (mtxExpr:_dMtx|_dMtx5):>With[{head=Head[mtxExpr],oppHead=If[Head[mtxExpr]===dMtx,dMtx5,dMtx]},
	  ursp[mtxExpr] head[]/4+ 
	  With[{n=Length[mtxExpr]}, Sum[(-1)^(jdx+1)/4 Take[mtxExpr,{jdx}] ursp[Delete[mtxExpr,{{jdx}}]], {jdx,1,n}]] + 
	  With[{n=Length[mtxExpr]}, Sum[1/4*I*(-1)^(jdx+kdx+1) head[sigPair[mtxExpr[[jdx]],mtxExpr[[kdx]]]] ursp[Delete[mtxExpr,{{jdx},{kdx}}]], {jdx,1,n},{kdx,1,jdx-1}]] +
	  With[{dummyIndex=Unique[]},ursp5[Prepend[mtxExpr,idx[dummyIndex]]] oppHead[idx[dummyIndex]]/4] +
	  ursp5[mtxExpr] oppHead[]/4] }
  ];

chisholmExpansion[True(*ChiralBasis*)] = Function[# /. {
  (*Special case: product of exactly two Dirac matrices expands into unit matrix and sigma matrix*)
  (mtx:dMtxL|dMtxR)[] :> mtx[],
  (mtx:dMtxL|dMtxR)[a_] :> mtx[a],
  (mtx:dMtxL|dMtxR)[a_,b_] :> pair[a,b] mtx[] - I mtx[sigPair[a,b]],

  (*General formula with arbitrary number of Dirac matrices*)
  (mtxExpr:_dMtxL|_dMtxR):>With[{head=Head[mtxExpr],sign=If[Head[mtxExpr]===dMtxL,-1,+1]},
	  ursp[mtxExpr] head[]/4+ 
	  With[{n=Length[mtxExpr]}, Sum[(-1)^(jdx+1)/4 Take[mtxExpr,{jdx}] ursp[Delete[mtxExpr,{{jdx}}]], {jdx, 1 , n}]] + 
	  With[{n=Length[mtxExpr]}, Sum[1/4*I*(-1)^(jdx+kdx+1) head[sigPair[mtxExpr[[jdx]],mtxExpr[[kdx]]]] ursp[Delete[mtxExpr,{{jdx},{kdx}}]], {jdx,1,n},{kdx,1,jdx-1}]] +
	  With[{dummyIndex=Unique[]},sign * ursp5[Prepend[mtxExpr,idx[dummyIndex]]] head[idx[dummyIndex]]/4] +
	  sign * ursp5[mtxExpr] head[]/4] }
  ];

gordonIdentity[False(*ChiralBasis*)][{e2_,p2ex_,m2_},{e1_,p1ex_,m1_},{p2_,p1_}] :=
  If[!PossibleZeroQ[e2 p2ex+e1 p1ex](*If momentum SUM [P = e2 p2 + e1 p1] non-vanishing*),
	If[!PossibleZeroQ[e2 p2ex-e1 p1ex](*If momentum transfer [q = e2 p2 - e1 p1] non-vanishing*),
	  With[{q=Simplify[e2 p2-e1 p1]}, 
	  With[{holdq=If[Length[DeleteCases[Variables[q],_?LScalarQ]]==1, q, Hold[q]]},
		Function[Expand[#,_LTensor|_dMtx|_dMtx5] /. {
		  (mtx:dMtx|dMtx5)[]*LTensor[p1ex,a_Symbol] :> With[{sgn = If[mtx===dMtx,1,-1]}, 
			- e1/2 mtx[]*LTensor[holdq,a] + e1/2 (m2+sgn m1) mtx[idx[a]] - e1/2 I mtx[sigPair[idx[a],vec[q]]]],

		  (mtx:dMtx|dMtx5)[]*LTensor[p2ex,a_Symbol] :> With[{sgn = If[mtx===dMtx,1,-1]}, 
			+ e2/2 mtx[]*LTensor[holdq,a] + e2/2 (m2+sgn m1) mtx[idx[a]] - e2/2 I mtx[sigPair[idx[a],vec[q]]]]}]
	  ]],

	  (*If momentum transfer q = e2 p2 - e1 p1 vanishes, then convective current equals Dirac current*)
	  Function[Expand[#,_LTensor|_dMtx|_dMtx5] //. {
		(mtx:dMtx|dMtx5)[]*LTensor[p1ex,a_Symbol] :> With[{sgn = If[mtx===dMtx,1,-1]}, e1 (m2+sgn m1) mtx[idx[a]]/2],
		(mtx:dMtx|dMtx5)[]*LTensor[p2ex,a_Symbol] :> With[{sgn = If[mtx===dMtx,1,-1]}, e2 (m2+sgn m1) mtx[idx[a]]/2]}]
	]
	,
  (*If momentum SUM vanishes [e2 p2 + e1 p1] vanishes, 
	then Gordon identity reduces to equations of motion which has already been applied*)
  Identity];

gordonIdentity[True(*ChiralBasis*)][{e2_,p2ex_,m2_},{e1_,p1ex_,m1_},{p2_,p1_}] :=
  If[!PossibleZeroQ[e2 p2ex+e1 p1ex](*If momentum SUM [P = e2 p2 + e1 p1] non-vanishing*),
	If[!PossibleZeroQ[e2 p2ex-e1 p1ex](*If momentum transfer [q = e2 p2 - e1 p1] non-vanishing*),
	  With[{q=Simplify[e2 p2-e1 p1]}, 
	  With[{holdq=If[Length[DeleteCases[Variables[q],_?LScalarQ]]==1, q, Hold[q]]},
		Function[Expand[#,_LTensor|_dMtxL|_dMtxR] /. {
		  (mtx:dMtxL|dMtxR)[]*LTensor[p1ex,a_Symbol] :> With[{oppMtx = If[mtx===dMtxL,dMtxR,dMtxL]}, 
			- e1/2 mtx[]*LTensor[holdq,a] + e1/2 m2 mtx[idx[a]] + e1/2 m1 oppMtx[idx[a]] - e1/2 I mtx[sigPair[idx[a],vec[q]]]],

		  (mtx:dMtxL|dMtxR)[]*LTensor[p2ex,a_Symbol] :> With[{oppMtx = If[mtx===dMtxL,dMtxR,dMtxL]}, 
			+ e2/2 mtx[]*LTensor[holdq,a] + e2/2 m2 mtx[idx[a]] + e2/2 m1 oppMtx[idx[a]] - e2/2 I mtx[sigPair[idx[a],vec[q]]]]}]
	  ]],

	  (*If momentum transfer q = e2 p2 - e1 p1 vanishes, then convective current equals Dirac current*)
	  Function[Expand[#,_LTensor|_dMtxL|_dMtxR] //. {
		(mtx:dMtxL|dMtxR)[]*LTensor[p1ex,a_Symbol] :> With[{oppMtx = If[mtx===dMtxL,dMtxR,dMtxL]}, e1/2 m2 mtx[idx[a]] + e1/2 m1 oppMtx[idx[a]]],
		(mtx:dMtxL|dMtxR)[]*LTensor[p2ex,a_Symbol] :> With[{oppMtx = If[mtx===dMtxL,dMtxR,dMtxL]}, e2/2 m2 mtx[idx[a]] + e2/2 m1 oppMtx[idx[a]]]}]
	]
	,
  (*If momentum SUM vanishes [e2 p2 + e1 p1] vanishes, 
	then Gordon identity reduces to equations of motion which have already been applied*)
  Identity];


(* ::Subsubsection::Closed:: *)
(*FermionLineExpand rules*)


fermionLineProductExpansionRule[optExternalContract_, optChiral_,optChisholm_,optSort_, optGordon_, globalKinematics_:False] :=
  Times[Optional[coefficient__], fl:(FermionLineProduct[_FermionLine..])] :>
	Module[{scalarCoeff, tensorCoeff,
			fermionKinematics,fermionSpinorsList,result},

	  (*Kinematics*)
	  If[globalKinematics===False,
		fermionKinematics = generateFermionLineKinematics[List@@(fl[[All,1;;2]]),$p],
		fermionKinematics = globalKinematics];

	  fermionSpinorsList = MapThread[ReplaceAll,{((List@@fl)[[All,1;;2]]),fermionKinematics[[1]]}];
	  (*$kinematicConstraint[mtx_] = Subtract@@Plus@@@Apply[Times,MapAt[mtx[vec[#]]&,Transpose[Take[List@@@fermionSpinorsList,All,All,2]],{All,All,2}],{2}]==0;*)

	  (*Destructure *)
	  tensorCoeff=(Times@@Cases[{coefficient},_LTensor])/.Flatten[fermionKinematics[[1]]];
	  scalarCoeff=(Times@@DeleteCases[{coefficient},_LTensor])/.fermionKinematics[[3]];

	  (*Parse Fermion lines matrices*)
	  result = Map[diracMtxParser, Map[(dMtx@@#)&, (flProd@@fl)[[All,3]]] /. Join@@fermionKinematics[[1]]];
	  result = clearG5PLPR[optChiral][result];
	  result = Distribute[result,List,flProd,Plus,flProd];

	  Internal`InheritedBlock[{dMtx,dMtx5,dMtxL,dMtxR},

		dMtx[Times[-1,e_]]:=-dMtx[e];
		dMtx5[Times[-1,e_]]:=-dMtx5[e];
		dMtxL[Times[-1,e_]]:=-dMtxL[e];
		dMtxR[Times[-1,e_]]:=-dMtxR[e];

		result = FixedPoint[fLineProdProcess[fermionSpinorsList,optChiral,optChisholm], tensorCoeff*result];

		If[optChisholm,
		  (*result = gammaToSigma[fermionSpinorsList,optChiral][result]*)
		  result = FixedPoint[gammaToSigma[fermionSpinorsList,optChiral], result]
		];

	  ];

	  (*If[True,
		result = flProdKinematicIdentities[fermionSpinorsList,optChiral][result]
	  ];*)

	  result = result /. fermionKinematics[[2]] /. fermionKinematics[[3]];

	  Block[{vec,idx,sig,dMtx,dMtx5,dMtxL,dMtxR,flProd},
		vec[arg_]:=LDot[DiracG,arg];
		idx[arg_]:=LTensor[DiracG,arg];
		dMtx[str___]:=DiracMatrix[str];
		dMtx5[str___]:=DiracMatrix[str,DiracG5];
		dMtxL[str___]:=DiracMatrix[str,DiracPL];
		dMtxR[str___]:=DiracMatrix[str,DiracPR];

		(*convert flProd[dMtx...] to FermionLineProduct[FermionLine[]]*)
		flProd[fls__] := Inner[FermionLine[Sequence@@#1,#2]&, List@@(fl[[All,1;;2]]), {fls}, FermionLineProduct];
	
		scalarCoeff*result

	  ]

	];


fermionLineExpansionRule[optExternalContract_, optChiral_, optChisholm_, optSort_, optGordon_, globalKinematics_:False] :=
  Times[Optional[coefficient__],FermionLine[{sig2:-1|1,p2_,m2_,restKin2___},{sig1:-1|1,p1_,m1_,restKin1___},DiracMatrix[diracMtx___]]] /; FreeQ[{diracMtx},Projector[__][__]] /; Check[LTensor[p1,Symbol]; LTensor[p2,Symbol]; True, False] :>
	Module[{scalarCoeff,tensorCoeff,p2ex,p1ex,fermionKinematics, result},

	  If[globalKinematics===False,
		fermionKinematics = generateFermionLineKinematics[FermionLine[{sig2,p2,m2},{sig1,p1,m1}],$p],
		fermionKinematics = globalKinematics];

	  tensorCoeff=(Times@@Cases[{coefficient},_LTensor])/.fermionKinematics[[1]];
	  scalarCoeff=(Times@@DeleteCases[{coefficient},_LTensor])/.fermionKinematics[[3]];

	  (*Express fermion momenta in terms of basis symbols.*)
	  {p2ex,p1ex}={p2,p1}/.fermionKinematics[[1]];

	  (*Parse string of dirac matrices*)
	  result=diracMtxParser[dMtx[diracMtx]/.fermionKinematics[[1]]];
	  result=clearG5PLPR[optChiral][result];

	  (*Replace Levi-Civita tensor that are contracted into on shell momenta with antisymmetric combination of gamma matrices.*)
	  If[optExternalContract,
		{tensorCoeff,result}=fLineTensorContract[tensorCoeff,result]
	  ];

	  (*Expand, apply spinor equations of motion*)  
	  result=result//.fLineRules[optChiral][{sig2,p2ex,m2},{sig1,p1ex,m1}];
	  (*Apply on shell conditions implied by spinors*)
	  result=Total[result,Infinity];
	  (*Result is a sum of dMtx and dMtx with _vec and _idx as arguments*)

	  If[optChisholm,
		result = chisholmExpansion[optChiral][result],
		If[optSort,result = dMtxSort[result]]
	  ];

	  If[optExternalContract && optGordon,
		result = gordonIdentity[optChiral][{sig2,p2ex,m2},{sig1,p1ex,m1},{p2,p1}][tensorCoeff*result], 
		result = tensorCoeff*result
	  ];

	  result = result /.fermionKinematics[[2]] /. fermionKinematics[[3]];

	  Block[{vec,idx,dMtx,dMtx5,dMtxL,dMtxR},
		vec[arg_]:=LDot[DiracG,arg];
		idx[arg_]:=LTensor[DiracG,arg];
		dMtx[str___]:=FermionLine[{sig2,p2,m2,restKin2},{sig1,p1,m1,restKin1},DiracMatrix[str]];
		dMtx5[str___]:=FermionLine[{sig2,p2,m2,restKin2},{sig1,p1,m1,restKin1},DiracMatrix[str,DiracG5]];
		dMtxL[str___]:=FermionLine[{sig2,p2,m2,restKin2},{sig1,p1,m1,restKin1},DiracMatrix[str,DiracPL]];
		dMtxR[str___]:=FermionLine[{sig2,p2,m2,restKin2},{sig1,p1,m1,restKin1},DiracMatrix[str,DiracPR]];
		
		scalarCoeff*result
	  ]

	];


diracMatrixExpansionRule[optExternalContract_,optChiral_,optDiracAlgebra_,optChisholm_,optSort_] := 
  Times[Optional[coefficient__],(mtxHead:DiracMatrix|Spur|Inactive[Spur])[diracMtx___]] /; FreeQ[{diracMtx},Projector[__][__]] :>
	Module[{tensorCoeff,scalarCoeff,result},

	  (*Parse string of dirac matrices*)
	  result=diracMtxParser[dMtx[diracMtx], optDiracAlgebra] // Total;
	  (*Result is a sum of dMtx with _vec, _idx, and DiracG5 and DiracPL and DiracPR as arguments*)

	  If[optDiracAlgebra, 
		result = clearG5PLPR[optChiral][result];

		If[optExternalContract,
		  tensorCoeff=Times@@Cases[{coefficient},_LTensor];
		  scalarCoeff=Times@@DeleteCases[{coefficient},_LTensor];
		  {tensorCoeff,result}=fLineTensorContract[tensorCoeff,result]
		];

		result = result //. dMtxRules		
	  ];

	  If[!(optDiracAlgebra && optExternalContract),
		(*If external tensors are not contracted into the DiracMatrix, 
		  then just put the coefficient into scalarCoefficient*)
		tensorCoeff=1;
		scalarCoeff=Times[coefficient];
	  ];


	  If[optChisholm,
		result = chisholmExpansion[optChiral][result],
		If[optSort, result = dMtxSort[result]]
	  ];

	  If[MatchQ[mtxHead,Spur|Inactive[Spur]],
		(*Use cyclic permutations to bring each term to canonical form*)
		(*Don't touch those with DiracG5, PL, PR because canonical form is right-most position*)
		result = result /. mtx:(dMtx[str__]):>First[Sort[Array[RotateLeft[mtx,#]&,Length@mtx]]]
	  ];

	  Block[{vec,idx,dMtx,dMtx5,dMtxL,dMtxR},
		vec[arg_]:=LDot[DiracG,arg];
		idx[arg_]:=LTensor[DiracG,arg];
		dMtx[str___]:=mtxHead[str];
		dMtx5[str___]:=mtxHead[str,DiracG5];
		dMtxL[str___]:=mtxHead[str,DiracPL];
		dMtxR[str___]:=mtxHead[str,DiracPR];
		
		scalarCoeff*tensorCoeff*result
	  ]

	];


(* ::Subsubsection:: *)
(*FermionLineExpand*)


Options[internalFermionLineProductExpand]:=Options[FermionLineExpand];
internalFermionLineProductExpand[preExpr_,postExpr_,OptionsPattern[]] :=
  With[{fTally=Tally[Cases[preExpr,_FermionLineProduct,{0,Infinity}],(#1[[All,1;;2]]===#2[[All,1;;2]])&]},
	With[{globalFermionKinematics = If[Length[fTally]==1, generateFermionLineKinematics[List@@(fTally[[1,1,All,1;;2]]),$p], False],
		  optChiralBasis=If[OptionValue[ChiralBasis]===Automatic, !FreeQ[preExpr,DiracPL|DiracPR], OptionValue[ChiralBasis]],
		  optChisholmExpand=If[OptionValue[ChisholmExpand]===Automatic,True,OptionValue[ChisholmExpand]]},
	  X`Utilities`ClearDuplicatedTensors[postExpr /. fermionLineProductExpansionRule[True, optChiralBasis,optChisholmExpand,True,OptionValue[GordonIdentity],globalFermionKinematics]]
	]
  ];

Options[internalFermionLineExpand]:=Options[FermionLineExpand];
internalFermionLineExpand[preExpr_,postExpr_,OptionsPattern[]] :=
  With[{fTally=Tally[Cases[preExpr,_FermionLine,{0,Infinity}],(#1[[1;;2]]===#2[[1;;2]])&]},
	With[{globalFermionKinematics = If[Length[fTally]==1, generateFermionLineKinematics[fTally[[1,1,1;;2]],$p], False],
		  optChiralBasis=If[OptionValue[ChiralBasis]===Automatic, !FreeQ[preExpr,DiracPL|DiracPR], OptionValue[ChiralBasis]],
		  optChisholmExpand=If[OptionValue[ChisholmExpand]===Automatic,True,OptionValue[ChisholmExpand]]},
	  X`Utilities`ClearDuplicatedTensors[Switch[OptionValue[GordonIdentity],
		True,   X`Utilities`CollectByTensorStructures[postExpr] (*So that vectors are all multiplying FermionLines*),
		False, postExpr] /. fermionLineExpansionRule[True, optChiralBasis,optChisholmExpand,True,OptionValue[GordonIdentity],globalFermionKinematics]]
	]
  ];

Options[internalDiracMatrixExpand]:=Options[FermionLineExpand];
internalDiracMatrixExpand[preExpr_,postExpr_,OptionsPattern[]] :=
 With[{optChiralBasis=If[OptionValue[ChiralBasis]===Automatic, !FreeQ[preExpr,DiracPL|DiracPR], OptionValue[ChiralBasis]],
	   optChisholmExpand=If[OptionValue[ChisholmExpand]===Automatic,False,OptionValue[ChisholmExpand]]},
  X`Utilities`ClearDuplicatedTensors[postExpr /. diracMatrixExpansionRule[True, optChiralBasis, True, optChisholmExpand, True]]

];


FermionLineExpand::opts = "Value of option `1` -> `2` is not `3`.";
FermionLineExpand::mixfl = "Input is a mixed expression in DiracMatrix, FermionLine, FermionLineProduct.  Expecting only one type of object.";

(*FermionLineExpand only works correctly if the expression 
  1.  is of uniform tensor type-- only FermionLineProduct, only FermionLine, or only DiracMatrix
  2.  contains no products of DiracMatrix or products of FermionLine*)

FermionLineExpand[expr_, opts:OptionsPattern[]?(X`Internal`ValidOptionsQ[FermionLineExpand])] :=
  Module[{result},
	Catch[
	  If[OptionValue[DiracAlgebra],
		result = Which[
		  !FreeQ[expr, _FermionLineProduct], internalFermionLineProductExpand[expr, expr, opts],
		  !FreeQ[expr, _FermionLine], internalFermionLineExpand[expr, expr, opts],
		  !FreeQ[expr, _DiracMatrix|_Spur|Blank[Inactive[Spur]]], internalDiracMatrixExpand[expr, expr, opts],
		  True, expr
		],

		result=X`Utilities`ClearDuplicatedTensors[expr /. diracMatrixExpansionRule[False, False, False, False, False]]
	  ]
	,DiracMatrix,messageInvalidDiracMatrix[FermionLineExpand]] /; Check[validFermionLineExpandInputQ[expr,FermionLineExpand];True,False]
  ] /; Check[validFermionLineExpandInputQ[expr,FermionLineExpand] && validFermionLineExpandOptionsQ[opts];True,False];


validFermionLineExpandInputQ[expr_,messageName_]:=
  If[!FreeQ[expr, _DiracMatrix|_FermionLine|_FermionLineProduct],
	With[{flatPoly=expr/.{_FermionLineProduct:>FermionLineProduct, _FermionLine:>FermionLine, _DiracMatrix:>DiracMatrix}},
	  If[(*Check if two or more distinct objects are present*)
		BooleanCountingFunction[1,3][FreeQ[flatPoly,FermionLineProduct], FreeQ[flatPoly,FermionLine], FreeQ[flatPoly,DiracMatrix]],
		Message[messageName::mixfl]
	  ]
	]
  ];

Options[validFermionLineExpandOptionsQ] := Options[FermionLineExpand];
validFermionLineExpandOptionsQ[OptionsPattern[]]:=
  CompoundExpression[
	(*Check options*)
	If[!MemberQ[{True,False,Automatic},OptionValue[ChisholmExpand]],Message[FermionLineExpand::opttfa,ChisholmExpand,OptionValue[ChisholmExpand]]],
	If[!MemberQ[{True,False},OptionValue[GordonIdentity]],Message[FermionLineExpand::opttf,GordonIdentity,OptionValue[GordonIdentity],"True or False"]],
	If[!MemberQ[{True,False,Automatic},OptionValue[ChiralBasis]],Message[FermionLineExpand::opttfa,ChiralBasis,OptionValue[ChiralBasis],"True, False, or Automatic"]],
	True
  ];


(* ::Subsection::Closed:: *)
(*Finish*)


SetAttributes[{internalDiracMatrixExpand,diracMatrixExpansionRule},Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[{internalFermionLineExpand,fermionLineExpansionRule},Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[{internalFermionLineProductExpand,fermionLineProductExpansionRule},Unevaluated@{Protected, ReadProtected, Locked}];


(*Protecting Functions*)
SetAttributes[Spur, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[{DiracMatrix,FermionLine,FermionLineProduct}, Unevaluated@{Protected, ReadProtected}];
SetAttributes[{FermionLineExpand, ChiralBasis, ChisholmExpand, GordonIdentity}, Unevaluated@{Protected, ReadProtected}];
SetAttributes[Projector, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[{Dirac1,DiracG,DiracG5,DiracS,DiracPL,DiracPR,SpinorU,SpinorV},Unevaluated@{Constant, Protected, ReadProtected}];
SetAttributes[X`Utilities`ValidDiracMatrixQ,Unevaluated@{Protected, ReadProtected, Locked}];


End[];


(*EndPackage[]*)

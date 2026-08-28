(* ::Package:: *)

Begin["`Private`"];


(* ::Subsection::Closed:: *)
(*For third-party packages*)


If[Quiet[NameQ["X`$DiracAlgebra"]],
  (*Full Package-x functionality*)
  Null
,
  (*For third party packages that use only OneLoop.m*)
  X`Mu;X`Eps;X`PVA;X`PVB;X`PVC;X`PVD;X`ScalarC0;X`ScalarD0;X`ScalarC0IR6;X`ScalarD0IR12;X`ScalarD0IR13;X`ScalarD0IR16;X`Kallen\[Lambda];
  X`Kibble\[Phi];X`DiscB;X`DiscExpand;X`KallenExpand;X`KibbleExpand;X`C0Expand;X`D0Expand;X`ContinuedDiLog;X`DiLog;X`Ln;X`LoopRefine;
  X`LoopRefineSeries;X`Discontinuity;
  X`Utilities`SimplifyLn;X`Utilities`SimplifyDiLog;X`Utilities`SimplifyContinuedDiLog;X`Utilities`ContinuedDiLogExpand;
  X`Utilities`EquivalentAlternatives;X`Utilities`PermutePVD;X`Utilities`PVNormal;
  Options[PVA]={Weights->{1},Dimensions->4};Options[PVB]={Weights->{1,1},Dimensions->4};
  Options[PVC]={Weights->{1,1,1},Dimensions->4};Options[PVD]={Weights->{1,1,1,1},Dimensions->4};
  
  X`Internal`ValidOptionsQ[symb_Symbol][x_]:=If[FilterRules[Options[symb],x]==={},Message[symb::optx,First[x],symb],True];
  Options[LoopRefine]={Analytic->False, Dimensions->4, ExplicitC0->Automatic, Organization->Function, TargetScale->Automatic, Part->All};
  Options[LoopRefineSeries]={Analytic->False, Dimensions->4, ExplicitC0->Automatic, Organization->Function, TargetScale->Automatic, Part->All};
  X`Utilities`TensorStructures[expr_]={1};
  X`Utilities`CollectByTensorStructures[expr_,f_]:=f[expr];

  X`Internal`PossibleAllZeroQ[mtx_]:=ReplaceAll[PossibleZeroQ[mtx],List->And];
  X`Internal`ValidOptionsQ[symb_Symbol][x_]:=If[FilterRules[Options[symb],x]==={},Message[symb::optx,First[x],symb],True];

  SetAttributes[X`Internal`CheckArgumentCount,HoldFirst];
  X`Internal`CheckArgumentCount[head_Symbol[args___],min_,max_]:=
  With[{hcargs=Hold[args]},
	ArgumentCountQ[head,
	  Length[
		If[Options[head]==={},
		  hcargs,
		  Replace[hcargs,_[a___,(Rule|RuleDelayed)[_String|_Symbol,_]..]:>Hold[a]]
		]
	  ],min,max
	]
  ];

  X`Internal`ToTargetPrecision[f_,args_List,extraPrec_:0]:=
  Block[{ttpNewArgs,ttpResult,ttpPrecisionOfInput,ttpPrecisionOfResult},

	ttpPrecisionOfInput=Precision[args];

	ttpNewArgs=NumericalMath`RaisePrecision[args,ttpPrecisionOfInput+extraPrec];

	ttpResult=Quiet[f@@ttpNewArgs];
	ttpPrecisionOfResult=If[Internal`ExceptionFreeQ[ttpResult],Precision[ttpResult],0];

	While[ttpPrecisionOfResult<ttpPrecisionOfInput,
	  ttpNewArgs=NumericalMath`RaisePrecision[ttpNewArgs,Precision[ttpNewArgs]+1+Sow[(ttpPrecisionOfInput-ttpPrecisionOfResult),"PrecisionLoss"]];
	  ttpResult=Quiet[f@@ttpNewArgs];
	  ttpPrecisionOfResult=If[Internal`ExceptionFreeQ[ttpResult],Precision[ttpResult],0];
	];
	
	ttpResult
  ];

  pow[a_,0]:=1;  pow[a_,b_]:=a^b;

  SetAttributes[
  {X`Internal`PossibleAllZeroQ,X`Internal`ValidOptionsQ,
   X`Internal`CheckArgumentCount,X`Internal`ToTargetPrecision},
  {Protected,ReadProtected,Locked}];
];


(* ::Section:: *)
(*Internal helper functions*)


(* ::Subsection:: *)
(*For powers and logarithms*)


(* ::Subsubsection::Closed:: *)
(*rationalCoefficientSimplify, rootKallen*)


(*Used in analytic forms for complicated ScalarC0, ScalarD0 and their discontinuities*)
(*First argument is an external invariant; last two arguments are masses.
  Returns the positive root in case one argument vanishes, making it a perfect square. *)
rootKallen=
  Function[{a,b,c},
	Which[
	  PossibleZeroQ[b]&&PossibleZeroQ[c],a,
	  PossibleZeroQ[c],a-b,
	  PossibleZeroQ[b],a-c,
	  PossibleZeroQ[a],b-c,
	  PossibleZeroQ[(a-b-c)^2-4b c],0,
	  True,Sqrt[Kallen\[Lambda][a,b,c]]
	]
  ];


rationalCoefficientSimplify = (FactorSquareFree@((Expand[Numerator[#]/.{Kallen\[Lambda][a_,b_,c_]:>a^2+b^2+c^2-2a b-2b c-2a c, Kibble\[Phi][s1_,s2_,s3_,s4_,s12_,s23_]:>-s12^2 s23-s1^2 s3+s12 (-(s23-s3) (s23-s4)+s2 (s23+s4))-s2 (s23 (s3-s4)+s4 (s2-s3+s4))+s1 (s12 (-s2+s23+s3)+(s23-s3) (s3-s4)+s2 (s3+s4))}])*Expand[Denominator[#]]^(-1)&)@(Together[#]))& ;


(* ::Subsubsection::Closed:: *)
(*olog and logArgumentSimplify*)


(*Ordered logs for masses*)
olog[x_,y_]:=Signature[{x,y}]Log[#1/#2]&@@Sort[{x,y}];


(*To simplify arugments of logs and polylogs that are complicated and contain square-roots*)
logArgumentSimplify = 
  Function[{argument},
	Divide@@Map[Collect[Simplify[#,TimeConstraint->0.2,ComplexityFunction->(Simplify`SimplifyCount[#]+10000*Count[#,_Piecewise|_Abs|_Complex,{0,Infinity}]&)],
	  Power[_,_Rational],FactorSquareFree]&, {Numerator[argument],Denominator[argument]}]
  ];


(* ::Subsubsection::Closed:: *)
(*simplifyLn*)


simplifyLn[arg_,inf_,cplxVar_:{}]:=
  With[{realVariables=Complement[Union[Variables[arg],Variables[inf]],Variables[cplxVar]]},
	With[{(*Implicit assumption: all variables are real, and no combination can possibly vanish*)
	  coreAssumptions=Join[(#\[Element]Reals)&/@realVariables, (#!=0)&/@Cases[arg,Times[x_]:>x,Infinity]]},
	  If[(*First check if User added contradictory assumptions*)
		 Check[Assuming[coreAssumptions,False],True,{$Assumptions::cas,$Assumptions::fas}],
		 (*If contradictory assumptions were encountered, just return the unsimplified Ln*)
		  Ln[arg,inf],
		  (*Otherwise proceed with simplification*)
		  Quiet[
			If[(*Check if it is impossible for argument to be on cut*)
			  TrueQ[!Assuming[coreAssumptions,Refine[arg\[Element]Reals && arg<0, TimeConstraint->0.2]]],
			   (*If argument can't be on cut, return built-in simplified Log*)
			  Log[Assuming[coreAssumptions,logArgumentSimplify[arg]]],

			  (*It may be possible for argument to be on cut.  Simplify infinitessimal part with the added assumption that argument is on cut.
				Simplify the arguments of the resultant logarithms*)
			  Ln[arg,
				(*Infinitessimal part of log*)
				Assuming[Append[coreAssumptions, arg<0],
				  FixedPoint[Simplify[ReplaceRepeated[Refine[Sign[#]], {Sign[Sqrt[expr_]]->1, (c_. Sign[expr_]^p_/;OddQ[p] )|( c_. Sign[expr_] ):>c*expr, c_. Sign[expr_]^p_ | c_. Sign[expr_^p_] :> c /; EvenQ[p]}],TimeConstraint->0.2,ComplexityFunction->(Simplify`SimplifyCount[#]+10000*Count[#,_Piecewise|_Abs|_Complex,{0,Infinity}]&)]&, inf]
				]
			  ]/.{Ln[argNew_,infNew_]:>Ln[Assuming[coreAssumptions,logArgumentSimplify[argNew]],infNew],
				  Log[argNew_]:>Log[Assuming[coreAssumptions,logArgumentSimplify[argNew]]]}
			], {$Assumptions::cas,$Assumptions::fas,Simplify::time,FullSimplify::time}
		  ]
	  ]
	]
  ];


X`Utilities`SimplifyLn[expr_] := expr/.Ln[arg_,inf_]:>simplifyLn[arg,inf];

X`Utilities`SimplifyLn[expr_, cplxVar_Symbol] := expr/.Ln[arg_,inf_]:>simplifyLn[arg,inf,{cplxVar}];
X`Utilities`SimplifyLn[expr_, cplxVar_List] := expr/.Ln[arg_,inf_]:>simplifyLn[arg,inf,cplxVar];


(* ::Subsubsection::Closed:: *)
(*simplifyDiLog*)


simplifyDiLog[arg_,inf_,cplxVar_:{}]:=
  With[{realVariables=Complement[Union[Variables[arg],Variables[inf]],Variables[cplxVar]]},
	With[{(*Implicit assumption: all variables are real, and no combination can possibly vanish*)
	  coreAssumptions=Join[(#\[Element]Reals)&/@realVariables, (#!=0)&/@Cases[arg,Times[x_]:>x,Infinity]]},	
	  If[(*First check if User added contradictory assumptions; or a false statement*)
		 Check[Assuming[coreAssumptions,False],True,{$Assumptions::cas,$Assumptions::fas}],
		  (*If contradictory assumptions were encountered, just return the unsimplified DiLog*)
		  DiLog[arg,inf],
		  (*Otherwise proceed with simplification*)
		  Quiet[
			If[(*Check if it is impossible for argument to be on cut*)
			  TrueQ[!Assuming[coreAssumptions,Refine[arg\[Element]Reals && 1-arg<0, TimeConstraint->0.2]]],
			   (*If argument can't be on cut, return simplified built-in PolyLog*)
			  PolyLog[2,Assuming[coreAssumptions,logArgumentSimplify[arg]]],

			  (*It may be possible for argument to be on cut.  Simplify infinitessimal part with the added assumption that argument is on cut.
				Simplify the arguments of the resultant logarithms*)
			  DiLog[arg,
				(*Infinitessimal part of dilog*)
				Assuming[Append[coreAssumptions, arg>1],
				  FixedPoint[Simplify[ReplaceRepeated[Refine[Sign[#]], {Sign[Sqrt[expr_]]->1, (c_. Sign[expr_]^p_/;OddQ[p] )|( c_. Sign[expr_] ):>c*expr, c_. Sign[expr_]^p_ | c_. Sign[expr_^p_] :> c /; EvenQ[p]}],TimeConstraint->0.2,ComplexityFunction->(Simplify`SimplifyCount[#]+10000*Count[#,_Piecewise|_Abs|_Complex,{0,Infinity}]&)]&, inf]
				]
			  ]/.{DiLog[argNew_,infNew_]:>DiLog[Assuming[coreAssumptions,logArgumentSimplify[argNew]],infNew],
				  PolyLog[2,argNew_]:>PolyLog[2,Assuming[coreAssumptions,logArgumentSimplify[argNew]]],
				  Log[argNew_]:>Log[Assuming[coreAssumptions,logArgumentSimplify[argNew]]]}
			], {$Assumptions::cas,$Assumptions::fas,Simplify::time,FullSimplify::time}
		  ]
	  ]
	]
  ];


X`Utilities`SimplifyDiLog[expr_] := expr/.DiLog[arg_,inf_]:>simplifyDiLog[arg,inf];

X`Utilities`SimplifyDiLog[expr_, cplxVar_Symbol] := expr/.DiLog[arg_,inf_]:>simplifyDiLog[arg,inf,{cplxVar}];
X`Utilities`SimplifyDiLog[expr_, cplxVar_List] := expr/.DiLog[arg_,inf_]:>simplifyDiLog[arg,inf,cplxVar];


(* ::Subsubsection::Closed:: *)
(*simplifyContinuedDiLog*)


SetAttributes[internalContinuedDiLog,Orderless];
internalContinuedDiLog[{PossibleZeroQ[0], _},__]:=\[Pi]^2/6;

internalContinuedDiLog[{x_?Assumptions`APositive, xEps_},{y_,yEps_},rest___]:=internalContinuedDiLog[{x y,x yEps+y xEps},rest];

internalContinuedDiLog[{x_,xEps_},{y_,yEps_},rest___] /; PossibleZeroQ[x*y-1] :=internalContinuedDiLog[rest];
internalContinuedDiLog[] := 0;

simplifyContinuedDiLog[arg__]:=
  With[{coreAssumptions=Join[#\[Element]Reals&/@Variables[{arg}[[All,1]]],#>0&/@(Variables[{arg}[[All,1]]]^2)]},
	If[
	  (*First check if User added contradictory assumptions*)
	  Check[Assuming[coreAssumptions,False],True,{$Assumptions::cas,$Assumptions::fas}],
	  (*If contradictory assumptions were encountered, just return the unsimplified ContinuedDiLog*)
	  ContinuedDiLog[arg],
	  (*Otherwise proceed with simplification. check if argument is on cut, and simplify accordingly*)
	  (*THIS TAKES WAY TOO LONG*)
	  (*Assuming[coreAssumptions,  ContinuedDiLog@@(Map[Simplify[#,TimeConstraint->0.01,ComplexityFunction->(Simplify`SimplifyCount[#]+10000*Count[#,_Piecewise|_Abs|_Complex,{0,Infinity}]&)]&,internalContinuedDiLog[arg],{2}])]*)
	  ContinuedDiLog[arg]
	]
  ];


X`Utilities`SimplifyContinuedDiLog[expr_] := expr/.ContinuedDiLog[args:({_,_}..)]:>simplifyContinuedDiLog[args];


X`Utilities`ContinuedDiLogExpand[expr_] := expr /.HoldPattern[ContinuedDiLog[{x_,xEps_},{y_,yEps_}]]:>DiLog[1-x y,-x yEps-xEps y]+(Ln[x y,x yEps+xEps y]-Ln[x,xEps]-Ln[y,yEps])Ln[1-x y,-x yEps-xEps y];


(* ::Subsection:: *)
(*Permutations*)


(* ::Subsubsection::Closed:: *)
(*permutedSetDelayed, equivalentAlternatives*)


permGroup[f_]:=f/.{
 Kallen\[Lambda]->PermutationGroup[{PermutationCycles[{2,3,1}]}],
 Kibble\[Phi]->PermutationGroup[{PermutationCycles[{2,3,4,1,6,5}], PermutationCycles[{5,2,6,4,1,3}]}],
 DiscB->PermutationGroup[{Cycles[{{3,2}}]}],
 ScalarC0->PermutationGroup[{Cycles[{{1,3,2},{6,5,4}}]}],
 ScalarC0IR6->PermutationGroup[{Cycles[{{3,2}}]}],
 analD0|analD0IR|ScalarD0->PermutationGroup[{PermutationCycles[{2,3,4,1,6,5,8,9,10,7}],PermutationCycles[{5,2,6,4,1,3,7,9,8,10}]}],
 ScalarD0IR12->PermutationGroup[Cycles[{}]],
 ScalarD0IR13->PermutationGroup[{Cycles[{}],Cycles[{{1,3},{4,5},{6,7}}],Cycles[{{1,4},{3,5}}],Cycles[{{1,5},{3,4},{6,7}}]}],
 ScalarD0IR16->PermutationGroup[{Cycles[{}],Cycles[{{1,2},{5,7}}]}]
};

SetAttributes[permutedSetDelayed,HoldAll];
permutedSetDelayed[(f_Symbol)[args__],rhs_] := 
  With[{setOfRules=((HoldPattern[f[##]]:>rhs)&@@@DeleteDuplicates[Permute[{args},permGroup[f]],Internal`ComparePatterns[#1,#2]==="Identical"&]) },
	AppendTo[DownValues[f],setOfRules]
  ];

permutedSetDelayed[(wrapper_Symbol)[f_Symbol][args__],rhs_] := 
  With[{setOfRules=((HoldPattern[wrapper[f][##]]:>rhs)&@@@DeleteDuplicates[Permute[{args},permGroup[f]],Internal`ComparePatterns[#1,#2]==="Identical"&]) },
	AppendTo[SubValues[wrapper],setOfRules]
  ];


(*Patch 27-Feb-2020*)
SetAttributes[conditionalPermutedSetDelayed,HoldAll];
conditionalPermutedSetDelayed[(f_Symbol)[args__],cond_,rhs_] :=
  With[{setOfRules=DeleteDuplicates[(HoldPattern[Condition[f[##],cond]]:>rhs)&@@@Permute[{args},permGroup[f]],Internal`ComparePatterns[#1,#2]==="Identical"&]},
	AppendTo[DownValues[f],#]& /@ setOfRules
  ];

conditionalPermutedSetDelayed[(wrapper_Symbol)[f_Symbol][args__],cond_,rhs_] :=
  With[{setOfRules=DeleteDuplicates[(HoldPattern[Condition[wrapper[f][##],cond]]:>rhs)&@@@Permute[{args},permGroup[f]],Internal`ComparePatterns[#1,#2]==="Identical"&]},
	AppendTo[SubValues[wrapper],#]& /@ setOfRules
  ];


SetAttributes[equivalentAlternatives,HoldAll];
equivalentAlternatives[PVA[r_,args:PatternSequence[_]]]:=HoldPattern[PVA[r,args]];

equivalentAlternatives[PVB[r_,0,args:PatternSequence[_,_,_]]]:=
  With[{group=PermutationGroup[{Cycles[{{3,2}}]}]},
	Replace[Composition[HoldPattern,Alternatives]@@(Hold[r,0,##]&@@@DeleteDuplicates[Permute[List[args],group],Internal`ComparePatterns[#1,#2]==="Identical"&]),Hold->PVB,{3},Heads->True]
  ];
equivalentAlternatives[PVC[r_,0,0,args:PatternSequence[_,_,_,_,_,_]]]:=
  With[{group=PermutationGroup[{Cycles[{{1,3,2},{6,5,4}}]}]},
	Replace[Composition[HoldPattern,Alternatives]@@(Hold[r,0,0,##]&@@@DeleteDuplicates[Permute[List[args],group],Internal`ComparePatterns[#1,#2]==="Identical"&]),Hold->PVC,{3},Heads->True]
  ];
equivalentAlternatives[PVD[r_,0,0,0,args:PatternSequence[_,_,_,_,_,_,_,_,_,_]]]:=
  With[{group=PermutationGroup[{PermutationCycles[{2,3,4,1,6,5,8,9,10,7}],PermutationCycles[{5,2,6,4,1,3,7,9,8,10}]}]},
	Replace[Composition[HoldPattern,Alternatives]@@(Hold[r,0,0,0,##]&@@@DeleteDuplicates[Permute[List[args],group],Internal`ComparePatterns[#1,#2]==="Identical"&]),Hold->PVD,{3},Heads->True]
  ];

equivalentAlternatives[PVB[args:PatternSequence[_,_,_,_,_]]]:=PVB[args];
equivalentAlternatives[PVC[args:PatternSequence[_,_,_,_,_,_,_,_,_]]]:=PVC[args];
equivalentAlternatives[PVD[args:PatternSequence[_,_,_,_,_,_,_,_,_,_,_,_,_,_]]]:=PVD[args];

equivalentAlternatives[f_Symbol[args__]]:=
  Replace[Composition[HoldPattern,Alternatives]@@(Hold[##]&@@@DeleteDuplicates[Permute[List[args],permGroup[f]],Internal`ComparePatterns[#1,#2]==="Identical"&]),Hold->f,{3},Heads->True];



SetAttributes[X`Utilities`EquivalentAlternatives,HoldFirst];
X`Utilities`EquivalentAlternatives::badf = "`1` is not a valid function.";

X`Utilities`EquivalentAlternatives[f_Symbol[args__]] := 
  equivalentAlternatives[f[args]] /; 
	Check[Switch[f,
	  PVA,ArgumentCountQ[f,Length[Unevaluated[f[args]]],2,2],
	  PVB,ArgumentCountQ[f,Length[Unevaluated[f[args]]],5,5],
	  PVC,ArgumentCountQ[f,Length[Unevaluated[f[args]]],9,9],
	  PVD,ArgumentCountQ[f,Length[Unevaluated[f[args]]],14,14],
	  Kallen\[Lambda],ArgumentCountQ[f,Length[Unevaluated[f[args]]],3,3],
	  Kibble\[Phi],ArgumentCountQ[f,Length[Unevaluated[f[args]]],6,6],
	  DiscB,ArgumentCountQ[f,Length[Unevaluated[f[args]]],3,3],
	  ScalarC0,ArgumentCountQ[f,Length[Unevaluated[f[args]]],6,6],
	  ScalarC0IR6,ArgumentCountQ[f,Length[Unevaluated[f[args]]],3,3],
	  ScalarD0,ArgumentCountQ[f,Length[Unevaluated[f[args]]],10,10],
	  ScalarD0IR12,ArgumentCountQ[f,Length[Unevaluated[f[args]]],6,6],
	  ScalarD0IR13,ArgumentCountQ[f,Length[Unevaluated[f[args]]],7,7],
	  ScalarD0IR16,ArgumentCountQ[f,Length[Unevaluated[f[args]]],7,7],
	  _,Message[X`Utilities`EquivalentAlternatives::badf,f]
  ];True,False];

X`Utilities`EquivalentAlternatives[_] := Null /; Message[X`Utilities`EquivalentAlternatives::args, X`Utilities`EquivalentAlternatives];

LHS_X`Utilities`EquivalentAlternatives:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,1];Fail];


(* ::Subsubsection::Closed:: *)
(*Utilities`PermutePVD*)


X`Utilities`PermutePVD[s:Except[_Plus|_Times, _],t:Except[_Plus|_Times, _]][expr_]:=
  ReplaceAll[expr,
	{HoldPattern[PVD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]]/;!FreeQ[s1,s|t]&&!FreeQ[s3,s|t](*&&FreeQ[{s2,s4,s12,s23,m0,m1,m2,m3},s|t]*):>PVD[r,n2,n1,n3,s12,s2,s23,s4,s1,s3,m0,m2,m1,m3],
	 HoldPattern[PVD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]]/;!FreeQ[s2,s|t]&&!FreeQ[s4,s|t](*&&FreeQ[{s1,s3,s12,s23,m0,m1,m2,m3},s|t]*):>PVD[r,n1,n3,n2,s1,s23,s3,s12,s4,s2,m0,m1,m3,m2],

	 HoldPattern[ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]]/;!FreeQ[s1,s|t]&&!FreeQ[s3,s|t](*&&FreeQ[{s2,s4,s12,s23,m0,m1,m2,m3},s|t]*):>ScalarD0[s12,s2,s23,s4,s1,s3,m0,m2,m1,m3],
	 HoldPattern[ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]]/;!FreeQ[s2,s|t]&&!FreeQ[s4,s|t](*&&FreeQ[{s1,s3,s12,s23,m0,m1,m2,m3},s|t]*):>ScalarD0[s1,s23,s3,s12,s4,s2,m0,m1,m3,m2],

	 HoldPattern[Kibble\[Phi][s1_,s2_,s3_,s4_,s12_,s23_]]/;!FreeQ[s1,s|t]&&!FreeQ[s3,s|t](*&&FreeQ[{s2,s4,s12,s23,m0,m1,m2,m3},s|t]*):>Kibble\[Phi][s12,s2,s23,s4,s1,s3],
	 HoldPattern[Kibble\[Phi][s1_,s2_,s3_,s4_,s12_,s23_]]/;!FreeQ[s2,s|t]&&!FreeQ[s4,s|t](*&&FreeQ[{s1,s3,s12,s23,m0,m1,m2,m3},s|t]*):>Kibble\[Phi][s1,s23,s3,s12,s4,s2],

	 HoldPattern[ScalarD0IR13[s2_,s3_,s4_,s12_,s23_,m2_,m3_]]/;!FreeQ[s2,s|t]&&!FreeQ[s4,s|t](*&&FreeQ[{s3,s12,s23,m2,m3},s|t]*):>ScalarD0IR13[s12,s3,s23,s2,s4,m2,m3]}
  ];


(* ::Section::Closed:: *)
(*Special functions: elementary*)


(* ::Subsection:: *)
(*Kallen\[Lambda]*)


(* ::Subsubsection::Closed:: *)
(*Numeric evaluation*)


SetAttributes[Kallen\[Lambda],{Orderless,NumericFunction}];

Kallen\[Lambda][a_?NumericQ,b_?NumericQ,c_?NumericQ] := a^2+b^2+c^2-2 a b-2a c-2b c;


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


Kallen\[Lambda][0, b_,c_]            := (b-c)^2;
Kallen\[Lambda][a_,c_,c_]            := (*a^2(1-4*c/a)*)a (a-4 c);
Kallen\[Lambda][a_,b_,c_] /; PossibleZeroQ[(a-b-c)^2-4b c] := 0;

(*Kallen\[Lambda][(m2_+m1_)^2,(m2_+m0_)^2,(m1_+m0_)^2] := -16 m0 m1 m2 (m0+m1+m2);*)


(* ::Subsubsection::Closed:: *)
(*Derivatives and series*)


Derivative[n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative][Kallen\[Lambda]] ^:= Derivative[n1,n2,n3][#1^2+#2^2+#3^2-2#1 #2-2#1 #3-2 #2 #3 &];


Kallen\[Lambda] /: HoldPattern[System`Private`InternalSeries[Kallen\[Lambda][a_,b_,c_],{z_,p0_,n_Integer}]] /; Internal`DependsOnQ[{a,b,c},z] := System`Private`InternalSeries[a^2-2 a b+b^2-2 a c-2 b c+c^2,{z,p0,n}];


(* ::Subsubsection::Closed:: *)
(*CompileValues*)


ClearAttributes[Internal`CompileValues,{Protected,ReadProtected}];
Internal`CompileValues[X`Kallen\[Lambda]]={HoldPattern[X`Kallen\[Lambda][a_,b_,c_]]:>Internal`CompileInline[a^2+b^2+c^2-2a b-2a c-2 b c]};
SetAttributes[Internal`CompileValues,{Protected,ReadProtected}];


LHS_Kallen\[Lambda]:=RuleCondition[X`Internal`CheckArgumentCount[LHS,3,3];Fail];


(* ::Subsubsection::Closed:: *)
(*KallenExpand*)


KallenExpand[expr_] := expr/.Kallen\[Lambda][a_,b_,c_]:>Expand[a^2+b^2+c^2-2a b-2b c-2a c];
LHS_KallenExpand:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,1];Fail];


(* ::Subsection:: *)
(*Kibble\[Phi]*)


(* ::Subsubsection::Closed:: *)
(*Numeric evaluation*)


SetAttributes[Kibble\[Phi], NumericFunction];

Kibble\[Phi][s1_?NumericQ,s2_?NumericQ,s3_?NumericQ,s4_?NumericQ,s12_?NumericQ,s23_?NumericQ]:=-s1 s12 s2+s1 s12 s23-s12^2 s23+s12 s2 s23-s12 s23^2-s1^2 s3+s1 s12 s3+s1 s2 s3+s1 s23 s3+s12 s23 s3-s2 s23 s3-s1 s3^2+s1 s2 s4+s12 s2 s4-s2^2 s4-s1 s23 s4+s12 s23 s4+s2 s23 s4+s1 s3 s4-s12 s3 s4+s2 s3 s4-s2 s4^2;


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


Kibble\[Phi][left___,x_Plus,right___]:=
  With[{lenL=Length[{left}],lenR=Length[{right}]},
	With[
	  {exchangeResAndNewArg=
		Reap[Switch[lenL,
		  0,{#5,#6,#2,#4,Sow@Expand[-#1+#2-#3+#4+#5+#6],#3}&[left,x,right],
		  1,{#1,#6,#5,#3,#4,Sow@Expand[-#4-#2+#1+#6+#3+#5]}&[left,x,right],
		  2,{#5,#2,#4,#6,#1,Sow@Expand[-#1-#3+#5+#2+#6+#4]}&[left,x,right],
		  3,{#1,#3,#6,#5,Sow@Expand[-#4-#2+#1+#6+#3+#5],#2}&[left,x,right],
		  4,{#1,#3,#2,#4,Sow@Expand[#1+#2+#3+#4-#5-#6],#6}&[left,x,right],
		  5,{#1,#2,#4,#3,#5,Sow@Expand[#1+#2+#3+#4-#5-#6]}&[left,x,right]]]
	  },
	  Kibble\[Phi]@@First[exchangeResAndNewArg] /; MatchQ[Last@Last@Last@exchangeResAndNewArg,Except[_Plus]]
	]/;lenL+lenR===5&&Count[{left,right},_Plus]===0
  ];


(*Special cases to be substituted automatically*)
permutedSetDelayed[Kibble\[Phi][0,0,0,s4_,s12_,s23_],-s12 s23 (s12-s4+s23)];
permutedSetDelayed[Kibble\[Phi][s1_,s2_,s1_,s1_,0,0],-s1 (s1-s2)^2];
permutedSetDelayed[Kibble\[Phi][s1_,s1_,s1_,s1_,s12_,s23_],-s12 s23 (-4 s1+s12+s23)];


(* ::Subsubsection::Closed:: *)
(*Derivatives and series*)


Derivative[n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative,n4_Integer?NonNegative,n5_Integer?NonNegative,n6_Integer?NonNegative][Kibble\[Phi]] ^:=
  Derivative[n1,n2,n3,n4,n5,n6][-#1^2 #3+#1 #2 #3-#1 #3^2+#1 #2 #4-#2^2 #4+#1 #3 #4+#2 #3 #4-#2 #4^2-#1 #2 #5+#1 #3 #5+#2 #4 #5-#3 #4 #5+#1 #3 #6-#2 #3 #6-#1 #4 #6+#2 #4 #6+#1 #5 #6+#2 #5 #6+#3 #5 #6+#4 #5 #6-#5^2 #6-#5 #6^2&];
  
Kibble\[Phi] /: HoldPattern[System`Private`InternalSeries[Kibble\[Phi][s1_,s2_,s3_,s4_,s12_,s23_],{z_,p0_,n_Integer}]] /; Internal`DependsOnQ[{s1,s2,s3,s4,s12,s23},z] := System`Private`InternalSeries[-s1 s12 s2+s1 s12 s23-s12^2 s23+s12 s2 s23-s12 s23^2-s1^2 s3+s1 s12 s3+s1 s2 s3+s1 s23 s3+s12 s23 s3-s2 s23 s3-s1 s3^2+s1 s2 s4+s12 s2 s4-s2^2 s4-s1 s23 s4+s12 s23 s4+s2 s23 s4+s1 s3 s4-s12 s3 s4+s2 s3 s4-s2 s4^2,{z,p0,n}];


(* ::Subsubsection::Closed:: *)
(*CompileValues*)


ClearAttributes[Internal`CompileValues,{Protected,ReadProtected}];
Internal`CompileValues[Kibble\[Phi]]={HoldPattern[Kibble\[Phi][sa_,sb_,sc_,sd_,sab_,sbc_]]:>Internal`CompileInline[Module[{s1=sa,s2=sb,s3=sc,s4=sd,s12=sab,s23=sbc},-s1 s12 s2+s1 s12 s23-s12^2 s23+s12 s2 s23-s12 s23^2-s1^2 s3+s1 s12 s3+s1 s2 s3+s1 s23 s3+s12 s23 s3-s2 s23 s3-s1 s3^2+s1 s2 s4+s12 s2 s4-s2^2 s4-s1 s23 s4+s12 s23 s4+s2 s23 s4+s1 s3 s4-s12 s3 s4+s2 s3 s4-s2 s4^2]]};
SetAttributes[Internal`CompileValues,{Protected,ReadProtected}];


LHS_Kibble\[Phi]:=RuleCondition[X`Internal`CheckArgumentCount[LHS,6,6];Fail];


(* ::Subsubsection::Closed:: *)
(*KibbleExpand*)


With[{rules={
  equivalentAlternatives[Kibble\[Phi][0,s23_,s3_,0,s12_,s23_]]:>-s23 (s12^2-s12 s3+s23 s3),
  equivalentAlternatives[Kibble\[Phi][0,0,s3_,s4_,s12_,t23_]]:>-s12 ((s3-t23) (s4-t23)+s12 t23),
  equivalentAlternatives[Kibble\[Phi][0,s2_,0,s4_,s12_,t23_]]:>-(s12-s2-s4+t23) (-s2 s4+s12 t23),
  equivalentAlternatives[Kibble\[Phi][s1_,s2_,s2_,s1_,s12_,s23_]]:>-s23 (s12 s23+Kallen\[Lambda][s1,s2,s12]),
  equivalentAlternatives[Kibble\[Phi][s1_,s2_,s2_,s4_,s12_,s23_]]:>-s2 (s1-s4)^2+(s1-s4) (s2-s4+s12) s23-s12 s23^2-s23 Kallen\[Lambda][s2,s4,s12],
  equivalentAlternatives[Kibble\[Phi][s1_,s2_,s1_,s2_,s12_,s23_]]:>(-s12+2 (s1+s2)-s23) (-(s1-s2)^2+s12 s23),
  equivalentAlternatives[Kibble\[Phi][s1_,s2_,s3_,s4_,s12_,s23_]]:>-s12^2 s23-s1^2 s3+s12 (-(s23-s3) (s23-s4)+s2 (s23+s4))-s2 (s23 (s3-s4)+s4 (s2-s3+s4))+s1 (s12 (-s2+s23+s3)+(s23-s3) (s3-s4)+s2 (s3+s4))}},

  KibbleExpand[expr_]:=expr/.rules
];

LHS_KibbleExpand:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,1];Fail];


(* ::Subsection:: *)
(*DiscB*)


(* ::Subsubsection::Closed:: *)
(*Numeric evaluation*)


SetAttributes[DiscB, NumericFunction];


(*For numeric evaluations*)
DiscB[s_?Internal`RealValuedNumericQ,m0_?NonNegative,m1_?NonNegative] := 
  Which[
	s==0, Which[m0==m1, -2, True, Message[DiscB::irdiv,"non-Landauian"]; ComplexInfinity],
	m0==0 || m1==0, Message[DiscB::irdiv,"Mass"]; -\[Infinity]/Sign[s],
	s==(m0+m1)^2 || s==(m0-m1)^2, 0,
	True, 1/s Sqrt[m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2] Log[(2m0 m1)/(-s+m0^2+m1^2-Sqrt[m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2])]
  ];


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


Evaluate[If[$VersionNumber >= 10.1,
  DiscB[Optional[c_Integer?Positive] m_^2,m_,m_],
  DiscB[Optional[c_Integer] m_^2,m_,m_] /; Positive[c]]] := (Sqrt[(-4+c) c] Log[1/2 (2-c+Sqrt[(-4+c) c])])/c;
DiscB[0,m_,m_]    := -2;
DiscB[0,m0_,m1_]  := (Message[DiscB::irdiv,"non-Landauian"]; ComplexInfinity);
DiscB[m0_^2,m0_,0]   := 0;
DiscB[m1_^2,0,m1_]   := 0;
DiscB[s_,m0_,0]   := (Message[DiscB::irdiv,"Mass"]; ((m0^2-s) \[Infinity])/s);
DiscB[s_,0,m1_]   := (Message[DiscB::irdiv,"Mass"]; ((m1^2-s) \[Infinity])/s);
DiscB[s_,m0_,m1_]/;PossibleZeroQ[s-(m0+m1)^2] || PossibleZeroQ[s-(m0-m1)^2] := 0;
DiscB[s_,m0_,m1_]/;!OrderedQ[{m0,m1}]:=DiscB[s,m1,m0];


(* ::Subsubsection::Closed:: *)
(*Derivatives and series*)


(*Derivatives at regular points*)
Derivative[n1_Integer?Positive,n2_Integer,n3_Integer][DiscB] ^:= Derivative[n1-1,n2,n3][(-(1/#1)+(#1-#2^2-#3^2)/Kallen\[Lambda][#1,#2^2,#3^2])DiscB[#1,#2,#3]-1/#1&];
Derivative[n1_Integer,n2_Integer?Positive,n3_Integer][DiscB] ^:= Derivative[n1,n2-1,n3][(-2 #2(#1+#3^2-#2^2))/Kallen\[Lambda][#1,#2^2,#3^2] DiscB[#1,#2,#3]+(#1+#2^2-#3^2)/(#2 #1)&];
Derivative[n1_Integer,n2_Integer,n3_Integer?Positive][DiscB] ^:= Derivative[n1,n2,n3-1][(-2 #3(#1+#2^2-#3^2))/Kallen\[Lambda][#1,#2^2,#3^2] DiscB[#1,#2,#3]+(#1+#3^2-#2^2)/(#3 #1)&];


(*Expansion near s=0*)
DiscB /: HoldPattern[System`Private`InternalSeries[DiscB[fs_,m0_,m1_],{s_,p_,nn_Integer}]] /; Internal`DependsOnQ[fs,s]&&!Internal`DependsOnQ[m0,s]&&!Internal`DependsOnQ[m1,s] :=
With[{lim=System`SeriesDump`getExpansionPoint[fs,s,p]},
  Module[{res,a,c,nAdj=System`SeriesDump`AdjustExpansionOrder[fs,lim,s,p,nn]},
	Which[
	  PossibleZeroQ[m0-m1],
	    res=-2+Sum[((n!)(n-1)!)/(2n+1)! fs^n/m0^(2n),{n,1,nAdj+1}],

	  True,
		a[-1]:=(m0^2-m1^2)/2 olog[m0^2,m1^2];
		a[0]:=-1-1/2 (m0^2+m1^2)/(m0^2-m1^2) olog[m0^2,m1^2];
		a[n_]:=-(1/2) n!/(n+1) (a[-1]c[n+1]+Sum[1/r! a[r]c[n-r],{r,0,n-1}]);
		c[n_]:=2/(m0^2-m1^2)^(2n) Sum[Binomial[2n,2k]m0^(2k) m1^(2n-2k),{k,0,n}];
		res=a[-1] 1/fs+Sum[1/n! Collect[a[n],Log[_],Simplify]fs^n,{n,0,nAdj+1}]
	];

	System`SeriesDump`SafeSeries[res,{s,p,nn}]
  ] /; PossibleZeroQ[lim]
];


(*Threshold expansion near s=(m0+m1)^2*)
DiscB /: HoldPattern[System`Private`InternalSeries[DiscB[fs_,m0_,m1_],{s_,p_,nn_Integer}]] /; Internal`DependsOnQ[fs,s]:=
  With[{lim=System`SeriesDump`getExpansionPoint[fs,s,p]},
	Module[{delta, sgn=Which[PossibleZeroQ[lim-(m0+m1)^2],1,True,-1], nAdj=System`SeriesDump`AdjustExpansionOrder[fs,lim,s,p,nn]},
	(*Print["1.  Threshold expansion"];*)
	  Assuming[{m0>0,m1>0},
		Simplify[System`SeriesDump`SafeSeries[
		  With[{r=Sqrt[sgn 4 m0 m1+delta]},
			1/((m0+sgn m1)^2+delta) r Sqrt[delta](If[sgn===1,I \[Pi],0]+Sum[(-2 sgn^n)/((4m0 m1)^n n) Sum[Binomial[n,2j](r^2-sgn 8m0 m1)^j r^(n-2j),{j,0,n/2}](Sqrt[delta])^n,{n,1,2*nAdj+1}])
		  ]/.delta->fs-lim,{s,p,nn}]
		]
	  ]
	]/;(PossibleZeroQ[(lim-(m0+m1)^2)]||PossibleZeroQ[(lim-(m0-m1)^2)])
  ];


(*Expansion near m0=0*)
(*DiscB[s, m0, m0]*)
DiscB /: HoldPattern[System`Private`InternalSeries[DiscB[s_,m_,m_],{me_,p_,nn_Integer}]] /; !Internal`DependsOnQ[s,m]&&Internal`DependsOnQ[m,me] :=
  With[{lim=System`SeriesDump`getExpansionPoint[m,me,p]},
	Module[{res, nAdj=System`SeriesDump`AdjustExpansionOrder[m,lim,me,p,nn]},
	  res = Log[-m^2/s]Sum[Binomial[1/2,k](-4)^k (m^2/s)^k,{k,0,nn+2}]+Sum[Sum[(-4)^l/(k-l) Binomial[1/2,l]Binomial[2(k-l),k-l],{l,0,k-1}](m^2/s)^k,{k,1,nAdj+1}];
	  System`SeriesDump`SafeSeries[res,{me,p,nn}]
  ]/;PossibleZeroQ[lim]
];

(*DiscB[m1^2, m0, m1] for small m0*)
DiscB /: HoldPattern[System`Private`InternalSeries[DiscB[s_,ma_,mb_],{me_,p_,nn_Integer}]] /; !Internal`DependsOnQ[s,me]:=
  Module[{res, m0, m1,nAdj},
	If[Internal`DependsOnQ[ma,me],m0=ma; m1=mb, m0=mb; m1=ma];
	nAdj=System`SeriesDump`AdjustExpansionOrder[m0,System`SeriesDump`getExpansionPoint[m0,me,p],me,p,nn];
	res =
	  With[{rtlam=2*I m0 m1 Sum[Binomial[1/2,i](-m0^2/(4m1^2))^i,{i,0,nAdj+1}],
			delMercator=(-I m0)/(2 m1)+Sum[Binomial[1/2,i](-m0^2/(4m1^2))^i,{i,1,nAdj+1}]},
		1/m1^2 (rtlam) I \[Pi]/2 + 1/m1^2 (rtlam)Sum[(-1)^(j+1) delMercator^j/j,{j,1,nAdj+1}]
	  ];
    System`SeriesDump`SafeSeries[res,{me,p,nn}]
]/;(Xor[Internal`DependsOnQ[ma,me]&&PossibleZeroQ[s-mb^2]&&PossibleZeroQ[System`SeriesDump`getExpansionPoint[ma,me,p]],
		Internal`DependsOnQ[mb,me]&&PossibleZeroQ[s-ma^2]&&PossibleZeroQ[System`SeriesDump`getExpansionPoint[mb,me,p]]]);

(*DiscB[m0^2, m0, m1] for small m0*)
DiscB /: HoldPattern[System`Private`InternalSeries[DiscB[s_,ma_,mb_],{me_,p_,nn_Integer}]]:=
  Module[{res, m0, m1, nAdj},
	If[Internal`DependsOnQ[ma,me],m0=ma; m1=mb, m0=mb; m1=ma];
	nAdj=System`SeriesDump`AdjustExpansionOrder[m0,System`SeriesDump`getExpansionPoint[m0,me,p],me,p,nn];
	res =
	  With[{rtlam=m1^2 Sum[Binomial[1/2,i](-4 m0^2/(m1^2))^i,{i,0,nn+2}],
			delMercator=1/2*Sum[Binomial[1/2,i](-4 m0^2/(m1^2))^i,{i,1,nn+2}]},
		1/(2*m0^2) (rtlam) olog[m1^2,m0^2] + 1/m0^2 (rtlam)Sum[(-1)^(j+1) delMercator^j/j,{j,1,nAdj+1}]
	  ];
    System`SeriesDump`SafeSeries[res,{me,p,nn}]
]/;(Xor[Internal`DependsOnQ[ma,me]&&!Internal`DependsOnQ[mb,me]&&PossibleZeroQ[s-ma^2]&&PossibleZeroQ[System`SeriesDump`getExpansionPoint[ma,me,p]],
		Internal`DependsOnQ[mb,me]&&!Internal`DependsOnQ[ma,me]&&PossibleZeroQ[s-mb^2]&&PossibleZeroQ[System`SeriesDump`getExpansionPoint[mb,me,p]]]);

(*DiscB[s, m0, m1] for small m0*)
DiscB /: HoldPattern[System`Private`InternalSeries[DiscB[s_,ma_,mb_],{me_,p_,nn_Integer}]] /; !Internal`DependsOnQ[s,me]:=
  Module[{res, m0, m1, nAdj},
	If[Internal`DependsOnQ[me,ma],m0=ma; m1=mb, m0=mb; m1=ma];
	nAdj = System`SeriesDump`AdjustExpansionOrder[m0,System`SeriesDump`getExpansionPoint[m0,me,p],me,p,nn];
	res =
	  With[{rtlam=(s-m1^2)+(s-m1^2)Sum[Binomial[1/2,i]m0^2^i (m0^2-2s-2m1^2)^i/(s-m1^2)^(2i),{i,1,nAdj+1}],
			delMercator=(-(m0^2/(4 m1^2))-(m0^2-2s-2m1^2)/(2m1^2) Sum[Binomial[1/2,i+1]m0^2^i (m0^2-2s-2m1^2)^i/(s-m1^2)^(2i),{i,1,nAdj+1}])},
		1/s rtlam Log[(m0 m1)/(m1^2-s)]+1/s (rtlam)Sum[(-1)^(j+1) delMercator^j/j,{j,1,nAdj+1}]
	  ];
    System`SeriesDump`SafeSeries[res,{me,p,nn}]
]/;(Xor[Internal`DependsOnQ[ma,me]&&!Internal`DependsOnQ[mb,me]&&PossibleZeroQ[System`SeriesDump`getExpansionPoint[ma,me,p]],
		Internal`DependsOnQ[mb,me]&&!Internal`DependsOnQ[ma,me]&&PossibleZeroQ[System`SeriesDump`getExpansionPoint[mb,me,p]]]);


(* ::Subsubsection::Closed:: *)
(*CompileValues*)


ClearAttributes[Internal`CompileValues,{Protected,ReadProtected}];

Internal`CompileValues[DiscB]={HoldPattern[DiscB[pp_,ma_,mb_]]:>
  Internal`CompileInline[
	Module[{s=pp+0I,m0=ma+0I,m1=mb+0I},
	  Which[
		s==0 && m0==m1, -2,
		True, Sqrt[m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2]/s Log[(-s+m0^2+m1^2+Sqrt[m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2])/(2m0 m1)]
	  ]
	]
  ]
};

SetAttributes[Internal`CompileValues,{Protected,ReadProtected}];


LHS_DiscB:=RuleCondition[X`Internal`CheckArgumentCount[LHS,3,3];Fail];


(* ::Subsubsection::Closed:: *)
(*DiscExpand*)


DiscExpand[expr_]:=
  expr/.{DiscB[c_ m_^2,m_,m_] /; FreeQ[{c,m}, _Complex] :> (Sqrt[(-4+c) c] Log[1/2 (2-c+Sqrt[(-4+c) c])])/c
		,DiscB[s_,m_,m_] /; FreeQ[{s,m}, _Complex]       :> 1/s Sqrt[s(s-4 m^2)] Log[(2 m^2-s+Sqrt[s(s-4 m^2)])/(2m^2)]
        ,DiscB[s_,m0_,m1_] /; FreeQ[{s,m0,m1}, _Complex] :> 1/s Sqrt[Kallen\[Lambda][s,m0^2,m1^2]] Log[(m0^2+m1^2-s+Sqrt[Kallen\[Lambda][s,m0^2,m1^2]])/(2m0 m1)]};

LHS_DiscExpand:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,1];Fail];


(* ::Subsection:: *)
(*Ln*)


(* ::Subsubsection::Closed:: *)
(*Numeric and symbolic evaluation*)


Ln::branch="'`1`' in position 2 does not indicate branch.";
SetAttributes[Ln,{NumericFunction,Listable}];


Ln[x_?NumericQ,xEps_?NumericQ] :=
  Piecewise[
  	{{-Log[1/x], Im[x] == 0 && Re[x] < 0 && Re[xEps] < 0},
		{Log[x], Implies[Im[x] == 0 && Re[x] < 0, Re[xEps] > 0]}}, 
  	  Message[Ln::branch, xEps, x]; Indeterminate];

Ln[x_,xEps_?NumericQ] := 
  Which[
	TrueQ[Refine[x>=0]],
	Log[x],
	True,
	Which[
		TrueQ[Re[xEps] < 0],
		-Log[Together[1/x]],
		TrueQ[Re[xEps] > 0],
		Log[x],
		True,
		Message[Ln::branch, xEps, x]; Piecewise[{{Log[x],Im[x]!=0 || Re[x]>0}},Indeterminate]
	]
  ];

Ln[x_, xEps_DirectedInfinity] := Ln[x, Sign[xEps[[1]]]];

Ln[x_?NumericQ,xEps_]/;Im[x]!=0||Re[x]>=0:=Log[x];

Ln[x_]:=Log[x];


(* ::Subsubsection::Closed:: *)
(*Derivatives and series*)


Derivative[n1_Integer,m2_Integer][Ln] := 
	Which[
	  m2>0, 0,
	  PossibleZeroQ[#1], ComplexInfinity, 
	  True, If[n1==0, Ln[#1,#2], ((-1)^(n1-1) (n1-1)!)/#1^n1]
	]&;


Ln /: HoldPattern[System`Private`InternalSeries[Ln[f_,lnEps_],{z_,p0_,n_Integer}]] /; Internal`DependsOnQ[{f,lnEps},z] && System`SeriesDump`limitPointAccessibleQ[f,z,p0] :=
  System`Private`InternalSeries[Log[f],{z,p0,n}]/.Log[arg_]:>Ln[arg,System`SeriesDump`MainTerm[lnEps,z,p0]];


(* ::Subsubsection::Closed:: *)
(*CompileValues*)


ClearAttributes[Internal`CompileValues,{Protected,ReadProtected}];

Internal`CompileValues[Ln]={
HoldPattern[Ln[x_Real,xEps_Real]]:>Internal`CompileInline[
  Which[Re[x] < 0 && Re[xEps] < 0, Log[-x] - I Pi,
		Re[x] < 0, Log[-x] + I Pi,
		True, Log[x]]],

HoldPattern[Ln[x_,xEps_]]:>Internal`CompileInline[
	Module[{xx=x+0I,xxEps=xEps+0I},
	  Which[Im[xx] == 0 && Re[xx] < 0 && Re[xxEps] < 0, -Log[1/xx],
		True, Log[xx]]]],

HoldPattern[Ln[x_Real]]:>Internal`CompileInline[
  Which[Re[x] < 0, Log[-x] + I Pi,
		True, Log[x]]],

HoldPattern[Ln[x_]]:>Internal`CompileInline[Log[x]]
};

SetAttributes[Internal`CompileValues,{Protected,ReadProtected}];


LHS_Ln:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,2];Fail];


(* ::Subsection:: *)
(*DiLog*)


(* ::Subsubsection::Closed:: *)
(*Numeric and symbolic evaluation*)


DiLog::branch="'`1`' in position 2 does not indicate branch.";
SetAttributes[DiLog,{NumericFunction,Listable}];


DiLog[x_?NumericQ, cond_?NumericQ] := 
  Piecewise[{
	{Conjugate[PolyLog[2, x]],  Im[x] == 0 && Re[x] > 1 && Re[cond] > 0}, 
    {PolyLog[2, x], Implies[Im[x] == 0 && Re[x] > 1, Re[cond] < 0]}},
	Message[DiLog::branch, cond, x]; Indeterminate
  ];

DiLog[x_, cond_?NumericQ] :=
  Which[
	TrueQ[Refine[x<=1]],
	PolyLog[2,x],
	True,
	Which[
		Re[cond] > 0,
		-PolyLog[2, Together[x/(x - 1)]] - (1/2)*Log[Together[1/(1 - x)]]^2,
		Re[cond] < 0,
		PolyLog[2,x],
		True,
		Message[DiLog::branch, cond, x]; Piecewise[{{PolyLog[2,x],Im[x]!=0||Re[x]<1}},Indeterminate]
	]
  ];

DiLog[x_?NumericQ,cond_]/;Im[x]!=0||Re[x]<=1:=PolyLog[2,x];

DiLog[x_]:=PolyLog[2,x];


(* ::Subsubsection::Closed:: *)
(*Derivatives and series*)


Derivative[n1_Integer,m2_Integer][DiLog] := 
	Which[
	  m2>0, 0,
	  PossibleZeroQ[#1], If[n1==0,0,n1!/n1^2], 
	  True, If[n1==0, DiLog[#1,#2], Derivative[n1-1,0][-Ln[1-#1,#2]/#1&][#1,#2]]
	]&;


LHS_DiLog:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,2];Fail];


(* ::Subsubsection::Closed:: *)
(*CompileValues*)


(*In section Transcendental special functions/Compilable internal functions section *)


(* ::Subsection::Closed:: *)
(*ContinuedDiLog*)


ContinuedDiLog[{x_?NumericQ,xeps_?NumericQ},{y_?NumericQ,yeps_?NumericQ}]:=DiLog[1-x y,-(xeps y+x yeps)]+NEtaArg[x,xeps,y,yeps,2*Pi*I*Ln[1-x y,-(xeps y+x yeps)]];

ContinuedDiLog[{x_?NumericQ,xeps_?NumericQ},{y_?NumericQ,yeps_?NumericQ},{z_?NumericQ,zeps_?NumericQ}]:=
  DiLog[1-x y z,-(xeps y z+x yeps z+ x y zeps)]+NEtaArg[x y,xeps y+x yeps,z,zeps,2 \[Pi] I Ln[1-x y z,-(xeps y z+x yeps z+ x y zeps)]]+NEtaArg[x,xeps,y,yeps,2 \[Pi] I Ln[1-x y z,-(xeps y z+x yeps z+ x y zeps)]];


continuedDiLogForm[x__List]:=
  With[{args=Transpose[{x}]},
	-(Plus@@Ln[First[args],Last[args]])Log[1-Times@@First[args]]-DiLog[Times@@First[args]]
  ];

ContinuedDiLog/:Derivative[args:({_Integer,0}..)][ContinuedDiLog]:=Derivative[args][continuedDiLogForm];

ContinuedDiLog/:Derivative[___,{_,0},___][ContinuedDiLog]:=0& ;


SetAttributes[ContinuedDiLog,Orderless];


ContinuedDiLog[{x_,xEps_}]:=DiLog[1-x,-xEps];

ContinuedDiLog[{0, xEps_},__List]:=\[Pi]^2/6;

ContinuedDiLog[{x_?Positive, xEps_},{y_,yEps_},rest___List]:=ContinuedDiLog[{x y,-xEps y-yEps x},rest];

(*ContinuedDiLog[{x_, _},{Power[x_,-1],_},rest___List]:=ContinuedDiLog[rest];*)


(*CompileValues in section Transcendental special functions/Compilable internal functions section *)


LHS_ContinuedDiLog:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,Infinity];Fail];


(* ::Section::Closed:: *)
(*Special functions: transcendental*)


(* ::Subsection:: *)
(*Compilable internal functions*)


(* ::Subsubsection::Closed:: *)
(*Logs and Veltman eta*)


(*Numerical Ln and Arg*)
NLn=Function[{x, xEps}, If[Im[x] == 0 && Re[x] < 0 && Re[xEps] < 0, -Log[1/x], Log[x]]];
NArg=Function[{x, xEps}, If[Im[x] == 0 && Re[x] < 0 && Re[xEps] < 0, -Pi, Arg[x]]];


(*Numerical Veltman eta symbol*)
With[{im=If[Im[#]!=0,Im[#1],Re[#2]]&},

  (*Veltman's eta function, without 2\[Pi]I*)
  NEtaArg=Function[{x, xeps, y, yeps, arg},
	Which[
	  im[x,xeps]<0&&im[y,yeps]<0&&im[x y,x yeps+y xeps]>=0, arg,
	  im[x,xeps]>=0&&im[y,yeps]>=0&&im[x y,x yeps+y xeps]<0, -arg,
	True,0
	]
  ];

  (*DNS' modification of Veltman's eta function, without 2\[Pi]I*)
  NEtaTildeArg=Function[{x,xeps,y,yeps,arg},
	Which[
	  Im[y]!=0,
	  Which[
		im[x,xeps]<0&&im[y,yeps]<0&&im[x y,x yeps+y xeps]>=0, arg,
		im[x,xeps]>=0&&im[y,yeps]>=0&&im[x y,x yeps+y xeps]<0, -arg,
		True,0
	  ],

	  Re[y]<0,
	  Which[
		im[x,xeps]<0&&Re[yeps]<0, arg,
		im[x,xeps]>=0&&Re[yeps]>=0, -arg,
		True,0
	  ],
	  True,0
	]
  ]
];

(*Three argument eta function, without 2\[Pi]I*)
NEta3Arg=Function[{x, xeps, y, yeps, z, zeps, arg},
  NEtaArg[x*y,x*yeps+y*xeps,z,zeps,arg]+NEtaArg[x,xeps,y,yeps,arg]
];


(* ::Subsubsection::Closed:: *)
(*Dilogarithm*)


(*Real part of dilogarithm, with smaller memory footprint*)
Module[{formalX,realRegion1,realRegion2,realRegion3,realSegment(*,reLi2numOnRealAxes*),region1,region2,region3,unitCircle},

	realRegion1=Function[x,Sum[x^k/k^2,{k,1,23}]];

	With[{div=9},
		With[{x=Sort[formalX/.Solve[LegendreP[div,formalX]==0,formalX]//N]},
			With[{y=Chop[x/2+1/2],w=Table[2/((1-x[[i]]^2)*Derivative[0,1][LegendreP][div,x[[i]]]^2),{i,1,div}]},
				With[{realRegion2expr=-1/4.*Sum[Chop[w[[i]]] Log[1-2 y[[i]] #+y[[i]]^2 #^2]/y[[i]],{i,1,div}]},
					realRegion2=Function[realRegion2expr]
				]
			]
		]
	];


	realRegion3=With[{rr1=realRegion1},
		Function[{x},If[x==1,Pi^2/6.,-rr1[1-x]-Log[x] Log[1-x]+\[Pi]^2/6.]]];

	realSegment=With[{rr1=realRegion1,rr2=realRegion2,rr3=realRegion3},
		Function[{x},If[-0.5<=x<=0.5,rr1[x],If[x<=0,rr2[x],rr3[x]]]]];

	reLi2numOnRealAxes=With[{rS=realSegment},
		Function[{x},Re@If[-1.<=x<=1.,rS[x],-rS[1/x]-Pi^2/6-1/2*(1/4 Log[x^2]^2-Arg[-x]^2)]]];

	region1=Function[{r,\[Theta]},Sum[r^k Cos[k \[Theta]]/k^2,{k,1,40}]];

	With[{div=16},
		With[{x=Sort[formalX/.Solve[LegendreP[div,formalX]==0,formalX]//N]},
			With[{y=Chop[x/2+1/2],w=Table[2/((1-x[[i]]^2)*Derivative[0,1][LegendreP][div,x[[i]]]^2),{i,1,div}]},
				With[{region2expr=-1/4.*Sum[Chop[w[[i]]] Log[1-2 y[[i]]#1 Cos[#2]+y[[i]]^2 #1^2]/y[[i]],{i,1,div}]},
					region2=Function[region2expr]
				]
			]
		]
	];

	region3=With[{r1=region1},
		Function[{r,\[Theta]},-r1[Sqrt[1-2 r Cos[\[Theta]]+r^2],ArcTan[1-r Cos[\[Theta]],-r Sin[\[Theta]]]]-(-\[Theta] ArcTan[1-r Cos[\[Theta]],- r Sin[\[Theta]]]+1/4 Log[r^2] Log[(1-r Cos[\[Theta]])^2+r^2 Sin[\[Theta]]^2])+\[Pi]^2/6.]];

	unitCircle=With[{r1=region1,r2=region2,r3=region3},
		Function[{r,\[Theta]},
			If[0<=r<0.5,r1[r,\[Theta]],
				If[Re[Sqrt[1-2 r Cos[\[Theta]]+r^2]]>0.5,r2[r,\[Theta]],r3[r,\[Theta]]]
			]
		]
	];

	NReLi2=With[{reLi2=reLi2numOnRealAxes,uC=unitCircle},
		Function[{z},
		If[Im[z]==0.,
			reLi2[Re[z]],
			With[{r=Abs[z],\[Theta]=Arg[z]},
				If[0<=r<=1,uC[r,\[Theta]],-uC[1/r,-\[Theta]]-\[Pi]^2/6-1/2*(1/4 Log[r^2]^2-(Abs[\[Theta]]-\[Pi])^2)]
			]
		]]
	];
];


Module[{imLi2numOnRealAxes,formalX,region1,region2,region3,unitCircle},

	imLi2numOnRealAxes=Function[{x},Re@If[x<=1.,0.,-\[Pi] Log[x]]];

	region1=Function[{r,\[Theta]},Sum[r^k Sin[k \[Theta]]/k^2,{k,1,40}]];

	With[{div=16},
		With[{x=Sort[formalX/.Solve[LegendreP[div,formalX]==0,formalX]//N]},
			With[{y=Chop[x/2+1/2],w=Table[2/((1-x[[i]]^2)*Derivative[0,1][LegendreP][div,x[[i]]]^2),{i,1,div}]},
				With[{region2expr=1/2.*Sum[Chop[w[[i]]] ArcTan[(y[[i]] #1 Sin[#2])/(1-y[[i]] #1 Cos[#2])]/y[[i]],{i,1,div}]},
					region2=Function[region2expr]
				]
			]
		]
	];

	region3=With[{r1=region1},
		Function[{r,\[Theta]},-r1[Sqrt[1-2 r Cos[\[Theta]]+r^2],ArcTan[1-r Cos[\[Theta]],-r Sin[\[Theta]]]]-1/2 (ArcTan[1-r Cos[\[Theta]],- r Sin[\[Theta]]]Log[r^2]+ If[Abs[\[Theta]]<10^-5&&.999<r<1.001,\[Theta] (-1+r+2 Log[Abs[\[Theta]]]),\[Theta] Log[1+r^2-2r Cos[\[Theta]]]])]];

	unitCircle=With[{r1=region1,r2=region2,r3=region3},
		Function[{r,\[Theta]},
		If[0<=r<0.5,
			r1[r,\[Theta]],
			If[Re[Sqrt[1-2 r Cos[\[Theta]]+r^2]]>0.5,r2[r,\[Theta]],r3[r,\[Theta]]]
		]]
	];

	NImLi2=With[{imLi2=imLi2numOnRealAxes,uC=unitCircle(*,argNegExp=Function[angle,If[angle+\[Pi]<\[Pi],angle+\[Pi],angle-\[Pi]]]*)},
		Function[{z},
		If[Im[Chop[z]]==0.,
			imLi2[Re[z]],
			With[{r=Abs[z],\[Theta]=Arg[z]},
				If[0<=r<=1, uC[r,\[Theta]], -uC[1/r,-\[Theta]]-1/2 (*argNegExp[\[Theta]]*)(\[Theta]-Sign[\[Theta]]*\[Pi])Log[r^2]]
			]
		]]
	];
];


(*Numerical DiLog*)
With[{NReLi2=NReLi2, NImLi2=NImLi2, NEtaArg=NEtaArg},
  NDiLog=Function[{x, xEps}, If[Im[x] == 0 && Re[x] > 1 && Re[xEps] > 0, NReLi2[x] - I NImLi2[x], NReLi2[x] + I NImLi2[x]]]
];


(*Numerical continued dilogarithm*)
With[{NReLi2=NReLi2, NImLi2=NImLi2, NEtaArg=NEtaArg, NDiLog=NDiLog, NLn=NLn, NArg=NArg},
  NContinuedDiLog=Function[{x,xEps,y,yEps}, NDiLog[1-x y,-(xEps y+x yEps)] + NEtaArg[x,xEps,y,yEps, 2 Pi I NLn[1-x y,-(xEps y+x yEps)]]];
  NReContinuedDiLog=Function[{x,xEps,y,yEps}, NReLi2[1-x y] + NEtaArg[x,xEps,y,yEps, -2 Pi NArg[1-x y,-(xEps y+x yEps)]]];
  NImContinuedDiLog=Function[{x,xEps,y,yEps}, NImLi2[1-x y] + NEtaArg[x,xEps,y,yEps, 2 Pi Log[Abs[1-x y]]]]
];


(* ::Subsubsection::Closed:: *)
(*CompileValues for DiLog and PolyLog*)


ClearAttributes[Internal`CompileValues,{Protected,ReadProtected}];
With[{reLi2numOnRealAxes=reLi2numOnRealAxes,imLi2numOnRealAxes=Function[{x},If[x<=1.,0.,-\[Pi] Log[x]]],
	  NReLi2=NReLi2,NImLi2=NImLi2},

Internal`CompileValues[DiLog]=
  {HoldPattern[DiLog[x_,xEps_]]:>
	Internal`CompileInline[
	  Which[Re[x] > 1 && Re[xEps] >= 0, reLi2numOnRealAxes[x] + I imLi2numOnRealAxes[x],
		True, reLi2numOnRealAxes[x] - I imLi2numOnRealAxes[x]]],

  HoldPattern[DiLog[x_]]:>
	Internal`CompileInline[reLi2numOnRealAxes[x] + I imLi2numOnRealAxes[x]],

  HoldPattern[DiLog[x_,xEps_]]:>
	Internal`CompileInline[Module[{xx=x+0I,xxEps=xEps+0I},
	  Which[Im[xx] == 0 && Re[xx] > 1 && Re[xxEps] >= 0, NReLi2[xx] + I NImLi2[xx],
		True, NReLi2[xx] - I NImLi2[xx]]]],

  HoldPattern[DiLog[x_]]:>
	Internal`CompileInline[Module[{xx=x+0I},
	  NReLi2[xx] + I NImLi2[xx]]]};

Internal`CompileValues[PolyLog]=
  {HoldPattern[PolyLog[2,x_Real]]:>
	Internal`CompileInline[reLi2numOnRealAxes[x] + I imLi2numOnRealAxes[x]],

  HoldPattern[PolyLog[2,x_]]:>
	Internal`CompileInline[Module[{xx=x+0I},
	  NReLi2[xx] + I NImLi2[xx]]]}
];

SetAttributes[Internal`CompileValues,{Protected,ReadProtected}];


(* ::Subsubsection::Closed:: *)
(*Finite B function*)


(* Finite part of scalar B functions.  Implemented for r=0 and r=-1 ONLY.
   'tHooft mass set to 1.*)
NFiniteB = With[
 {NLn=Function[{arg,eps},If[eps==1,Log[arg],-Log[1/arg]]],
  x=Function[{sgn},1/2+(m0^2-m1^2)/(2s)+sgn/(2s) Sqrt[m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2]]},
 With[{
	f=Function[{r,sgn}, If[Abs[r]<10,  (1-r^(n+1))NLn[1-1/r,sgn]-Sum[r^(n-k)/(k+1),{k,0,n}],  Log[1-1/r]+Sum[r^(n-k)/(k+1),{k,n+1,n+10}]]],
	harmNumber=Function[{n},Sum[1/k,{k,1,n}]]},

  NFiniteB = Function@@Hold[{r,n,s,m0,m1},
	If[r==0,
	  Which[
		s==m0==m1==0,0,
		s==m0==0,(-1)^n/(n+1) (-Log[m1^2]+1/(n+1)),
		s==m1==0,(-1)^n/(n+1) (-Log[m0^2]+harmNumber[n+1]),
		m0==m1==0,(-1)^n/(n+1) (Log[1/-s]+1/(n+1)+harmNumber[n+1]),
		s==0&&m0==m1,(-1)^n/(n+1) (-Log[m0^2]),
		s==m1^2&&m0==0,(-1)^n/(n+1) (-Log[m1^2]+2/(n+1)),
		s==m0^2&&m1==0,(-1)^n/(n+1) (-Log[m0^2]+2 harmNumber[n+1]),
		s==0,(-1)^n/(n+1) (-Log[m1^2]-(m0^2/(m0^2-m1^2))^(n+1) Log[m0^2/m1^2]+Sum[1/(k+1) ((m0*m0)/(m0^2-m1^2))^(n-k),{k,0,n}]),
		m0==0,(-1)^n/(n+1) (-Log[m1^2]+1/(n+1)+(1-m1^2/s)^(n+1) Log[m1^2/(m1^2-s)]+Sum[1/(k+1) (1-m1^2/s)^(n-k),{k,0,n}]),
		m1==0,(-1)^n/(n+1) (-Log[m0^2]+harmNumber[n+1]+(1-(m0^2/s)^(n+1))Log[m0^2/(m0^2-s)]+Sum[1/(k+1) (m0^2/s)^(n-k),{k,0,n}]),
		True,(-1)^n/(n+1) (-Log[m0^2]-f[x[1],1]-f[x[-1],-1])
	  ],
(*When r==-1*)
	  Which[s==m0==m1==0,0,
		s==m0==0,If[n==0,2/m1^2 (-Log[m1^2]),(2(-1)^(n+1))/(m1^2 n)],
		s==m1==0,(2(-1)^n)/m0^2 (-Log[m0^2]+harmNumber[n]),
		m0==m1==0,If[n==0,-4/s (Log[1/-s]),(2(-1)^(n+1))/s (Log[1/-s]+harmNumber[n-1])],
		s==0&&m0==m1,(2(-1)^(n+1))/m0^2 1/(n+1),
		s==m1^2&&m0==0,If[n==1,-1/m1^2 (-Log[m1^2]),(2(-1)^(n+1))/m1^2 1/(n-1)],
		s==m0^2&&m1==0,If[n==0,2/m0^2,(-1)^(n+1)/m0^2 n(-Log[m0^2]+2harmNumber[n-1]-2)],
		s==0,(2(-1)^(n+1))/(m1^2-m0^2) (Sum[1/(k+1) ((m0*m0)/(m0^2-m1^2))^(n-1-k),{k,0,n-1}]+(m0^2/(m0^2-m1^2))^n Log[m1^2/m0^2]),
		m0==0,If[n==0,-2/(s-m1^2) (-Log[m1^2]+2Log[m1^2/(-s+m1^2)]),(2(-1)^(n+1))/s (Sum[1/(k+1) ((s-m1^2)/s)^(n-2-k),{k,0,n-2}]+((s-m1^2)/s)^(n-1) Log[m1^2/(-s+m1^2)])],
		m1==0,(2(-1)^n)/(s-m0^2) (-Log[1/(-s+m0^2)]+Sum[1/(k+1) (m0^2/s)^(n-1-k),{k,0,n-1}]-(m0^2/s)^n Log[m0^2/(-s+m0^2)]-harmNumber[n]),
		s==(m0+m1)^2,(2(-1)^(n+1))/(m0+m1)^2 (n Sum[1/(k+1) (m0/(m0-m1))^(n-2-k),{k,0,n-2}]+n (m0/(m0-m1))^(n-1) Log[m1/m0]-(1-m0/m1)+If[n==0,-1+m1/m0,0]),
		s==(m0-m1)^2,(2(-1)^(n+1))/(m0-m1)^2 (n Sum[1/(k+1) (m0/(m0-m1))^(n-2-k),{k,0,n-2}]+n (m0/(m0-m1))^(n-1) Log[m1/m0]-(1-m0/m1)+If[n==0,-1+m1/m0,0]),
		True,(2(-1)^(n+1))/Sqrt[m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2] (Sum[x[1]^(n-1-k)/(k+1),{k,0,n-1}]-Sum[x[-1]^(n-1-k)/(k+1),{k,0,n-1}]+x[1]^n Log[1-1/x[1]]+x[-1]^n Log[(1-1/x[-1])^-1])
	  ]
	  ]
	]
  ]
];


(* ::Subsection:: *)
(*ScalarC0*)


(* ::Subsubsection::Closed:: *)
(*Numeric evaluation*)


SetAttributes[ScalarC0,NumericFunction];


NsoftDivC0Q = 
  Compile[{{p1, _Real}, {q, _Real}, {p2, _Real}, {m0, _Real}, {m1, _Real}, {m2, _Real}},
   Module[{
     y11 = 2 m1^2,               y12 = m1^2 + m2^2 - q,  y13 = m0^2 + m1^2 - p1,
     (*y21 = m1^2 + m2^2 - q,*)  y22 = 2 m2^2,           y23 = m0^2 + m2^2 - p2,
     (*y31 = m0^2 + m1^2 - p1, y32 = m0^2 + m2^2 - p2,*) y33 = 2 m0^2},
    
	(y12==0&&((y11==0&&y13==0)||(y22==0&&y23==0)))||(y13==0&&y23==0&&y33==0)
    ]
 ];
 
NcollDivC0Q = 
  Compile[{{p1, _Real}, {q, _Real}, {p2, _Real}, {m0, _Real}, {m1, _Real}, {m2, _Real}},
   Module[{
     y11 = 2 m1^2,           y12 = m1^2 + m2^2 - q,  y13 = m0^2 + m1^2 - p1,
     (*y21 = m1^2 + m2^2 - q,*)  y22 = 2 m2^2,           y23 = m0^2 + m2^2 - p2,
     (*y31 = m0^2 + m1^2 - p1, y32 = m0^2 + m2^2 - p2,*) y33 = 2 m0^2},
    
	  (y11==0&&((y12==0&&((y13==0&&y23==0)||y22==0))||(y13==0&&y33==0)))||(y23==0&&((y12==0&&y13==0&&(y22==0||y33==0))||(y22==0&&y33==0)))
    
    ]
];
NirDivC0Q = Compile[{{p1, _Real}, {q, _Real}, {p2, _Real}, {m0, _Real}, {m1, _Real}, {m2, _Real}},
   Module[{
     y11 = 2 m1^2,           y12 = m1^2 + m2^2 - q,  y13 = m0^2 + m1^2 - p1,
     (*y21 = m1^2 + m2^2 - q,*)  y22 = 2 m2^2,           y23 = m0^2 + m2^2 - p2,
     (*y31 = m0^2 + m1^2 - p1, y32 = m0^2 + m2^2 - p2,*) y33 = 2 m0^2},
    
    (y11==0||y22==0||y33==0)&&(y11==0||y23==0)&&(y12==0||y13==0||y23==0)&&(y12==0||y33==0)&&(y13==0||y22==0)
    ]
];


With[{NFiniteB=NFiniteB,
	  \[Lambda]ppq=p1^2-2 p1 p2+p2^2-2 p1 q-2 p2 q+q^2, \[Lambda]p01=m0^4-2 m0^2 m1^2+m1^4-2 m0^2 p1-2 m1^2 p1+p1^2,
	  \[Lambda]q12=m1^4-2 m1^2 m2^2+m2^4-2 m1^2 q-2 m2^2 q+q^2, \[Lambda]p02=m0^4-2 m0^2 m2^2+m2^4-2 m0^2 p2-2 m2^2 p2+p2^2,
	  tInv=Function[{s,\[Mu]1,\[Mu]2,\[Mu]3,\[Mu]4,sign},1/(2s) (-s^2+s(\[Mu]1+\[Mu]2+\[Mu]3+\[Mu]4)-(\[Mu]1-\[Mu]2)(\[Mu]3-\[Mu]4)+sign Sqrt[s^2-2 s \[Mu]1+\[Mu]1^2-2 s \[Mu]2-2 \[Mu]1 \[Mu]2+\[Mu]2^2] Sqrt[s^2-2 s \[Mu]3+\[Mu]3^2-2 s \[Mu]4-2 \[Mu]3 \[Mu]4+\[Mu]4^2])],
	  (*Argument of the twelve dilogarithms for most general case*)
	  dilogArg = Function[{pa,pb,pc,ma,mb,mc,sgn,term},
		Which[
		(*Channel momentum non-vanishing*)
			pa!=0,
			  1+(Sqrt[pa^2-2 pa pb+pb^2-2 pa pc-2 pb pc+pc^2](term pa-mb^2+mc^2-sgn Sqrt[mb^4-2 mb^2 mc^2+mc^4-2 mb^2 pa-2 mc^2 pa+pa^2]))/(-pa^2+pa (mb^2+mc^2+pb+pc)+(mb^2-mc^2) (pb-pc)+sgn Sqrt[mb^4+(mc^2-pa)^2-2 mb^2 (mc^2+pa)]Sqrt[pa^2+(pb-pc)^2-2 pa (pb+pc)]-2 pa ma^2),
			(*Channel momentum vanishing*)
			mc==mb||sgn==-1||Re[pb]<Re[pc],
			  0,
			True,
			  Which[
				term==1,  ((mb^2-mc^2) (pb (mb^2+pb)-(mc^2+pb) pc+ma^2 (-pb+pc)))/(-ma^2 (mb^2-mc^2) (pb-pc)+(mb^2-mc^2+pb-pc) (mb^2 pb-mc^2 pc)),
				True,  ((mb^2-mc^2) (mb^2 pb+ma^2 (-pb+pc)-pc (mc^2-pb+pc)))/(-ma^2 (mb^2-mc^2) (pb-pc)+(mb^2-mc^2+pb-pc) (mb^2 pb-mc^2 pc))]
			 ]]},

  With[{body = Which[
		(*All external invariants vanishing*)
		p1==p2==q==0,
		If[m0!=m1!=m2, -(1/((m0^2-m1^2)(m0^2-m2^2)(m1^2-m2^2))) *
		  ( If[m0!=0&&m1!=0, m0^2 m1^2 Log[m0^2/m1^2],0] + 
  		  If[m0!=0&&m2!=0, m0^2 m2^2 Log[m2^2/m0^2],0] +
  		  If[m1!=0&&m2!=0, m1^2 m2^2 Log[m1^2/m2^2],0] ) ,
  		 If[m2!=m0&&m2!=m1, 1/(m0^2-m2^2)*(If[m2!=0, m2^2/(-m0^2+m2^2) Log[m2^2/m0^2], 0] - 1),
  		 	If[m1!=m0&&m1!=m2,1/(m0^2-m1^2)*(If[m1!=0,m1^2/(-m0^2+m1^2) Log[m1^2/m0^2], 0] - 1),
  		 		If[m0!=m1&&m0!=m2,1/(m2^2-m0^2)*(If[m0!=0,m0^2/(-m2^2+m0^2) Log[m0^2/m2^2], 0] - 1), -(1/(2m0^2))]
  		 	]
  		 ]
  	  ],

	    (*Vanishing det(Z) but not det(X)*)
	    \[Lambda]ppq==0,
	    Module[{adjX01=p2(p1-m1^2+m0^2)+1/2 (q-p1-p2)(p2-m2^2+m0^2),adjX02=1/2 (q-p1-p2)(p1-m1^2+m0^2)+p1(p2-m2^2+m0^2)},
		  Which[
			adjX01==0 && adjX02==0,
			If[p2!=0,
				1/2 (NFiniteB[-1,0,p2,m0,m2]+((p1+p2-q)/(2 p2)) NFiniteB[-1,1,p1,m1,m0]+(1-(p1+p2-q)/(2 p2)) NFiniteB[-1,1,q,m1,m2]),
				-(1/2) NFiniteB[-1,1,q,m1,m0]],
			Abs[adjX01] > Abs[adjX02],
			1/adjX01 (p2(NFiniteB[0,0,p2,m0,m2]-NFiniteB[0,0,q,m2,m1])+(1/2)*(q-p1-p2)(NFiniteB[0,0,p1,m0,m1]-NFiniteB[0,0,q,m2,m1])),
			True,
			1/adjX02 (1/2 (q-p1-p2)(NFiniteB[0,0,p2,m0,m2]-NFiniteB[0,0,q,m2,m1])+p1(NFiniteB[0,0,p1,m0,m1]-NFiniteB[0,0,q,m2,m1]))
		  ]
		],

	    (*Most general case*)
		True,

		(*REAL PART of scalarC0 in most general case*)
		If[(*Physical region*)
			Re[\[Lambda]ppq]>0,
			1/Sqrt[\[Lambda]ppq]*
			(If[Re[\[Lambda]p01]<=0,
				2(NReLi2[dilogArg[p1,p2,q,m2,m1,m0,1,1]]-NReLi2[dilogArg[p1,p2,q,m2,m1,m0,1,-1]]),
				NReLi2[dilogArg[p1,p2,q,m2,m1,m0,1,1]]-NReLi2[dilogArg[p1,p2,q,m2,m1,m0,1,-1]]+NReLi2[dilogArg[p1,p2,q,m2,m1,m0,-1,1]]-NReLi2[dilogArg[p1,p2,q,m2,m1,m0,-1,-1]]]+
			 If[Re[\[Lambda]q12]<=0,
				2(NReLi2[dilogArg[q,p1,p2,m0,m2,m1,1,1]]-NReLi2[dilogArg[q,p1,p2,m0,m2,m1,1,-1]]),
				NReLi2[dilogArg[q,p1,p2,m0,m2,m1,1,1]]-NReLi2[dilogArg[q,p1,p2,m0,m2,m1,1,-1]]+NReLi2[dilogArg[q,p1,p2,m0,m2,m1,-1,1]]-NReLi2[dilogArg[q,p1,p2,m0,m2,m1,-1,-1]]]+
			 If[Re[\[Lambda]p02]<=0,
				2(NReLi2[dilogArg[p2,q,p1,m1,m0,m2,1,1]]-NReLi2[dilogArg[p2,q,p1,m1,m0,m2,1,-1]]),
				NReLi2[dilogArg[p2,q,p1,m1,m0,m2,1,1]]-NReLi2[dilogArg[p2,q,p1,m1,m0,m2,1,-1]]+NReLi2[dilogArg[p2,q,p1,m1,m0,m2,-1,1]]-NReLi2[dilogArg[p2,q,p1,m1,m0,m2,-1,-1]]])


			,(*Gap region \[Lambda]ppq<0*)
			Module[{
			z1p=If[Re[\[Lambda]p01]>0, Re[1/2 ((1-(m0^2-m1^2)/p1)+1/p1 Sqrt[\[Lambda]p01])], 1/2 ((1-(m0^2-m1^2)/p1)+1/p1 Sqrt[\[Lambda]p01])],
			z1m=If[Re[\[Lambda]p01]>0, Re[1/2 ((1-(m0^2-m1^2)/p1)-1/p1 Sqrt[\[Lambda]p01])], 1/2 ((1-(m0^2-m1^2)/p1)-1/p1 Sqrt[\[Lambda]p01])],
			z2p=If[Re[\[Lambda]p02]>0, Re[1/2 ((1+(m0^2-m2^2)/p2)+1/p2 Sqrt[\[Lambda]p02])], 1/2 ((1+(m0^2-m2^2)/p2)+1/p2 Sqrt[\[Lambda]p02])],
			z2m=If[Re[\[Lambda]p02]>0, Re[1/2 ((1+(m0^2-m2^2)/p2)-1/p2 Sqrt[\[Lambda]p02])], 1/2 ((1+(m0^2-m2^2)/p2)-1/p2 Sqrt[\[Lambda]p02])],
			z12p=If[Re[\[Lambda]q12]>0, Re[1/2 ((1+(m2^2-m1^2)/q)+1/q Sqrt[\[Lambda]q12])], 1/2 ((1+(m2^2-m1^2)/q)+1/q Sqrt[\[Lambda]q12])],
			z12m=If[Re[\[Lambda]q12]>0, Re[1/2 ((1+(m2^2-m1^2)/q)-1/q Sqrt[\[Lambda]q12])], 1/2 ((1+(m2^2-m1^2)/q)-1/q Sqrt[\[Lambda]q12])],
			z1=1/2 ((1+(m1^2-m0^2)/p1)-(-p1^2+p1(p2+q+m0^2+m1^2)-(p2-q)(m0^2-m1^2)-2m2^2 p1)/(p1 Sqrt[\[Lambda]ppq])),
			z2=1/2 ((1+(m0^2-m2^2)/p2)-(-p2^2+p2(q+p1+m2^2+m0^2)-(q-p1)(m2^2-m0^2)-2m1^2 p2)/(p2 Sqrt[\[Lambda]ppq])),
			z12=1/2 ((1+(m2^2-m1^2)/q)-(-q^2+q(p1+p2+m1^2+m2^2)-(p1-p2)(m1^2-m2^2)-2m0^2 q)/(q Sqrt[\[Lambda]ppq]))},

			Re[1/Sqrt[-\[Lambda]ppq]*(
				(NImLi2[dilogArg[p1,p2,q,m2,m1,m0,1,1]]-NImLi2[dilogArg[p1,p2,q,m2,m1,m0,1,-1]]+
				   NEtaArg[1-z1p,-1,1/(z1-z1p),-I/(z1-z1p)^2, 2 Pi Log[Abs[(-1+z1)/(z1-z1p)]]]-NEtaArg[-z1p,-1,1/(z1-z1p),-I/(z1-z1p)^2,2 Pi Log[Abs[z1/(z1 - z1p)]]]+
				   NImLi2[dilogArg[p1,p2,q,m2,m1,m0,-1,1]]-NImLi2[dilogArg[p1,p2,q,m2,m1,m0,-1,-1]]+
				   NEtaArg[1-z1m,1,1/(z1-z1m),I/(z1-z1m)^2, 2 Pi Log[Abs[(-1+z1)/(z1-z1m)]]]-NEtaArg[-z1m,1,1/(z1-z1m),+I/(z1-z1m)^2,2 Pi Log[Abs[z1/(z1 - z1m)]]]-
				   (-If[Im[z1-z1p]<0 && Im[z1-z1m]<0, 2 Pi Log[Abs[(1-z1)/-z1]], 0]))+
				(NImLi2[dilogArg[p2,q,p1,m1,m0,m2,1,1]]-NImLi2[dilogArg[p2,q,p1,m1,m0,m2,1,-1]]+
				  NEtaArg[1-z2p,-1,1/(z2-z2p),-I/(z2-z2p)^2, 2 Pi Log[Abs[(-1+z2)/(z2-z2p)]]]-NEtaArg[-z2p,-1,1/(z2-z2p),-I/(z2-z2p)^2, 2 Pi Log[Abs[z2/(z2 - z2p)]]]+
				  NImLi2[dilogArg[p2,q,p1,m1,m0,m2,-1,1]]-NImLi2[dilogArg[p2,q,p1,m1,m0,m2,-1,-1]]+
				  NEtaArg[1-z2m,1,1/(z2-z2m),I/(z2-z2m)^2, 2 Pi Log[Abs[(-1+z2)/(z2-z2m)]]]-NEtaArg[-z2m,1,1/(z2-z2m),I/(z2-z2m)^2,2 Pi Log[Abs[z2/(z2 - z2m)]]]-
				  (-If[Im[z2-z2p]<0 && Im[z2-z2m]<0, 2 Pi Log[Abs[(1-z2)/-z2]], 0]))+
				(NImLi2[dilogArg[q,p1,p2,m0,m2,m1,1,1]]-NImLi2[dilogArg[q,p1,p2,m0,m2,m1,1,-1]]+
				  NEtaArg[1-z12p,-1,1/(z12-z12p),-I/(z12-z12p)^2, 2 Pi Log[Abs[(-1+z12)/(z12-z12p)]]]-NEtaArg[-z12p,-1,1/(z12-z12p),-I/(z12-z12p)^2, 2 Pi Log[Abs[z12/(z12 - z12p)]]]+
				  NImLi2[dilogArg[q,p1,p2,m0,m2,m1,-1,1]]-NImLi2[dilogArg[q,p1,p2,m0,m2,m1,-1,-1]]+
				  NEtaArg[1-z12m,1,1/(z12-z12m),I/(z12-z12m)^2, 2 Pi Log[Abs[(-1+z12)/(z12-z12m)]]]-NEtaArg[-z12m,1-I,1/(z12-z12m),I/(z12-z12m)^2, 2 Pi Log[Abs[z12/(z12 - z12m)]]]-
				  (-If[Im[z12-z12p]<0 && Im[z12-z12m]<0, 2 Pi Log[Abs[(1-z12)/-z12]], 0])))]]
			] +
		  (*IMAGINARY PART of scalarC0 in most general case*)
			I * Module[{logArgument=
							If[Re[p1]>=Re[(m0+m1)^2],(tInv[p1,p2,q,m0^2,m1^2,1]-m2^2)/(tInv[p1,p2,q,m0^2,m1^2,-1]-m2^2),1]*
							If[Re[p2]>=Re[(m0+m2)^2],(tInv[p2,q,p1,m2^2,m0^2,1]-m1^2)/(tInv[p2,q,p1,m2^2,m0^2,-1]-m1^2),1]*
							If[Re[q]>=Re[(m1+m2)^2],(tInv[q,p1,p2,m1^2,m2^2,1]-m0^2)/(tInv[q,p1,p2,m1^2,m2^2,-1]-m0^2),1]
					  },

				Re[\[Pi]/Sqrt[\[Lambda]ppq] (Log[logArgument] + If[Im[logArgument]>0&&!(m0==0&&m1==0&&m2==0),-2\[Pi] I ,0]) + 
				If[(*Defines the leading Landau singularity surface*)
					Re[-2 m0^2 m1^2 p1+2 m0^2 m2^2 p1+2 m1^2 m2^2 p1-2 m2^4 p1-2 m2^2 p1^2+2 m0^2 m1^2 p2-2 m1^4 p2-2 m0^2 m2^2 p2+2 m1^2 m2^2 p2+2 m1^2 p1 p2+2 m2^2 p1 p2-2 m1^2 p2^2-2 m0^4 q+2 m0^2 m1^2 q+2 m0^2 m2^2 q-2 m1^2 m2^2 q+2 m0^2 p1 q+2 m2^2 p1 q+2 m0^2 p2 q+2 m1^2 p2 q-2 p1 p2 q-2 m0^2 q^2] <= 0 && 
					(*Pick out part that is wedged against normal threshold planes*)
					Re[p1]<=Re[(m0+m1)^2] && Re[p2]<=Re[(m0+m2)^2] && Re[q]<=Re[(m1+m2)^2] && Re[m2 p1+m1 p2+m0 q]>=Re[(m0+m1) (m0+m2) (m1+m2)],
					 (-2 \[Pi]^2)/Sqrt[-\[Lambda]ppq] , 
					0
					]
				]

			]
	    ]
	},

	 
	  With@@Hold[{NReLi2=Re[PolyLog[2,#]]&, NImLi2=Im[PolyLog[2,#]]&, NEtaArg=X`Private`NEtaArg},
		  NScalarC0AP = Function@@Hold[{p1,p2,q,m2,m1,m0},body]
	  ];

	  With@@Hold[{NReLi2=X`Private`NReLi2, NImLi2=X`Private`NImLi2, NEtaArg=X`Private`NEtaArg},
		  NScalarC0MP := NScalarC0MP = Compile[{{p1,_Complex},{p2,_Complex},{q,_Complex},{m2,_Complex},{m1,_Complex},{m0,_Complex}},body]
	  ];
  ]
];


(*Machine precision evaluation, using compiled code*)
expr : ScalarC0[p1_?Internal`RealValuedNumericQ, q_?Internal`RealValuedNumericQ, p2_?Internal`RealValuedNumericQ, 
   m0_?NonNegative, m1_?NonNegative, m2_?NonNegative] /; Precision[Hold[expr]]===MachinePrecision :=
  If[NirDivC0Q[p1,q,p2,m0,m1,m2],
   Switch[{NsoftDivC0Q[p1,q,p2,m0,m1,m2], NcollDivC0Q[p1,q,p2,m0,m1,m2]},
    {True, False},
    Message[ScalarC0::irdiv, "Soft"]; ComplexInfinity,
    {False, True},
    Message[ScalarC0::irdiv, "Collinear"]; ComplexInfinity,
    _,
    Message[ScalarC0::irdiv, "Soft and collinear"]; ComplexInfinity
    ],
    
   (*No IR divergence*)
   NScalarC0MP[q,p2,p1,m0,m1,m2] (*Order of arguments is still in V1 form*)
  ];

(*Arbitrary precision evaluation, using native Mathematica functions*)
expr : ScalarC0[p1_?Internal`RealValuedNumericQ, q_?Internal`RealValuedNumericQ, p2_?Internal`RealValuedNumericQ, 
   m0_?NonNegative, m1_?NonNegative, m2_?NonNegative] /; Precision[Hold[expr]]<\[Infinity] :=
  If[NirDivC0Q[p1,q,p2,m0,m1,m2],
   Switch[{NsoftDivC0Q[p1,q,p2,m0,m1,m2], NcollDivC0Q[p1,q,p2,m0,m1,m2]},
    {True, False},
    Message[ScalarC0::irdiv, "Soft"]; ComplexInfinity,
    {False, True},
    Message[ScalarC0::irdiv, "Collinear"]; ComplexInfinity,
    _,
    Message[ScalarC0::irdiv, "Soft and collinear"]; ComplexInfinity
    ],
    
   (*No IR divergence*)
   X`Internal`ToTargetPrecision[NScalarC0AP,{q,p2,p1,m0,m1,m2},3]
   (*NScalarC0AP[q,p2,p1,m0,m1,m2]*) (*Order of arguments is still in V1 form*)
  ];


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


softDivC0Q=Function[{p1,q,p2,m0,m1,m2},
	With[{
     y11 = 2 m1^2,           y12 = m1^2 + m2^2 - q,  y13 = m0^2 + m1^2 - p1,
     (*y21 = m1^2 + m2^2 - q,*)  y22 = 2 m2^2,           y23 = m0^2 + m2^2 - p2,
     (*y31 = m0^2 + m1^2 - p1, y32 = m0^2 + m2^2 - p2,*) y33 = 2 m0^2},
	(PossibleZeroQ[y12]&&((PossibleZeroQ[y11]&&PossibleZeroQ[y13])||(PossibleZeroQ[y22]&&PossibleZeroQ[y23])))||(PossibleZeroQ[y13]&&PossibleZeroQ[y23]&&PossibleZeroQ[y33])
	]
];

collDivC0Q=Function[{p1,q,p2,m0,m1,m2},
	With[{
     y11 = 2 m1^2,           y12 = m1^2 + m2^2 - q,  y13 = m0^2 + m1^2 - p1,
     (*y21 = m1^2 + m2^2 - q,*)  y22 = 2 m2^2,           y23 = m0^2 + m2^2 - p2,
     (*y31 = m0^2 + m1^2 - p1, y32 = m0^2 + m2^2 - p2,*) y33 = 2 m0^2},
	(PossibleZeroQ[y11]&&((PossibleZeroQ[y12]&&((PossibleZeroQ[y13]&&PossibleZeroQ[y23])||PossibleZeroQ[y22]))||(PossibleZeroQ[y13]&&PossibleZeroQ[y33])))||(PossibleZeroQ[y23]&&((PossibleZeroQ[y12]&&PossibleZeroQ[y13]&&(PossibleZeroQ[y22]||PossibleZeroQ[y33]))||(PossibleZeroQ[y22]&&PossibleZeroQ[y33])))
	]
];

irDivC0Q=Function[{p1,q,p2,m0,m1,m2},
	With[{
     y11 = 2 m1^2,           y12 = m1^2 + m2^2 - q,  y13 = m0^2 + m1^2 - p1,
     (*y21 = m1^2 + m2^2 - q,*)  y22 = 2 m2^2,           y23 = m0^2 + m2^2 - p2,
     (*y31 = m0^2 + m1^2 - p1, y32 = m0^2 + m2^2 - p2,*) y33 = 2 m0^2},
	(PossibleZeroQ[m0] || PossibleZeroQ[m1] || PossibleZeroQ[m2]) && ((PossibleZeroQ[y11]||PossibleZeroQ[y22]||PossibleZeroQ[y33])&&(PossibleZeroQ[y11]||PossibleZeroQ[y23])&&(PossibleZeroQ[y12]||PossibleZeroQ[y13]||PossibleZeroQ[y23])&&(PossibleZeroQ[y12]||PossibleZeroQ[y33])&&(PossibleZeroQ[y13]||PossibleZeroQ[y22]))
	]
];

(*Check for IR divergences*)
ScalarC0[p1_,q_,p2_,m0_,m1_,m2_] /; irDivC0Q[p1,q,p2,m0,m1,m2] := 
  Switch[{softDivC0Q[p1,q,p2,m0,m1,m2], collDivC0Q[p1,q,p2,m0,m1,m2]},
	{True, False},
    Message[ScalarC0::irdiv, "Soft"]; ComplexInfinity,
    {False, True},
    Message[ScalarC0::irdiv, "Collinear"]; ComplexInfinity,
    _,
    Message[ScalarC0::irdiv, "Soft and collinear"]; ComplexInfinity
  ];



(*ScalarC0 as a symbolic function, replace with analytic formula for vanishing external invariants*)

ScalarC0[0,0,0,m0_,m1_,m2_]:=
	Switch[
		Count[{m0,m1,m2},0],
		0,
		Switch[
				SortBy[Tally[{m0,m1,m2}],Last],
				{{_,1},{_,1},{_,1}},
				(m1^2 olog[m0^2,m1^2])/((-m0^2+m1^2) (m1^2-m2^2))+(m2^2 olog[m0^2,m2^2])/((-m0^2+m2^2) (-m1^2+m2^2)),
				{{_,1},{_,2}},
				SortBy[Tally[{m0,m1,m2}],Last]/.{{a_,1},{b_,2}}:>1/(a^2-b^2)-(a^2 olog[a^2,b^2])/(a^2-b^2)^2,
				_,
				-(1/(2 m0^2))],
		1,
		Switch[
				DeleteCases[SortBy[Tally[{m0,m1,m2}],Last],{0,1}],
				{{_,1},{_,1}},
				DeleteCases[SortBy[Tally[{m0,m1,m2}],Last],{0,1}]/.{{a_,1},{b_,1}}:>olog[a^2,b^2]/(-a^2+b^2),
				_,
				DeleteCases[SortBy[Tally[{m0,m1,m2}],Last],{0,1}]/.{{a_,2}}:>-(1/a^2)],
		_,
		$Failed (*Infrared divergent; should already be caught by irDivC0Q*)
	];

ScalarC0[p1_,p2_,q_,m1_,m0_,m2_] /; !OrderedQ[{{p1,m2},{p2,m1},{q,m0}}] :=
	ScalarC0[#1,#3,#5,#4,#6,#2] &@@ Flatten[Sort[{{p1,m2},{p2,m1},{q,m0}}]];


LHS_ScalarC0:=RuleCondition[X`Internal`CheckArgumentCount[LHS,6,6];Fail];


(* ::Subsection:: *)
(*ScalarC0IR6*)


(* ::Subsubsection::Closed:: *)
(*Numeric evaluation*)


SetAttributes[ScalarC0IR6,NumericFunction];

With[{body := 
  Module[{lambda=m0^4-2 m0^2 m2^2+m2^4-2 m0^2 s-2 m2^2 s+s^2,
		  zp=1/2 (1+(m0^2-m2^2)/s+1/s Sqrt[m0^4-2 m0^2 m2^2+m2^4-2 m0^2 s-2 m2^2 s+s^2]),
		  zm=1/2 (1+(m0^2-m2^2)/s-1/s Sqrt[m0^4-2 m0^2 m2^2+m2^4-2 m0^2 s-2 m2^2 s+s^2])},
	Which[
	  (*Vanishes at s=0, by definition*)
	  s==0, 0,
	  (*Pseudothreshold*)
	  s==(m0-m2)^2, -(1/(m0 m2))+((m0+m2) Log[m2^2/m0^2])/(4 m2^2 m0-4 m2 m0^2),
	  (*Above normal threshold*)
	  Re[(m0+m2)^2]<Re[s],( Log[m0 m2/s]/Sqrt[lambda] 1/2 Log[(zm (-1+zp))/((-1+zm) zp)])-1/(2Sqrt[lambda]) 1/2 (2 \[Pi]^2-Log[1-zm]^2+Log[zm]^2-2 Log[1-zm] Log[1-zp]+Log[1-zp]^2+2 Log[zm] Log[zp]-Log[zp]^2+4 Log[-1+1/zp] Log[-zm+zp]-4 NReLi2[(-1+zp)/(-zm+zp)]+4 NReLi2[-(zp/(zm-zp))]) + I*Pi/Sqrt[lambda] Log[(s m0 m2)/lambda],
	  (*Below pseudothreshold*)
	  Re[s]<Re[(m0-m2)^2], Log[m0 m2/Abs[s]]/Sqrt[lambda] 1/2 Log[(zm (-1+zp))/((-1+zm) zp)]-1/(2Sqrt[lambda]) 1/2 (Re[-Log[-1+zm]^2+Log[zm]^2-2 Log[-1+zm] Log[1-zp]+Log[1-zp]^2+2 Log[zm] Log[-zp]-Log[-zp]^2+4 Log[zm-zp] (Log[-1+zp]-Log[zp])]+4 NReLi2[-(zp/(zm-zp))]-4 NReLi2[(-1+zp)/(-zm+zp)]),
	  (*Unphysical region (gap)*)
	  True,( Log[m0 m2/s]/Sqrt[-lambda] 1/2 (Arg[-(zm/(1-zm))]-Arg[-(zp/(1-zp))]))-1/(2Sqrt[-lambda]) (2 NImLi2[-(zp/(zm-zp))]-2 NImLi2[(-1+zp)/(-zm+zp)]+1/2 \[Pi] Log[m2^2/m0^2]+Arg[-zm] Log[m0^2/s]-Arg[1-zm] Log[m2^2/s]+Arg[(-1+zp)/zp] Log[4 Im[zp]^2])
	]
  ]},

  With@@Hold[{NReLi2=Re[PolyLog[2,#]]&,NImLi2=Im[PolyLog[2,#]]&}, 
	NScalarC0IR6AP = Function@@Hold[{s,m0,m2}, body]];

  With@@Hold[{NReLi2=X`Private`NReLi2, NImLi2=X`Private`NImLi2},
	NScalarC0IR6MP := NScalarC0IR6MP = Compile[{{s,_Complex},{m0,_Complex},{m2,_Complex}}, body]]	
];


(*Machine precision evaluation, using compiled code*)
expr : ScalarC0IR6[s_?Internal`RealValuedNumericQ,m0_?NonNegative,m2_?NonNegative] /; Precision[Hold[expr]]===MachinePrecision := 
	Which[
	  s==(m0+m2)^2, If[m0==0 || m2==0, Message[ScalarC0IR6::irdiv, "Threshold and collinear"], Message[ScalarC0IR6::irdiv, "Threshold"]]; ComplexInfinity,
	  m0==0 || m2==0, Message[ScalarC0IR6::irdiv, "Collinear"]; ComplexInfinity,
	  True, NScalarC0IR6MP[s,m0,m2]
	];

(*Arbitrary precision evaluation, using native Mathematica functions*)
expr : ScalarC0IR6[s_?Internal`RealValuedNumericQ,m0_?NonNegative,m2_?NonNegative] /; Precision[Hold[expr]]<\[Infinity] := 
	Which[
	  s==(m0+m2)^2, If[m0==0 || m2==0, Message[ScalarC0IR6::irdiv, "Threshold and collinear"], Message[ScalarC0IR6::irdiv, "Threshold"]]; ComplexInfinity,
	  m0==0 || m2==0, Message[ScalarC0IR6::irdiv, "Collinear"]; ComplexInfinity,
	  True, (*NScalarC0IR6AP[s,m0,m2]*)X`Internal`ToTargetPrecision[NScalarC0IR6AP,{s,m0,m2},3]
	];


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


ScalarC0IR6[s_,m0_,m1_] /; PossibleZeroQ[s-(m0+m1)^2] := If[PossibleZeroQ[m0] || PossibleZeroQ[m1], Message[ScalarC0IR6::irdiv, "Threshold and collinear"]; ComplexInfinity, Message[ScalarC0IR6::irdiv, "Threshold"]; ComplexInfinity];
ScalarC0IR6[_,0,_] := (Message[ScalarC0IR6::irdiv, "Collinear"]; ComplexInfinity);
ScalarC0IR6[_,_,0] := (Message[ScalarC0IR6::irdiv, "Collinear"]; ComplexInfinity);


ScalarC0IR6[0,m0_,m1_]=0;
(*ScalarC0IR6[s_,m0_,m1_] /; PossibleZeroQ[s-(m0-m1)^2] :=-(1/(m0 m1))+((m0+m1) olog[m0^2,m1^2])/(4 m0^2 m1-4 m0 m1^2);*)

ScalarC0IR6[s_,m0_,m1_]/;!OrderedQ[{m0,m1}]:=ScalarC0IR6[s,m1,m0];

LHS_ScalarC0IR6:=RuleCondition[X`Internal`CheckArgumentCount[LHS,3,3];Fail];


(* ::Subsubsection::Closed:: *)
(*Derivatives*)


Derivative[n1_Integer?Positive,n2_Integer,n3_Integer][ScalarC0IR6] ^:= Derivative[n1-1,n2,n3][1/Kallen\[Lambda][#1,#2^2,#3^2] ((Log[#2^2/#3^2] (-#2^2+#3^2))/(2  #1)+ScalarC0IR6[#1,#2,#3] (-#1+#2^2+#3^2)+(DiscB[#1,#2,#3] (-#1^2+(#2^2-#3^2)^2))/Kallen\[Lambda][#1,#2^2,#3^2])&];
Derivative[n1_Integer,n2_Integer?Positive,n3_Integer][ScalarC0IR6] ^:= Derivative[n1,n2-1,n3][1/(Kallen\[Lambda][#1,#2^2,#3^2] #2)(-2 ScalarC0IR6[#1,#2,#3] #2^2 (-#1+#2^2-#3^2)+1/2 Log[#2^2/#3^2] (-#1+3 #2^2+#3^2)+(DiscB[#1,#2,#3] #1 (-3 #2^4+(-#1+#3^2)^2+2 #2^2 (#1+#3^2)))/Kallen\[Lambda][#1,#2^2,#3^2])&];
Derivative[n1_Integer,n2_Integer,n3_Integer?Positive][ScalarC0IR6] ^:= Derivative[n1,n2,n3-1][1/(Kallen\[Lambda][#1,#2^2,#3^2] #3)(-2 ScalarC0IR6[#1,#2,#3] #3^2 (-#1-#2^2+#3^2)+1/2 Log[#3^2/#2^2] (-#1+#2^2+3 #3^2)+(DiscB[#1,#2,#3] #1 ((-#1+#2^2)^2+2 (#1+#2^2) #3^2-3 #3^4))/Kallen\[Lambda][#1,#2^2,#3^2])&];


(* ::Subsection::Closed:: *)
(*C0Expand*)


refineC0[p1_,q_,p2_,m0_,m1_,m2_] :=
  Module[{
    f={p1-m1^2+m0^2,p2-m2^2+m0^2},
    gramZ={{p1, -(q-p1-p2)/2},{-(q-p1-p2)/2, p2}},
    adjZ={{p2, (q-p1-p2)/2},{(q-p1-p2)/2, p1}},
	Xij,
    adjX0,adjXij,
    i,j,k,m,n},

  Xij={{m0^2,f[[1]]/2,f[[2]]/2},{f[[1]]/2,p1,-(q-p1-p2)/2},{f[[2]]/2,-(q-p1-p2)/2,p2}};
  adjX0=Table[Sum[adjZ[[j,k]]f[[k]],{k,1,2}],{j,1,2}]; (*up to a constant: -1*)
  adjXij=Table[4m0^2 adjZ[[i,j]]+Sum[(KroneckerDelta[i,m]KroneckerDelta[n,j]-KroneckerDelta[i,j]KroneckerDelta[n,m])f[[n]] f[[m]],{n,1,2},{m,1,2}],{i,1,2},{j,1,2}];
  
  Which[
    X`Internal`PossibleAllZeroQ[gramZ] && X`Internal`PossibleAllZeroQ[f] && (m0=!=0),
    (*Print["Case 6: gramZ & f vanishing."];*)
      ReplaceRepeated[passVeltC[0,0,0,p1,q,p2,m0,m1,m2],refineRulesCcase6],

    X`Internal`PossibleAllZeroQ[gramZ] && !(X`Internal`PossibleAllZeroQ[f]),
    (*Print["Case 5: gramZ vanishing but f non-vanishing."];*)
      With[{siga=Which[!PossibleZeroQ[f[[1]]],1,True,2]},
        ReplaceRepeated[passVeltC[0,0,0,p1,q,p2,m0,m1,m2],{refineRulesCcase5a[[siga]],refineRulesCcase5b}]
      ],
  
    PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0],
    (*Print["Case 4: detZ and adjX0 are zero"];*)
      Replace[passVeltC[0,0,0,p1,q,p2,m0,m1,m2],refineRulesCcase4],
    
    PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3: detZ=0"];*)
      With[{
        siga=Which[!PossibleZeroQ[adjZ[[1,1]]],{1,1}, !PossibleZeroQ[adjZ[[2,2]]],{2,2},True,{1,2}],
        sigb=Which[!PossibleZeroQ[adjX0[[1]]],1,True,2]},
        (*Print["siga=",siga,"  sigb=",sigb, "adjZ = ", adjZ];*)
        ReplaceRepeated[passVeltC[0,0,0,p1,q,p2,m0,m1,m2],{refineRulesCcase3a[[Sequence@@siga]],refineRulesCcase3b[[sigb]]}] 
      ],

    !(PossibleZeroQ[Det[gramZ]]),
    (*Print["Case 1: detZ nonZero; r=", r];*)
    If[Head[analC0[{p1,m2},{p2,m1},{q,m0}]]===analC0, analC0force[{p1,m2},{p2,m1},{q,m0}], analC0[{p1,m2},{p2,m1},{q,m0}]],

    True,
	ScalarC0[p1,q,p2,m0,m1,m2]

  ]
];


C0Expand[expr_]:=
  expr /.
	{ScalarC0[p1_,q_,p2_,m0_,m1_,m2_] /; FreeQ[{p1,q,p2,m0,m1,m2}, _Complex]:>
	  Module[{result, intMass = Variables[{m0,m1,m2}]},
		result = Coefficient[refineC0[p1,q,p2,m0,m1,m2],Eps,0];
		If[intMass=!={}, result = result/.Mu->First[intMass]];

		expressionOptimizer[result,intMass,{1},"FunctionExpand"]
	  ],

	 ScalarC0IR6[s_,m0_,m2_] /; FreeQ[{s,m0,m2}, _Complex] :> pvC0IR6force[s,m0,m2]
	};


(* ::Subsection:: *)
(*ScalarD0*)


(* ::Subsubsection::Closed:: *)
(*Numeric evaluation*)


SetAttributes[ScalarD0,NumericFunction];


With[{NEtaArg=X`Private`NEtaArg, NEtaTildeArg=X`Private`NEtaTildeArg,NLn=X`Private`NLn,NArg=X`Private`NArg,
	  fQ=Function[{y1,y2,y3,y4,r13,k12,k23,k34,k14},(1/r13-r13)y1+(k23-r13 k12)y2+(1-r13^2)y3+(k34-r13 k14)y4],
	  fQbar=Function[{y1,y2,y3,y4,r24,k12,k23,k34,k14},(k12-k14 r24)y1+(1-r24^2)y2+(k23-k34 r24)y3+(1/r24-r24)y4],
	  fP=Function[{k,y},k y+1+y^2],

	  (*The following two are needed for the imaginary part*)
	  kappa=Function[{sa,sb,sc,sd,sab,sbc,ma,mb,mc,md},ma^4 (sb+sbc-sc)+mb^4 (sab-sc+sd)+sa (md^2 (sa-sab-sb)+sab sbc-sa sc+mc^2 (2 md^2+sa-sbc-sd)+sb sd)-mb^2 (sa sab+md^2 (sa+sab-sb)+sab sbc-2 sa sc+sa sd-2 sab sd+sb sd+mc^2 (sa-sbc+sd))-ma^2 (md^2 sa-md^2 sab+md^2 sb+sa sb+sa sbc+sab sbc-2 sb sbc-2 sa sc+mc^2 (sa+sbc-sd)+sb sd+mb^2 (-2 sa+sab+sb+sbc-2 sc+sd))],
	  \[Lambda]s01=Function[{s,ma,mb},ma^4+(mb^2-s)^2-2 ma^2 (mb^2+s)]},


  (*****FOUR vanishing masses*****)
  With[{body :=
    Module[{mFree = 1}, Module[{k12=-s1/mFree^2,k23=-s2/mFree^2,k34=-s3/mFree^2,k14=-s4/mFree^2,k13=-s12/mFree^2,k24=-s23/mFree^2},
	  Module[{a=k24 k34, b=k13 k24+k12 k34-k14 k23, c=k12 k13, d=k23},
		Module[{ x1=(-b+Sqrt[b^2-4a c])/(2a),x2=(-b-Sqrt[b^2-4a c])/(2a),x1Eps=-d/Sqrt[b^2-4a c],x2Eps=d/Sqrt[b^2-4a c]},
		  1/(mFree^4 Sqrt[b^2-4 a c])*
			(1/2*NLn[-x1,-x1Eps]^2-1/2*NLn[-x2,-x2Eps]^2+

			NContinuedDiLog[k34/k13,k34-k13,-x1,-x1Eps]-
			NContinuedDiLog[k34/k13,k34-k13,-x2,-x2Eps]+
			NContinuedDiLog[k24/k12,k24-k12,-x1,-x1Eps]-
			NContinuedDiLog[k24/k12,k24-k12,-x2,-x2Eps]+

			(-NLn[-x1,-x1Eps]+NLn[-x2,-x2Eps])*(NLn[k12,-1]+NLn[k13,-1]-NLn[k14,-1]-NLn[k23,-1])
			)
		]
	  ]
	]]},

	With@@Hold[{NContinuedDiLog = ContinuedDiLog[{#1,#2},{#3,#4}]&}, 
	  NScalarD0fourVanishingMassesAP = (Function@@Hold[{s1,s2,s3,s4,s12,s23}, body])];

	With@@Hold[{NContinuedDiLog = X`Private`NContinuedDiLog},
	  NScalarD0fourVanishingMassesMP := NScalarD0fourVanishingMassesMP = Compile[{{s1,_Complex},{s2,_Complex},{s3,_Complex},{s4,_Complex},{s12,_Complex},{s23,_Complex}}, body, CompilationOptions->{"ExpressionOptimization"->False}]]

  ];


  (*****THREE vanishing masses*****)
  With[{body := Module[{sa=0+0I, sb=0+0I, sc=0+0I, sd=0+0I, sab=0+0I, sbc=0+0I, principalFormula=True},

	Which[
	  (*Look for permutation for which k12 and k13 are nonvanishing; use principal formula*)
	  Re[s1] != Re[m1^2] && Re[s12] != Re[m1^2], sa=s1; sb=s2; sc=s3; sd=s4; sab=s12; sbc=s23(*; ma=m1; principalFormula=True*),
	  Re[s1] != Re[m1^2] && Re[s4] != Re[m1^2],  sa=s1; sb=s23; sc=s3; sd=s12; sab=s4; sbc=s2(*; ma=m1; principalFormula=True*),
	  Re[s12] != Re[m1^2] && Re[s4] != Re[m1^2], sa=s4; sb=s3; sc=s2; sd=s1; sab=s12; sbc=s23(*; ma=m1; principalFormula=True*),
	  (*Look for permutation for which k12 and k13 both vanishing; use secondary formula*)
	  Re[s1] == Re[m1^2] && Re[s12] == Re[m1^2], sa=s1; sb=s2; sc=s3; sd=s4; sab=s12; sbc=s23; principalFormula=False,
	  Re[s1] == Re[m1^2] && Re[s4] == Re[m1^2],  sa=s1; sb=s23; sc=s3; sd=s12; sab=s4; sbc=s2; principalFormula=False,
	  Re[s12] == Re[m1^2] && Re[s4] == Re[m1^2], sa=s4; sb=s3; sc=s2; sd=s1; sab=s12; sbc=s23; principalFormula=False
	];

	Module[{mFree = 1},Module[{k12=(m1^2-sa)/(m1 mFree),k23=(-sb)/(mFree^2),k34=(-sc)/(mFree^2),k14=(m1^2 - sd)/(m1 mFree),k13=(m1^2 -sab)/(m1 mFree),k24=(-sbc)/(mFree^2)},
	  Module[{a=k24 k34,b=k13 k24+k12 k34-k14 k23,c=k12 k13-k23,d=k23,
			  modifiedDetY=(k13 k24+k12 k34-k14 k23)^2-4(k24 k34)(k12 k13-k23)},
		Module[{x1=(-b+Sqrt[b^2-4a c])/(2a),x2=(-b-Sqrt[b^2-4a c])/(2a),x1Eps=-d/Sqrt[b^2-4a c],x2Eps=d/Sqrt[b^2-4a c]},

		  1/(m1 mFree^3 Sqrt[b^2-4a c])*
			(-NContinuedDiLog[k14,-1,-x1,-x1Eps]+
			NContinuedDiLog[k14,-1,-x2,-x2Eps]+

			If[principalFormula,
			  (*Use principal formula*)
			  NContinuedDiLog[k34/k13,k34-k13,-x1,-x1Eps]-
			  NContinuedDiLog[k34/k13,k34-k13,-x2,-x2Eps]+
			  NContinuedDiLog[k24/k12,k24-k12,-x1,-x1Eps]-
			  NContinuedDiLog[k24/k12,k24-k12,-x2,-x2Eps]+

			  (-NLn[-x1,-x1Eps]+NLn[-x2,-x2Eps])(NLn[k12,-1]+NLn[k13,-1]-NLn[k23,-1]),
			  (*Use secondary formula*)
			  -NLn[-x1,-x1Eps]^2+NLn[-x2,-x2Eps]^2+
			  (-NLn[-x1,-x1Eps]+NLn[-x2,-x2Eps])(NLn[k24,-1]+NLn[k34,-1]-NLn[k23,-1])
			]
			)
		]
	  ]
	]
	]]},

	With@@Hold[{NContinuedDiLog = ContinuedDiLog[{#1,#2},{#3,#4}]&, sqrtThr=Sqrt[#^2-4]&}, 
	  NScalarD0threeVanishingMassesAP = (Function@@Hold[{s1,s2,s3,s4,s12,s23,m1}, body])];

	With@@Hold[{NContinuedDiLog = X`Private`NContinuedDiLog, sqrtThr=Function[{kij},If[Abs[kij]<2,Sqrt[kij^2-4],Re[Sqrt[kij^2-4]]+0*I]]},
	  NScalarD0threeVanishingMassesMP := NScalarD0threeVanishingMassesMP = Compile[{{s1,_Complex},{s2,_Complex},{s3,_Complex},{s4,_Complex},{s12,_Complex},{s23,_Complex},{m1,_Complex}}, body, CompilationOptions->{"ExpressionOptimization"->False}]]	
  ];


  (*****TWO vanishing masses*****)
  With[{body := Module[{sa=0+0I, sb=0+0I, sc=0+0I, sd=0+0I, sab=0+0I, sbc=0+0I, ma=0+0I, md=0+0I, principalFormula=True},

	Which[
	  (*Look for permutation for which k12 and k13 are nonvanishing; use principal formula*)
	  Re[s1] != Re[m1^2] && Re[s12] != Re[m1^2], sa=s1; sb=s2; sc=s3; sd=s4; sab=s12; sbc=s23; ma=m1; md=m4(*; principalFormula=True*),
	  Re[s23] != Re[m4^2] && Re[s3] != Re[m4^2], sa=s23; sb=s2; sc=s12; sd=s4; sab=s3; sbc=s1; ma=m4; md=m1(*; principalFormula=True*),
	  (*Look for permutation for which k13 and k24 are nonvanishing; use secondary formula*)
	  Re[s12] != Re[m1^2] && Re[s23] != Re[m4^2],  sa=s1; sb=s2; sc=s3; sd=s4; sab=s12; sbc=s23; ma=m1; md=m4; principalFormula=False,
	  Re[s3] != Re[s4^2] && Re[s1] != Re[m1^2], sa=s23; sb=s2; sc=s12; sd=s4; sab=s3; sbc=s1; ma=m4; md=m1; principalFormula=False
	];

	Module[{mFree = 1(*Max[Re[E/(ma+md)],E]*)},Module[{k12=(ma^2-sa)/(ma mFree),k23=(-sb)/(mFree^2),k34=(md^2-sc)/(mFree md),k14=(ma^2+md^2 - sd)/(ma md),k13=(ma^2 -sab)/(ma mFree),k24=(md^2-sbc)/(mFree md)},
	  Module[{r14=(k14+Sign[k14]sqrtThr[k14])/2},
		Module[{r14Eps=If[Abs[k14]==2,1,-(1-r14^-2)^-1]},
		  Module[{a=k24 k34-k23, b=k13 k24+k12 k34-k14 k23, c=k12 k13-k23, d=k23,
				  modifiedDetY=(k13 k24+k12 k34-k14 k23)^2-4(k24 k34-k23)(k12 k13-k23)},
			Module[{x1=(-b+Sqrt[b^2-4a c])/(2a),x2=(-b-Sqrt[b^2-4a c])/(2a),x1Eps=-d/Sqrt[b^2-4a c],x2Eps=d/Sqrt[b^2-4a c]},

			  1/(ma mFree^2 md Sqrt[modifiedDetY])*
				(-NContinuedDiLog[r14,r14Eps,-x1,-x1Eps]-
				NContinuedDiLog[1/r14,-r14Eps/r14^2,-x1,-x1Eps]+
				NContinuedDiLog[r14,r14Eps,-x2,-x2Eps]+
				NContinuedDiLog[1/r14,-r14Eps/r14^2,-x2,-x2Eps]+

				If[principalFormula,
				  (*Use principal formula*)
				  NContinuedDiLog[k34/k13,k34-k13,-x1,-x1Eps]-
				  NContinuedDiLog[k34/k13,k34-k13,-x2,-x2Eps]+
				  NContinuedDiLog[k24/k12,k24-k12,-x1,-x1Eps]-
				  NContinuedDiLog[k24/k12,k24-k12,-x2,-x2Eps]+

				  (-NLn[-x1,-x1Eps]+NLn[-x2,-x2Eps])(-Log[1/k12]-Log[1/k13]+Log[1/k23]),
				  (*Use secondary formula*)
				  -1/2*NLn[-x1,-x1Eps]^2 + 1/2*NLn[-x2,-x2Eps]^2+
				  (-NLn[-x1,-x1Eps]+NLn[-x2,-x2Eps])(-Log[1/k24]-Log[1/k13]+Log[1/k23])
				]
				)
			]
		  ]
		]
	  ]
	]
	]]},

	Clear[NScalarD0twoVanishingMassesAP,NScalarD0twoVanishingMassesMP];

	With@@Hold[{NContinuedDiLog = ContinuedDiLog[{#1,#2},{#3,#4}]&, sqrtThr=Sqrt[#^2-4]&}, 
	  NScalarD0twoVanishingMassesAP = (Function@@Hold[{s1,s2,s3,s4,s12,s23,m1,m4}, body])];

	With@@Hold[{NContinuedDiLog = X`Private`NContinuedDiLog, sqrtThr=Function[{kij},If[Abs[kij]<2,Sqrt[kij^2-4],Re[Sqrt[kij^2-4]]+0*I]]},
	  NScalarD0twoVanishingMassesMP := NScalarD0twoVanishingMassesMP = Compile[{{s1,_Complex},{s2,_Complex},{s3,_Complex},{s4,_Complex},{s12,_Complex},{s23,_Complex},{m1,_Complex},{m4,_Complex}}, body, CompilationOptions->{"ExpressionOptimization"->False}]]
  ];


  (*****ONE vanishing mass*****)
  With[{body := Module[{sa=0+0I, sb=0+0I, sc=0+0I, sd=0+0I, sab=0+0I, sbc=0+0I, ma=0+0I, mb=0+0I, md=0+0I},
	Which[
	  Re[s12] != Re[m1^2], sa=s1; sb=s2; sc=s3; sd=s4; sab=s12; sbc=s23; ma=m1; mb=m2; md=m4,
	  Re[s2] != Re[m2^2],  sa=s1; sb=s12; sc=s3; sd=s23; sab=s2; sbc=s4; ma=m2; mb=m1; md=m4,
	  Re[s3] != Re[m4^2],  sa=s23; sb=s2; sc=s12; sd=s4; sab=s3; sbc=s1; ma=m4; mb=m2; md=m1
	];

	Module[{mFree = 1},Module[{k12=(ma^2+mb^2-sa)/(ma mb),k23=(mb^2 -sb)/(mb mFree),k34=(md^2-sc)/(mFree md),k14=(ma^2+md^2 - sd)/(ma md),k13=(ma^2 -sab)/(ma mFree),k24=(mb^2+md^2-sbc)/(mb md)},
	  Module[{r12=(k12+Sign[k12]sqrtThr[k12])/2, r14=(k14+Sign[k14]sqrtThr[k14])/2,r24=(k24+Sign[k24]sqrtThr[k24])/2},
		Module[{r12Eps=If[Abs[k12]==2,1,-(1-r12^-2)^-1],r14Eps=If[Abs[k14]==2,1,-(1-r14^-2)^-1],r24Eps=If[Abs[k24]==2,1,-(1-r24^-2)^-1]},
		  Module[{a=k34/r24-k23, b=-k13(*(1/r24-r24)*)Sign[k24]sqrtThr[k24]+k12 k34-k14 k23, c=k12 k13-k13 k14 r24+r24 k34-k23, d=k23-r24 k34},
			Module[{modifiedDetY=Re[b^2-4a c]+0 I,
					gamma12=If[Re[b^2-4a c]>0,1,Sign[Re[-2 a d]]], imr24=If[Re[k24^2-4]<0,Im[r24],Re[r24Eps]], 
					x1=(-b+Sqrt[Re[b^2-4a c]+0 I])/(2a),x2=(-b-Sqrt[Re[b^2-4a c]+0 I])/(2a),x1Eps=-d/Sqrt[Re[b^2-4a c]+0 I],x2Eps=d/Sqrt[Re[b^2-4a c]+0 I]},

			  1/(ma mb mFree md Sqrt[modifiedDetY])*
				(-NReContinuedDiLog[r14,r14Eps,-x1,-x1Eps]-
				NReContinuedDiLog[1/r14,-r14Eps/r14^2,-x1,-x1Eps]+
				NReContinuedDiLog[r14,r14Eps,-x2,-x2Eps]+
				NReContinuedDiLog[1/r14,-r14Eps/r14^2,-x2,-x2Eps]+

				NReContinuedDiLog[r12,r12Eps,-x1/r24,-x1Eps/r24]+
				NReContinuedDiLog[1/r12,-r12Eps/r12^2,-x1/r24,-x1Eps/r24]-
				NReContinuedDiLog[r12,r12Eps,-x2/r24,-x2Eps/r24]-
				NReContinuedDiLog[1/r12,-r12Eps/r12^2,-x2/r24,-x2Eps/r24]+

				NReContinuedDiLog[k34/k13,k34-k13,-x1,-x1Eps]-
				NReContinuedDiLog[k34/k13,k34-k13,-x2,-x2Eps]-
				NReContinuedDiLog[k23/k13,k23-k13,-x1/r24,-x1Eps/r24]+
				NReContinuedDiLog[k23/k13,k23-k13,-x2/r24,-x2Eps/r24]+

				NEtaTildeArg[-x1,-x1Eps,1/r24,-r24Eps/r24^2, -2 \[Pi](If[Re[(k24^2-4)modifiedDetY]>0,NArg[Re[fQbar[1,0,0,x1,r24,k12,k23,k34,k14]/d],gamma12 Sign[imr24]],Arg[fQbar[1,0,0,x1,r24,k12,k23,k34,k14]/d]]-Arg[1/k13])] - 
				NEtaTildeArg[-x2,-x2Eps,1/r24,-r24Eps/r24^2, -2 \[Pi](If[Re[(k24^2-4)modifiedDetY]>0,NArg[Re[fQbar[1,0,0,x2,r24,k12,k23,k34,k14]/d],-gamma12 Sign[imr24]],Arg[fQbar[1,0,0,x2,r24,k12,k23,k34,k14]/d]]-Arg[1/k13])]
				) + 

				1/(ma mb mFree md Sqrt[Abs[modifiedDetY]])*
				  If[Re[modifiedDetY]>0,(\[Pi] I)*Log[If[Re[sa]>Re[(ma+mb)^2],(kappa[sa,sb,sc,sd,sab,sbc,ma,mb,0,md]+Sqrt[\[Lambda]s01[sa,ma,mb]] ma mb mFree md Sqrt[modifiedDetY])/(kappa[sa,sb,sc,sd,sab,sbc,ma,mb,0,md]-Sqrt[\[Lambda]s01[sa,ma,mb]] ma mb mFree md Sqrt[modifiedDetY]),1]*
							If[Re[sab]>Re[(ma)^2],(kappa[sab,sb,sbc,sd,sa,sc,ma,0,mb,md]+Sqrt[\[Lambda]s01[sab,ma,0]] ma mb mFree md Sqrt[modifiedDetY])/(kappa[sab,sb,sbc,sd,sa,sc,ma,0,mb,md]-Sqrt[\[Lambda]s01[sab,ma,0]] ma mb mFree md Sqrt[modifiedDetY]),1]*
							If[Re[sb]>Re[(mb)^2],(kappa[sb,sc,sd,sa,sbc,sab,mb,0,md,ma]+Sqrt[\[Lambda]s01[sb,mb,0]] ma mb mFree md Sqrt[modifiedDetY])/(kappa[sb,sc,sd,sa,sbc,sab,mb,0,md,ma]-Sqrt[\[Lambda]s01[sb,mb,0]] ma mb mFree md Sqrt[modifiedDetY]),1]*
							If[Re[sbc]>Re[(mb+md)^2],(kappa[sbc,sb,sab,sd,sc,sa,md,mb,0,ma]+Sqrt[\[Lambda]s01[sbc,md,mb]] ma mb mFree md Sqrt[modifiedDetY])/(kappa[sbc,sb,sab,sd,sc,sa,md,mb,0,ma]-Sqrt[\[Lambda]s01[sbc,md,mb]] ma mb mFree md Sqrt[modifiedDetY]),1]*
							If[Re[sc]>Re[(md)^2],(kappa[sc,sd,sa,sb,sab,sbc,0,md,ma,mb]+Sqrt[\[Lambda]s01[sc,0,md]] ma mb mFree md Sqrt[modifiedDetY])/(kappa[sc,sd,sa,sb,sab,sbc,0,md,ma,mb]-Sqrt[\[Lambda]s01[sc,0,md]] ma mb mFree md Sqrt[modifiedDetY]),1]*
							If[Re[sd]>Re[(ma+md)^2],(kappa[sd,sa,sb,sc,sbc,sab,md,ma,mb,0]+Sqrt[\[Lambda]s01[sd,md,ma]] ma mb mFree md Sqrt[modifiedDetY])/(kappa[sd,sa,sb,sc,sbc,sab,md,ma,mb,0]-Sqrt[\[Lambda]s01[sd,md,ma]] ma mb mFree md Sqrt[modifiedDetY]),1]]
				,
				(-NImContinuedDiLog[r14,r14Eps,-x1,-x1Eps]-
				NImContinuedDiLog[1/r14,-r14Eps/r14^2,-x1,-x1Eps]+
				NImContinuedDiLog[r14,r14Eps,-x2,-x2Eps]+
				NImContinuedDiLog[1/r14,-r14Eps/r14^2,-x2,-x2Eps]+

				NImContinuedDiLog[r12,r12Eps,-x1/r24,-x1Eps/r24]+
				NImContinuedDiLog[1/r12,-r12Eps/r12^2,-x1/r24,-x1Eps/r24]-
				NImContinuedDiLog[r12,r12Eps,-x2/r24,-x2Eps/r24]-
				NImContinuedDiLog[1/r12,-r12Eps/r12^2,-x2/r24,-x2Eps/r24]+

				NImContinuedDiLog[k34/k13,k34-k13,-x1,-x1Eps]-
				NImContinuedDiLog[k34/k13,k34-k13,-x2,-x2Eps]-
				NImContinuedDiLog[k23/k13,k23-k13,-x1/r24,-x1Eps/r24]+
				NImContinuedDiLog[k23/k13,k23-k13,-x2/r24,-x2Eps/r24]+

				NEtaTildeArg[-x1,-x1Eps,1/r24,-r24Eps/r24^2, 2 \[Pi] Log[Abs[fQbar[1,0,0,x1,r24,k12,k23,k34,k14]/d * k13]]] - 
				NEtaTildeArg[-x2,-x2Eps,1/r24,-r24Eps/r24^2,2 \[Pi] Log[Abs[fQbar[1,0,0,x2,r24,k12,k23,k34,k14]/d * k13]]]
				
				)
				  ]
			]
		  ]
		]
	  ]
	]]
	]},

	Clear[NScalarD0oneVanishingMassesAP,NScalarD0oneVanishingMassesMP];

	With@@Hold[{NReContinuedDiLog=Function[{x,xEps,y,yEps}, Re[PolyLog[2,1-x y]] + NEtaArg[x,xEps,y,yEps, -2 Pi NArg[1-x y,-(xEps y+x yEps)]]], 
				NImContinuedDiLog=Function[{x,xEps,y,yEps}, Im[PolyLog[2,1-x y]] + NEtaArg[x,xEps,y,yEps, 2 Pi Log[Abs[1-x y]]]],
				sqrtThr=Sqrt[#^2-4]&}, 
	  NScalarD0oneVanishingMassesAP = (Function@@Hold[{s1,s2,s3,s4,s12,s23,m1,m2,m4}, body])];

	With@@Hold[{NReContinuedDiLog = X`Private`NReContinuedDiLog, NImContinuedDiLog = X`Private`NImContinuedDiLog, sqrtThr=Function[{kij},If[Abs[kij]<2,Sqrt[kij^2-4],Re[Sqrt[kij^2-4]]+0*I]]},
	  NScalarD0oneVanishingMassesMP := NScalarD0oneVanishingMassesMP = Compile[{{s1,_Complex},{s2,_Complex},{s3,_Complex},{s4,_Complex},{s12,_Complex},{s23,_Complex},{m1,_Complex},{m2,_Complex},{m4,_Complex}}, body, CompilationOptions->{"ExpressionOptimization"->False}]]

  ];

  (*****ZERO vanishing mass*****)
  With[{body := Module[{sa=0+0I, sb=0+0I, sc=0+0I, sd=0+0I, sab=0+0I, sbc=0+0I, ma=0+0I, mb=0+0I, mc=0+0I, md=0+0I, oneRealQ=True},

	Which[
		Re[(m1^2+m2^2-s1)^2]>Re[4 m1^2 m2^2], sa=s12; sb=s2; sc=s23; sd=s4; sab=s1; sbc=s3; ma=m1; mb=m3; mc=m2; md=m4,
		Re[(m2^2+m3^2-s2)^2]>Re[4 m2^2 m3^2], sa=s23; sb=s3; sc=s12; sd=s1; sab=s2; sbc=s4; ma=m2; mb=m4; mc=m3; md=m1,
		Re[(m3^2+m4^2-s3)^2]>Re[4 m3^2 m4^2], sa=s2; sb=s23; sc=s4; sd=s12; sab=s3; sbc=s1; ma=m3; mb=m2; mc=m4; md=m1,
		Re[(m1^2+m4^2-s4)^2]>Re[4 m1^2 m4^2], sa=s3; sb=s12; sc=s1; sd=s23; sab=s4; sbc=s2; ma=m4; mb=m3; mc=m1; md=m2,
		Re[(m1^2+m3^2-s12)^2]>Re[4 m1^2 m3^2], sa=s1; sb=s2; sc=s3; sd=s4; sab=s12; sbc=s23; ma=m1; mb=m2; mc=m3; md=m4,
		Re[(m2^2+m4^2-s23)^2]>Re[4 m2^2 m4^2], sa=s3; sb=s2; sc=s1; sd=s4; sab=s23; sbc=s12; ma=m4; mb=m3; mc=m2; md=m1,
		True, sa=s3; sb=s2; sc=s1; sd=s4; sab=s23; sbc=s12; ma=m4; mb=m3; mc=m2; md=m1; oneRealQ=False
	];

	  Module[{k12=(ma^2 + mb^2 - sa)/(ma*mb), k23=(mb^2 + mc^2 - sb)/(mb*mc), k34=(mc^2 + md^2 - sc)/(mc*md), k14=(ma^2 + md^2 - sd)/(ma*md), k13=(ma^2 + mc^2 - sab)/(ma*mc), k24=(mb^2 + md^2 - sbc)/(mb*md)},
		Module[{r12=(k12+Sign[k12]sqrtThr[k12])/2, r23=(k23+Sign[k23]sqrtThr[k23])/2, r34=(k34+Sign[k34]sqrtThr[k34])/2, r14=(k14+Sign[k14]sqrtThr[k14])/2, r13=(k13+Sign[k13]sqrtThr[k13])/2, r24=(k24+Sign[k24]sqrtThr[k24])/2},
		  Module[{r12Eps=If[Abs[k12]==2,1,-(1-r12^-2)^-1], r23Eps=If[Abs[k23]==2,1,-(1-r23^-2)^-1], r34Eps=If[Abs[k34]==2,1,-(1-r34^-2)^-1], r14Eps=If[Abs[k14]==2,1,-(1-r14^-2)^-1], r13Eps=If[Abs[k13]==2,1,-(1-r13^-2)^-1], r24Eps=If[Abs[k24]==2,1,-(1-r24^-2)^-1],
				  a=k34/r24+r13 k12-k14 r13/r24-k23, b=Sign[k24]sqrtThr[k24]Sign[k13]sqrtThr[k13]+k12 k34-k14 k23, c=k12/r13+r24 k34-k14 r24/r13-k23, d=k23-r13 k12-r24 k34+r13 r24 k14,
				  detY=16-4 k12^2-4 k13^2-4 k14^2+4 k12 k13 k23-4 k23^2+k14^2 k23^2+4 k12 k14 k24-2 k13 k14 k23 k24-4 k24^2+k13^2 k24^2+4 k13 k14 k34-2 k12 k14 k23 k34-2 k12 k13 k24 k34+4 k23 k24 k34-4 k34^2+k12^2 k34^2},
			Module[{imr24=If[Re[k24^2-4]<0,Im[r24],Re[r24Eps]], sgnb=If[Sign[Re[b]]!=0,Sign[Re[b]],1]},
			  Module[{gamma12=sgnb If[Re@detY>0,1,Sign[Re[-2 a d]]], x2=(-b-sgnb Sqrt[detY])/(2a), x2Eps=sgnb d/Sqrt[detY],x1=0+0I,x1Eps=0+0I},
					  x1=c/(a*x2); x1Eps=-x2Eps;

				sgnb/(ma mb mc md Sqrt[detY])*
					(NReContinuedDiLog[r12,r12Eps,-x1/r24,-x1Eps/r24]+
					NReContinuedDiLog[1/r12,-r12Eps/r12^2,-x1/r24,-x1Eps/r24]-
					NReContinuedDiLog[r12,r12Eps,-x2/r24,-x2Eps/r24]-
					NReContinuedDiLog[1/r12,-r12Eps/r12^2,-x2/r24,-x2Eps/r24]-

					NReContinuedDiLog[r23,r23Eps,-x1 r13/r24,-x1Eps r13/r24]-
					NReContinuedDiLog[1/r23,-r23Eps/r23^2,-x1 r13/r24,-x1Eps r13/r24]+
					NReContinuedDiLog[r23,r23Eps,-x2 r13/r24,-x2Eps r13/r24]+
					NReContinuedDiLog[1/r23,-r23Eps/r23^2,-x2 r13/r24,-x2Eps r13/r24]+

					NReContinuedDiLog[r34,r34Eps,-x1 r13,-x1Eps r13]+
					NReContinuedDiLog[1/r34,-r34Eps/r34^2,-x1 r13,-x1Eps r13]-
					NReContinuedDiLog[r34,r34Eps,-x2 r13,-x2Eps r13]-
					NReContinuedDiLog[1/r34,-r34Eps/r34^2,-x2 r13,-x2Eps r13]-

					NReContinuedDiLog[r14,r14Eps,-x1,-x1Eps]-
					NReContinuedDiLog[1/r14,-r14Eps/r14^2,-x1,-x1Eps]+
					NReContinuedDiLog[r14,r14Eps,-x2,-x2Eps]+
					NReContinuedDiLog[1/r14,-r14Eps/r14^2,-x2,-x2Eps]

					+If[oneRealQ,
					 NEtaTildeArg[-x1,-x1Eps,r13,r13Eps, -2 \[Pi] ( NArg[r13 x1,r13 x1Eps]+ NArg[fQ[1/x1,0,0,1,r13,k12,k23,k34,k14],-1]+If[Re[(k24^2-4)detY]>0,NArg[Re[fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d],gamma12 Sign[r13 imr24]],Arg[fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d]])]+
					 NEtaTildeArg[-x1,-x1Eps,1/r24,-r24Eps/r24^2, -2 \[Pi] (NArg[x1/r24,x1Eps/r24]+NArg[fQ[r24/x1,1,0,0,r13,k12,k23,k34,k14],-1]+If[Re[(k24^2-4)detY]>0,NArg[Re[fQbar[1,0,0,x1,r24,k12,k23,k34,k14]/d],gamma12 Sign[imr24]],Arg[fQbar[1,0,0,x1,r24,k12,k23,k34,k14]/d]])]-
					(NEtaTildeArg[-x1,-x1Eps,r13/r24,(r13Eps r24-r13 r24Eps)/r24^2, -2 \[Pi] (NArg[r13 x1/r24,r13 x1Eps/r24]+NArg[fQ[r24/x1,1,0,0,r13,k12,k23,k34,k14],-1]+If[Re[(k24^2-4)detY]>0,NArg[Re[fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d],gamma12 Sign[r13 imr24]],Arg[fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d]])]+NEtaArg[r13,r13Eps,1/r24,-r24Eps/r24^2, -2 \[Pi] (NArg[r13 x1/r24,r13 x1Eps/r24]+NArg[fQ[r24/x1,1,0,0,r13,k12,k23,k34,k14],-1]+If[Re[(k24^2-4)detY]>0,NArg[Re[fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d],gamma12 Sign[r13 imr24]],Arg[fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d]])])+
					 NEtaArg[r13,r13Eps,1/r24,-r24Eps/r24^2, NEtaTildeArg[-x1,-x1Eps,-r13/r24,-(r13Eps r24-r13 r24Eps)/r24^2,-4 \[Pi]^2]]

					-NEtaTildeArg[-x2,-x2Eps,r13,r13Eps, -2 \[Pi] (NArg[r13 x2,r13 x2Eps]+NArg[fQ[1/x2,0,0,1,r13,k12,k23,k34,k14],-1]+If[Re[(k24^2-4)detY]>0,NArg[Re[fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d],-gamma12 Sign[r13 imr24]],Arg[fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d]])]-
					NEtaTildeArg[-x2,-x2Eps,1/r24,-r24Eps/r24^2, -2 \[Pi] (NArg[x2/r24,x2Eps/r24]+NArg[fQ[r24/x2,1,0,0,r13,k12,k23,k34,k14],-1]+If[Re[(k24^2-4)detY]>0,NArg[Re[fQbar[1,0,0,x2,r24,k12,k23,k34,k14]/d],-gamma12 Sign[imr24]],Arg[fQbar[1,0,0,x2,r24,k12,k23,k34,k14]/d]])]+
					(NEtaTildeArg[-x2,-x2Eps,r13/r24,(r13Eps r24-r13 r24Eps)/r24^2, -2 \[Pi] (NArg[r13 x2/r24,r13 x2Eps/r24]+NArg[fQ[r24/x2,1,0,0,r13,k12,k23,k34,k14],-1]+If[Re[(k24^2-4)detY]>0,NArg[Re[fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d],-gamma12 Sign[r13 imr24]],Arg[fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d]])]+NEtaArg[r13,r13Eps,1/r24,-r24Eps/r24^2, -2 \[Pi] (NArg[r13 x2/r24,r13 x2Eps/r24]+NArg[fQ[r24/x2,1,0,0,r13,k12,k23,k34,k14],-1]+If[Re[(k24^2-4)detY]>0,NArg[Re[fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d],-gamma12 Sign[r13 imr24]],Arg[fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d]])])-
					 NEtaArg[r13,r13Eps,1/r24,-r24Eps/r24^2,NEtaTildeArg[-x2,-x2Eps,-r13/r24,-(r13Eps r24-r13 r24Eps)/r24^2,-4 \[Pi]^2]]
					,
					(NEtaArg[-x1,-x1Eps,1/r24,1, -2\[Pi] * (If[Re@detY<0,NArg[Re[r24/x1 fP[k12,x1/r24]],I x1/r24 gamma12],Arg[r24/x1 fP[k12,x1/r24]]]+NArg[x1/r24,x1Eps/r24])]+
					NEtaArg[-x1,-x1Eps,r13,1, -2\[Pi] * (If[Re@detY<0,NArg[Re[1/(r13 x1) fP[k34,r13 x1]],I r13 x1 gamma12],Arg[1/(r13 x1) fP[k34,r13 x1]]]+NArg[r13 x1,r13 x1Eps])]-
					(NEtaArg[-x1,-x1Eps,r13/r24,1, -2\[Pi] * (If[Re@detY<0,NArg[Re[r24/(r13 x1) fP[k23,(r13 x1)/r24]],I (r13 x1)/r24 gamma12],Arg[r24/(r13 x1) fP[k23,(r13 x1)/r24]]]+NArg[(r13 x1)/r24,(r13 x1Eps)/r24])]+
					NEtaArg[r13,1,1/r24,1, -2\[Pi] * (If[Re@detY<0,NArg[Re[r24/(r13 x1) fP[k23,(r13 x1)/r24]],I (r13 x1)/r24 gamma12],Arg[r24/(r13 x1) fP[k23,(r13 x1)/r24]]]+NArg[(r13 x1)/r24,(r13 x1Eps)/r24])])+
					NEtaArg[-x1,-x1Eps,-(r13/r24),1,NEtaArg[r13,1,1/r24,1,-4\[Pi]^2(1-gamma12)]])
					-
					(NEtaArg[-x2,-x2Eps,1/r24,1, -2\[Pi] * (If[Re@detY<0,NArg[Re[r24/x2 fP[k12,x2/r24]],-I x2/r24 gamma12],Arg[r24/x2 fP[k12,x2/r24]]]+NArg[x2/r24,x2Eps/r24])]+
					NEtaArg[-x2,-x2Eps,r13,1, -2\[Pi] * (If[Re@detY<0,NArg[Re[1/(r13 x2) fP[k34,r13 x2]],-I r13 x2 gamma12],Arg[1/(r13 x2) fP[k34,r13 x2]]]+NArg[r13 x2,r13 x2Eps])]-
					(NEtaArg[-x2,-x2Eps,r13/r24,1, -2\[Pi] * (If[Re@detY<0,NArg[Re[r24/(r13 x2) fP[k23,(r13 x2)/r24]],-I (r13 x2)/r24 gamma12],Arg[r24/(r13 x2) fP[k23,(r13 x2)/r24]]]+NArg[(r13 x2)/r24,(r13 x2Eps)/r24])]+
					NEtaArg[r13,1,1/r24,1, -2\[Pi] * (If[Re@detY<0,NArg[Re[r24/(r13 x2) fP[k23,(r13 x2)/r24]],-I (r13 x2)/r24 gamma12],Arg[r24/(r13 x2) fP[k23,(r13 x2)/r24]]]+NArg[(r13 x2)/r24,(r13 x2Eps)/r24])])+
					NEtaArg[-x2,-x2Eps,-(r13/r24),1,NEtaArg[r13,1,1/r24,1,-4\[Pi]^2(1+gamma12)]])
					]
				)


				+ 1/(m1 m2 m3 m4 Sqrt[Abs[detY]]) *
					If[Re@detY>0,
					  Module[{kappa1=kappa[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4],kappa2=kappa[s2,s3,s4,s1,s23,s12,m2,m3,m4,m1],kappa3=kappa[s3,s4,s1,s2,s12,s23,m3,m4,m1,m2],
							  kappa4=kappa[s4,s1,s2,s3,s23,s12,m4,m1,m2,m3],kappa12=kappa[s12,s2,s23,s4,s1,s3,m1,m3,m2,m4],kappa23=kappa[s23,s2,s12,s4,s3,s1,m4,m2,m3,m1]},

						(\[Pi] I)*Log[If[Re[s1]>Re[(m1+m2)^2],(kappa1+Sqrt[\[Lambda]s01[s1,m1,m2]] m1 m2 m3 m4 Sqrt[detY])/(kappa1-Sqrt[\[Lambda]s01[s1,m1,m2]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s12]>Re[(m1+m3)^2],(kappa12+Sqrt[\[Lambda]s01[s12,m1,m3]] m1 m2 m3 m4 Sqrt[detY])/(kappa12-Sqrt[\[Lambda]s01[s12,m1,m3]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s2]>Re[(m2+m3)^2],(kappa2+Sqrt[\[Lambda]s01[s2,m2,m3]] m1 m2 m3 m4 Sqrt[detY])/(kappa2-Sqrt[\[Lambda]s01[s2,m2,m3]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s23]>Re[(m2+m4)^2],(kappa23+Sqrt[\[Lambda]s01[s23,m4,m2]] m1 m2 m3 m4 Sqrt[detY])/(kappa23-Sqrt[\[Lambda]s01[s23,m4,m2]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s3]>Re[(m3+m4)^2],(kappa3+Sqrt[\[Lambda]s01[s3,m3,m4]] m1 m2 m3 m4 Sqrt[detY])/(kappa3-Sqrt[\[Lambda]s01[s3,m3,m4]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s4]>Re[(m1+m4)^2],(kappa4+Sqrt[\[Lambda]s01[s4,m4,m1]] m1 m2 m3 m4 Sqrt[detY])/(kappa4-Sqrt[\[Lambda]s01[s4,m4,m1]] m1 m2 m3 m4 Sqrt[detY]),1]]

						(*(\[Pi] I)*Log[If[Re[s1]>Re[(m1+m2)^2],(kappa[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4]+Sqrt[\[Lambda]s01[s1,m1,m2]] m1 m2 m3 m4 Sqrt[detY])/(kappa[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4]-Sqrt[\[Lambda]s01[s1,m1,m2]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s12]>Re[(m1+m3)^2],(kappa[s12,s2,s23,s4,s1,s3,m1,m3,m2,m4]+Sqrt[\[Lambda]s01[s12,m1,m3]] m1 m2 m3 m4 Sqrt[detY])/(kappa[s12,s2,s23,s4,s1,s3,m1,m3,m2,m4]-Sqrt[\[Lambda]s01[s12,m1,m3]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s2]>Re[(m2+m3)^2],(kappa[s2,s3,s4,s1,s23,s12,m2,m3,m4,m1]+Sqrt[\[Lambda]s01[s2,m2,m3]] m1 m2 m3 m4 Sqrt[detY])/(kappa[s2,s3,s4,s1,s23,s12,m2,m3,m4,m1]-Sqrt[\[Lambda]s01[s2,m2,m3]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s23]>Re[(m2+m4)^2],(kappa[s23,s2,s12,s4,s3,s1,m4,m2,m3,m1]+Sqrt[\[Lambda]s01[s23,m4,m2]] m1 m2 m3 m4 Sqrt[detY])/(kappa[s23,s2,s12,s4,s3,s1,m4,m2,m3,m1]-Sqrt[\[Lambda]s01[s23,m4,m2]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s3]>Re[(m3+m4)^2],(kappa[s3,s4,s1,s2,s12,s23,m3,m4,m1,m2]+Sqrt[\[Lambda]s01[s3,m3,m4]] m1 m2 m3 m4 Sqrt[detY])/(kappa[s3,s4,s1,s2,s12,s23,m3,m4,m1,m2]-Sqrt[\[Lambda]s01[s3,m3,m4]] m1 m2 m3 m4 Sqrt[detY]),1]*
							If[Re[s4]>Re[(m1+m4)^2],(kappa[s4,s1,s2,s3,s23,s12,m4,m1,m2,m3]+Sqrt[\[Lambda]s01[s4,m4,m1]] m1 m2 m3 m4 Sqrt[detY])/(kappa[s4,s1,s2,s3,s23,s12,m4,m1,m2,m3]-Sqrt[\[Lambda]s01[s4,m4,m1]] m1 m2 m3 m4 Sqrt[detY]),1]]*)
					  ]
					,

				sgnb(NImContinuedDiLog[r12,r12Eps,-x1/r24,-x1Eps/r24]+
					NImContinuedDiLog[1/r12,-r12Eps/r12^2,-x1/r24,-x1Eps/r24]-
					NImContinuedDiLog[r12,r12Eps,-x2/r24,-x2Eps/r24]-
					NImContinuedDiLog[1/r12,-r12Eps/r12^2,-x2/r24,-x2Eps/r24]-

					NImContinuedDiLog[r23,r23Eps,-x1 r13/r24,-x1Eps r13/r24]-
					NImContinuedDiLog[1/r23,-r23Eps/r23^2,-x1 r13/r24,-x1Eps r13/r24]+
					NImContinuedDiLog[r23,r23Eps,-x2 r13/r24,-x2Eps r13/r24]+
					NImContinuedDiLog[1/r23,-r23Eps/r23^2,-x2 r13/r24,-x2Eps r13/r24]+

					NImContinuedDiLog[r34,r34Eps,-x1 r13,-x1Eps r13]+
					NImContinuedDiLog[1/r34,-r34Eps/r34^2,-x1 r13,-x1Eps r13]-
					NImContinuedDiLog[r34,r34Eps,-x2 r13,-x2Eps r13]-
					NImContinuedDiLog[1/r34,-r34Eps/r34^2,-x2 r13,-x2Eps r13]-

					NImContinuedDiLog[r14,r14Eps,-x1,-x1Eps]-
					NImContinuedDiLog[1/r14,-r14Eps/r14^2,-x1,-x1Eps]+
					NImContinuedDiLog[r14,r14Eps,-x2,-x2Eps]+
					NImContinuedDiLog[1/r14,-r14Eps/r14^2,-x2,-x2Eps]+ 

					+ If[oneRealQ,
					NEtaTildeArg[-x1,-x1Eps,r13,r13Eps, 2 \[Pi] Log[Abs[r13 x1*fQ[1/x1,0,0,1,r13,k12,k23,k34,k14]*fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d]]]+
					NEtaTildeArg[-x1,-x1Eps,1/r24,-r24Eps/r24^2, 2 \[Pi] Log[Abs[x1/r24*fQ[r24/x1,1,0,0,r13,k12,k23,k34,k14]*fQbar[1,0,0,x1,r24,k12,k23,k34,k14]/d]]]-
					(NEtaTildeArg[-x1,-x1Eps,r13/r24,(r13Eps r24-r13 r24Eps)/r24^2, 2 \[Pi] Log[Abs[r13 x1/r24*fQ[r24/x1,1,0,0,r13,k12,k23,k34,k14]*fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d]]]
											+NEtaArg[r13,r13Eps,1/r24,-r24Eps/r24^2, 2 \[Pi] Log[Abs[r13 x1/r24*fQ[r24/x1,1,0,0,r13,k12,k23,k34,k14]*fQbar[0,0,1,r13 x1,r24,k12,k23,k34,k14]/d]]])

					-NEtaTildeArg[-x2,-x2Eps,r13,r13Eps, 2 \[Pi] Log[Abs[r13 x2*fQ[1/x2,0,0,1,r13,k12,k23,k34,k14]*fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d]]]-
					NEtaTildeArg[-x2,-x2Eps,1/r24,-r24Eps/r24^2, 2 \[Pi] Log[Abs[x2/r24*fQ[r24/x2,1,0,0,r13,k12,k23,k34,k14]*fQbar[1,0,0,x2,r24,k12,k23,k34,k14]/d]]]+
					(NEtaTildeArg[-x2,-x2Eps,r13/r24,(r13Eps r24-r13 r24Eps)/r24^2, 2 \[Pi] Log[Abs[r13 x2/r24*fQ[r24/x2,1,0,0,r13,k12,k23,k34,k14]*fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d]]]
											+NEtaArg[r13,r13Eps,1/r24,-r24Eps/r24^2, 2 \[Pi] Log[Abs[r13 x2/r24*fQ[r24/x2,1,0,0,r13,k12,k23,k34,k14]*fQbar[0,0,1,r13 x2,r24,k12,k23,k34,k14]/d]]])
					,
					(NEtaArg[-x1,-x1Eps,1/r24,1, 2 \[Pi] Log[Abs[fP[k12,x1/r24]]]]+
					NEtaArg[-x1,-x1Eps,r13,1, 2 \[Pi] Log[Abs[fP[k34,r13 x1]]]]-
					(NEtaArg[-x1,-x1Eps,r13/r24,1, 2 \[Pi] Log[Abs[fP[k23,(r13 x1)/r24]]]]+
					NEtaArg[r13,1,1/r24,1, 2 \[Pi] Log[Abs[fP[k23,(r13 x1)/r24]]]]))
					-
					(NEtaArg[-x2,-x2Eps,1/r24,1, 2 \[Pi] Log[Abs[fP[k12,x2/r24]]]]+
					NEtaArg[-x2,-x2Eps,r13,1, 2 \[Pi] Log[Abs[fP[k34,r13 x2]]]]-
					(NEtaArg[-x2,-x2Eps,r13/r24,1, 2 \[Pi] Log[Abs[fP[k23,(r13 x2)/r24]]]]+
					NEtaArg[r13,1,1/r24,1, 2 \[Pi] Log[Abs[fP[k23,(r13 x2)/r24]]]]))
					]
				)]
			  ]
			]
		  ]
		]
	  ]
	]},

	Clear[NScalarD0noVanishingMassesAP,NScalarD0noVanishingMassesMP];

	With@@Hold[{NReContinuedDiLog=Function[{x,xEps,y,yEps}, Re[PolyLog[2,1-x y]] + NEtaArg[x,xEps,y,yEps, -2 Pi NArg[1-x y,-(xEps y+x yEps)]]], 
				NImContinuedDiLog=Function[{x,xEps,y,yEps}, Im[PolyLog[2,1-x y]] + NEtaArg[x,xEps,y,yEps, 2 Pi Log[Abs[1-x y]]]],
				sqrtThr=Sqrt[#^2-4]&}, 
	  NScalarD0noVanishingMassesAP = (Function@@Hold[{s1,s2,s3,s4,s12,s23,m1,m2,m3,m4}, body])];

	With@@Hold[{NReContinuedDiLog = X`Private`NReContinuedDiLog, NImContinuedDiLog = X`Private`NImContinuedDiLog, sqrtThr=Function[{kij},If[Abs[kij]<2,Sqrt[kij^2-4],Re[Sqrt[kij^2-4]]+0*I]]},
	  NScalarD0noVanishingMassesMP := NScalarD0noVanishingMassesMP = Compile[{{s1,_Complex},{s2,_Complex},{s3,_Complex},{s4,_Complex},{s12,_Complex},{s23,_Complex},{m1,_Complex},{m2,_Complex},{m3,_Complex},{m4,_Complex}}, body, CompilationOptions->{"ExpressionOptimization"->False}]]

  ];

];


NsoftDivD0Q=Function[{s1,s2,s3,s4,s12,s23,m0,m1,m2,m3},
	With[{
		y11=2 m0^2,y12=m0^2+m1^2-s1,y13=m0^2+m2^2-s12,y14=m0^2+m3^2-s4,
		(*y21=m0^2+m1^2-s1,*)y22=2 m1^2,y23=m1^2+m2^2-s2,y24=m1^2+m3^2-s23,
		(*y31=m0^2+m2^2-s12,y32=m1^2+m2^2-s2,*)y33=2 m2^2,y34=m2^2+m3^2-s3,
		(*y41=m0^2+m3^2-s4,y42=m1^2+m3^2-s23,y43=m2^2+m3^2-s3,*)y44=2 m3^2},

		(y11==0&&((y12==0&&((y13==0&&y22==0&&y24==0)||y14==0))||(y13==0&&y14==0&&y24==0&&y44==0)))||(y23==0&&((y22==0&&(y12==0||(y13==0&&y24==0&&y33==0)))||(y33==0&&y34==0)))||(y34==0&&y44==0&&((y13==0&&y24==0&&y33==0)||y14==0))
	]
];

NcollDivD0Q=Function[{s1,s2,s3,s4,s12,s23,m0,m1,m2,m3},
	With[{
		y11=2 m0^2,y12=m0^2+m1^2-s1,y13=m0^2+m2^2-s12,y14=m0^2+m3^2-s4,
		(*y21=m0^2+m1^2-s1,*)y22=2 m1^2,y23=m1^2+m2^2-s2,y24=m1^2+m3^2-s23,
		(*y31=m0^2+m2^2-s12,y32=m1^2+m2^2-s2,*)y33=2 m2^2,y34=m2^2+m3^2-s3,
		(*y41=m0^2+m3^2-s4,y42=m1^2+m3^2-s23,y43=m2^2+m3^2-s3,*)y44=2 m3^2},

		(y11==0&&((y12==0&&((y14==0&&y24==0)||y22==0))||(y14==0&&y44==0)))||(y13==0&&((y12==0&&y22==0&&y23==0)||(y14==0&&y34==0&&y44==0)))||(y33==0&&((y23==0&&(y22==0||(y24==0&&y34==0)))||(y34==0&&y44==0)))
	]
];

NirDivD0Q=Function[{s1,s2,s3,s4,s12,s23,m0,m1,m2,m3},
	With[{
		y11=2 m0^2,y12=m0^2+m1^2-s1,y13=m0^2+m2^2-s12,y14=m0^2+m3^2-s4,
		(*y21=m0^2+m1^2-s1,*)y22=2 m1^2,y23=m1^2+m2^2-s2,y24=m1^2+m3^2-s23,
		(*y31=m0^2+m2^2-s12,y32=m1^2+m2^2-s2,*)y33=2 m2^2,y34=m2^2+m3^2-s3,
		(*y41=m0^2+m3^2-s4,y42=m1^2+m3^2-s23,y43=m2^2+m3^2-s3,*)y44=2 m3^2},

		(m0==0||m1==0||m2==0||m3==0)&&((y11==0&&((y12==0&&(y13==0||y14==0||y22==0))||(y13==0&&(y14==0||y33==0))||(y14==0&&y44==0)))||((y12==0||y23==0||y44==0)&&(y12==0||y24==0||y33==0)&&y22==0&&(y23==0||y24==0))||(y33==0&&((y13==0&&(y23==0||y34==0))||(y34==0&&(y23==0||y44==0))))||(y44==0&&((y14==0&&(y24==0||y34==0))||(y24==0&&y34==0))))
	]
];


(*Machine precision evaluation, using compiled code*)

If[$VersionNumber!=10.4 (*To avoid lengthy compilation times*),
expr : ScalarD0[s1_?Internal`RealValuedNumericQ, s2_?Internal`RealValuedNumericQ, s3_?Internal`RealValuedNumericQ, 
   s4_?Internal`RealValuedNumericQ, s12_?Internal`RealValuedNumericQ, s23_?Internal`RealValuedNumericQ,
  m1_?NonNegative,m2_?NonNegative,m3_?NonNegative,m4_?NonNegative] /; Precision[Hold[expr]]===MachinePrecision :=
If[NirDivD0Q[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4],
   Switch[{NsoftDivD0Q[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4], NcollDivD0Q[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4]},
	{True, False},
    Message[ScalarD0::irdiv, "Soft"]; ComplexInfinity,
    {False, True},
    Message[ScalarD0::irdiv, "Collinear"]; ComplexInfinity,
    {True, True},
    Message[ScalarD0::irdiv, "Soft and collinear"]; ComplexInfinity,
	_,
	Message[ScalarD0::irdiv, "Threshold"]; ComplexInfinity
  ],

  (*No IR divergence*)
  Which[
	m1==0.,
	  Which[
		m2==0.,
		  Which[
			m3==0.,
			  If[m4==0.,
				NScalarD0fourVanishingMassesMP[s1,s2,s3,s4,s12,s23],
				NScalarD0threeVanishingMassesMP[s4,s1,s2,s3,s23,s12,m4]
			  ],
			m4==0.,NScalarD0threeVanishingMassesMP[s2,s1,s4,s3,s12,s23,m3],
			True,NScalarD0twoVanishingMassesMP[s2,s1,s4,s3,s12,s23,m3,m4]
		  ],
		m3==0.,
		  If[m4==0.,
			NScalarD0threeVanishingMassesMP[s1,s4,s3,s2,s23,s12,m2],
			NScalarD0twoVanishingMassesMP[s2,s12,s4,s23,s1,s3,m2,m4]
		  ],
		m4==0.,NScalarD0twoVanishingMassesMP[s1,s4,s3,s2,s23,s12,m2,m3],
		True,NScalarD0oneVanishingMassesMP[s3,s4,s1,s2,s12,s23,m3,m4,m2]
	  ],

	m2==0.,
	  Which[
		m3==0.,
		  If[m4==0.,
			NScalarD0threeVanishingMassesMP[s1,s2,s3,s4,s12,s23,m1],
			NScalarD0twoVanishingMassesMP[s1,s2,s3,s4,s12,s23,m1,m4]
		  ],
		m4==0.,NScalarD0twoVanishingMassesMP[s1,s23,s3,s12,s4,s2,m1,m3],
		True,NScalarD0oneVanishingMassesMP[s3,s23,s1,s12,s2,s4,m3,m4,m1]
	  ],

	m3==0.,
	  If[m4==0.,
		NScalarD0twoVanishingMassesMP[s23,s3,s12,s1,s2,s4,m2,m1],
		NScalarD0oneVanishingMassesMP[s1,s2,s3,s4,s12,s23,m1,m2,m4]
	  ],

	m4==0.,NScalarD0oneVanishingMassesMP[s2,s23,s4,s12,s3,s1,m3,m2,m1],
	True, NScalarD0noVanishingMassesMP[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4] 


  ]
 ];
];


(*Arbitrary precision evaluation, using native Mathematica functions*)

expr : ScalarD0[s1_?Internal`RealValuedNumericQ, s2_?Internal`RealValuedNumericQ, s3_?Internal`RealValuedNumericQ, 
   s4_?Internal`RealValuedNumericQ, s12_?Internal`RealValuedNumericQ, s23_?Internal`RealValuedNumericQ,
  m1_?NonNegative,m2_?NonNegative,m3_?NonNegative,m4_?NonNegative] /; Precision[Hold[expr]]<\[Infinity]:=
If[NirDivD0Q[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4],
   Switch[{NsoftDivD0Q[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4], NcollDivD0Q[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4]},
	{True, False},
    Message[ScalarD0::irdiv, "Soft"]; ComplexInfinity,
    {False, True},
    Message[ScalarD0::irdiv, "Collinear"]; ComplexInfinity,
    {True, True},
    Message[ScalarD0::irdiv, "Soft and collinear"]; ComplexInfinity,
	_,
	Message[ScalarD0::irdiv, "Threshold"]; ComplexInfinity
  ],
  (*No IR divergence*)
  Which[
	m1==0.,
	  Which[
		m2==0.,
		  Which[
			m3==0.,
			  If[m4==0.,
				(*NScalarD0fourVanishingMassesAP[s1,s2,s3,s4,s12,s23]*)X`Internal`ToTargetPrecision[NScalarD0fourVanishingMassesAP,{s1,s2,s3,s4,s12,s23},3],
				(*NScalarD0threeVanishingMassesAP[s4,s1,s2,s3,s23,s12,m4]*)X`Internal`ToTargetPrecision[NScalarD0threeVanishingMassesAP,{s4,s1,s2,s3,s23,s12,m4},3]
			  ],
			m4==0.,(*NScalarD0threeVanishingMassesAP[s2,s1,s4,s3,s12,s23,m3]*)X`Internal`ToTargetPrecision[NScalarD0threeVanishingMassesAP,{s2,s1,s4,s3,s12,s23,m3},3],
			True,(*NScalarD0twoVanishingMassesAP[s2,s1,s4,s3,s12,s23,m3,m4]*)X`Internal`ToTargetPrecision[NScalarD0twoVanishingMassesAP,{s2,s1,s4,s3,s12,s23,m3,m4},3]
		  ],
		m3==0.,
		  If[m4==0.,
			(*NScalarD0threeVanishingMassesAP[s1,s4,s3,s2,s23,s12,m2]*)X`Internal`ToTargetPrecision[NScalarD0threeVanishingMassesAP,{s1,s4,s3,s2,s23,s12,m2},3],
			(*NScalarD0twoVanishingMassesAP[s2,s12,s4,s23,s1,s3,m2,m4]*)X`Internal`ToTargetPrecision[NScalarD0twoVanishingMassesAP,{s2,s12,s4,s23,s1,s3,m2,m4},3]
		  ],
		m4==0.,(*NScalarD0twoVanishingMassesAP[s1,s4,s3,s2,s23,s12,m2,m3]*)X`Internal`ToTargetPrecision[NScalarD0twoVanishingMassesAP,{s1,s4,s3,s2,s23,s12,m2,m3},3],
		True,(*NScalarD0oneVanishingMassesAP[s3,s4,s1,s2,s12,s23,m3,m4,m2]*)X`Internal`ToTargetPrecision[NScalarD0oneVanishingMassesAP,{s3,s4,s1,s2,s12,s23,m3,m4,m2},6]
	  ],

	m2==0.,
	  Which[
		m3==0.,
		  If[m4==0.,
			(*NScalarD0threeVanishingMassesAP[s1,s2,s3,s4,s12,s23,m1]*)X`Internal`ToTargetPrecision[NScalarD0threeVanishingMassesAP,{s1,s2,s3,s4,s12,s23,m1},3],
			(*NScalarD0twoVanishingMassesAP[s1,s2,s3,s4,s12,s23,m1,m4]*)X`Internal`ToTargetPrecision[NScalarD0twoVanishingMassesAP,{s1,s2,s3,s4,s12,s23,m1,m4},3]
		  ],
		m4==0.,(*NScalarD0twoVanishingMassesAP[s1,s23,s3,s12,s4,s2,m1,m3]*)X`Internal`ToTargetPrecision[NScalarD0twoVanishingMassesAP,{s1,s23,s3,s12,s4,s2,m1,m3},3],
		True,(*NScalarD0oneVanishingMassesAP[s3,s23,s1,s12,s2,s4,m3,m4,m1]*)X`Internal`ToTargetPrecision[NScalarD0oneVanishingMassesAP,{s3,s23,s1,s12,s2,s4,m3,m4,m1},6]
	  ],

	m3==0.,
	  If[m4==0.,
		(*NScalarD0twoVanishingMassesAP[s23,s3,s12,s1,s2,s4,m2,m1]*)X`Internal`ToTargetPrecision[NScalarD0twoVanishingMassesAP,{s23,s3,s12,s1,s2,s4,m2,m1},3],
		(*NScalarD0oneVanishingMassesAP[s1,s2,s3,s4,s12,s23,m1,m2,m4]*)X`Internal`ToTargetPrecision[NScalarD0oneVanishingMassesAP,{s1,s2,s3,s4,s12,s23,m1,m2,m4},6]
	  ],

	m4==0.,(*NScalarD0oneVanishingMassesAP[s2,s23,s4,s12,s3,s1,m3,m2,m1]*)X`Internal`ToTargetPrecision[NScalarD0oneVanishingMassesAP,{s2,s23,s4,s12,s3,s1,m3,m2,m1},6],
	True, (*NScalarD0noVanishingMassesAP[s1,s2,s3,s4,s12,s23,m1,m2,m3,m4]*)X`Internal`ToTargetPrecision[NScalarD0noVanishingMassesAP,{s1,s2,s3,s4,s12,s23,m1,m2,m3,m4},7] 


  ]
 ];


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


ScalarD0[Except[_Slot,s1_],s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]:=
  With[{
	(*Sorting by cyclic permutations and their reverse.
	  Arguments of ScalarD0 should be sorted by s12,s23 first.
	  So each permutation below has 5th and 6th brought to front.*)
	possibilities={
	  {s12,s23,s1,s2,s3,s4,m0,m1,m2,m3},{s23,s12,s1,s4,s3,s2,m1,m0,m3,m2},
	  {s12,s23,s2,s1,s4,s3,m2,m1,m0,m3},{s23,s12,s4,s1,s2,s3,m3,m0,m1,m2},
	  {s23,s12,s3,s2,s1,s4,m3,m2,m1,m0},{s12,s23,s3,s4,s1,s2,m2,m3,m0,m1},
	  {s23,s12,s2,s3,s4,s1,m1,m2,m3,m0},{s12,s23,s4,s3,s2,s1,m0,m3,m2,m1}}
  },
  With[{canonicalOrdering=possibilities[[First[Ordering[possibilities,1]]]]},

	(*Slots #1,#2 are in 5th and 6th positions to
	  put s12 and s23 in their proper position after sorting.*)
  (ScalarD0[#3,#4,#5,#6,#1,#2,#7,#8,#9,#10]&@@canonicalOrdering)/;canonicalOrdering=!={s12,s23,s1,s2,s3,s4,m0,m1,m2,m3}
  ]
];

softDivD0Q=Function[{s1,s2,s3,s4,s12,s23,m0,m1,m2,m3},
	With[{
		y11=2 m0^2,y12=m0^2+m1^2-s1,y13=m0^2+m2^2-s12,y14=m0^2+m3^2-s4,
		(*y21=m0^2+m1^2-s1,*)y22=2 m1^2,y23=m1^2+m2^2-s2,y24=m1^2+m3^2-s23,
		(*y31=m0^2+m2^2-s12,y32=m1^2+m2^2-s2,*)y33=2 m2^2,y34=m2^2+m3^2-s3,
		(*y41=m0^2+m3^2-s4,y42=m1^2+m3^2-s23,y43=m2^2+m3^2-s3,*)y44=2 m3^2},

		(PossibleZeroQ[y11]&&((PossibleZeroQ[y12]&&((PossibleZeroQ[y13]&&PossibleZeroQ[y22]&&PossibleZeroQ[y24])||PossibleZeroQ[y14]))||(PossibleZeroQ[y13]&&PossibleZeroQ[y14]&&PossibleZeroQ[y24]&&PossibleZeroQ[y44])))||(PossibleZeroQ[y23]&&((PossibleZeroQ[y22]&&(PossibleZeroQ[y12]||(PossibleZeroQ[y13]&&PossibleZeroQ[y24]&&PossibleZeroQ[y33])))||(PossibleZeroQ[y33]&&PossibleZeroQ[y34])))||(PossibleZeroQ[y34]&&PossibleZeroQ[y44]&&((PossibleZeroQ[y13]&&PossibleZeroQ[y24]&&PossibleZeroQ[y33])||PossibleZeroQ[y14]))
	]
];

collDivD0Q=Function[{s1,s2,s3,s4,s12,s23,m0,m1,m2,m3},
	With[{
		y11=2 m0^2,y12=m0^2+m1^2-s1,y13=m0^2+m2^2-s12,y14=m0^2+m3^2-s4,
		(*y21=m0^2+m1^2-s1,*)y22=2 m1^2,y23=m1^2+m2^2-s2,y24=m1^2+m3^2-s23,
		(*y31=m0^2+m2^2-s12,y32=m1^2+m2^2-s2,*)y33=2 m2^2,y34=m2^2+m3^2-s3,
		(*y41=m0^2+m3^2-s4,y42=m1^2+m3^2-s23,y43=m2^2+m3^2-s3,*)y44=2 m3^2},

		(PossibleZeroQ[y11]&&((PossibleZeroQ[y12]&&((PossibleZeroQ[y14]&&PossibleZeroQ[y24])||PossibleZeroQ[y22]))||(PossibleZeroQ[y14]&&PossibleZeroQ[y44])))||(PossibleZeroQ[y13]&&((PossibleZeroQ[y12]&&PossibleZeroQ[y22]&&PossibleZeroQ[y23])||(PossibleZeroQ[y14]&&PossibleZeroQ[y34]&&PossibleZeroQ[y44])))||(PossibleZeroQ[y33]&&((PossibleZeroQ[y23]&&(PossibleZeroQ[y22]||(PossibleZeroQ[y24]&&PossibleZeroQ[y34])))||(PossibleZeroQ[y34]&&PossibleZeroQ[y44])))
	]
];

irDivD0Q=Function[{s1,s2,s3,s4,s12,s23,m0,m1,m2,m3},
	With[{
		y11=2 m0^2,y12=m0^2+m1^2-s1,y13=m0^2+m2^2-s12,y14=m0^2+m3^2-s4,
		(*y21=m0^2+m1^2-s1,*)y22=2 m1^2,y23=m1^2+m2^2-s2,y24=m1^2+m3^2-s23,
		(*y31=m0^2+m2^2-s12,y32=m1^2+m2^2-s2,*)y33=2 m2^2,y34=m2^2+m3^2-s3,
		(*y41=m0^2+m3^2-s4,y42=m1^2+m3^2-s23,y43=m2^2+m3^2-s3,*)y44=2 m3^2},

		(PossibleZeroQ[m0] || PossibleZeroQ[m1] || PossibleZeroQ[m2] || PossibleZeroQ[m3]) && ((PossibleZeroQ[y11]&&((PossibleZeroQ[y12]&&(PossibleZeroQ[y13]||PossibleZeroQ[y14]||PossibleZeroQ[y22]))||(PossibleZeroQ[y13]&&(PossibleZeroQ[y14]||PossibleZeroQ[y33]))||(PossibleZeroQ[y14]&&PossibleZeroQ[y44])))||((PossibleZeroQ[y12]||PossibleZeroQ[y23]||PossibleZeroQ[y44])&&(PossibleZeroQ[y12]||PossibleZeroQ[y24]||PossibleZeroQ[y33])&&PossibleZeroQ[y22]&&(PossibleZeroQ[y23]||PossibleZeroQ[y24]))||(PossibleZeroQ[y33]&&((PossibleZeroQ[y13]&&(PossibleZeroQ[y23]||PossibleZeroQ[y34]))||(PossibleZeroQ[y34]&&(PossibleZeroQ[y23]||PossibleZeroQ[y44]))))||(PossibleZeroQ[y44]&&((PossibleZeroQ[y14]&&(PossibleZeroQ[y24]||PossibleZeroQ[y34]))||(PossibleZeroQ[y24]&&PossibleZeroQ[y34]))))

	]
];

(*Check for IR divergences*)
ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] /; irDivD0Q[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3](*False*) := 
  Switch[{softDivD0Q[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3], collDivD0Q[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]},
	{True, False},
    Message[ScalarD0::irdiv, "Soft"]; ComplexInfinity,
    {False, True},
    Message[ScalarD0::irdiv, "Collinear"]; ComplexInfinity,
    {True, True},
    Message[ScalarD0::irdiv, "Soft and collinear"]; ComplexInfinity,
	_,
	Message[ScalarD0::irdiv, "Threshold"]; ComplexInfinity
  ];

(*Automatic substitutions of analytic expressions*)
ScalarD0[0,0,0,0,0,0,m0_,m1_,m2_,m3_] :=
	Switch[
		Count[{m0,m1,m2,m3},0],
		0,
		Switch[
			SortBy[Tally[{m0,m1,m2,m3}],Last],
			{{_,1},{_,1},{_,1},{_,1}},
			(m1^2 olog[m0^2,m1^2])/((-m0^2+m1^2) (m1^2-m2^2) (m1^2-m3^2))+(m2^2 olog[m0^2,m2^2])/((-m0^2+m2^2) (-m1^2+m2^2) (m2^2-m3^2))+(m3^2 olog[m0^2,m3^2])/((-m0^2+m3^2) (-m1^2+m3^2) (-m2^2+m3^2)),
			{{_,1},{_,1},{_,2}},
			SortBy[Tally[{m0,m1,m2,m3}],Last]/.{{a_,1},{b_,1},{c_,2}}:>1/((b^2-c^2) (-a^2+c^2))-(a^2 olog[a^2,c^2])/((a^2-b^2) (a^2-c^2)^2)+(b^2 olog[b^2,c^2])/((a^2-b^2) (b^2-c^2)^2),
			{{_,2},{_,2}},
			SortBy[Tally[{m0,m1,m2,m3}],Last]/.{{a_,2},{b_,2}}:>-(2/(a^2-b^2)^2)+((a^2+b^2) olog[a^2,b^2])/(a^2-b^2)^3,
			{{_,1},{_,3}},
			SortBy[Tally[{m0,m1,m2,m3}],Last]/.{{a_,1},{b_,3}}:>(a^2+b^2)/(2 (-a^2 b+b^3)^2)-(a^2 olog[a^2,b^2])/(a^2-b^2)^3,
			_,
			1/(6 m0^4)],
		1,
		Switch[
			DeleteCases[SortBy[Tally[{m0,m1,m2,m3}],Last],{0,1}],
			{{_,1},{_,1},{_,1}},
			DeleteCases[SortBy[Tally[{m0,m1,m2,m3}],Last],{0,1}]/.{{a_,1},{b_,1},{c_,1}}:>-(olog[a^2,c^2]/((a^2-b^2) (a^2-c^2)))+olog[b^2,c^2]/((a^2-b^2) (b^2-c^2)),
			{{_,1},{_,2}},
			DeleteCases[SortBy[Tally[{m0,m1,m2,m3}],Last],{0,1}]/.{{a_,1},{b_,2}}:>1/(a^2 b^2-b^4)-olog[a^2,b^2]/(a^2-b^2)^2,
			_,

			DeleteCases[SortBy[Tally[{m0,m1,m2,m3}],Last],{0,1}]/.{{a_,3}}:>1/(2 a^4)],
		_,
		$Failed (*Infrared divergent; should be caught by irDivD0Q*)
	];


LHS_ScalarD0:=RuleCondition[X`Internal`CheckArgumentCount[LHS,10,10];Fail];


(* ::Subsection:: *)
(*ScalarD0IR12*)


(* ::Subsubsection::Closed:: *)
(*Numeric evaluation*)


SetAttributes[ScalarD0IR12, NumericFunction];


(*Numerical implementation*)
With[{NLn=X`Private`NLn},
  With[{body := 
	1/((p20-m2^2)(p31-m3^2)) (Log[m3^2/(m3^2-p31)](2 NLn[(m2^2-p21)/(m2^2-p20),(p20-p21)]+Log[m3^2/(m3^2-p31)])-2 NDiLog[(p21-p20)/(m2^2-p20),-p20+p21]+
	If[m2!=0,
	  Module[{r1=(-m2^2-m3^2+Sqrt[-4 m2^2 m3^2+(m2^2+m3^2-p32)^2]+p32)/(2 m2^2),r2=(-m2^2-m3^2-Sqrt[-4 m2^2 m3^2+(m2^2+m3^2-p32)^2]+p32)/(2 m2^2)},
		NContinuedDiLog[(m3^2-p31)/(m2^2-p21),-m2^2+m3^2+p21-p31,-(1/r1),-m3^2/r1+m2^2 r1]+
		NContinuedDiLog[(m3^2-p31)/(m2^2-p21),-m2^2+m3^2+p21-p31,-(1/r2),-m3^2/r2+m2^2 r2]-\[Pi]^2/8
	  ],
	\[Pi]^2/24+NContinuedDiLog[(m3^2-p31)/-p21,m3^2+p21-p31,(m3^2-p32)/m3^2,-1]
	])
  },

  With@@Hold[{NContinuedDiLog=ContinuedDiLog[{#1,#2},{#3,#4}]&, NDiLog=DiLog}, 
	NScalarD0IR12AP = Function@@Hold[{p21,p32,p20,p31,m2,m3}, body]];

  With@@Hold[{NContinuedDiLog=X`Private`NContinuedDiLog, NDiLog=X`Private`NDiLog},
	NScalarD0IR12MP := NScalarD0IR12MP = Compile[{{p21,_Complex},{p32,_Complex},{p20,_Complex},{p31,_Complex},{m2,_Complex},{m3,_Complex}}, body]]
  ]
];


(*Machine precision evaluation, using compiled code*)
expr : ScalarD0IR12[p21_?Internal`RealValuedNumericQ,p32_?Internal`RealValuedNumericQ,p20_?Internal`RealValuedNumericQ,p31_?Internal`RealValuedNumericQ,m2_?NonNegative,m3_?NonNegative] /; Precision[Hold[expr]]===MachinePrecision := 
	Which[
	  p21-m2^2==0, Message[ScalarD0IR12::irdiv, "Soft"]; ComplexInfinity,
	  m3==0, Message[ScalarD0IR12::irdiv, "Collinear"]; ComplexInfinity,
	  p20==m2^2 || p31==m3^2, Message[ScalarD0IR12::irdiv, "Threshold"]; ComplexInfinity,
	  True, NScalarD0IR12MP[p21,p32,p20,p31,m2,m3]
	];


(*Arbitrary precision evaluation, using native Mathematica functions*)
expr : ScalarD0IR12[p21_?Internal`RealValuedNumericQ,p32_?Internal`RealValuedNumericQ,p20_?Internal`RealValuedNumericQ,p31_?Internal`RealValuedNumericQ,m2_?NonNegative,m3_?NonNegative] /; Precision[Hold[expr]]<\[Infinity] := 
	Which[
	  p21-m2^2==0, Message[ScalarD0IR12::irdiv, "Soft"]; ComplexInfinity,
	  m3==0, Message[ScalarD0IR12::irdiv, "Collinear"]; ComplexInfinity,
	  p20==m2^2 || p31==m3^2, Message[ScalarD0IR12::irdiv, "Threshold"]; ComplexInfinity,
	  True, (*NScalarD0IR12AP[p21,p32,p20,p31,m2,m3]*)X`Internal`ToTargetPrecision[NScalarD0IR12AP,{p21,p32,p20,p31,m2,m3}]
	];


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


ScalarD0IR12[p21_,p32_,p20_,p31_,m2_,m3_] /; (PossibleZeroQ[p21-m2^2]) := (Message[ScalarD0IR12::irdiv, "Soft"]; ComplexInfinity);
ScalarD0IR12[p21_,p32_,p20_,p31_,m2_,m3_] /; (PossibleZeroQ[m3]) := (Message[ScalarD0IR12::irdiv, "Collinear"]; ComplexInfinity);
ScalarD0IR12[p21_,p32_,p20_,p31_,m2_,m3_] /; (PossibleZeroQ[p20-m2^2] || PossibleZeroQ[p31-m3^2]) := (Message[ScalarD0IR12::irdiv, "Threshold"]; ComplexInfinity);


ScalarD0IR12[0,0,0,0,m2_,m3_] := 1/( m2^2 m3^2) (-(\[Pi]^2/8)+PolyLog[2,1-m3^2/m2^2]);


(* ::Subsubsection::Closed:: *)
(*Derivatives*)


Derivative[n1_Integer?Positive,n2_Integer,n3_Integer,n4_Integer,n5_Integer,n6_Integer][ScalarD0IR12] ^:= Derivative[n1-1,n2,n3,n4,n5,n6][Function[{s2,s3,s12,s23,m2,m3},(s3 DiscB[s3,m2,m3])/((m2^2-s12) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))+((-m2^2 m3^2+m3^4+2 m3^2 s2-m2^2 s23-m3^2 s23-m3^2 s3+s23 s3) Log[m2^2/m3^2])/(2 (m2^2-s12) (m3^2-s23) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))-(2 Log[m2^2/(m2^2-s12)])/((m2^2-s12) (s12-s2) (m3^2-s23))+((m2^4 m3^2 s12-m2^2 m3^4 s12-3 m2^4 m3^2 s2+3 m2^2 m3^4 s2-m2^2 m3^2 s12 s2-m3^4 s12 s2+5 m2^2 m3^2 s2^2-m3^4 s2^2-2 m3^2 s2^3+2 m2^6 s23-2 m2^4 m3^2 s23-m2^4 s12 s23+3 m2^2 m3^2 s12 s23-3 m2^4 s2 s23-3 m2^2 m3^2 s2 s23+m2^2 s12 s2 s23+m3^2 s12 s2 s23+m2^2 s2^2 s23+m3^2 s2^2 s23+2 m2^4 s23^2-2 m2^2 s12 s23^2+2 m2^4 m3^2 s3-m2^2 m3^2 s12 s3-3 m2^2 m3^2 s2 s3+m3^2 s12 s2 s3+m3^2 s2^2 s3-2 m2^4 s23 s3+m2^2 s12 s23 s3+3 m2^2 s2 s23 s3-s12 s2 s23 s3-s2^2 s23 s3) Log[m2^2/(m2^2-s2)])/((m2^2-s12) (m2^2-s2) (s12-s2) (m3^2-s23) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))+((-m2^2 m3^2+m3^4+2 m3^2 s2-m2^2 s23-m3^2 s23-m3^2 s3+s23 s3) Log[m3^2/(m3^2-s23)])/((m2^2-s12) (m3^2-s23) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))]];
Derivative[n1_Integer,n2_Integer?Positive,n3_Integer,n4_Integer,n5_Integer,n6_Integer][ScalarD0IR12] ^:= Derivative[n1,n2-1,n3,n4,n5,n6][Function[{s2,s3,s12,s23,m2,m3},-((s3 (m2^4-m2^2 m3^2-m2^2 s2-m3^2 s2+2 m2^2 s23-m2^2 s3+s2 s3) DiscB[s3,m2,m3])/((m2^2-s12) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3) (m2^4-2 m2^2 m3^2+m3^4-2 m2^2 s3-2 m3^2 s3+s3^2)))+((m2^2-s2) Log[m2^2/m3^2])/(2 (m2^2-s12) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))+((-m2^2+s2) Log[m2^2/(m2^2-s2)])/((m2^2-s12) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))+((m2^2-s2) Log[m3^2/(m3^2-s23)])/((m2^2-s12) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))]];
Derivative[n1_Integer,n2_Integer,n3_Integer?Positive,n4_Integer,n5_Integer,n6_Integer][ScalarD0IR12] ^:= Derivative[n1,n2,n3-1,n4,n5,n6][Function[{s2,s3,s12,s23,m2,m3},Log[m2^2/m3^2]^2/(4 (m2^2-s12)^2 (m3^2-s23))+(2 (m2^2-s2) Log[m2^2/(m2^2-s12)])/((m2^2-s12)^2 (s12-s2) (m3^2-s23))-(2 (m2^2-s2) Log[m2^2/(m2^2-s2)])/((m2^2-s12)^2 (s12-s2) (m3^2-s23))+(2 Log[m3^2/(m3^2-s23)])/((m2^2-s12)^2 (m3^2-s23))+Log[m2^2/m3^2] (1/((m2^2-s12)^2 (m3^2-s23))+Log[m2^2/(m2^2-s12)]/((m2^2-s12)^2 (m3^2-s23))-Log[m2^2/(m2^2-s2)]/((m2^2-s12)^2 (m3^2-s23))+Log[m3^2/(m3^2-s23)]/((m2^2-s12)^2 (m3^2-s23)))+ScalarD0IR12[s2,s3,s12,s23,m2,m3]/(m2^2-s12)]];
Derivative[n1_Integer,n2_Integer,n3_Integer,n4_Integer?Positive,n5_Integer,n6_Integer][ScalarD0IR12] ^:= Derivative[n1,n2,n3,n4-1,n5,n6][Function[{s2,s3,s12,s23,m2,m3},-(((m2^2-s2) s3 DiscB[s3,m2,m3])/((m2^2-s12) (m3^2-s23) (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3)))+Log[m2^2/m3^2]^2/(4 (m2^2-s12) (m3^2-s23)^2)+(2 Log[m2^2/(m2^2-s12)])/((m2^2-s12) (m3^2-s23)^2)-((m2^2-s2) (m2^2 m3^2-m3^4-2 m3^2 s2+m2^2 s23+m3^2 s23+m3^2 s3-s23 s3) Log[m2^2/(m2^2-s2)])/((m2^2-s12) (m3^2-s23)^2 (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))-Log[m2^2/(m3^2-s23)]/((m2^2-s12) (m3^2-s23) s23)+((-m2^2 m3^4 s2+m3^6 s2+m3^4 s2^2+2 m2^4 m3^2 s23-2 m2^2 m3^4 s23-3 m2^2 m3^2 s2 s23-m3^4 s2 s23+m3^2 s2^2 s23+3 m2^2 m3^2 s23^2-m2^2 s23^3+m2^2 m3^4 s3-m3^4 s2 s3-m2^2 m3^2 s23 s3+m3^2 s2 s23 s3) Log[m3^2/(m3^2-s23)])/((m2^2-s12) (m3^2-s23)^2 s23 (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))+Log[m2^2/m3^2] ((-2 m2^2 m3^4 s2+2 m3^6 s2+2 m3^4 s2^2+3 m2^4 m3^2 s23-3 m2^2 m3^4 s23-3 m2^2 m3^2 s2 s23-3 m3^4 s2 s23-m2^4 s23^2+5 m2^2 m3^2 s23^2+m2^2 s2 s23^2+m3^2 s2 s23^2-2 m2^2 s23^3+2 m2^2 m3^4 s3-2 m3^4 s2 s3-3 m2^2 m3^2 s23 s3+3 m3^2 s2 s23 s3+m2^2 s23^2 s3-s2 s23^2 s3)/(2 (m2^2-s12) (m3^2-s23)^2 s23 (-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2+m2^4 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m2^2 m3^2 s3-m3^2 s2 s3-m2^2 s23 s3+s2 s23 s3))+Log[m2^2/(m2^2-s12)]/((m2^2-s12) (m3^2-s23)^2)-Log[m2^2/(m2^2-s2)]/((m2^2-s12) (m3^2-s23)^2)+Log[m3^2/(m3^2-s23)]/((m2^2-s12) (m3^2-s23)^2))+ScalarD0IR12[s2,s3,s12,s23,m2,m3]/(m3^2-s23)]];


LHS_ScalarD0IR12:=RuleCondition[X`Internal`CheckArgumentCount[LHS,6,6];Fail];


(* ::Subsection:: *)
(*ScalarD0IR13*)


(* ::Subsubsection::Closed:: *)
(*Numeric evaluation*)


SetAttributes[ScalarD0IR13, NumericFunction];


With[{NLn=X`Private`NLn},
  With[{body :=
	Module[{p21=sb, p32=sc, p30=sd, p20=sab, p31=sbc, m2=mc, m3=md},
    Which[
	  (*Exteral invariants vanishing*)
	  sb==0 && sc==0 && sd==0 && sab==0 && sbc==0,
		If[mc==md, -(2/mc^4), -(1/(mc^2 md^2))+Log[mc^2/md^2]/(md^2 (-mc^2+md^2))],
	  sb==0 && sd==0 && sab==0 && sbc==0,
	    -(((mc^2-md^2) Log[mc^2/md^2])/(2 mc^2 md^2 sc))+(Sqrt[mc^4-2 mc^2 md^2+md^4-2 mc^2 sc-2 md^2 sc+sc^2] Log[(mc^2+md^2-sc+Sqrt[mc^4-2 mc^2 md^2+md^4-2 mc^2 sc-2 md^2 sc+sc^2])/(2 mc md)])/(mc^2 md^2 sc),
	  (*Internal masses vanishing*)
	  mc==0 && md==0,
		1/(p20 p31-p21 p30)*((1/2 NLn[p21/p30,p30-p21]+NLn[p32/p30,p30-p32])(NLn[p30/p20,p20-p30]-NLn[p31/p21,p21-p31])+2NDiLog[(p20-p21)/-p21,p20-p21]-2NDiLog[(p30-p31)/-p31,p30-p31]-
		2NContinuedDiLog[p31/p21,p21-p31,p20/p30,p30-p20]+1/2 NLn[p30/p20,p20-p30]^2-1/2 NLn[p31/p21,p21-p31]^2),
	  (*At least one mass nonvanishing*)
      True,
		If[md==0, p21=sd; p32=sc; p30=sb; p20=sbc; p31=sab; m2=0+0I; m3=mc,
				 p21=sb; p32=sc; p30=sd; p20=sab; p31=sbc; m2=mc; m3=md];

	1/((p20-m2^2)(p31-m3^2)-(p21-m2^2)(p30-m3^2))*
	  ((NLn[(m3^2-p30)/(m2^2-p20),-m2^2+m3^2+p20-p30]-NLn[(m3^2-p31)/(m2^2-p21),-m2^2+m3^2+p21-p31])(1/2 NLn[(m2^2-p21)/(m3^2-p30),m2^2-m3^2-p21+p30]+Log[m3^2/(m3^2-p30)])+
	  2 NDiLog[(p20-p21)/(m2^2-p21),p20-p21]-2 NDiLog[(p30-p31)/(m3^2-p31),p30-p31]-2 NContinuedDiLog[(m3^2-p31)/(m2^2-p21),-m2^2+m3^2+p21-p31,(m2^2-p20)/(m3^2-p30),m2^2-m3^2-p20+p30]+
	  Which[
		p32==0,
		(NDiLog[1-(m3^2-p31)/(m2^2-p21),m2^2-m3^2-p21+p31]-NDiLog[1-(m3^2-p30)/(m2^2-p20),m2^2-m3^2-p20+p30])+(NDiLog[1-m2^2/m3^2 (m3^2-p31)/(m2^2-p21),m2^2-m3^2-p21+p31]-NDiLog[1-m2^2/m3^2 (m3^2-p30)/(m2^2-p20),m2^2-m3^2-p20+p30]),
		m2==0,
		NContinuedDiLog[(m3^2-p31)/-p21,m3^2+p21-p31,(m3^2-p32)/m3^2,-1]-NContinuedDiLog[(m3^2-p30)/-p20,+m3^2+p20-p30,(m3^2-p32)/m3^2,-1],
		True,

		 Module[{x3=(-m2^2-m3^2+p32-Sqrt[-4 m2^2 m3^2+(m2^2+m3^2-p32)^2])/(2m3^2), x4=(-m2^2-m3^2+p32+Sqrt[-4 m2^2 m3^2+(m2^2+m3^2-p32)^2])/(2m3^2)},
		  -NContinuedDiLog[(m3^2-p30)/(m2^2-p20),(-m2^2+m3^2+p20-p30),-x3,-m3^2 x3+m2^2/x3]-
		  NContinuedDiLog[(m3^2-p30)/(m2^2-p20),(-m2^2+m3^2+p20-p30),-x4,-m3^2 x4+m2^2/x4]+
		  NContinuedDiLog[(m3^2-p31)/(m2^2-p21),(-m2^2+m3^2+p21-p31),-x3,-m3^2 x3+m2^2/x3]+
		  NContinuedDiLog[(m3^2-p31)/(m2^2-p21),(-m2^2+m3^2+p21-p31),-x4,-m3^2 x4+m2^2/x4]
		]
	  ])
    ]
  ]},

  With@@Hold[{NContinuedDiLog=ContinuedDiLog[{#1,#2},{#3,#4}]&, NDiLog=DiLog}, 
	NScalarD0IR13AP = Function@@Hold[{sb,sc,sd,sab,sbc,mc,md}, body]];

  With@@Hold[{NContinuedDiLog=X`Private`NContinuedDiLog, NDiLog=X`Private`NDiLog},
	NScalarD0IR13MP := NScalarD0IR13MP = Compile[{{sb,_Complex},{sc,_Complex},{sd,_Complex},{sab,_Complex},{sbc,_Complex},{mc,_Complex},{md,_Complex}}, body]]
  ]
];


(*Machine precision evaluation, using compiled code*)
expr : ScalarD0IR13[s2_?Internal`RealValuedNumericQ, s3_?Internal`RealValuedNumericQ, s4_?Internal`RealValuedNumericQ, s12_?Internal`RealValuedNumericQ, s23_?Internal`RealValuedNumericQ, m2_?NonNegative, m3_?NonNegative] /; Precision[Hold[expr]]===MachinePrecision :=
  Which[
	s4==m3^2 || s2==m2^2, Message[ScalarD0IR13::irdiv, "Soft"]; ComplexInfinity,
	s12==m2^2 || s23==m3^2, Message[ScalarD0IR13::irdiv, "Threshold"]; ComplexInfinity,
	True, NScalarD0IR13MP[s2, s3, s4, s12, s23, m2, m3]
  ];

(*Arbitrary precision evaluation, using native Mathematica functions*)
expr : ScalarD0IR13[s2_?Internal`RealValuedNumericQ, s3_?Internal`RealValuedNumericQ, s4_?Internal`RealValuedNumericQ, s12_?Internal`RealValuedNumericQ, s23_?Internal`RealValuedNumericQ, m2_?NonNegative, m3_?NonNegative] /; Precision[Hold[expr]]<\[Infinity] :=
  Which[
	s4==m3^2 || s2==m2^2, Message[ScalarD0IR13::irdiv, "Soft"]; ComplexInfinity,
	s12==m2^2 || s23==m3^2, Message[ScalarD0IR13::irdiv, "Threshold"]; ComplexInfinity,
	True, (*NScalarD0IR13AP[s2, s3, s4, s12, s23, m2, m3]*)X`Internal`ToTargetPrecision[NScalarD0IR13AP,{s2,s3,s4,s12,s23,m2,m3}]
  ];


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


ScalarD0IR13[s2_,s3_,s4_,s12_,s23_,m2_,m3_] /; !OrderedQ[{s2,m2},{s4,m3}] := ScalarD0IR13[s4,s3,s2,s23,s12,m3,m2];


ScalarD0IR13[s2_,s3_,s4_,s12_,s23_,m2_,m3_] /; (PossibleZeroQ[s4-m3^2] || PossibleZeroQ[s2-m2^2])  := (Message[ScalarD0IR13::irdiv, "Soft"]; ComplexInfinity);
ScalarD0IR13[s2_,s3_,s4_,s12_,s23_,m2_,m3_] /; (PossibleZeroQ[s12-m2^2] || PossibleZeroQ[s23-m3^2]) := (Message[ScalarD0IR13::irdiv, "Threshold"]; ComplexInfinity);

ScalarD0IR13[s2_,s3_,s4_,s12_,s23_,m2_,m3_] /; !OrderedQ[{s12,s23}] := ScalarD0IR13[s4,s3,s2,s23,s12,m3,m2];


ScalarD0IR13[0,0,0,0,0,m2_,m3_] :=
  If[PossibleZeroQ[m2-m3],
	-(2/m2^4),
	-(1/(m2^2 m3^2))+Log[m2^2/m3^2]/(m3^2 (-m2^2+m3^2))
  ];


LHS_ScalarD0IR13:=RuleCondition[X`Internal`CheckArgumentCount[LHS,7,7];Fail];


(* ::Subsection:: *)
(*ScalarD0IR16*)


(* ::Subsubsection::Closed:: *)
(*Symbolic evaluation*)


SetAttributes[ScalarD0IR16, NumericFunction];


ScalarD0IR16[s2_,s3_,s12_,s23_,m1_,m2_,m3_] /; !OrderedQ[{{s2,m1},{s3,m3}}] := ScalarD0IR16[s3,s2,s12,s23,m3,m2,m1];


ScalarD0IR16[s2_,s3_,s12_,s23_,m1_,m2_,m3_] /; PossibleZeroQ[m1] || PossibleZeroQ[m3] := (Message[ScalarD0IR16::irdiv, "Collinear"]; ComplexInfinity);
ScalarD0IR16[s2_,s3_,s12_,s23_,m1_,m2_,m3_] /; PossibleZeroQ[s12 - m2^2] || PossibleZeroQ[s23 - (m1+m3)^2] := (Message[ScalarD0IR16::irdiv, "Threshold"]; ComplexInfinity);
ScalarD0IR16[s2_,s3_,s12_,s23_,m1_,m2_,m3_] /; PossibleZeroQ[s2-m1^2] && PossibleZeroQ[s3-m3^2] && PossibleZeroQ[m2] := (Message[ScalarD0IR16::irdiv, "Soft"]; ComplexInfinity);


ScalarD0IR16[0,0,0,0,m1_,m2_,m3_] := 
  Which[
	PossibleZeroQ[m1-m3] && PossibleZeroQ[m2-m3],
	-(1/m3^4),
	PossibleZeroQ[m1-m3],
	Log[m3^2/m2^2]/(m2^4-m2^2 m3^2),
	True,
	(PolyLog[2,1-m1^2/m2^2]-PolyLog[2,1-m3^2/m2^2])/(m2^2 (m1^2-m3^2))
  ];


LHS_ScalarD0IR16:=RuleCondition[X`Internal`CheckArgumentCount[LHS,7,7];Fail];


(* ::Subsection::Closed:: *)
(*D0Expand*)


refineD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :=
  Module[{
    f={s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
    gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }},
    adjZ={{s12 s4-1/4 (s12-s3+s4)^2,1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4))},{1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),s1 s4-1/4 (s1-s23+s4)^2,1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4))},{1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4)),1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4)),s1 s12-1/4 (s1+s12-s2)^2}},
    
	adjX0,
	adjXij = {{2 (-m0^4 s3-m2^4 s4-s12 (m3^4+m3^2 (s12-s3-s4)+s3 s4)+m2^2 ((s12+s3-s4) s4+m3^2 (s12-s3+s4))+m0^2 (m3^2 (s12+s3-s4)+s3 (s12-s3+s4)+m2^2 (-s12+s3+s4))),-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s12-s3+s4) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4)),(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4)-2 s12 (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))+(m0^2-m2^2+s12) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4))},{-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s1-s23+s4) (-(m0^2-m2^2+s12) (m0^2-m3^2+s4)+2 m0^2 (s12-s3+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s12-s3+s4)),2 (-m0^4 s23-m1^4 s4-s1 (m3^4+m3^2 (s1-s23-s4)+s23 s4)+m1^2 ((s1+s23-s4) s4+m3^2 (s1-s23+s4))+m0^2 (m3^2 (s1+s23-s4)+s23 (s1-s23+s4)+m1^2 (-s1+s23+s4))),-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4)+(s1+s12-s2) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m2^2+s12) (-2 s1 (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s1-s23+s4))},{(2 (m0^2-m1^2+s1) s12-(m0^2-m2^2+s12) (s1+s12-s2)) (m0^2-m3^2+s4)-(4 m0^2 s12-(m0^2-m2^2+s12)^2) (s1-s23+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4),-(-2 s1 (m0^2-m2^2+s12)+(m0^2-m1^2+s1) (s1+s12-s2)) (m0^2-m3^2+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s1-s23+s4)-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4),2 (-m1^4 s12-m0^4 s2-s1 (m2^4+m2^2 (s1-s12-s2)+s12 s2)+m1^2 (m2^2 (s1+s12-s2)+s12 (s1-s12+s2))+m0^2 ((s1+s12-s2) s2+m2^2 (s1-s12+s2)+m1^2 (-s1+s12+s2)))}},
    
    j,k},
  
	adjX0=Table[Sum[adjZ[[j,k]]f[[k]],{k,1,3}],{j,1,3}];
  
  Which[
    X`Internal`PossibleAllZeroQ[gramZ] && X`Internal`PossibleAllZeroQ[f] && !(PossibleZeroQ[m0]),
    (*Print["Case 6: gramZ & f vanishing."];*)
      ReplaceRepeated[passVeltD[0,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineRulesDcase6],

    X`Internal`PossibleAllZeroQ[gramZ] && !(X`Internal`PossibleAllZeroQ[f]),
    (*Print["Case 5: gramZ vanishing but f non-vanishing.  f=", f];*)
      With[{siga=First@Ordering[f,1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
		(*Print["f=", f, "  sig:", siga];*)
        ReplaceRepeated[passVeltD[0,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDcase5a[[siga]],refineRulesDcase5b}]
      ],
  
	PossibleZeroQ[s12] && PossibleZeroQ[s3-s4] && PossibleZeroQ[s1-s2],
	  Replace[passVeltD[0,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],
		If[PossibleZeroQ[m0-m2],refineRulesDcaseX4,refineRulesDcaseX3]],

	PossibleZeroQ[s23] && PossibleZeroQ[s3-s2] && PossibleZeroQ[s1-s4],
	  Replace[passVeltD[0,0,0,0,s3,s2,s1,s4,s23,s12,m3,m2,m1,m0],
		If[PossibleZeroQ[m3-m1],refineRulesDcaseX4,refineRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s1] && PossibleZeroQ[s23-s4] && PossibleZeroQ[s12-s2],
	  Replace[passVeltD[0,0,0,0,s12,s2,s23,s4,s1,s3,m0,m2,m1,m3],
		If[PossibleZeroQ[m0-m1],refineRulesDcaseX4,refineRulesDcaseX3]],

	PossibleZeroQ[s2] && PossibleZeroQ[s1-s12] && PossibleZeroQ[s3-s23],
	  Replace[passVeltD[0,0,0,0,s1,s12,s3,s23,s2,s4,m1,m0,m2,m3],
		If[PossibleZeroQ[m1-m2],refineRulesDcaseX4,refineRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s3] && PossibleZeroQ[s23-s2] && PossibleZeroQ[s12-s4],
	  Replace[passVeltD[0,0,0,0,s23,s2,s12,s4,s3,s1,m3,m1,m2,m0],
		If[PossibleZeroQ[m3-m2],refineRulesDcaseX4,refineRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s4] && PossibleZeroQ[s1-s23] && PossibleZeroQ[s3-s12],
	  Replace[passVeltD[0,0,0,0,s1,s23,s3,s12,s4,s2,m0,m1,m3,m2],
		If[PossibleZeroQ[m0-m3],refineRulesDcaseX4,refineRulesDcaseX3]],



	PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0] && !(X`Internal`PossibleAllZeroQ[adjZ]) && !(X`Internal`PossibleAllZeroQ[adjXij]),
	(*Print["Case 4 PVD: det Z=0, adjX0=0"];*)
	  With[{siga=First@Ordering[Flatten[Simplify[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
			sigb=First@Ordering[Flatten[Simplify[adjXij]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
			(*Print["adjZ=", adjZ, "  sig:", siga];*)
			(*Print["adjXij=", adjXij, "  sig:", sigb];*)
			KallenExpand@ReplaceRepeated[passVeltD[0,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDcase4a[[siga]],refineRulesDcase4b[[sigb]],refineRulesDcase4c[[sigb]]}]
	  ],

    
    PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3 PVD: detZ=0"];*)
      With[{
        siga=First@Ordering[Flatten[Simplify[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
        sigb=First@Ordering[Simplify[adjX0],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
        (*Print["adjZ=", adjZ, "  sig:", siga];*)
		(*Print["adjX0=", adjX0, "  sig:", sigb];*)
        KallenExpand@ReplaceRepeated[passVeltD[0,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDcase3a[[siga]],refineRulesDcase3b[[sigb]]}]
      ],


	True,
	ScalarD0[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]
  ]
 
  
];


D0Expand[expr_]:=
  Catch[expr /. 
	{pv: ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> 
	  Module[{result, intMass = Variables[{m0,m1,m2,m3}]},
		(*First see if it can be refineD for detZ=0*)
		result = refineD0[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];
		If[Head[result]=!=ScalarD0,
		(*If it was refineD, then optimize expression*)
		  If[NumericQ[pv],
			result = result /. passVeltC[0,0,0,p1_,q_,p2_,ma_,mb_,mc_] :> Coefficient[refineC0[p1,q,p2,ma,mb,mc],Eps,0],
			result = result /. passVeltC[0,0,0,p1_,q_,p2_,ma_,mb_,mc_] :> ScalarC0[p1,q,p2,ma,mb,mc]
		  ];

		  result = Coefficient[result,Eps,0];
		  result = If[!FreeQ[result,FeynmanIRepsilon],
					If[!(PossibleZeroQ[D[result,FeynmanIRepsilon]]), Message[D0Expand::irdiv,"Non-logarithmic (power) infrared"];Throw[ComplexInfinity, "PowerIRSingularity"];],
					result/.FeynmanIRepsilon->0
				   ];

		  If[intMass=!={}, result = result/.Mu->First[intMass]];
		  result = expressionOptimizer[result, intMass, {1}, "FunctionExpand"],

		(*Otherwise use lookup table (they are simplified on an individual basis)*)
		  With[{res=analD0[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]},
			If[Head[res]===analD0, 
			  ScalarD0[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],
			  res]
		  ]
		]
		
	  ]
	 ,HoldPattern[ScalarD0IR16[args___]] /; FreeQ[{args},Complex]:> pvD0IR16force[args]
	 ,HoldPattern[ScalarD0IR13[args___]] /; FreeQ[{args},Complex]:> pvD0IR13force[args]
	 ,HoldPattern[ScalarD0IR12[args___]] /; FreeQ[{args},Complex]:> pvD0IR12force[args]}
  ,"PowerIRSingularity"];


(* ::Section:: *)
(*Library of analytic formulae*)


(* ::Subsection:: *)
(*Scalar C function*)


(* ::Subsubsection::Closed:: *)
(*Simple cases*)


(*analC0 will be converted if ExplicitC0 -> Automatic *)
(*analC0force will also be converted if ExplicitC0 -> All*)

SetAttributes[{analC0,analC0force},Orderless];


(*One nonzero external invariant. *)
(*Two vanishing masses*)
analC0[{0,0},{0,0},{q_,m0_}]:=1/q (\[Pi]^2/6+1/2 Log[-(m0^2/q)]^2+PolyLog[2,(m0^2+q)/q]);

(*One vanishing mass*)
analC0[{0,m0_},{0,m0_},{m0_^2,0}]:=-\[Pi]^2/(9 m0^2);
analC0[{0,0},{0,m0_},{q_,m0_}]:=-1/q DiLog[q/m0^2,1];
analC0[{0,0},{0,m1_},{q_,m0_}]:=1/q (PolyLog[2,1-m1^2/m0^2]-DiLog[1+(q-m1^2)/m0^2,1]);

(*No vanishing masses*)
analC0[{0,m0_},{0,m0_},{m0_^2,m0_}]:=-(\[Pi]^2/(18 m0^2));
analC0[{0,m0_},{0,m0_},{q_,m0_}]:=1/(2q) Log[1-(q-Sqrt[q(q-4 m0^2)])/(2 m0^2)]^2;

(*Two non-zero external invariants*)
analC0[{m0_^2,0},{0,0},{q_,m0_}]:=(Log[m0^2/q]Log[-(m0^2/q)]-1/2 Log[m0^2/q]^2)/(q-m0^2);
analC0[{0,0},{m_^2,m_},{q_,m_}]:=1/(q-m^2)(\[Pi]^2/6-simplifyDiLog[q/m^2,q]);
analC0[{0,m0_},{m0_^2,m0_},{q_,m0_}]:=-(\[Pi]^2/(9 (2 m0^2-2 q)))-Log[1+(-q+Sqrt[q (-4 m0^2+q)])/(2 m0^2)]^2/(2 (m0^2-q));
analC0[{0,m_},{p2_,m_},{q_,m_}]:=1/(2(p2-q)) (FunctionExpand[Log[1+(-p2+Sqrt[p2 (-4 m^2+p2)])/(2 m^2)]]^2-FunctionExpand[Log[1+(-q+Sqrt[q (-4 m^2+q)])/(2 m^2)]]^2);

(*Three non-zero external invariants*)
analC0[{s_,0},{s_,0},{s_,0}]:=(PolyGamma[1,1/3]-PolyGamma[1,2/3])/(3 s);

(*If it fails to match*)
(*_analC0:=Fail;*)


(* ::Subsubsection::Closed:: *)
(*Complicated cases*)


(*One external invariant non-vanishing*)
analC0force[{0,m2_},{0,m1_},{q_,m1_}]:=1/q *(PolyLog[2,1-m2^2/m1^2]-simplifyDiLog[(2 q)/(m1^2-m2^2+q+Sqrt[Kallen\[Lambda][q,m2^2,m1^2]]),-1]-
    simplifyDiLog[(2 q)/(m1^2-m2^2+q-Sqrt[Kallen\[Lambda][q,m2^2,m1^2]]),1]);

(*From QCDTools and also checked by hand*)
analC0force[{0,m_},{0,m_},{s_,0}]:=1/s (-(\[Pi]^2/6)+1/2 Log[(2 m^2-s+Sqrt[s (-4 m^2+s)])/(s+Sqrt[s (-4 m^2+s)])]^2-1/2 Log[(s+Sqrt[s (-4 m^2+s)])/(2 s)]^2+PolyLog[2,1-s/m^2]+PolyLog[2,(2 m^2)/(2 m^2-s+Sqrt[s (-4 m^2+s)])]-PolyLog[2,(2 m^2)/(s+Sqrt[s (-4 m^2+s)])]+PolyLog[2,(-2 m^2+2 s)/(s+Sqrt[s (-4 m^2+s)])]-PolyLog[2,-((2 (m^2-s))/(-2 m^2+s+Sqrt[s (-4 m^2+s)]))]);

analC0force[{0,m2_},{0,m1_},{q_,m0_}]:=
	1/q * (
	simplifyDiLog[((m0^2-m2^2) (m0^2-m1^2+q))/(m0^4+m1^2 m2^2-m0^2 (m1^2+m2^2-q)),-1]-
    simplifyDiLog[((m0^2-m1^2) (m0^2-m2^2))/(m0^4+m1^2 m2^2-m0^2 (m1^2+m2^2-q)),-1]-
    simplifyDiLog[(2 (m0^2-m1^2+q))/(2 m0^2-m1^2-m2^2+q+Sqrt[Kallen\[Lambda][q,m2^2,m1^2]]),-q(m0^2-m1^2+q)]+
    simplifyDiLog[(2 (m0^2-m1^2))/(2 m0^2-m1^2-m2^2+q+Sqrt[Kallen\[Lambda][q,m2^2,m1^2]]),-(m0^2-m1^2) q]-
    simplifyDiLog[(2 (m0^2-m1^2+q))/(2 m0^2-m1^2-m2^2+q-Sqrt[Kallen\[Lambda][q,m2^2,m1^2]]),q(m0^2-m1^2+q)]+
    simplifyDiLog[(2 (m0^2-m1^2))/(2 m0^2-m1^2-m2^2+q-Sqrt[Kallen\[Lambda][q,m2^2,m1^2]]),(m0^2-m1^2) q]
	);


(*Two external invariants non-vanishing*)

analC0force[{p1_,m2_},{0,0},{q_,0}]:=-(1/(q-p1))(-PolyLog[2,q/p1]+simplifyDiLog[((m2^2+p1-q) q)/(m2^2 p1),(p1-q) (m2^2+p1-q) q]+\[Pi]^2/6-simplifyDiLog[(m2^2+p1-q)/m2^2,p1]);

analC0force[{p1_,m0_},{0,0},{q_,m0_}]:=1/(p1-q) (1/2 Log[-(m0^2/p1)]^2-1/2 Log[-(m0^2/q)]^2+PolyLog[2,m0^2/p1]-PolyLog[2,m0^2/q]);

analC0force[{p1_,m2_},{0,m1_},{q_,m0_}]:=
  Module[
	{dilogArg=Function[{pa,pc,ma,mb,mc,sgn,term},(2 ma^2 pa-2 mc^2 pc+2 mb^2 (-pa+pc)+pa (pa-pc) (1+term))/(2 ma^2 pa+pa (-mc^2+pa)-(mc^2+pa) pc+mb^2 (-pa+pc)+(pa-pc) sgn rootKallen[pa,mb^2,mc^2])],
	 dilogEps=Function[{pa,pc,ma,mb,mc,sgn,term}, sgn*Which[(PossibleZeroQ[mb] && PossibleZeroQ[mc]) || PossibleZeroQ[pa-(mb+mc)^2](*Both channel masses vanishing, or threshold*),
				1/pa,
				PossibleZeroQ[mc] (*Second channel mass vanishing*),
				(*mb^2-pa*)pa-mb^2,
				PossibleZeroQ[mb] (*First channel mass vanishing*),
				pa-mc^2,
				True (*Both masses non-vanishing*),
				1]*(-pa^2 (pc-pa)^2 term+pa (pc-pa)^2 (mb^2-mc^2)-pa(pc-pa)(-pa^2+pa(pc+mc^2+mb^2)+pc(mc^2-mb^2)-2ma^2 pa))]},

	1/(q-p1)*(
	Sum[term simplifyDiLog[dilogArg[p1,q,m2,m1,m0,sgn,term],dilogEps[p1,q,m2,m1,m0,sgn,term]]
		-term simplifyDiLog[dilogArg[q,p1,m0,m1,m2,sgn,term],dilogEps[q,p1,m0,m1,m2,sgn,term]], {sgn,{-1,1}}, {term,{-1,1}}] 

	+ If[!PossibleZeroQ[m0-m2],
		simplifyDiLog[((m0^2-m2^2) (-m2^2 p1+m1^2 (p1-q)+q (m0^2-p1+q)))/(m0^4 q+m2^2 (p1 (m2^2+p1-q)+m1^2 (-p1+q))+m0^2 (m1^2 (p1-q)+q (-p1+q)-m2^2 (p1+q))),-1]
		-simplifyDiLog[((-m0^2+m2^2) (m2^2 p1+p1^2-m0^2 q-p1 q+m1^2 (-p1+q)))/(m0^4 q+m2^2 (p1 (m2^2+p1-q)+m1^2 (-p1+q))+m0^2 (m1^2 (p1-q)+q (-p1+q)-m2^2 (p1+q))),-1],
		0]
	)
];


(*All external invariants non-vanishing*)
analC0force[{m_^2,0},{m_^2,0},{q_,m_}]:=(2 \[Pi]^2)/(3 Sqrt[1-(4 m^2)/q] q)+Log[1+(-q+q Sqrt[1-(4 m^2)/q])/(2 m^2)]^2/(2 Sqrt[1-(4 m^2)/q] q)+(2 PolyLog[2,1+(-q+q Sqrt[1-(4 m^2)/q])/(2 m^2)])/(Sqrt[1-(4 m^2)/q] q);
analC0force[{p1_,0},{p1_,0},{q_,0}] :=2/Sqrt[q (-4 p1+q)] (PolyLog[2,-((-2 p1+q-Sqrt[q (-4 p1+q)])/(2 p1))]-PolyLog[2,-((-2 p1+q+Sqrt[q (-4 p1+q)])/(2 p1))]);
analC0force[{p1_,0},{p2_,0},{q_,0}] := -(PolyLog[2,(p1+p2-q-Sqrt[Kallen\[Lambda][p1,p2,q]])/(p1+p2-q+Sqrt[Kallen\[Lambda][p1,p2,q]])]/Sqrt[Kallen\[Lambda][p1,p2,q]])+PolyLog[2,(p1+p2-q+Sqrt[Kallen\[Lambda][p1,p2,q]])/(p1+p2-q-Sqrt[Kallen\[Lambda][p1,p2,q]])]/Sqrt[Kallen\[Lambda][p1,p2,q]]-PolyLog[2,(p1-p2+q-Sqrt[Kallen\[Lambda][p1,p2,q]])/(p1-p2+q+Sqrt[Kallen\[Lambda][p1,p2,q]])]/Sqrt[Kallen\[Lambda][p1,p2,q]]+PolyLog[2,(p1-p2+q+Sqrt[Kallen\[Lambda][p1,p2,q]])/(p1-p2+q-Sqrt[Kallen\[Lambda][p1,p2,q]])]/Sqrt[Kallen\[Lambda][p1,p2,q]]-PolyLog[2,(-p1+p2+q-Sqrt[Kallen\[Lambda][p1,p2,q]])/(-p1+p2+q+Sqrt[Kallen\[Lambda][p1,p2,q]])]/Sqrt[Kallen\[Lambda][p1,p2,q]]+PolyLog[2,-((-p1+p2+q+Sqrt[Kallen\[Lambda][p1,p2,q]])/(p1-p2-q+Sqrt[Kallen\[Lambda][p1,p2,q]]))]/Sqrt[Kallen\[Lambda][p1,p2,q]];


(*Most general expression*)
analC0force[{p1_,m2_},{p2_,m1_},{q_,m0_}]:=
Module[
	{dilogArg=
		Function[{pa,pb,pc,ma,mb,mc,sgn,term}, (-2 ma^2 pa+(mc^2-pa) (pa-pb)+mb^2 (pa+pb-pc)+(mc^2+pa) pc+(-mb^2+mc^2+pa term) Sqrt[Kallen\[Lambda][pa,pb,pc]])/(-2 ma^2 pa+(mc^2-pa) (pa-pb)+mb^2 (pa+pb-pc)+(mc^2+pa) pc+sgn rootKallen[pa,mb^2,mc^2] Sqrt[Kallen\[Lambda][pa,pb,pc]])
		],
	 dilogEps=
		Function[{pa,pb,pc,ma,mb,mc,sgn,term}, 
			sgn*
			Which[(PossibleZeroQ[mb] && PossibleZeroQ[mc]) || PossibleZeroQ[pa-(mb+mc)^2](*Both channel masses vanishing, or threshold*),
				1/pa,
				PossibleZeroQ[mc] (*Second channel mass vanishing*),
				(*mb^2-pa*)pa-mb^2,
				PossibleZeroQ[mb] (*First channel mass vanishing*),
				pa-mc^2,
				True (*Both masses non-vanishing*),
				1]*pa(pa (2 ma^2+pa-pb-pc-term Sqrt[Kallen\[Lambda][pa,pb,pc]])+ mb^2 (-pa-pb+pc+Sqrt[Kallen\[Lambda][pa,pb,pc]])- mc^2 (pa-pb+pc+Sqrt[Kallen\[Lambda][pa,pb,pc]]))
		]
	},

	ConditionalExpression[1/Sqrt[Kallen\[Lambda][q,p1,p2]]*
		Sum[term simplifyDiLog[dilogArg[p1,p2,q,m2,m1,m0,sgn,term],dilogEps[p1,p2,q,m2,m1,m0,sgn,term]] + 
			term simplifyDiLog[dilogArg[q,p1,p2,m0,m2,m1,sgn,term],dilogEps[q,p1,p2,m0,m2,m1,sgn,term]] + 
			term simplifyDiLog[dilogArg[p2,q,p1,m1,m0,m2,sgn,term],dilogEps[p2,q,p1,m1,m0,m2,sgn,term]],{sgn,{-1,1}},{term,{-1,1}}],
		Refine[Kallen\[Lambda][q,p1,p2]>0]]
];


(* ::Subsection::Closed:: *)
(*ScalarC0IR6*)


pvC0IR6force[s_,m0_,m1_] /; PossibleZeroQ[s-(m0-m1)^2] :=-(1/(m0 m1))+((m0+m1) olog[m0^2,m1^2])/(4 m0^2 m1-4 m0 m1^2);
pvC0IR6force[s_,m_,m_] := -(\[Pi]^2/(6 Sqrt[s(s-4 m^2)]))+(DiscB[s,m,m] Log[(2 m^4-m^2 (s+Sqrt[s(s-4 m^2)]))/(2 (-4 m^2+s)^2)])/(2 (-4 m^2+s))-(2 PolyLog[2,(-2 m^2+s-Sqrt[s(-4 m^2+s)])/(2 m^2)])/Sqrt[s(s-4 m^2)];
pvC0IR6force[s_,m0_,m2_] := 1/(4 Sqrt[Kallen\[Lambda][m0^2,m2^2,s]]) (4 Log[(m0 m2)/s] Log[(2 m0 m2)/(m0^2+m2^2-s-Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])]-Log[(2 s)/(m0^2-m2^2+s-Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])]^2-Log[(m0^2-m2^2-s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])/(2 s)]^2-2 Log[(2 s)/(m0^2-m2^2+s-Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])] Log[(m0^2-m2^2+s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])/(2 s)]+Log[(m0^2-m2^2+s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])/(2 s)]^2+2 Log[(m0^2-m2^2-s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])/(2 s)] Log[-((2 s)/(-m0^2+m2^2+s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]]))]+Log[-((2 s)/(-m0^2+m2^2+s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]]))]^2-4 Log[(-m0^2+m2^2-s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])/(-m0^2+m2^2+s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])] Log[Sqrt[Kallen\[Lambda][m0^2,m2^2,s]]/s]+4 PolyLog[2,(-m0^2+m2^2-s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])/(2 Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])]-4 PolyLog[2,(-m0^2+m2^2+s+Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])/(2 Sqrt[Kallen\[Lambda][m0^2,m2^2,s]])]);


(* ::Subsection:: *)
(*Scalar D function*)


(* ::Subsubsection::Closed:: *)
(*Finite cases*)


(*Davydychev's formula arXiv: 9307323*)
permutedSetDelayed[
  analD0[0,0,0,0,s12_,s23_,m_,m_,m_,m_],
  ConditionalExpression[1/(8 m^3 Sqrt[-s23]) (\[Pi]^2+2 Log[((1+Sqrt[1-(4 m^2)/s23]) (-2 m+Sqrt[4 m^2-s23]))/Sqrt[-s23]]^2+2 Log[Sqrt[-s23]/(2 m)]^2-4 Log[-((2 m (-2 m+Sqrt[4 m^2-s23]))/s23)]^2+4 PolyLog[2,-((2 m)/Sqrt[-s23])]-4 PolyLog[2,((-1+Sqrt[1-(4 m^2)/s23]) (-2 m+Sqrt[4 m^2-s23]))/Sqrt[-s23]]-4 PolyLog[2,-(Sqrt[-s23]/(2 m))]+4 PolyLog[2,((-1+Sqrt[1-(4 m^2)/s23]) (-2 m+Sqrt[4 m^2-s23]) Sqrt[-s23])/(4 m^2)]),Simplify[s23<0]]
	/; PossibleZeroQ[s12-m^2]
];

permutedSetDelayed[
  analD0[0,0,0,0,s12_,s23_,m_,m_,m_,m_],
  ConditionalExpression[1/(s12 Sqrt[1-(4 m^2)/s12-(4 m^2)/s23] s23)2 (-(\[Pi]^2/2)-Log[((1+Sqrt[1-(4 m^2)/s12]) s23 (Sqrt[1-(4 m^2)/s12]-Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)]))/(4 m^2)]^2-Log[(s12 (1+Sqrt[1-(4 m^2)/s23]) (Sqrt[1-(4 m^2)/s23]-Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)]))/(4 m^2)]^2+Log[-((s23 (Sqrt[1-(4 m^2)/s12]-Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)])^2)/(4 m^2))] Log[-((s12 (Sqrt[1-(4 m^2)/s23]-Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)])^2)/(4 m^2))]+2 Log[-(1/(4 m^2))s12 (Sqrt[1-(4 m^2)/s12]+Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)]) (-Sqrt[1-(4 m^2)/s23]+Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)])]^2-2 PolyLog[2,-(((-1+Sqrt[1-(4 m^2)/s12]) s12 (Sqrt[1-(4 m^2)/s12]-Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)]))/(4 m^2))]+2 PolyLog[2,((-1+Sqrt[1-(4 m^2)/s12]) s23 (Sqrt[1-(4 m^2)/s12]-Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)]))/(4 m^2)]+2 PolyLog[2,(s12 (-1+Sqrt[1-(4 m^2)/s23]) (Sqrt[1-(4 m^2)/s23]-Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)]))/(4 m^2)]-2 PolyLog[2,-(((-1+Sqrt[1-(4 m^2)/s23]) s23 (Sqrt[1-(4 m^2)/s23]-Sqrt[1-(4 m^2 (s12+s23))/(s12 s23)]))/(4 m^2))]),Simplify[s12 s23 (s12 s23-4 m^2 (s12+s23))>0]]
];

(*Duplancic's and Nizic's formula arXiv:0201306*)
permutedSetDelayed[
  analD0[s1_,s2_,s3_,s4_,s12_,s23_,0,0,0,0],
  ConditionalExpression[ScalarC0[s12 s23,s1 s3,s2 s4,0,0,0],Simplify[(s12>0||s23>0)&&(s1>0||s3>0)&&(s2>0||s4>0)]]
];


(*  With the exception of subcase y01=y02=0 with m1=m2=m3=0 which I derived,
    all expressions below come from Denner and Dittmaier 2011  *)

rootsum[var_,poly_,func_]:=RootSum[Function[var,poly],Function[var,func]];

rootsumInternal[var_,poly_,List[xList_,{root_,rootEps_}]]:=
  If[(*If external invariant is on threshold with internal masses, need to specify infinitessimal parts explicitly*)
	PossibleZeroQ[Discriminant[poly,var]],
	With[{rt=root/.var->Root[poly,var,1]}, simplifyContinuedDiLog[xList,{rt,1}]+simplifyContinuedDiLog[xList,{rt,-1}]],
	rootsum[var,poly, simplifyContinuedDiLog[xList,{root,rootEps}]]
  ];


(*{y00=2 m0^2,    y01=m0^2+m1^2-s1,     y02=m0^2+m2^2-s12,  y03=m0^2+m3^2-s4,
                     y11=2 m1^2,        y12=m1^2+m2^2-s2,   y13=m1^2+m3^2-s23,
                                        y22=2 m2^2,         y23=m2^2+m3^2-s3,
                                                            y33=2 m3^2}*)


(*One nonvanishing mass, m1=m2=m3=0*)

With[{y00=2 ma^2,    y01=ma^2-sa,  y02=ma^2-sab,  y03=ma^2-sd,
                     y11=0,        y12=-sb,       y13=-sbc,
                                   y22=0,         y23=-sc,
                                                  y33=0,

permutations=
  {{sa->s1,sb->s2,sc->s3,sd->s4,sab->s12,sbc->s23,ma->m0,mb->m1,mc->m2,md->m3},
   {sa->s1,sb->s23,sc->s3,sd->s12,sab->s4,sbc->s2,ma->m0,mb->m1,mc->m3,md->m2},
   {sa->s4,sb->s3,sc->s2,sd->s1,sab->s12,sbc->s23,ma->m0,mb->m3,mc->m2,md->m1}(*,
   {sa->s12,sb->s3,sc->s23,sd->s1,sab->s4,sbc->s2,ma->m0,mb->m2,mc->m3,md->m1},
   {sa->s12,sb->s2,sc->s23,sd->s4,sab->s1,sbc->s3,ma->m0,mb->m2,mc->m1,md->m3},
   {sa->s4,sb->s23,sc->s2,sd->s12,sab->s1,sbc->s3,ma->m0,mb->m3,mc->m1,md->m2}*)}},

  With[
	 {a=y13 y23,
	   b=y02 y13+y01 y23-y03 y12,
	   c=y01 y02-ma^2 y12,
	   d=y12},

	permutedSetDelayed[analD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,0,0,0],
	  Block[{choices, sa,sb,sc,sd,sab,sbc,ma},
	  Assuming[{m0>=0},
		If[(*Check if y01 and y02 are non-zero for some permutation.*)
		   (choices=Extract[permutations,Position[(Not[pZQ[y01]] && Not[pZQ[y02]]/.permutations)/.pZQ->PossibleZeroQ,True]])=!={},
		  Set@@@First[choices];
		  rootsum[\[FormalX], Collect[\[FormalX]^2 a+\[FormalX] b+c,\[FormalX]],
			1/(2 a \[FormalX]+b)(
			  simplifyContinuedDiLog[{-\[FormalX],d/(2 a \[FormalX]+b)},{y23/y02, y23-y02}]-
			  simplifyContinuedDiLog[{-\[FormalX],d/(2 a \[FormalX]+b)},{y03/ma^2,y03-2ma^2}]+
			  simplifyContinuedDiLog[{-\[FormalX],d/(2 a \[FormalX]+b)},{y13/y01,y13-y01}]-
			  simplifyLn[-\[FormalX],d/(2 a \[FormalX]+b),{\[FormalX]}](simplifyLn[y01/y12,y01-y12]+simplifyLn[y02/ma^2,y02-2ma^2]) )],

		  Set@@@First[Extract[permutations,Position[(pZQ[y01] && pZQ[y02]/.permutations)/.pZQ->PossibleZeroQ,True]]];
		  rootsum[\[FormalX], Collect[\[FormalX]^2 a+\[FormalX] b+c,\[FormalX]],
		    1/(2 a \[FormalX]+b)(
			  -simplifyContinuedDiLog[{-\[FormalX],d/(2 a \[FormalX]+b)},{y03/ma^2,y03-2ma^2}]-
			  simplifyLn[-\[FormalX],d/(2 a \[FormalX]+b),{\[FormalX]}]^2+
			  simplifyLn[-\[FormalX],d/(2 a \[FormalX]+b),{\[FormalX]}](simplifyLn[-ma^2/sc,ma^2+sc]+simplifyLn[sb/sbc,-sb+sbc]))
		  ]
		]
	  ]
	  ]
	]

  ]
];


(*Two masses nonvanishing*)

With[{y00=2 ma^2,    y01=ma^2-sa,  y02=ma^2-sab,  y03=ma^2+md^2-sd,
                     y11=0,        y12=-sb,       y13=md^2-sbc,
                                   y22=0,         y23=md^2-sc,
                                                  y33=2 md^2,

permutations=
  {{sa->s1,sb->s2,sc->s3,sd->s4,sab->s12,sbc->s23,ma->m0,mb->m1,mc->m2,md->m3},
   {sa->s23,sb->s2,sc->s12,sd->s4,sab->s3,sbc->s1,ma->m3,mb->m1,mc->m2,md->m0}(*,
   {sa->s3,sb->s2,sc->s1,sd->s4,sab->s23,sbc->s12,ma->m3,mb->m2,mc->m1,md->m0},
   {sa->s12,sb->s2,sc->s23,sd->s4,sab->s1,sbc->s3,ma->m0,mb->m2,mc->m1,md->m3}*)}},

  With[
	  {a=y13 y23-md^2 y12,
	   b=y02 y13+y01 y23-y03 y12,
	   c=y01 y02-ma^2 y12,
	   d=y12},

	permutedSetDelayed[analD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,0,0,m3_],
	  Block[{choices, sa,sb,sc,sd,sab,sbc,ma,md},
	  Assuming[{m0>=0,m3>=0},
		If[(*Check if there y01 and y02 are non-zero for some permutation.*)
		   (choices=Extract[permutations,Position[(Not[pZQ[y01]]&&Not[pZQ[y02]]/.permutations)/.pZQ->PossibleZeroQ,True]])=!={},
		  Set@@@First[choices];
		  rootsum[\[FormalX], Collect[\[FormalX]^2 a+\[FormalX] b+c,\[FormalX]],
		    1/(2 a \[FormalX]+b) (
			simplifyContinuedDiLog[{-\[FormalX],d/(2 a \[FormalX]+b)},{y23/y02,y23-y02}]-
		    rootsumInternal[\[FormalR],ma^2+y03 \[FormalR]+md^2 \[FormalR]^2,(*ContinuedDiLog*)List[{-\[FormalX],d/(2 a \[FormalX]+b)},{-1/\[FormalR],-ma^2/\[FormalR]+md^2 \[FormalR]}]]+
		    simplifyContinuedDiLog[{-\[FormalX],d/(2 a \[FormalX]+b)},{y13/y01,y13-y01}]-
		    simplifyLn[-\[FormalX],d/(2 a \[FormalX]+b),{\[FormalX]}](simplifyLn[y01/y12,y01-y12]+simplifyLn[y02/ma^2,y02-2ma^2]))],

		  (*Pick the permutation for which y02 and y13 are nonvanishing.*)
		  Set@@@First[Extract[permutations,Position[(Not[pZQ[y02]]&&Not[pZQ[y13]]/.permutations)/.pZQ->PossibleZeroQ,True]]];
		  rootsum[\[FormalX], Collect[\[FormalX]^2 a+\[FormalX] b+c,\[FormalX],Simplify],
			1/(2 a \[FormalX]+b) (
			  -rootsumInternal[\[FormalR],ma^2+y03 \[FormalR]+md^2 \[FormalR]^2,(*ContinuedDiLog*)List[{-\[FormalX],d/(2 a \[FormalX]+b)},{-1/\[FormalR],-ma^2/\[FormalR]+md^2 \[FormalR]}]]+
			  -1/2*simplifyLn[-\[FormalX],d/(2 a \[FormalX]+b),{\[FormalX]}]^2-simplifyLn[-\[FormalX],d/(2 a \[FormalX]+b),{\[FormalX]}](simplifyLn[y13/y12,y13-y12]+simplifyLn[y02/ma^2,y02-2ma^2]))
		]

		]
	  ]
	  ]
	]

  ]

];


(*Three masses nonvanishing*)

With[
{y00=2 ma^2,    y01=ma^2+mb^2-sa,  y02=ma^2-sab,  y03=ma^2+md^2-sd,
                y11=2 mb^2,        y12=mb^2-sb,   y13=mb^2+md^2-sbc,
                                   y22=0,         y23=md^2-sc,
                                                  y33=2 md^2,

(*r13:=Refine[1/(2mb^2)*(-sbc+mb^2+md^2+Sqrt[Kallen\[Lambda][sbc,mb^2,md^2]])],*)
r13:=Refine[1/(2mb^2)*(-sbc+mb^2+md^2+rootKallen[sbc,mb^2,md^2])],

(*These are the possible kinematic configurations keeping m2=0*)
permutations=
  {{sa->s1,sb->s2,sc->s3,sd->s4,sab->s12,sbc->s23,ma->m0,mb->m1,mc->m2,md->m3},
  {sa->s4,sb->s3,sc->s2,sd->s1,sab->s12,sbc->s23,ma->m0,mb->m3,mc->m2,md->m1},
  {sa->s1,sb->s12,sc->s3,sd->s23,sab->s2,sbc->s4,ma->m1,mb->m0,mc->m2,md->m3},
  {sa->s23,sb->s3,sc->s12,sd->s1,sab->s2,sbc->s4,ma->m1,mb->m3,mc->m2,md->m0},
  {sa->s23,sb->s2,sc->s12,sd->s4,sab->s3,sbc->s1,ma->m3,mb->m1,mc->m2,md->m0},
  {sa->s4,sb->s12,sc->s2,sd->s23,sab->s3,sbc->s1,ma->m3,mb->m0,mc->m2,md->m1}}},

  With[
	  {a:=mb^2 r13 y23-md^2 y12,
	   b:=y02(mb^2 r13-md^2/r13) + y01 y23 - y03 y12,
	   c:=y02(y01 - y03/r13)-ma^2(y12-y23/r13),
	   d:=y12-y23/r13},

	permutedSetDelayed[analD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,0,m3_],
	  Block[{choices, sa,sb,sc,sd,sab,sbc,ma,mb,md,conditionalWrapper=Identity},
	  Assuming[{m0>=0,m1>=0,m3>=0},

		If[(*Check if there is a Euclidean channel*)
		  (choices = Extract[permutations,Position[Refine[(Not[pZQ[a]]&&Not[pZQ[y02]]&&sbc-(mb-md)^2<=0/.permutations)/.pZQ->PossibleZeroQ],True]])=!={},
		  Set@@@First[choices];
		  conditionalWrapper=Identity,

		  (*If s1, s4 or s23 are not Euclidean*)
		  Set@@@First[Pick[permutations,Map[Not[PossibleZeroQ[#]]&,(a&&y02/.permutations),{2}]]];
		  conditionalWrapper=ConditionalExpression[#,sbc<=(mb-md)^2]&;
		];

		conditionalWrapper[
		  rootsum[\[FormalX], Collect[\[FormalX]^2 a+\[FormalX] b+c,\[FormalX]],
			1/(2 a \[FormalX]+b) (
			simplifyContinuedDiLog[{-\[FormalX],d/(2 a \[FormalX]+b)},{y23/y02,y23-y02}]-
			rootsumInternal[\[FormalR],ma^2+y03 \[FormalR]+md^2 \[FormalR]^2,(*ContinuedDiLog*)List[{-\[FormalX],d/(2 a \[FormalX]+b)},{-1/\[FormalR],-ma^2/\[FormalR]+md^2 \[FormalR]}]]-
			simplifyContinuedDiLog[{-\[FormalX] r13,d r13/(2 a \[FormalX]+b)},{y12/y02,y12-y02}]+
			rootsumInternal[\[FormalR],ma^2+y01 \[FormalR]+mb^2 \[FormalR]^2,(*ContinuedDiLog*)List[{-\[FormalX] r13,d r13/(2 a \[FormalX]+b)},{-1/\[FormalR],-ma^2/\[FormalR]+mb^2 \[FormalR]}]])
		  ]]
	  ]]
	]
  ]

];


(*Four masses nonvanishing*)

With[
{y00=2 ma^2,    y01=ma^2+mb^2-sa,  y02=ma^2+mc^2-sab,  y03=ma^2+md^2-sd,
                y11=2 mb^2,        y12=mb^2+mc^2-sb,   y13=mb^2+md^2-sbc,
                                        y22=2 mc^2,    y23=mc^2+md^2-sc,
                                                       y33=2 md^2,

(*r13:=Refine[1/(2mb^2)*(-sbc+mb^2+md^2+Sqrt[Kallen\[Lambda][sbc,mb^2,md^2]])],
r20:=Refine[1/(2mc^2)*(-sab+mc^2+ma^2+Sqrt[Kallen\[Lambda][sab,mc^2,ma^2]])],*)
r13:=1/(2mb^2)*(-sbc+mb^2+md^2+rootKallen[sbc,mb^2,md^2]),
r20:=1/(2mc^2)*(-sab+mc^2+ma^2+rootKallen[sab,mc^2,ma^2]),

permutations=
  {{sa->s1,sb->s4,sc->s3,sd->s2,sab->s23,sbc->s12,ma->m1,mb->m0,mc->m3,md->m2},
   {sa->s2,sb->s3,sc->s4,sd->s1,sab->s23,sbc->s12,ma->m1,mb->m2,mc->m3,md->m0},
   {sa->s3,sb->s2,sc->s1,sd->s4,sab->s23,sbc->s12,ma->m3,mb->m2,mc->m1,md->m0},
   {sa->s4,sb->s1,sc->s2,sd->s3,sab->s23,sbc->s12,ma->m3,mb->m0,mc->m1,md->m2},
   {sa->s1,sb->s2,sc->s3,sd->s4,sab->s12,sbc->s23,ma->m0,mb->m1,mc->m2,md->m3},
   {sa->s2,sb->s1,sc->s4,sd->s3,sab->s12,sbc->s23,ma->m2,mb->m1,mc->m0,md->m3},
   {sa->s3,sb->s4,sc->s1,sd->s2,sab->s12,sbc->s23,ma->m2,mb->m3,mc->m0,md->m1},
   {sa->s4,sb->s3,sc->s2,sd->s1,sab->s12,sbc->s23,ma->m0,mb->m3,mc->m2,md->m1},
   {sa->s1,sb->s23,sc->s3,sd->s12,sab->s4,sbc->s2,ma->m0,mb->m1,mc->m3,md->m2},
   {sa->s23,sb->s1,sc->s12,sd->s3,sab->s4,sbc->s2,ma->m3,mb->m1,mc->m0,md->m2},
   {sa->s3,sb->s12,sc->s1,sd->s23,sab->s4,sbc->s2,ma->m3,mb->m2,mc->m0,md->m1},
   {sa->s12,sb->s3,sc->s23,sd->s1,sab->s4,sbc->s2,ma->m0,mb->m2,mc->m3,md->m1},
   {sa->s3,sb->s23,sc->s1,sd->s12,sab->s2,sbc->s4,ma->m2,mb->m3,mc->m1,md->m0},
   {sa->s1,sb->s12,sc->s3,sd->s23,sab->s2,sbc->s4,ma->m1,mb->m0,mc->m2,md->m3},
   {sa->s12,sb->s1,sc->s23,sd->s3,sab->s2,sbc->s4,ma->m2,mb->m0,mc->m1,md->m3},
   {sa->s23,sb->s3,sc->s12,sd->s1,sab->s2,sbc->s4,ma->m1,mb->m3,mc->m2,md->m0},
   {sa->s2,sb->s12,sc->s4,sd->s23,sab->s1,sbc->s3,ma->m1,mb->m2,mc->m0,md->m3},
   {sa->s12,sb->s2,sc->s23,sd->s4,sab->s1,sbc->s3,ma->m0,mb->m2,mc->m1,md->m3},
   {sa->s4,sb->s23,sc->s2,sd->s12,sab->s1,sbc->s3,ma->m0,mb->m3,mc->m1,md->m2},
   {sa->s23,sb->s4,sc->s12,sd->s2,sab->s1,sbc->s3,ma->m1,mb->m3,mc->m0,md->m2},
   {sa->s2,sb->s23,sc->s4,sd->s12,sab->s3,sbc->s1,ma->m2,mb->m1,mc->m3,md->m0},
   {sa->s23,sb->s2,sc->s12,sd->s4,sab->s3,sbc->s1,ma->m3,mb->m1,mc->m2,md->m0},
   {sa->s4,sb->s12,sc->s2,sd->s23,sab->s3,sbc->s1,ma->m3,mb->m0,mc->m2,md->m1},
   {sa->s12,sb->s4,sc->s23,sd->s2,sab->s3,sbc->s1,ma->m2,mb->m0,mc->m3,md->m1}}},

  With[
	{a:=mb^2 r13(y23-y03/r20)-md^2(y12-y01/r20),
	 b:=(mc^2 r20-ma^2/r20)(mb^2 r13-md^2/r13)+y01 y23-y03 y12,
	 c:=mc^2 r20(y01-y03/r13)-ma^2(y12-y23/r13),
	 d:=y12-y01/r20-y23/r13+y03/(r20 r13)},

	permutedSetDelayed[analD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_],
	  Block[
		{choices,conditionalWrapper=Identity,
		  sa,sb,sc,sd,sab,sbc,ma,mb,mc,md},
	  Assuming[{m0>=0,m1>=0,m2>=0,m3>=0},

		If[(*Check if there is a pair of overlapping Euclidean channels*)
		  (choices = Extract[permutations,Position[Refine[({sab-(ma-mc)^2<=0, sbc-(mb-md)^2<=0}/.permutations)],{True,True}]])=!={},
		  Set@@@First[choices];
			rootsum[\[FormalX], Collect[\[FormalX]^2 a+\[FormalX] b+c,\[FormalX]],
			  1/(2 a \[FormalX]+b) (
			  rootsumInternal[\[FormalR],mc^2+y23 \[FormalR]+md^2 \[FormalR]^2, (*ContinuedDiLog*)List[{-\[FormalX],d/(2 a \[FormalX]+b)},         {-1/\[FormalR] 1/r20,(-mc^2/\[FormalR]+md^2 \[FormalR])/r20}]]-
			  rootsumInternal[\[FormalR],ma^2+y03 \[FormalR]+md^2 \[FormalR]^2, (*ContinuedDiLog*)List[{-\[FormalX],d/(2 a \[FormalX]+b)},         {-1/\[FormalR],       -ma^2/\[FormalR]+md^2 \[FormalR]}]]-
			  rootsumInternal[\[FormalR],mc^2+y12 \[FormalR]+mb^2 \[FormalR]^2, (*ContinuedDiLog*)List[{-\[FormalX] r13, d r13/(2 a \[FormalX]+b)},{-1/\[FormalR] 1/r20,(-mc^2/\[FormalR]+mb^2 \[FormalR])/r20}]]+
			  rootsumInternal[\[FormalR],ma^2+y01 \[FormalR]+mb^2 \[FormalR]^2, (*ContinuedDiLog*)List[{-\[FormalX] r13, d r13/(2 a \[FormalX]+b)},{-1/\[FormalR],       -ma^2/\[FormalR]+mb^2 \[FormalR]}]])
		    ],

		  If[(*Check if there is one Euclidean channel*)
			(choices = Extract[permutations,Position[Refine[(sab-(ma-mc)^2<=0/.permutations)],True]])=!={},
			Set@@@First[choices]; conditionalWrapper=Identity,
			Set@@@First[permutations]; conditionalWrapper=ConditionalExpression[#,sab<=(ma-mc)^2]&
		  ];
		  conditionalWrapper[
			rootsum[\[FormalX], Collect[\[FormalX]^2 a+\[FormalX] b+c,\[FormalX]],
			  1/(2 a \[FormalX]+b) (
			  rootsumInternal[\[FormalR],mc^2+y23 \[FormalR]+md^2 \[FormalR]^2, (*ContinuedDiLog*)List[{-\[FormalX],d/(2 a \[FormalX]+b)},         {-1/\[FormalR] 1/r20,(-mc^2/\[FormalR]+md^2 \[FormalR])/r20}]]-
			  rootsumInternal[\[FormalR],ma^2+y03 \[FormalR]+md^2 \[FormalR]^2, (*ContinuedDiLog*)List[{-\[FormalX],d/(2 a \[FormalX]+b)},         {-1/\[FormalR],       -ma^2/\[FormalR]+md^2 \[FormalR]}]]-
			  rootsumInternal[\[FormalR],mc^2+y12 \[FormalR]+mb^2 \[FormalR]^2, (*ContinuedDiLog*)List[{-\[FormalX] r13, d r13/(2 a \[FormalX]+b)},{-1/\[FormalR] 1/r20,(-mc^2/\[FormalR]+mb^2 \[FormalR])/r20}]]+
			  rootsumInternal[\[FormalR],ma^2+y01 \[FormalR]+mb^2 \[FormalR]^2, (*ContinuedDiLog*)List[{-\[FormalX] r13, d r13/(2 a \[FormalX]+b)},{-1/\[FormalR],       -ma^2/\[FormalR]+mb^2 \[FormalR]}]]-
			  (-Ln[-\[FormalX],d/(2 a \[FormalX]+b)]-Log[r13]+Ln[-\[FormalX] r13,d r13/(2 a \[FormalX]+b)])*
				(Ln[(\[FormalX]^2 md^2+mc^2 r20^2+\[FormalX] r20 (mc^2+md^2-sc))/(r20^2 (ma^2+\[FormalX]^2 md^2+\[FormalX] (ma^2+md^2-sd))),(r20 (y12-y23/r13)+(mb^2 r13-md^2/r13) \[FormalX])/(r20^2 (y01-y03/r13+(mb^2 r13-md^2/r13) \[FormalX]))]-Log[mc^2/ma^2]))
			]]

		  
		]

		
	  ]]
	]
  ]

];


(* ::Subsubsection::Closed:: *)
(*IR divergent cases*)


(*Box 1*) 
permutedSetDelayed[
  analD0IR[0,0,0,0,p20_,p31_,0,0,0,0],
(*Ellis+Zanderighi*)  (*Print["IR Box-1"];*) 1/(p20 p31) (4/Eps^2+2/Eps (Log[Mu^2/-p20]+Log[Mu^2/-p31])+2Log[Mu^2/-p31]Log[Mu^2/-p20]-4\[Pi]^2/3)
];

(*Box 2*) 
permutedSetDelayed[
  analD0IR[0,0,0,p30_,p20_,p31_,0,0,0,0],
  (*Print["IR Box-2"];*)
(*Ellis+Zanderighi*) 1/(p20 p31) (2/Eps^2+2/Eps (Log[Mu^2/-p20]+Log[Mu^2/-p31]-Log[Mu^2/-p30])+2Log[Mu^2/-p31]Log[Mu^2/-p20]-Log[Mu^2/-p30]^2-2 simplifyDiLog[1-p30/p20,p30-p20]-2 simplifyDiLog[1-p30/p31,p30-p31]-\[Pi]^2/2)
(*Duplancic and Nizic arXiv: 0006249 eq. 72*)  (*1/(p20 p31)* (2/Eps^2-\[Pi]^2/6-(2 (Log[-(Mu^2/p30)]-Log[Mu^2/-p20]-Log[Mu^2/-p31]))/Eps+1/3 (-\[Pi]^2+6 DiLog[1-(p20-p30+p31)/p20,-((p20-p30+p31)/(p20 p31))]+6 DiLog[1-(p20-p30+p31)/p31,-((p20-p30+p31)/(p20 p31))]-6 DiLog[1-(p30 (p20-p30+p31))/(p20 p31),-((p20-p30+p31)/(p20 p31))]-3 Log[-(Mu^2/p30)]^2+3 Log[Mu^2/-p20]^2+3 Log[Mu^2/-p31]^2))*)
];

(*Box 3*)

permutedSetDelayed[
  analD0IR[0,p21_,0,p30_,p20_,p31_,0,0,0,0],
  (*Print["IR Box-3"];*)
(*Denner+Dittmaier 2010*)  (*1/(-p21 p30+p20 p31) 2 ((1/Eps+Log[-(Mu^2/p20)]) (Log[-(Mu^2/p20)]-Log[-(Mu^2/p21)]-Log[-(Mu^2/p30)]+Log[-(Mu^2/p31)])+simplifyDiLog[1-p20/p21,p20-p21]+simplifyDiLog[1-p20/p30,p20-p30]-simplifyDiLog[1-p21/p31,p21-p31]-simplifyDiLog[1-p30/p31,p30-p31]+simplifyDiLog[1-(p21 p30)/(p20 p31),-(((p20-p21) p30)/p31)-(p21 (-p30+p31))/p20]+simplifyLn[1-(p21 p30)/(p20 p31),-(((p20-p21) p30)/p31)-(p21 (-p30+p31))/p20] (-Log[-(Mu^2/p20)]+Log[-(Mu^2/p21)]+Log[-(Mu^2/p30)]-Log[-(Mu^2/p31)]+simplifyLn[(p21 p30)/(p20 p31),((p20-p21) p30)/p31+(p21 (-p30+p31))/p20]))*)
(*Duplancic and Nizic arXiv: 0006249 eq. 71*) 1/(-p21 p30+p20 p31)*(2 simplifyDiLog[1-(p20 (p20-p21-p30+p31))/(-p21 p30+p20 p31),-((p20-p21-p30+p31)/(-p21 p30+p20 p31))]-2 simplifyDiLog[1-(p21 (p20-p21-p30+p31))/(-p21 p30+p20 p31),-((p20-p21-p30+p31)/(-p21 p30+p20 p31))]-2 simplifyDiLog[1-(p30 (p20-p21-p30+p31))/(-p21 p30+p20 p31),-((p20-p21-p30+p31)/(-p21 p30+p20 p31))]+2 simplifyDiLog[1-(p31 (p20-p21-p30+p31))/(-p21 p30+p20 p31),-((p20-p21-p30+p31)/(-p21 p30+p20 p31))]+Log[-(Mu^2/p20)]^2-Log[-(Mu^2/p21)]^2-Log[-(Mu^2/p30)]^2-(2 (-Log[-(Mu^2/p20)]+Log[-(Mu^2/p21)]+Log[-(Mu^2/p30)]-Log[-(Mu^2/p31)]))/Eps+Log[-(Mu^2/p31)]^2)
];

(*Box 4 [Derived from box 8 by taking m3->0]*)
permutedSetDelayed[
  analD0IR[0,0,p32_,p30_,p20_,p31_,0,0,0,0],
  (*Print["IR Box-4"];*) 1/(p20 p31 Eps^2)+(Log[-(Mu^2/p20)]-Log[-(Mu^2/p30)]+2 Log[-(Mu^2/p31)]-Log[-(Mu^2/p32)])/(p20 p31 Eps)+1/(p20 p31) (-2 simplifyDiLog[1-p30/p31,-p31]-2 simplifyDiLog[1-p32/p31,-p31]-simplifyLn[p20/p31,-p20+p31]^2+3/2 Log[-(Mu^2/p20)]^2-1/2 Log[-(Mu^2/p30)]^2+Log[-(Mu^2/p31)]^2-Log[-(Mu^2/p20)] Log[-(Mu^2/p32)]-1/2 Log[-(Mu^2/p32)]^2+Log[-(Mu^2/p30)] (-Log[-(Mu^2/p20)]+Log[-(Mu^2/p32)])-\[Pi]^2/12)
];

(*Box 6*)
conditionalPermutedSetDelayed[
  analD0IR[0,0,p32_,p30_,p20_,p31_,0,0,0,m3_],PossibleZeroQ[p32-m3^2] && PossibleZeroQ[p30-m3^2],
  (*Print["IR Box-6"];*) 1/(p20(p31-m3^2)) (2/Eps^2+1/Eps (2Log[Mu^2/m3^2]+Log[m3^2/-p20]+2Log[m3^2/(m3^2-p31)])+(Log[m3^2/-p20]+Log[Mu^2/m3^2])(Log[Mu^2/m3^2]+2 Log[m3^2/(m3^2-p31)])-2\[Pi]^2/3)
];

(*Box 7*)
conditionalPermutedSetDelayed[
  analD0IR[0,0,p32_,p30_,p20_,p31_,0,0,0,m3_], PossibleZeroQ[p30-m3^2],
  (*Print["IR Box-7"];*) 1/(p20(p31-m3^2)) (3/(2 Eps^2)+1/Eps (3/2 Log[Mu^2/m3^2]+Log[m3^2/-p20]-Log[m3^2/(m3^2-p32)]+2Log[m3^2/(m3^2-p31)])-(1/2 Log[Mu^2/m3^2]+Log[m3^2/(m3^2-p32)])^2+2(Log[Mu^2/m3^2]+Log[m3^2/-p20])(1/2 Log[Mu^2/m3^2]+Log[m3^2/(m3^2-p31)])-2simplifyDiLog[(p32-p31)/(m3^2-p31),-p31+p32]-(13\[Pi]^2)/24)
];

(*Box 8*)
permutedSetDelayed[
  analD0IR[0,0,p32_,p30_,p20_,p31_,0,0,0,m3_],
  (*Print["IR Box-8"];*) 1/(p20(p31-m3^2)) (1/Eps^2+1/Eps (Log[Mu^2/-p20]+Log[m3^2/(m3^2-p31)]-Log[m3^2/(m3^2-p32)]+Log[m3^2/(m3^2-p31)]-Log[m3^2/(m3^2-p30)](*simplifyLn[(m3^2-p32)/(m3^2-p31),p31-p32]+simplifyLn[(m3^2-p30)/(m3^2-p31),p31-p30]*))+1/2 Log[Mu^2/-p20]^2+Log[Mu^2/-p20](Log[m3^2/(m3^2-p31)]-Log[m3^2/(m3^2-p32)]+Log[m3^2/(m3^2-p31)]-Log[m3^2/(m3^2-p30)](*simplifyLn[(m3^2-p32)/(m3^2-p31),p31-p32]+simplifyLn[(m3^2-p30)/(m3^2-p31),p31-p30]*))-1/2 (Log[m3^2/(m3^2-p30)]-Log[m3^2/(m3^2-p32)](*simplifyLn[(m3^2-p32)/(m3^2-p30),p30-p32]*))^2-2simplifyDiLog[(p32-p31)/(m3^2-p31),-p31+p32]-2simplifyDiLog[(p30-p31)/(m3^2-p31),p30-p31]+(*ContinuedDiLog[{p20/(p32-m3^2),-p20},{m3^2/(m3^2-p30),m3^2}]*)(simplifyDiLog[1-(m3^2 p20)/((m3^2-p30) (-m3^2+p32)),(m3^2 p20)/(m3^2-p30)-(m3^2 p20)/(-m3^2+p32)]+(-simplifyLn[m3^2/(m3^2-p30),m3^2]-simplifyLn[p20/(-m3^2+p32),-p20]+simplifyLn[(m3^2 p20)/((m3^2-p30) (-m3^2+p32)),-((m3^2 p20)/(m3^2-p30))+(m3^2 p20)/(-m3^2+p32)]) simplifyLn[1-(m3^2 p20)/((m3^2-p30) (-m3^2+p32)),(m3^2 p20)/(m3^2-p30)-(m3^2 p20)/(-m3^2+p32)])-\[Pi]^2/4)
];

(*Box 11*)
conditionalPermutedSetDelayed[
  analD0IR[0,p21_,p32_,p30_,p20_,p31_,0,0,m2_,m3_], PossibleZeroQ[p21-m2^2] && PossibleZeroQ[p30-m3^2],
  (*Print["IR Box-11"];*) 1/((p20-m2^2)(p31-m3^2)) (1/Eps^2+1/Eps (1/2 Log[Mu^2/m2^2]+Log[m2^2/(m2^2-p20)])+1/Eps (1/2 Log[Mu^2/m3^2]+Log[m3^2/(m3^2-p31)])+2(1/2 Log[Mu^2/m2^2]+Log[m2^2/(m2^2-p20)])(1/2 Log[Mu^2/m3^2]+Log[m3^2/(m3^2-p31)])-If[PossibleZeroQ[p32],olog[m2^2,m3^2]^2/4,Log[(m3^2+m2^2-p32+Sqrt[Kallen\[Lambda][p32,m2^2,m3^2]])/(2m2 m3)]^2]-7/12 \[Pi]^2)
];

(*Box 9*)
conditionalPermutedSetDelayed[
  analD0IR[0,p21_,p32_,p30_,p20_,p31_,0,0,0,m3_], PossibleZeroQ[p30-m3^2],
  (*Print["IR Box-9"];*) (-((Log[-(m3^2/p20)]-Log[-(m3^2/p21)]+Log[m3^2/(m3^2-p31)])/(m3^2 p20-p20 p31))) (1/Eps+Log[Mu^2/m3^2])+(1/Eps^2+Log[Mu^2/m3^2]/Eps+1/2 Log[Mu^2/m3^2]^2)/(2 (-p20) (m3^2-p31))+ScalarD0IR12[p21,p32,p20,p31,0,m3]
];

(*Box 12*)
conditionalPermutedSetDelayed[
  analD0IR[0,p21_,p32_,p30_,p20_,p31_,0,0,m2_,m3_], PossibleZeroQ[p30-m3^2],
  (*Print["IR Box-12"];*) ScalarD0IR12[p21,p32,p20,p31,m2,m3]+(Log[m2^2/(m2^2-p20)]/((m2^2-p20) (m3^2-p31))-Log[m2^2/(m2^2-p21)]/((m2^2-p20) (m3^2-p31))+Log[m3^2/(m3^2-p31)]/((m2^2-p20) (m3^2-p31))) (1/Eps+Log[Mu^2/m3^2])+(1/Eps^2+Log[Mu^2/m3^2]/Eps+1/2 Log[Mu^2/m3^2]^2)/(2 (m2^2-p20) (m3^2-p31))
];

(*Box 5 [limiting case of Box 13]*)
permutedSetDelayed[
  analD0IR[0,p21_,p32_,p30_,p20_,p31_,0,0,0,0],
  (*Print["IR Box-5"];*) (-Log[-(Mu^2/p20)]+Log[-(Mu^2/p21)]+Log[-(Mu^2/p30)]-Log[-(Mu^2/p31)])/(p21 p30-p20 p31) (1/Eps+1/2 Log[Mu^2/-p30]+1/2 Log[Mu^2/-p21])+ScalarD0IR13[p21,p32,p30,p20,p31,0,0]
];

(*Box 10 [limiting case of Box 13]*)
permutedSetDelayed[
  analD0IR[0,p21_,p32_,p30_,p20_,p31_,0,0,0,m3_],
  (*Print["IR Box-10"];*) ((-Log[-(m3^2/p20)]+Log[-(m3^2/p21)]+Log[m3^2/(m3^2-p30)]-Log[m3^2/(m3^2-p31)]) (1/Eps+1/2 Log[Mu^2/(m3^2-p30)]+1/2 Log[Mu^2/-p21]))/(m3^2 p20-m3^2 p21+p21 p30-p20 p31)+ScalarD0IR13[p21,p32,p30,p20,p31,0,m3]
];

(*Box 13*)
permutedSetDelayed[
  analD0IR[0,p21_,p32_,p30_,p20_,p31_,0,0,m2_,m3_],
  (*Print["IR Box-13"];*) ScalarD0IR13[p21,p32,p30,p20,p31,m2,m3] + (-Log[m2^2/(m2^2-p20)]+Log[m2^2/(m2^2-p21)]+Log[m3^2/(m3^2-p30)]-Log[m3^2/(m3^2-p31)])/(m3^2 p20-m3^2 p21-m2^2 p30+p21 p30+m2^2 p31-p20 p31) (1/Eps+1/2 Log[Mu^2/(m3^2-p30)]+1/2 Log[Mu^2/(m2^2-p21)])
];

(*Box 14 [especially simple]*)
conditionalPermutedSetDelayed[
  analD0IR[s1_,s2_,s3_,s4_,p20_,p31_,0,m1_,0,m3_], PossibleZeroQ[s1-m1^2] && PossibleZeroQ[s2-m1^2] && PossibleZeroQ[s3-m3^2] && PossibleZeroQ[s4-m3^2], 
  (*Print["IR Box-14"];*) (2 p31 DiscB[p31,m1,m3] (1/Eps+Log[-(Mu^2/p20)]))/(p20 Kallen\[Lambda][m1^2,m3^2,p31]) 
];

(*Box 16*)
conditionalPermutedSetDelayed[
  analD0IR[s1_,s2_,s3_,s4_,s12_,s23_,0,m1_,m2_,m3_], PossibleZeroQ[s1-m1^2] && PossibleZeroQ[s4-m3^2],
  (*Print["IR Box-16"];*) ScalarD0IR16[s2,s3,s12,s23,m1,m2,m3] + s23 DiscB[s23,m1,m3]/((s12-m2^2)*Kallen\[Lambda][s23,m1^2,m3^2])*(1/Eps+Log[Mu^2/m1^2]/2+Log[Mu^2/m3^2]/2)
];


(* ::Subsection:: *)
(*ScalarD0IR12, ScalarD0IR13, ScalarD0IR16*)


(* ::Subsubsection::Closed:: *)
(*ScalarD0IR12*)


pvD0IR12force[p21_,p32_,p20_,p31_,m2_,m3_] :=
  1/((p20-m2^2)(p31-m3^2)) (-\[Pi]^2/8 + Log[m3^2/(m3^2-p31)](2*simplifyLn[(m2^2-p21)/(m2^2-p20),p20-p21]+Log[m3^2/(m3^2-p31)])-2 simplifyDiLog[(p21-p20)/(m2^2-p20),-p20+p21] + 
	Which[
	  PossibleZeroQ[p32],
	  simplifyDiLog[1-(m3^2-p31)/(m2^2-p21),m2^2-m3^2-p21+p31]+simplifyDiLog[1-(m2^2 (m3^2-p31))/(m3^2 (m2^2-p21)),m2^2-m3^2-p21+p31],
	  PossibleZeroQ[m2],
	  \[Pi]^2/6-ContinuedDiLog[{(m3^2-p31)/-p21,m3^2+p21-p31},{(m3^2-p32)/m3^2,-1}],
	  True,
	  rootsum[\[FormalR],m3^2+(-p32+m3^2+m2^2)\[FormalR]+m2^2 \[FormalR]^2,ContinuedDiLog[{(m3^2-p31)/(m2^2-p21),-(m2^2-m3^2-p21+p31)},{-(1/\[FormalR]),-m3^2/\[FormalR]+m2^2 \[FormalR]}]]
	]);


(* ::Subsubsection::Closed:: *)
(*ScalarD0IR13*)


(*Cases for det(Z) = 0*)
(*Obtained from Package-X*)
pvD0IR13force[s2_,0,0,0,0,m2_,m3_] := 1/(2 m3^2 s2) (Log[m2^2/m3^2] Log[m2^2/(m2^2-s2)]+Log[m3^2/(m2^2-s2)]^2+2 PolyLog[2,1-m2^2/m3^2]+2 PolyLog[2,(m2^2-m3^2-s2)/(m2^2-s2)]+2 PolyLog[2,s2/(-m2^2+s2)]);
pvD0IR13force[0,0,s2_,0,0,m3_,m2_] := pvD0IR13force[s2,0,0,0,0,m2,m3];

pvD0IR13force[0,0,0,0,s23_,m2_,m3_] := 1/(2 m2^2 s23) (Log[m2^2/m3^2]^2+Log[m2^2/m3^2] Log[m3^2/(m3^2-s23)]+2 PolyLog[2,1-m3^2/m2^2]+2 PolyLog[2,(-m2^2+m3^2-s23)/(m3^2-s23)]+2 PolyLog[2,s23/(-m3^2+s23)]);
pvD0IR13force[0,0,0,s23_,0,m3_,m2_] := pvD0IR13force[0,0,0,0,s23,m2,m3];

pvD0IR13force[0,s3_,0,0,0,m2_,m3_] := DiscB[s3,m2,m3]/(m2^2 m3^2)-((m2^2-m3^2) Log[m2^2/m3^2])/(2 m2^2 m3^2 s3);


pvD0IR13force[p21_,p32_,p30_,p20_,p31_,0,0]:=1/(p20 p31-p21 p30)*
  ((1/2 simplifyLn[p21/p30,p30-p21]+simplifyLn[p32/p30,p30-p32])(simplifyLn[p30/p20,p20-p30]-simplifyLn[p31/p21,p21-p31])+2simplifyDiLog[(p20-p21)/-p21,p20-p21]-2simplifyDiLog[(p30-p31)/-p31,p30-p31]-
	2ContinuedDiLog[{p31/p21,p21-p31},{p20/p30,p30-p20}]+1/2 simplifyLn[p30/p20,p20-p30]^2-1/2 simplifyLn[p31/p21,p21-p31]^2);

pvD0IR13force[p21_,p32_,p30_,p20_,p31_,m2_,0]:=pvD0IR13force[p30,p32,p21,p31,p20,0,m2];

pvD0IR13force[p21_,p32_,p30_,p20_,p31_,m2_,m3_] := 1/((p20-m2^2)(p31-m3^2)-(p21-m2^2)(p30-m3^2))*
  ((simplifyLn[(m3^2-p30)/(m2^2-p20),-m2^2+m3^2+p20-p30]-simplifyLn[(m3^2-p31)/(m2^2-p21),-m2^2+m3^2+p21-p31])(1/2 simplifyLn[(m2^2-p21)/(m3^2-p30),m2^2-m3^2-p21+p30]+Log[m3^2/(m3^2-p30)])+
  2simplifyDiLog[(p20-p21)/(m2^2-p21),p20-p21]-2simplifyDiLog[(p30-p31)/(m3^2-p31),p30-p31]-2ContinuedDiLog[{(m3^2-p31)/(m2^2-p21),-m2^2+m3^2+p21-p31},{(m2^2-p20)/(m3^2-p30),m2^2-m3^2-p20+p30}]+
  Which[
	PossibleZeroQ[p32],
	(simplifyDiLog[1-(m3^2-p31)/(m2^2-p21),m2^2-m3^2-p21+p31]-simplifyDiLog[1-(m3^2-p30)/(m2^2-p20),m2^2-m3^2-p20+p30])+(simplifyDiLog[1-m2^2/m3^2 (m3^2-p31)/(m2^2-p21),m2^2-m3^2-p21+p31]-simplifyDiLog[1-m2^2/m3^2 (m3^2-p30)/(m2^2-p20),m2^2-m3^2-p20+p30]),
	PossibleZeroQ[m2],
	ContinuedDiLog[{(m3^2-p31)/-p21,m3^2+p21-p31},{(m3^2-p32)/m3^2,-1}]-ContinuedDiLog[{(m3^2-p30)/-p20,+m3^2+p20-p30},{(m3^2-p32)/m3^2,-1}],
	True,
	rootsum[\[FormalX],m2^2+(m2^2+m3^2-p32)\[FormalX]+m3^2 \[FormalX]^2,ContinuedDiLog[{(m3^2-p31)/(m2^2-p21),-m2^2+m3^2+p21-p31},{-\[FormalX],m2^2/\[FormalX]-m3^2 \[FormalX]}]-ContinuedDiLog[{(m3^2-p30)/(m2^2-p20),-m2^2+m3^2+p20-p30},{-\[FormalX],m2^2/\[FormalX]-m3^2 \[FormalX]}]]
  ]);



(* ::Subsubsection:: *)
(*ScalarD0IR16*)


(*Cases for det(Z) = 0*)
pvD0IR16force[0,0,s_,0, m_,0,m_] := Log[-(m^2/s)]/(m^2 s);
pvD0IR16force[0,0,s_,0, m1_,0,m3_] := (Log[-(m1^2/s)] Log[m1^2/s])/((m1^2-m3^2) s)-Log[m1^2/s]^2/(2 (m1^2-m3^2) s)-(Log[-(m3^2/s)] Log[m3^2/s])/((m1^2-m3^2) s)+Log[m3^2/s]^2/(2 (m1^2-m3^2) s);
pvD0IR16force[0,0,s_,0, m_,m_,m_] := -(1/(m^2 (m^2-s)))-Log[m^2/(m^2-s)]/(m^2 (m^2-s));
pvD0IR16force[0,0,s_,0, m_,m2_,m_] := -(Log[m^2/m2^2]/((m^2-m2^2) (m2^2-s)))-Log[m2^2/(m2^2-s)]/(m^2 (m2^2-s));
pvD0IR16force[0,0,p20_,0, m1_,m2_,m3_] := ((-m1^2+p20) ScalarC0[0,m1^2,p20,m2,m1,0])/((m1^2-m3^2) (-m2^2+p20))+((m3^2-p20) ScalarC0[0,m3^2,p20,m2,m3,0])/((m1^2-m3^2) (-m2^2+p20));


(*Limit to Box 15*)

pvD0IR16force[p21_,p32_,p20_,p31_,m1_,0,m3_] /; PossibleZeroQ[p32-m3^2] :=
  With[{x31=(-1+Sqrt[1-4 m3 m1/(p31-(m3-m1)^2)])/(1+Sqrt[1-4 m3 m1/(p31-(m3-m1)^2)])},
	(p31 DiscB[p31,m1,m3])/(p20 Kallen\[Lambda][p31,m1^2,m3^2])*(1/2*Log[m3^2/m1^2] + Log[x31] + 2*simplifyLn[(m1^2-p21)/-p20,m1^2+p20-p21])+ 
	1/p20*If[PossibleZeroQ[m1-m3],1/(p31*Sqrt[1-4m1^2/p31]),Sign[p31-(m1-m3)^2]/Sqrt[Kallen\[Lambda][p31,m1^2,m3^2]]]*PolyLog[2,1-x31^2]
  ];

pvD0IR16force[p32_,p21_,p20_,p31_,m3_,0,m1_] /; PossibleZeroQ[p32-m3^2] :=
  With[{x31=(-1+Sqrt[1-4 m3 m1/(p31-(m3-m1)^2)])/(1+Sqrt[1-4 m3 m1/(p31-(m3-m1)^2)])},
	(p31 DiscB[p31,m1,m3])/(p20 Kallen\[Lambda][p31,m1^2,m3^2])*(1/2*Log[m3^2/m1^2] + Log[x31] + 2*simplifyLn[(m1^2-p21)/-p20,m1^2+p20-p21])+ 
	1/p20*If[PossibleZeroQ[m1-m3],1/(p31*Sqrt[1-4m1^2/p31]),Sign[p31-(m1-m3)^2]/Sqrt[Kallen\[Lambda][p31,m1^2,m3^2]]]*PolyLog[2,1-x31^2]
  ];

pvD0IR16force[p21_,p32_,p20_,p31_,m1_,0,m3_] := 
  With[{x31=(-1+Sqrt[1-4 m3 m1/(p31-(m3-m1)^2)])/(1+Sqrt[1-4 m3 m1/(p31-(m3-m1)^2)])},
	(p31 DiscB[p31,m1,m3])/(p20 Kallen\[Lambda][p31,m1^2,m3^2]) (1/2 Log[x31]-2Log[1-x31^2]+simplifyLn[(m1^2-p21)/-p20,m1^2+p20-p21]+simplifyLn[(m3^2-p32)/-p20,(m3^2+p20-p32)])+
	-1/p20*If[PossibleZeroQ[m1-m3],1/(p31*Sqrt[1-4m1^2/p31]),Sign[p31-(m1-m3)^2]/Sqrt[Kallen\[Lambda][p31,m1^2,m3^2]]] (-(\[Pi]^2/6)+PolyLog[2,x31^2]+1/2 simplifyLn[(m1(m3^2-p32))/(m3(m1^2-p21)),-m1^2+m3^2+p21-p32]^2+
	ContinuedDiLog[{x31,1},{(m1(m3^2-p32))/(m3(m1^2-p21)),-m1^2+m3^2+p21-p32}]+ContinuedDiLog[{x31,1},{(m3(m1^2-p21))/(m1(m3^2-p32)),m1^2-m3^2-p21+p32}])
  ];


(*Det[X]=0; likely not to have many applications*)

(*Visually this has a finite value, but hard to get*)
pvD0IR16force[p21_,p32_,p20_,0,m1_,m2_,m3_] /; PossibleZeroQ[m1-m3] := Undefined;

pvD0IR16force[p21_,p32_,p20_,0,m1_,m2_,m3_] := 
  With[{x31=m3/m1},
	-(Log[m1^2/m3^2]/(2 (m1^2-m3^2) (m2^2-p20))) (Log[(m1 m3)/m2^2]+2Log[m2^2/(m2^2-p20)]-2Log[1-x31^2])+
	-1/(p20-m2^2)*(-1/(m1^2-m3^2)) (-(\[Pi]^2/6)+Log[(-p21+m2^2+m1^2+Sqrt[Kallen\[Lambda][p21,m2^2,m1^2]])/(2 m2 m1)]^2+Log[(-p32+m3^2+m2^2+Sqrt[Kallen\[Lambda][p32,m3^2,m2^2]])/(2 m3 m2)]^2+PolyLog[2,x31^2]+
	rootsum[\[FormalX],m1 m2+\[FormalX]^2 m1 m2-\[FormalX] (m1^2+m2^2-p21),rootsum[\[FormalY],m2 m3+\[FormalY]^2 m2 m3-\[FormalY] (m2^2+m3^2-p32),ContinuedDiLog[{\[FormalX],\[FormalX]-1/\[FormalX]},{\[FormalY] x31, x31(\[FormalY]-1/\[FormalY])+\[FormalY]}]]])
  ];


(*Not all channels p31, p21 or p32 can be pseudo-Euclidean, since that would require a more accurate inf part of x31 in the third argument of the ContinuedDiLog*)
pvD0IR16force[p21_,p32_,p20_,p31_,m1_,m2_,m3_] := 
  With[{x31=(-1+Sqrt[1-4 m3 m1/(p31-(m3-m1)^2)])/(1+Sqrt[1-4 m3 m1/(p31-(m3-m1)^2)])},
	ConditionalExpression[(p31 DiscB[p31,m1,m3])/((p20-m2^2)Kallen\[Lambda][p31,m1^2,m3^2]) (Log[(m1 m3)/m2^2]+2Log[m2^2/(m2^2-p20)]-2Log[1-x31^2])+
	-1/(p20-m2^2)*If[PossibleZeroQ[m1-m3],1/(p31 Sqrt[1-4m1^2/p31]),Sign[p31-(m1-m3)^2]/Sqrt[Kallen\[Lambda][p31,m1^2,m3^2]]] (-(\[Pi]^2/6)+Log[(-p21+m2^2+m1^2+Sqrt[Kallen\[Lambda][p21,m2^2,m1^2]])/(2 m2 m1)]^2+Log[(-p32+m3^2+m2^2+Sqrt[Kallen\[Lambda][p32,m3^2,m2^2]])/(2 m3 m2)]^2+PolyLog[2,x31^2]+
	rootsum[\[FormalX],m1 m2+\[FormalX]^2 m1 m2-\[FormalX] (m1^2+m2^2-p21),rootsum[\[FormalY],m2 m3+\[FormalY]^2 m2 m3-\[FormalY] (m2^2+m3^2-p32),ContinuedDiLog[{\[FormalX],\[FormalX]-1/\[FormalX]},{\[FormalY], \[FormalY]-1/\[FormalY]},{x31,1}]]]), Kallen\[Lambda][p31,m1^2,m3^2]>=0 || Kallen\[Lambda][p21,m1^2,m2^2]>=0 || Kallen\[Lambda][p32,m2^2,m3^2]>=0 ]
  ];


(* ::Subsection:: *)
(*Discontinuities*)


(* ::Subsubsection::Closed:: *)
(*DiscB, and finite C0, D0 functions*)


(* For sqrt of Kallen\[Lambda] involving threshold invariant and masses, I can freely take the positive root, rootKallen,
   since it is already assumed that the invariant is above threshold.  *)
(* For sqrt of other polynomials, the sign may be important.*)


(*DISCONTINUITY of DiscB*)
disc[DiscB][chnl[s_],m0_,m1_]:=2*I*\[Pi]/s HeavisideTheta[s-(m0+m1)^2] rootKallen[s,m0^2,m1^2];


(*DISCONTINUITY of ScalarC0*)
With[{num:=(-2 q m0^2-m1^2 p1+m2^2 p1+m1^2 p2-m2^2 p2+m1^2 q+m2^2 q+p1 q+p2 q-q^2+rootKallen[q,p1,p2] rootKallen[q,m1^2,m2^2]),
	  den:=(-2 q m0^2-m1^2 p1+m2^2 p1+m1^2 p2-m2^2 p2+m1^2 q+m2^2 q+p1 q+p2 q-q^2-rootKallen[q,p1,p2] rootKallen[q,m1^2,m2^2])},
  permutedSetDelayed[
	disc[ScalarC0][p1_,chnl[q_],p2_,m0_,m1_,m2_],
	2 \[Pi] I/rootKallen[q,p1,p2]*(*olog[num,den]*)Log[logArgumentSimplify[num/den]]*HeavisideTheta[q-(m1+m2)^2]
  ]
];


(*DISCONTINUITY of ScalarD0 -- not used at the moment, save for when a dedicated function to extract discontinuity from special functions is added*)
(*permutedSetDelayed[disc[ScalarD0][chnl[s1_],s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_],
   With[{
	kappa=Factor[2 m0^2 m1^2 s1-m0^2 m2^2 s1-m1^2 m2^2 s1-m0^2 m3^2 s1-m1^2 m3^2 s1+2 m2^2 m3^2 s1+m2^2 s1^2+m3^2 s1^2-m0^2 m1^2 s12+m1^4 s12+m0^2 m3^2 s12-m1^2 m3^2 s12-m1^2 s1 s12-m3^2 s1 s12+m0^4 s2-m0^2 m1^2 s2-m0^2 m3^2 s2+m1^2 m3^2 s2-m0^2 s1 s2-m3^2 s1 s2+m0^4 s23-m0^2 m1^2 s23-m0^2 m2^2 s23+m1^2 m2^2 s23-m0^2 s1 s23-m2^2 s1 s23-m0^2 s12 s23-m1^2 s12 s23+s1 s12 s23+2 m0^2 s2 s23-m0^4 s3+2 m0^2 m1^2 s3-m1^4 s3+2 m0^2 s1 s3+2 m1^2 s1 s3-s1^2 s3-m0^2 m1^2 s4+m1^4 s4+m0^2 m2^2 s4-m1^2 m2^2 s4-m1^2 s1 s4-m2^2 s1 s4+2 m1^2 s12 s4-m0^2 s2 s4-m1^2 s2 s4+s1 s2 s4],
	factoredDeterminant=Factor[m2^4 s1^2-2 m2^2 m3^2 s1^2+m3^4 s1^2-2 m1^2 m2^2 s1 s12+2 m1^2 m3^2 s1 s12+2 m2^2 m3^2 s1 s12-2 m3^4 s1 s12+m1^4 s12^2-2 m1^2 m3^2 s12^2+m3^4 s12^2-2 m0^2 m2^2 s1 s2+2 m0^2 m3^2 s1 s2+2 m2^2 m3^2 s1 s2-2 m3^4 s1 s2-2 m0^2 m1^2 s12 s2+2 m0^2 m3^2 s12 s2+2 m1^2 m3^2 s12 s2-2 m3^4 s12 s2-4 m3^2 s1 s12 s2+m0^4 s2^2-2 m0^2 m3^2 s2^2+m3^4 s2^2+2 m0^2 m2^2 s1 s23-2 m2^4 s1 s23-2 m0^2 m3^2 s1 s23+2 m2^2 m3^2 s1 s23+2 m0^2 m1^2 s12 s23-4 m0^2 m2^2 s12 s23+2 m1^2 m2^2 s12 s23+2 m0^2 m3^2 s12 s23-4 m1^2 m3^2 s12 s23+2 m2^2 m3^2 s12 s23+2 m2^2 s1 s12 s23+2 m3^2 s1 s12 s23-2 m1^2 s12^2 s23-2 m3^2 s12^2 s23-2 m0^4 s2 s23+2 m0^2 m2^2 s2 s23+2 m0^2 m3^2 s2 s23-2 m2^2 m3^2 s2 s23+2 m0^2 s12 s2 s23+2 m3^2 s12 s2 s23+m0^4 s23^2-2 m0^2 m2^2 s23^2+m2^4 s23^2-2 m0^2 s12 s23^2-2 m2^2 s12 s23^2+s12^2 s23^2-4 m0^2 m1^2 s1 s3+2 m0^2 m2^2 s1 s3+2 m1^2 m2^2 s1 s3+2 m0^2 m3^2 s1 s3+2 m1^2 m3^2 s1 s3-4 m2^2 m3^2 s1 s3-2 m2^2 s1^2 s3-2 m3^2 s1^2 s3+2 m0^2 m1^2 s12 s3-2 m1^4 s12 s3-2 m0^2 m3^2 s12 s3+2 m1^2 m3^2 s12 s3+2 m1^2 s1 s12 s3+2 m3^2 s1 s12 s3-2 m0^4 s2 s3+2 m0^2 m1^2 s2 s3+2 m0^2 m3^2 s2 s3-2 m1^2 m3^2 s2 s3+2 m0^2 s1 s2 s3+2 m3^2 s1 s2 s3-2 m0^4 s23 s3+2 m0^2 m1^2 s23 s3+2 m0^2 m2^2 s23 s3-2 m1^2 m2^2 s23 s3+2 m0^2 s1 s23 s3+2 m2^2 s1 s23 s3+2 m0^2 s12 s23 s3+2 m1^2 s12 s23 s3-2 s1 s12 s23 s3-4 m0^2 s2 s23 s3+m0^4 s3^2-2 m0^2 m1^2 s3^2+m1^4 s3^2-2 m0^2 s1 s3^2-2 m1^2 s1 s3^2+s1^2 s3^2+2 m1^2 m2^2 s1 s4-2 m2^4 s1 s4-2 m1^2 m3^2 s1 s4+2 m2^2 m3^2 s1 s4-2 m1^4 s12 s4+2 m1^2 m2^2 s12 s4+2 m1^2 m3^2 s12 s4-2 m2^2 m3^2 s12 s4+2 m0^2 m1^2 s2 s4+2 m0^2 m2^2 s2 s4-4 m1^2 m2^2 s2 s4-4 m0^2 m3^2 s2 s4+2 m1^2 m3^2 s2 s4+2 m2^2 m3^2 s2 s4+2 m2^2 s1 s2 s4+2 m3^2 s1 s2 s4+2 m1^2 s12 s2 s4+2 m3^2 s12 s2 s4-2 m0^2 s2^2 s4-2 m3^2 s2^2 s4-2 m0^2 m1^2 s23 s4+2 m0^2 m2^2 s23 s4+2 m1^2 m2^2 s23 s4-2 m2^4 s23 s4-4 m2^2 s1 s23 s4+2 m1^2 s12 s23 s4+2 m2^2 s12 s23 s4+2 m0^2 s2 s23 s4+2 m2^2 s2 s23 s4-2 s12 s2 s23 s4+2 m0^2 m1^2 s3 s4-2 m1^4 s3 s4-2 m0^2 m2^2 s3 s4+2 m1^2 m2^2 s3 s4+2 m1^2 s1 s3 s4+2 m2^2 s1 s3 s4-4 m1^2 s12 s3 s4+2 m0^2 s2 s3 s4+2 m1^2 s2 s3 s4-2 s1 s2 s3 s4+m1^4 s4^2-2 m1^2 m2^2 s4^2+m2^4 s4^2-2 m1^2 s2 s4^2-2 m2^2 s2 s4^2+s2^2 s4^2]},
	  2 \[Pi] I HeavisideTheta[s1-(m0+m1)^2] * 
	  If[(*If factored determinant is of the form (...)^2(...)^2, can cancel the square root; and simplify*)
		MatchQ[factoredDeterminant,HoldPattern[Power[_,_Integer?EvenQ]|Times[Power[_,_Integer?EvenQ]..]]],
		  With[{rootDetY=Replace[factoredDeterminant,Power[x_,n_Integer?EvenQ]:>Power[x,n/2],{0,1}]},
			olog[Simplify[kappa+rootKallen[s1,m0^2,m1^2] rootDetY],Simplify[kappa-rootKallen[s1,m0^2,m1^2] rootDetY]]/rootDetY
		  ],
		(*Otherwise, the argument of the logarithm cannot be simplified*)
	    olog[kappa+rootKallen[s1,m0^2,m1^2] Sqrt[factoredDeterminant],kappa-rootKallen[s1,m0^2,m1^2] Sqrt[factoredDeterminant]]/Sqrt[factoredDeterminant]
	  ]
  ]
]*)


(*DISCONTINUITY of ScalarC0IR6*)
disc[ScalarC0IR6][chnl[s_],m0_,m1_]:=2 I \[Pi] HeavisideTheta[s-(m0+m1)^2] Log[(m0 m1 s)/Kallen\[Lambda][m0^2,m1^2,s]]/rootKallen[s,m0^2,m1^2];


(*DISCONTINUITY of ScalarD0IR12*)

disc[ScalarD0IR12][chnl[p21_],p32_,p20_,p31_,m2_,m3_] := 2 \[Pi] I HeavisideTheta[p21-m2^2]/(m2^2-p20) (m3^2-p31) *(-Log[((p20-p21)^2 (m2^4 p31+p21 (m3^4+m3^2 (p21-p31-p32)+p31 p32)-m2^2 (m3^2 (p21+p31-p32)+p31 (p21-p31+p32))))/((m2^2-p20)^2 (m2^2-p21)^2 (m3^2-p31)^2 m3^2)]);
disc[ScalarD0IR12][p21_,chnl[p32_],p20_,p31_,m2_,m3_] := disc[analD0][0,p21,chnl[p32],m3^2,p20,p31,0,0,m2,m3];
disc[ScalarD0IR12][p21_,p32_,chnl[p20_],p31_,m2_,m3_] := (2 I \[Pi] (Log[(m3^4 (p20-p21)^2)/((m2^2-p20)^2 (m3^2-p31)^2)]))/((m2^2-p20) (m3^2-p31)) HeavisideTheta[p20-m2^2];
disc[ScalarD0IR12][p21_,p32_,p20_,chnl[p31_],m2_,m3_] := (2 I \[Pi] (Log[(m3^2 (m2^4 p31+p21 (m3^4+m3^2 (p21-p31-p32)+p31 p32)-m2^2 (m3^2 (p21+p31-p32)+p31 (p21-p31+p32))))/((m2^2-p20)^2 (m3^2-p31)^2)]))/((m2^2-p20) (m3^2-p31)) HeavisideTheta[p31-m3^2];


(*discontinuity of ScalarD0IR13*)

disc[ScalarD0IR13][p21_,chnl[p32_],p30_,p20_,p31_,m2_,m3_] := disc[analD0][0,p21,chnl[p32],p30,p20,p31,0,0,m2,m3];
permutedSetDelayed[disc[ScalarD0IR13][p21_,p32_,p30_,p20_,chnl[p31_],m2_,m3_] , 2\[Pi] I (1/2 Log[((m2^2-p21) (m3^2-p30))/(-m3^2+p31)^2]+Log[((-p30+p31)^2 (m2^2 p31^2+m3^2 (p21 (m3^2+p21-p32)+m2^2 (-p21+p32))+p31 (m2^4+p21 (-m3^2+p32)-m2^2 (m3^2+p21+p32))))/((-m3^2+p31) (-(-m2^2+p21) (-m3^2+p30)+(-m2^2+p20) (-m3^2+p31))^2)])/(-(-m2^2+p21) (-m3^2+p30)+(-m2^2+p20) (-m3^2+p31)) HeavisideTheta[p31-m3^2]];


(*discontinuity of ScalarD0IR16*)

permutedSetDelayed[
  disc[ScalarD0IR16][chnl[s2_],s3_,s12_,s23_,m1_,m2_,m3_],
  -((2 I \[Pi] Log[(m1^4+m2^2 m3^2-m3^2 s2-m2^2 s23+s2 s23-m1^2 (m2^2+m3^2+s2+s23-2 s3)+Sqrt[Kallen\[Lambda][s23,m1^2,m3^2] Kallen\[Lambda][m1^2,m2^2,s2]])/(m1^4+m2^2 m3^2-m3^2 s2-m2^2 s23+s2 s23-m1^2 (m2^2+m3^2+s2+s23-2 s3)-Sqrt[Kallen\[Lambda][s23,m1^2,m3^2] Kallen\[Lambda][m1^2,m2^2,s2]])])/((m2^2-s12) Sqrt[Kallen\[Lambda][s23,m1^2,m3^2]]))HeavisideTheta[-(m1+m2)^2+s2]
];

permutedSetDelayed[
  disc[ScalarD0IR16][s2_,s3_,chnl[s12_],s23_,m1_,m2_,m3_],
  (4 I \[Pi] s23 DiscB[s23,m1,m3])/((s12-m2^2)Kallen\[Lambda][s23,m1^2,m3^2]) HeavisideTheta[-m2^2+s12]
];

permutedSetDelayed[
  disc[ScalarD0IR16][s2_,s3_,s12_,chnl[s23_],m1_,m2_,m3_],
  (2 \[Pi] I HeavisideTheta[-(m1+m3)^2+s23] Log[(m1 m3 (m2^4 s23+m1^4 s3+s2 (m3^4+m3^2 (s2-s23-s3)+s23 s3)+m1^2 ((m2^2-m3^2) (s2-s23)-(m2^2+m3^2+s2+s23) s3+s3^2)-m2^2 (m3^2 (s2+s23-s3)+s23 (s2-s23+s3))))/((m2^2-s12)^2 (m1^4-2 m1^2 m3^2+m3^4-2 m1^2 s23-2 m3^2 s23+s23^2))])/((-m2^2+s12) Sqrt[Kallen\[Lambda][m1^2,m3^2,s23]])
];


(* ::Subsubsection::Closed:: *)
(*D0 functions*)


(*permutedSetDelayed[
  disc[analD0][0,p21_,0,p30_,chnl[p20_],p31_,0,0,0,0],Print["D3"];
  (4 \[Pi] I)/(-p21 p30+p20 p31) (Log[logArgumentSimplify[(-p20^2+p20 p21+p20 p30-p21 p30)/((*p20 *)(-p21 p30+p20 p31))]]+ Log[Mu^2/p20]+1/Eps)HeavisideTheta[p20]
];

permutedSetDelayed[
  disc[analD0][0,0,p32_,p30_,p20_,chnl[p31_],0,0,0,m3_],Print["D8"];
  (4 I \[Pi])/(p20 (p31-m3^2)) ( Simplify@Log[logArgumentSimplify[p31 (p30-p31) (p31-p32)/(p20 (m3^2-p31)^2)]]+(1/Eps+Log[Mu^2/p31]))HeavisideTheta[p31-m3^2]
];

permutedSetDelayed[
  disc[analD0][0,p21_,p32_,p30_,p20_,chnl[p31_],0,0,m2_,m3_],Print["D13"];
  2 I \[Pi] Simplify@(Log[logArgumentSimplify[-p31 ((-p30+p31)^2 (-m2^2 m3^2 p21+m3^4 p21+m3^2 p21^2+m2^4 p31-m2^2 m3^2 p31-m2^2 p21 p31-m3^2 p21 p31+m2^2 p31^2+m2^2 m3^2 p32-m3^2 p21 p32-m2^2 p31 p32+p21 p31 p32))/((m3^2-p31)^2 (m3^2 p20-m3^2 p21-m2^2 p30+p21 p30+m2^2 p31-p20 p31)^2)]]+ 1/Eps+Log[Mu^2/p31])HeavisideTheta[p31-m3^2]/((m3^2 (-p20+p21)-p21 p30+m2^2 (p30-p31)+p20 p31))
];



permutedSetDelayed[
  disc[analD0][m1_^2,m1_^2,m3_^2,m3_^2,p20_,chnl[p31_],0,m1_,0,m3_],Print["D14"];
  (*(4 I \[Pi] HeavisideTheta[-(m1+m3)^2+p31] (1/Eps+Log[-(Mu^2/p20)]))/(p20 rootKallen[p31,m1^2,m3^2])*)
  (4 I \[Pi] HeavisideTheta[-(m1+m3)^2+p31] (1/Eps+Log[-p31/p20]+Log[Mu^2/p31]))/(p20 rootKallen[p31,m1^2,m3^2])
];

permutedSetDelayed[
  disc[analD0][m1_^2,s2_,s3_,m3_^2,s12_,chnl[s23_],0,m1_,m2_,m3_],Print["D16"];
-((2 I \[Pi] HeavisideTheta[-(m1+m3)^2+s23] (1/Eps+Log[logArgumentSimplify[s23(m1^2 m2^2 s2-m1^2 m3^2 s2-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2-m1^2 m2^2 s23+m2^4 s23+m1^2 m3^2 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m1^4 s3-m1^2 m2^2 s3-m1^2 m3^2 s3+m2^2 m3^2 s3-m1^2 s2 s3-m3^2 s2 s3-m1^2 s23 s3-m2^2 s23 s3+s2 s23 s3+m1^2 s3^2)/((m2^2-s12)^2 Kallen\[Lambda][s23,m1^2,m3^2])]]+Log[Mu^2/s23]))/((m2^2-s12) rootKallen[s23,m1^2,m3^2](*Sqrt[Kallen\[Lambda][m1^2,m3^2,s23]]*)))
];

(*DISCONTINUITY of ScalarD0*)
permutedSetDelayed[disc[analD0][chnl[s1_],s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_],Print["Dfinite"];
   With[{
	kappa=Factor[2 m0^2 m1^2 s1-m0^2 m2^2 s1-m1^2 m2^2 s1-m0^2 m3^2 s1-m1^2 m3^2 s1+2 m2^2 m3^2 s1+m2^2 s1^2+m3^2 s1^2-m0^2 m1^2 s12+m1^4 s12+m0^2 m3^2 s12-m1^2 m3^2 s12-m1^2 s1 s12-m3^2 s1 s12+m0^4 s2-m0^2 m1^2 s2-m0^2 m3^2 s2+m1^2 m3^2 s2-m0^2 s1 s2-m3^2 s1 s2+m0^4 s23-m0^2 m1^2 s23-m0^2 m2^2 s23+m1^2 m2^2 s23-m0^2 s1 s23-m2^2 s1 s23-m0^2 s12 s23-m1^2 s12 s23+s1 s12 s23+2 m0^2 s2 s23-m0^4 s3+2 m0^2 m1^2 s3-m1^4 s3+2 m0^2 s1 s3+2 m1^2 s1 s3-s1^2 s3-m0^2 m1^2 s4+m1^4 s4+m0^2 m2^2 s4-m1^2 m2^2 s4-m1^2 s1 s4-m2^2 s1 s4+2 m1^2 s12 s4-m0^2 s2 s4-m1^2 s2 s4+s1 s2 s4],
	factoredDeterminant=Factor[m2^4 s1^2-2 m2^2 m3^2 s1^2+m3^4 s1^2-2 m1^2 m2^2 s1 s12+2 m1^2 m3^2 s1 s12+2 m2^2 m3^2 s1 s12-2 m3^4 s1 s12+m1^4 s12^2-2 m1^2 m3^2 s12^2+m3^4 s12^2-2 m0^2 m2^2 s1 s2+2 m0^2 m3^2 s1 s2+2 m2^2 m3^2 s1 s2-2 m3^4 s1 s2-2 m0^2 m1^2 s12 s2+2 m0^2 m3^2 s12 s2+2 m1^2 m3^2 s12 s2-2 m3^4 s12 s2-4 m3^2 s1 s12 s2+m0^4 s2^2-2 m0^2 m3^2 s2^2+m3^4 s2^2+2 m0^2 m2^2 s1 s23-2 m2^4 s1 s23-2 m0^2 m3^2 s1 s23+2 m2^2 m3^2 s1 s23+2 m0^2 m1^2 s12 s23-4 m0^2 m2^2 s12 s23+2 m1^2 m2^2 s12 s23+2 m0^2 m3^2 s12 s23-4 m1^2 m3^2 s12 s23+2 m2^2 m3^2 s12 s23+2 m2^2 s1 s12 s23+2 m3^2 s1 s12 s23-2 m1^2 s12^2 s23-2 m3^2 s12^2 s23-2 m0^4 s2 s23+2 m0^2 m2^2 s2 s23+2 m0^2 m3^2 s2 s23-2 m2^2 m3^2 s2 s23+2 m0^2 s12 s2 s23+2 m3^2 s12 s2 s23+m0^4 s23^2-2 m0^2 m2^2 s23^2+m2^4 s23^2-2 m0^2 s12 s23^2-2 m2^2 s12 s23^2+s12^2 s23^2-4 m0^2 m1^2 s1 s3+2 m0^2 m2^2 s1 s3+2 m1^2 m2^2 s1 s3+2 m0^2 m3^2 s1 s3+2 m1^2 m3^2 s1 s3-4 m2^2 m3^2 s1 s3-2 m2^2 s1^2 s3-2 m3^2 s1^2 s3+2 m0^2 m1^2 s12 s3-2 m1^4 s12 s3-2 m0^2 m3^2 s12 s3+2 m1^2 m3^2 s12 s3+2 m1^2 s1 s12 s3+2 m3^2 s1 s12 s3-2 m0^4 s2 s3+2 m0^2 m1^2 s2 s3+2 m0^2 m3^2 s2 s3-2 m1^2 m3^2 s2 s3+2 m0^2 s1 s2 s3+2 m3^2 s1 s2 s3-2 m0^4 s23 s3+2 m0^2 m1^2 s23 s3+2 m0^2 m2^2 s23 s3-2 m1^2 m2^2 s23 s3+2 m0^2 s1 s23 s3+2 m2^2 s1 s23 s3+2 m0^2 s12 s23 s3+2 m1^2 s12 s23 s3-2 s1 s12 s23 s3-4 m0^2 s2 s23 s3+m0^4 s3^2-2 m0^2 m1^2 s3^2+m1^4 s3^2-2 m0^2 s1 s3^2-2 m1^2 s1 s3^2+s1^2 s3^2+2 m1^2 m2^2 s1 s4-2 m2^4 s1 s4-2 m1^2 m3^2 s1 s4+2 m2^2 m3^2 s1 s4-2 m1^4 s12 s4+2 m1^2 m2^2 s12 s4+2 m1^2 m3^2 s12 s4-2 m2^2 m3^2 s12 s4+2 m0^2 m1^2 s2 s4+2 m0^2 m2^2 s2 s4-4 m1^2 m2^2 s2 s4-4 m0^2 m3^2 s2 s4+2 m1^2 m3^2 s2 s4+2 m2^2 m3^2 s2 s4+2 m2^2 s1 s2 s4+2 m3^2 s1 s2 s4+2 m1^2 s12 s2 s4+2 m3^2 s12 s2 s4-2 m0^2 s2^2 s4-2 m3^2 s2^2 s4-2 m0^2 m1^2 s23 s4+2 m0^2 m2^2 s23 s4+2 m1^2 m2^2 s23 s4-2 m2^4 s23 s4-4 m2^2 s1 s23 s4+2 m1^2 s12 s23 s4+2 m2^2 s12 s23 s4+2 m0^2 s2 s23 s4+2 m2^2 s2 s23 s4-2 s12 s2 s23 s4+2 m0^2 m1^2 s3 s4-2 m1^4 s3 s4-2 m0^2 m2^2 s3 s4+2 m1^2 m2^2 s3 s4+2 m1^2 s1 s3 s4+2 m2^2 s1 s3 s4-4 m1^2 s12 s3 s4+2 m0^2 s2 s3 s4+2 m1^2 s2 s3 s4-2 s1 s2 s3 s4+m1^4 s4^2-2 m1^2 m2^2 s4^2+m2^4 s4^2-2 m1^2 s2 s4^2-2 m2^2 s2 s4^2+s2^2 s4^2]},
	  2 \[Pi] I HeavisideTheta[s1-(m0+m1)^2] * 
	  If[(*If factored determinant is of the form (...)^2(...)^2, can cancel the square root; and simplify*)
		MatchQ[factoredDeterminant,HoldPattern[Power[_,_Integer?EvenQ]|Times[Power[_,_Integer?EvenQ]..]]],
		  With[{rootDetY=Replace[factoredDeterminant,Power[x_,n_Integer?EvenQ]:>Power[x,n/2],{0,1}]},
			Log[(Simplify[kappa+rootKallen[s1,m0^2,m1^2] rootDetY])/(Simplify[kappa-rootKallen[s1,m0^2,m1^2] rootDetY])]/rootDetY
		  ],
		(*Otherwise, the argument of the logarithm cannot be simplified*)
	    Log[(kappa+rootKallen[s1,m0^2,m1^2] Sqrt[factoredDeterminant])/(kappa-rootKallen[s1,m0^2,m1^2] Sqrt[factoredDeterminant])]/Sqrt[factoredDeterminant]
	  ]
  ]
]*)



(* ::Subsubsection::Closed:: *)
(*D0 functions (with IR subtractions)*)


(*DISCONTINUITY of ScalarD0*)

(*Mandelstam double spectral function*)
permutedSetDelayed[disc[analD0][chnl[s1_],s2_,chnl[s3_],s4_,s12_,s23_,m0_,m1_,m2_,m3_],
   With[{
	kappa=Factor[2 m0^2 m1^2 s1-m0^2 m2^2 s1-m1^2 m2^2 s1-m0^2 m3^2 s1-m1^2 m3^2 s1+2 m2^2 m3^2 s1+m2^2 s1^2+m3^2 s1^2-m0^2 m1^2 s12+m1^4 s12+m0^2 m3^2 s12-m1^2 m3^2 s12-m1^2 s1 s12-m3^2 s1 s12+m0^4 s2-m0^2 m1^2 s2-m0^2 m3^2 s2+m1^2 m3^2 s2-m0^2 s1 s2-m3^2 s1 s2+m0^4 s23-m0^2 m1^2 s23-m0^2 m2^2 s23+m1^2 m2^2 s23-m0^2 s1 s23-m2^2 s1 s23-m0^2 s12 s23-m1^2 s12 s23+s1 s12 s23+2 m0^2 s2 s23-m0^4 s3+2 m0^2 m1^2 s3-m1^4 s3+2 m0^2 s1 s3+2 m1^2 s1 s3-s1^2 s3-m0^2 m1^2 s4+m1^4 s4+m0^2 m2^2 s4-m1^2 m2^2 s4-m1^2 s1 s4-m2^2 s1 s4+2 m1^2 s12 s4-m0^2 s2 s4-m1^2 s2 s4+s1 s2 s4],
	factoredDeterminant=Factor[m2^4 s1^2-2 m2^2 m3^2 s1^2+m3^4 s1^2-2 m1^2 m2^2 s1 s12+2 m1^2 m3^2 s1 s12+2 m2^2 m3^2 s1 s12-2 m3^4 s1 s12+m1^4 s12^2-2 m1^2 m3^2 s12^2+m3^4 s12^2-2 m0^2 m2^2 s1 s2+2 m0^2 m3^2 s1 s2+2 m2^2 m3^2 s1 s2-2 m3^4 s1 s2-2 m0^2 m1^2 s12 s2+2 m0^2 m3^2 s12 s2+2 m1^2 m3^2 s12 s2-2 m3^4 s12 s2-4 m3^2 s1 s12 s2+m0^4 s2^2-2 m0^2 m3^2 s2^2+m3^4 s2^2+2 m0^2 m2^2 s1 s23-2 m2^4 s1 s23-2 m0^2 m3^2 s1 s23+2 m2^2 m3^2 s1 s23+2 m0^2 m1^2 s12 s23-4 m0^2 m2^2 s12 s23+2 m1^2 m2^2 s12 s23+2 m0^2 m3^2 s12 s23-4 m1^2 m3^2 s12 s23+2 m2^2 m3^2 s12 s23+2 m2^2 s1 s12 s23+2 m3^2 s1 s12 s23-2 m1^2 s12^2 s23-2 m3^2 s12^2 s23-2 m0^4 s2 s23+2 m0^2 m2^2 s2 s23+2 m0^2 m3^2 s2 s23-2 m2^2 m3^2 s2 s23+2 m0^2 s12 s2 s23+2 m3^2 s12 s2 s23+m0^4 s23^2-2 m0^2 m2^2 s23^2+m2^4 s23^2-2 m0^2 s12 s23^2-2 m2^2 s12 s23^2+s12^2 s23^2-4 m0^2 m1^2 s1 s3+2 m0^2 m2^2 s1 s3+2 m1^2 m2^2 s1 s3+2 m0^2 m3^2 s1 s3+2 m1^2 m3^2 s1 s3-4 m2^2 m3^2 s1 s3-2 m2^2 s1^2 s3-2 m3^2 s1^2 s3+2 m0^2 m1^2 s12 s3-2 m1^4 s12 s3-2 m0^2 m3^2 s12 s3+2 m1^2 m3^2 s12 s3+2 m1^2 s1 s12 s3+2 m3^2 s1 s12 s3-2 m0^4 s2 s3+2 m0^2 m1^2 s2 s3+2 m0^2 m3^2 s2 s3-2 m1^2 m3^2 s2 s3+2 m0^2 s1 s2 s3+2 m3^2 s1 s2 s3-2 m0^4 s23 s3+2 m0^2 m1^2 s23 s3+2 m0^2 m2^2 s23 s3-2 m1^2 m2^2 s23 s3+2 m0^2 s1 s23 s3+2 m2^2 s1 s23 s3+2 m0^2 s12 s23 s3+2 m1^2 s12 s23 s3-2 s1 s12 s23 s3-4 m0^2 s2 s23 s3+m0^4 s3^2-2 m0^2 m1^2 s3^2+m1^4 s3^2-2 m0^2 s1 s3^2-2 m1^2 s1 s3^2+s1^2 s3^2+2 m1^2 m2^2 s1 s4-2 m2^4 s1 s4-2 m1^2 m3^2 s1 s4+2 m2^2 m3^2 s1 s4-2 m1^4 s12 s4+2 m1^2 m2^2 s12 s4+2 m1^2 m3^2 s12 s4-2 m2^2 m3^2 s12 s4+2 m0^2 m1^2 s2 s4+2 m0^2 m2^2 s2 s4-4 m1^2 m2^2 s2 s4-4 m0^2 m3^2 s2 s4+2 m1^2 m3^2 s2 s4+2 m2^2 m3^2 s2 s4+2 m2^2 s1 s2 s4+2 m3^2 s1 s2 s4+2 m1^2 s12 s2 s4+2 m3^2 s12 s2 s4-2 m0^2 s2^2 s4-2 m3^2 s2^2 s4-2 m0^2 m1^2 s23 s4+2 m0^2 m2^2 s23 s4+2 m1^2 m2^2 s23 s4-2 m2^4 s23 s4-4 m2^2 s1 s23 s4+2 m1^2 s12 s23 s4+2 m2^2 s12 s23 s4+2 m0^2 s2 s23 s4+2 m2^2 s2 s23 s4-2 s12 s2 s23 s4+2 m0^2 m1^2 s3 s4-2 m1^4 s3 s4-2 m0^2 m2^2 s3 s4+2 m1^2 m2^2 s3 s4+2 m1^2 s1 s3 s4+2 m2^2 s1 s3 s4-4 m1^2 s12 s3 s4+2 m0^2 s2 s3 s4+2 m1^2 s2 s3 s4-2 s1 s2 s3 s4+m1^4 s4^2-2 m1^2 m2^2 s4^2+m2^4 s4^2-2 m1^2 s2 s4^2-2 m2^2 s2 s4^2+s2^2 s4^2]},
	  2 \[Pi] I * 
	  If[(*If factored determinant is of the form (...)^2(...)^2, can cancel the square root; and simplify*)
		MatchQ[factoredDeterminant,HoldPattern[Power[_,_Integer?EvenQ]|Times[Power[_,_Integer?EvenQ]..]]],
		  With[{rootDetY=Replace[factoredDeterminant,Power[x_,n_Integer?EvenQ]:>Power[x,n/2],{0,1}]},
			HeavisideTheta[rootDetY]/rootDetY
		  ],
		(*Otherwise, the argument of the logarithm cannot be simplified*)
	    HeavisideTheta[factoredDeterminant]/Sqrt[factoredDeterminant]
	  ]
  ]
];

permutedSetDelayed[
  disc[analD0][0,p21_,0,p30_,chnl[p20_],p31_,0,0,0,0],
  (4 \[Pi] I)/(-p21 p30+p20 p31) (Log[logArgumentSimplify[($tarScaleSq(-p20^2+p20 p21+p20 p30-p21 p30))/(p20(-p21 p30+p20 p31))]]+ 1/Eps +Log[Mu^2/$tarScaleSq])HeavisideTheta[p20]
];

permutedSetDelayed[
  disc[analD0][0,0,p32_,p30_,p20_,chnl[p31_],0,0,0,m3_],
  (*Universal finite part*)-((4 I \[Pi] HeavisideTheta[-m3^2+p31] Log[logArgumentSimplify[((p30-p31) (p31-p32))/(p20 p31)]])/(p20 (m3^2-p31)))+
 (*Divergent part*) -((4 I \[Pi] HeavisideTheta[-m3^2+p31] (Log[p31*$tarScaleSq/(-m3^2+p31)^2]+1/Eps+Log[Mu^2/$tarScaleSq]))/(p20 (m3^2-p31)))
];

permutedSetDelayed[
  disc[analD0][0,p21_,p32_,p30_,p20_,chnl[p31_],0,0,m2_,m3_],
  (*Universal finite part*)(2 I \[Pi] HeavisideTheta[-m3^2+p31] (-Log[logArgumentSimplify[(-(p30-p31)^2 (m2^4 p31+p21 (m3^4+m3^2 (p21-p31-p32)+p31 p32)-m2^2 (m3^2 (p21+p31-p32)+p31 (p21-p31+p32))))/(p31 (m3^2 (p20-p21)+p21 p30-p20 p31+m2^2 (-p30+p31))^2)]]))/(m3^2 p20-m3^2 p21-m2^2 p30+p21 p30+m2^2 p31-p20 p31)+
  (*Divergent part*)-((2 I \[Pi] HeavisideTheta[-m3^2+p31] ( Log[p31*$tarScaleSq/(-m3^2+p31)^2]+1/Eps+Log[Mu^2/$tarScaleSq]))/(m3^2 p20-m3^2 p21-m2^2 p30+p21 p30+m2^2 p31-p20 p31))
];

permutedSetDelayed[
  disc[analD0][s1_,s2_,s3_,s4_,p20_,chnl[p31_],0,m1_,0,m3_],
  (*Universal finite part*)(4 I \[Pi] HeavisideTheta[-(m1+m3)^2+p31] (-Log[logArgumentSimplify[(-p20 p31)/Kallen\[Lambda][m1^2,m3^2,p31]]]))/(p20 rootKallen[p31,m1^2,m3^2]) + 
  (*Divergent part*)(4 I \[Pi] HeavisideTheta[-(m1+m3)^2+p31])/(p20 rootKallen[p31,m1^2,m3^2]) (1/Eps+Log[Mu^2/$tarScaleSq]+Log[p31*$tarScaleSq/Kallen\[Lambda][m1^2,m3^2,p31]])
	/; PossibleZeroQ[s1-m1^2] && PossibleZeroQ[s2-m1^2] && PossibleZeroQ[s3-m3^2] && PossibleZeroQ[s4-m3^2]
];

permutedSetDelayed[
  disc[analD0][s1_,s2_,s3_,s4_,s12_,chnl[s23_],0,m1_,m2_,m3_],
  (*Universal finite part*)(2 I \[Pi] HeavisideTheta[-(m1+m3)^2+s23])/((s12-m2^2) rootKallen[s23,m1^2,m3^2]) Log[logArgumentSimplify[1/((s12-m2^2)^2 s23) (m1^2 m2^2 s2-m1^2 m3^2 s2-m2^2 m3^2 s2+m3^4 s2+m3^2 s2^2-m1^2 m2^2 s23+m2^4 s23+m1^2 m3^2 s23-m2^2 m3^2 s23-m2^2 s2 s23-m3^2 s2 s23+m2^2 s23^2+m1^4 s3-m1^2 m2^2 s3-m1^2 m3^2 s3+m2^2 m3^2 s3-m1^2 s2 s3-m3^2 s2 s3-m1^2 s23 s3-m2^2 s23 s3+s2 s23 s3+m1^2 s3^2)]] + 
  (*Divergent part*)(2 I \[Pi] HeavisideTheta[-(m1+m3)^2+s23] )/((s12-m2^2)rootKallen[s23,m1^2,m3^2]) (1/Eps+Log[Mu^2/$tarScaleSq]+Log[s23*$tarScaleSq/Kallen\[Lambda][m1^2,m3^2,s23]])
	/; PossibleZeroQ[s1-m1^2] && PossibleZeroQ[s4-m3^2]
];

(*DISCONTINUITY of ScalarD0*)
permutedSetDelayed[disc[analD0][chnl[s1_],s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_],
   With[{
	kappa=Factor[2 m0^2 m1^2 s1-m0^2 m2^2 s1-m1^2 m2^2 s1-m0^2 m3^2 s1-m1^2 m3^2 s1+2 m2^2 m3^2 s1+m2^2 s1^2+m3^2 s1^2-m0^2 m1^2 s12+m1^4 s12+m0^2 m3^2 s12-m1^2 m3^2 s12-m1^2 s1 s12-m3^2 s1 s12+m0^4 s2-m0^2 m1^2 s2-m0^2 m3^2 s2+m1^2 m3^2 s2-m0^2 s1 s2-m3^2 s1 s2+m0^4 s23-m0^2 m1^2 s23-m0^2 m2^2 s23+m1^2 m2^2 s23-m0^2 s1 s23-m2^2 s1 s23-m0^2 s12 s23-m1^2 s12 s23+s1 s12 s23+2 m0^2 s2 s23-m0^4 s3+2 m0^2 m1^2 s3-m1^4 s3+2 m0^2 s1 s3+2 m1^2 s1 s3-s1^2 s3-m0^2 m1^2 s4+m1^4 s4+m0^2 m2^2 s4-m1^2 m2^2 s4-m1^2 s1 s4-m2^2 s1 s4+2 m1^2 s12 s4-m0^2 s2 s4-m1^2 s2 s4+s1 s2 s4],
	factoredDeterminant=Factor[m2^4 s1^2-2 m2^2 m3^2 s1^2+m3^4 s1^2-2 m1^2 m2^2 s1 s12+2 m1^2 m3^2 s1 s12+2 m2^2 m3^2 s1 s12-2 m3^4 s1 s12+m1^4 s12^2-2 m1^2 m3^2 s12^2+m3^4 s12^2-2 m0^2 m2^2 s1 s2+2 m0^2 m3^2 s1 s2+2 m2^2 m3^2 s1 s2-2 m3^4 s1 s2-2 m0^2 m1^2 s12 s2+2 m0^2 m3^2 s12 s2+2 m1^2 m3^2 s12 s2-2 m3^4 s12 s2-4 m3^2 s1 s12 s2+m0^4 s2^2-2 m0^2 m3^2 s2^2+m3^4 s2^2+2 m0^2 m2^2 s1 s23-2 m2^4 s1 s23-2 m0^2 m3^2 s1 s23+2 m2^2 m3^2 s1 s23+2 m0^2 m1^2 s12 s23-4 m0^2 m2^2 s12 s23+2 m1^2 m2^2 s12 s23+2 m0^2 m3^2 s12 s23-4 m1^2 m3^2 s12 s23+2 m2^2 m3^2 s12 s23+2 m2^2 s1 s12 s23+2 m3^2 s1 s12 s23-2 m1^2 s12^2 s23-2 m3^2 s12^2 s23-2 m0^4 s2 s23+2 m0^2 m2^2 s2 s23+2 m0^2 m3^2 s2 s23-2 m2^2 m3^2 s2 s23+2 m0^2 s12 s2 s23+2 m3^2 s12 s2 s23+m0^4 s23^2-2 m0^2 m2^2 s23^2+m2^4 s23^2-2 m0^2 s12 s23^2-2 m2^2 s12 s23^2+s12^2 s23^2-4 m0^2 m1^2 s1 s3+2 m0^2 m2^2 s1 s3+2 m1^2 m2^2 s1 s3+2 m0^2 m3^2 s1 s3+2 m1^2 m3^2 s1 s3-4 m2^2 m3^2 s1 s3-2 m2^2 s1^2 s3-2 m3^2 s1^2 s3+2 m0^2 m1^2 s12 s3-2 m1^4 s12 s3-2 m0^2 m3^2 s12 s3+2 m1^2 m3^2 s12 s3+2 m1^2 s1 s12 s3+2 m3^2 s1 s12 s3-2 m0^4 s2 s3+2 m0^2 m1^2 s2 s3+2 m0^2 m3^2 s2 s3-2 m1^2 m3^2 s2 s3+2 m0^2 s1 s2 s3+2 m3^2 s1 s2 s3-2 m0^4 s23 s3+2 m0^2 m1^2 s23 s3+2 m0^2 m2^2 s23 s3-2 m1^2 m2^2 s23 s3+2 m0^2 s1 s23 s3+2 m2^2 s1 s23 s3+2 m0^2 s12 s23 s3+2 m1^2 s12 s23 s3-2 s1 s12 s23 s3-4 m0^2 s2 s23 s3+m0^4 s3^2-2 m0^2 m1^2 s3^2+m1^4 s3^2-2 m0^2 s1 s3^2-2 m1^2 s1 s3^2+s1^2 s3^2+2 m1^2 m2^2 s1 s4-2 m2^4 s1 s4-2 m1^2 m3^2 s1 s4+2 m2^2 m3^2 s1 s4-2 m1^4 s12 s4+2 m1^2 m2^2 s12 s4+2 m1^2 m3^2 s12 s4-2 m2^2 m3^2 s12 s4+2 m0^2 m1^2 s2 s4+2 m0^2 m2^2 s2 s4-4 m1^2 m2^2 s2 s4-4 m0^2 m3^2 s2 s4+2 m1^2 m3^2 s2 s4+2 m2^2 m3^2 s2 s4+2 m2^2 s1 s2 s4+2 m3^2 s1 s2 s4+2 m1^2 s12 s2 s4+2 m3^2 s12 s2 s4-2 m0^2 s2^2 s4-2 m3^2 s2^2 s4-2 m0^2 m1^2 s23 s4+2 m0^2 m2^2 s23 s4+2 m1^2 m2^2 s23 s4-2 m2^4 s23 s4-4 m2^2 s1 s23 s4+2 m1^2 s12 s23 s4+2 m2^2 s12 s23 s4+2 m0^2 s2 s23 s4+2 m2^2 s2 s23 s4-2 s12 s2 s23 s4+2 m0^2 m1^2 s3 s4-2 m1^4 s3 s4-2 m0^2 m2^2 s3 s4+2 m1^2 m2^2 s3 s4+2 m1^2 s1 s3 s4+2 m2^2 s1 s3 s4-4 m1^2 s12 s3 s4+2 m0^2 s2 s3 s4+2 m1^2 s2 s3 s4-2 s1 s2 s3 s4+m1^4 s4^2-2 m1^2 m2^2 s4^2+m2^4 s4^2-2 m1^2 s2 s4^2-2 m2^2 s2 s4^2+s2^2 s4^2]},
	  2 \[Pi] I HeavisideTheta[s1-(m0+m1)^2] * 
	  If[(*If factored determinant is of the form (...)^2(...)^2, can cancel the square root; and simplify*)
		MatchQ[factoredDeterminant,HoldPattern[Power[_,_Integer?EvenQ]|Times[Power[_,_Integer?EvenQ]..]]],
		  With[{rootDetY=Replace[factoredDeterminant,Power[x_,n_Integer?EvenQ]:>Power[x,n/2],{0,1}]},
			Log[(Simplify[kappa+rootKallen[s1,m0^2,m1^2] rootDetY])/(Simplify[kappa-rootKallen[s1,m0^2,m1^2] rootDetY])]/rootDetY
		  ],
		(*Otherwise, the argument of the logarithm cannot be simplified*)
	    Log[(kappa+rootKallen[s1,m0^2,m1^2] Sqrt[factoredDeterminant])/(kappa-rootKallen[s1,m0^2,m1^2] Sqrt[factoredDeterminant])]/Sqrt[factoredDeterminant]
	  ]
  ]
];


(* ::Section::Closed:: *)
(*Exotic PV functions*)


(* ::Subsection:: *)
(*Derivatives*)


(* ::Subsubsection::Closed:: *)
(*taylorSeriesExistsQ*)


(*A functions, should always return False*)
With[{tadpoleSingularity0=#1&},
	taylorSeriesExistsQ[variationSignature__Integer][PVA] := 
		And[(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity0][##]]||!PossibleZeroQ[tadpoleSingularity0[##]])]&
];


(*B functions*)
With[{normalThresholds=#1-(#2+#3)^2&,
	  tadpoleSingularity0=#2&, tadpoleSingularity1=#3&},
	taylorSeriesExistsQ[variationSignature__Integer][PVB] := 
		And[(PossibleZeroQ[Derivative[variationSignature][normalThresholds][##]]||!PossibleZeroQ[normalThresholds[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity0][##]]||!PossibleZeroQ[tadpoleSingularity0[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity1][##]]||!PossibleZeroQ[tadpoleSingularity1[##]])]&
];


(*C functions*)
With[{normalThresholdp1=#1-(#4+#5)^2&, normalThresholdq=#2-(#5+#6)^2&, normalThresholdp2=#3-(#4+#6)^2&, 
	  tadpoleSingularity0=#4&, tadpoleSingularity1=#5&, tadpoleSingularity2=#6&},
	taylorSeriesExistsQ[variationSignature__Integer][PVC] := 
		And[(PossibleZeroQ[Derivative[variationSignature][normalThresholdp1][##]]||!PossibleZeroQ[normalThresholdp1[##]]),
			(PossibleZeroQ[Derivative[variationSignature][normalThresholdq][##]]||!PossibleZeroQ[normalThresholdq[##]]),
			(PossibleZeroQ[Derivative[variationSignature][normalThresholdp2][##]]||!PossibleZeroQ[normalThresholdp2[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity0][##]]||!PossibleZeroQ[tadpoleSingularity0[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity1][##]]||!PossibleZeroQ[tadpoleSingularity1[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity2][##]]||!PossibleZeroQ[tadpoleSingularity2[##]])]&
];


(*D functions*)
With[{normalThresholds1=#1-(#7+#8)^2&,normalThresholds2=#2-(#8+#9)^2&,normalThresholds3=#3-(#9+#10)^2&,normalThresholds4=#4-(#7+#10)^2&,
	  normalThresholds12=#5-(#7+#9)^2&,normalThresholds23=#6-(#8+#10)^2&,
	  tadpoleSingularity0=#7&, tadpoleSingularity1=#8&, tadpoleSingularity2=#9&,tadpoleSingularity3=#10&},
	taylorSeriesExistsQ[variationSignature__Integer][PVD] := 
		And[(*(PossibleZeroQ[Derivative[derivs][leadingSingularity][##]]||!PossibleZeroQ[leadingSingularity[##]]),*)
			(PossibleZeroQ[Derivative[variationSignature][normalThresholds1][##]]||!PossibleZeroQ[normalThresholds1[##]]),
			(PossibleZeroQ[Derivative[variationSignature][normalThresholds2][##]]||!PossibleZeroQ[normalThresholds2[##]]),
			(PossibleZeroQ[Derivative[variationSignature][normalThresholds3][##]]||!PossibleZeroQ[normalThresholds3[##]]),
			(PossibleZeroQ[Derivative[variationSignature][normalThresholds4][##]]||!PossibleZeroQ[normalThresholds4[##]]),
			(PossibleZeroQ[Derivative[variationSignature][normalThresholds12][##]]||!PossibleZeroQ[normalThresholds12[##]]),
			(PossibleZeroQ[Derivative[variationSignature][normalThresholds23][##]]||!PossibleZeroQ[normalThresholds23[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity0][##]]||!PossibleZeroQ[tadpoleSingularity0[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity1][##]]||!PossibleZeroQ[tadpoleSingularity1[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity2][##]]||!PossibleZeroQ[tadpoleSingularity2[##]]),
			(PossibleZeroQ[Derivative[variationSignature][tadpoleSingularity3][##]]||!PossibleZeroQ[tadpoleSingularity3[##]])]&
];


(* ::Subsubsection::Closed:: *)
(*InternalSeries (expansions at infinity)*)


Unprotect[System`Private`InternalSeries];


System`Private`InternalSeries[Hold[pvf:_PVA|_PVB|_PVC|_PVD],{z_,p_,nn_Integer}]:=Hold[pvf];

System`Private`InternalSeries[PVA[r_,fM0_,opts: OptionsPattern[PVA]],{z_,p_,nn_Integer}]:=
With[{limM0InfQ=PolynomialQ[fM0,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM0,z->p]]},
  Module[{exp,functionToExpand},

	exp=Exponent[fM0^2,z]/2;

	functionToExpand=(z^(2exp))^(r+2-Total[OptionValue[PVA,{opts},Weights]])*PVA[r,fM0/z^exp,opts];

	(1-Log[z^(2exp)] Eps+1/2 Log[z^(2exp)]^2 Eps^2)System`SeriesDump`SafeSeries[functionToExpand,{z,p,nn}]
  ]/;limM0InfQ
];

System`Private`InternalSeries[PVB[r_,n1_,fs_,fM0_,fM1_,opts: OptionsPattern[PVB]],{z_,p_,nn_Integer}]:=
With[{limsInfQ=PolynomialQ[fs,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs,z->p]],
	  limM0InfQ=PolynomialQ[fM0,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM0,z->p]],
	  limM1InfQ=PolynomialQ[fM1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM1,z->p]]},
  Module[{exp,functionToExpand},

	exp=Max[{Exponent[fs,z],Exponent[fM0^2,z],Exponent[fM1^2,z]}]/2;


	functionToExpand=(z^(2exp))^(r+2-Total[OptionValue[PVB,{opts},Weights]])*PVB[r,n1,fs/z^(2exp),fM0/z^exp,fM1/z^exp,opts];

	(1-Log[z^(2exp)] Eps+1/2 Log[z^(2exp)]^2 Eps^2)System`SeriesDump`SafeSeries[functionToExpand,{z,p,nn}]
  ]/;limsInfQ||limM0InfQ||limM1InfQ
];

System`Private`InternalSeries[PVC[r_,n1_,n2_,fp1_,fq_,fp2_,fM0_,fM1_,fM2_,opts: OptionsPattern[PVC]],{z_,p_,nn_Integer}]:=
With[{limp1InfQ=PolynomialQ[fp1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fp1,z->p]],
	  limqInfQ=PolynomialQ[fq,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fq,z->p]],
	  limp2InfQ=PolynomialQ[fp2,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fp2,z->p]],
	  limM0InfQ=PolynomialQ[fM0,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM0,z->p]],
	  limM1InfQ=PolynomialQ[fM1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM1,z->p]],
	  limM2InfQ=PolynomialQ[fM2,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM2,z->p]]},
  Module[{exp,functionToExpand},


	exp=Max[{Exponent[fp1,z],Exponent[fq,z],Exponent[fp2,z],Exponent[fM0^2,z],Exponent[fM1^2,z],Exponent[fM2^2,z]}]/2;

	functionToExpand=(z^(2exp))^(r+2-Total[OptionValue[PVC,{opts},Weights]])*PVC[r,n1,n2,fp1/z^(2exp),fq/z^(2exp),fp2/z^(2exp),fM0/z^exp,fM1/z^exp,fM2/z^exp,opts];

	(1-Log[z^(2exp)] Eps+1/2 Log[z^(2exp)]^2 Eps^2)System`SeriesDump`SafeSeries[functionToExpand,{z,p,nn}]
  ]/;limqInfQ||limp1InfQ||limp2InfQ||limM0InfQ||limM1InfQ||limM2InfQ
];

System`Private`InternalSeries[PVD[r_,n1_,n2_,n3_,fs1_,fs2_,fs3_,fs4_,fs12_,fs23_,fM0_,fM1_,fM2_,fM3_,opts: OptionsPattern[PVD]],{z_,p_,nn_Integer}]:=
With[{lims1InfQ=PolynomialQ[fs1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs1,z->p]],
	  lims2InfQ=PolynomialQ[fs2,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs2,z->p]],
	  lims3InfQ=PolynomialQ[fs3,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs3,z->p]],
	  lims4InfQ=PolynomialQ[fs4,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs4,z->p]],
	  lims12InfQ=PolynomialQ[fs12,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs12,z->p]],
	  lims23InfQ=PolynomialQ[fs23,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs23,z->p]],
	  limM0InfQ=PolynomialQ[fM0,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM0,z->p]],
	  limM1InfQ=PolynomialQ[fM1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM1,z->p]],
	  limM2InfQ=PolynomialQ[fM2,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM2,z->p]],
	  limM3InfQ=PolynomialQ[fM3,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM3,z->p]]},
  Module[{exp,functionToExpand},

	exp=Max[{Exponent[fs1,z],Exponent[fs2,z],Exponent[fs3,z],Exponent[fs4,z],Exponent[fs12,z],Exponent[fs23,z],Exponent[fM0^2,z],Exponent[fM1^2,z],Exponent[fM2^2,z],Exponent[fM3^2,z]}]/2;


	functionToExpand=(z^(2exp))^(r+2-Total[OptionValue[PVD,{opts},Weights]])*PVD[r,n1,n2,n3,fs1/z^(2exp),fs2/z^(2exp),fs3/z^(2exp),fs4/z^(2exp),fs12/z^(2exp),fs23/z^(2exp),fM0/z^exp,fM1/z^exp,fM2/z^exp,fM3/z^exp,opts];

	(1-Log[z^(2exp)] Eps+1/2 Log[z^(2exp)]^2 Eps^2)System`SeriesDump`SafeSeries[functionToExpand,{z,p,nn}]
  ]/;lims1InfQ||lims2InfQ||lims3InfQ||lims4InfQ||lims12InfQ||lims23InfQ||limM0InfQ||limM1InfQ||limM2InfQ||limM3InfQ
];

(*Scalar functions*)
System`Private`InternalSeries[ScalarC0[fp1_,fq_,fp2_,fM0_,fM1_,fM2_],{z_,p_,nn_Integer}]:=
With[{limp1InfQ=PolynomialQ[fp1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fp1,z->p]],
	  limqInfQ=PolynomialQ[fq,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fq,z->p]],
	  limp2InfQ=PolynomialQ[fp2,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fp2,z->p]],
	  limM0InfQ=PolynomialQ[fM0,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM0,z->p]],
	  limM1InfQ=PolynomialQ[fM1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM1,z->p]],
	  limM2InfQ=PolynomialQ[fM2,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM2,z->p]]},
  Module[{exp,functionToExpand},


	exp=Max[{Exponent[fp1,z],Exponent[fq,z],Exponent[fp2,z],Exponent[fM0^2,z],Exponent[fM1^2,z],Exponent[fM2^2,z]}]/2;

	functionToExpand=(z^(2exp))^(-1)*PVC[0,0,0,fp1/z^(2exp),fq/z^(2exp),fp2/z^(2exp),fM0/z^exp,fM1/z^exp,fM2/z^exp];

	System`SeriesDump`SafeSeries[functionToExpand,{z,p,nn}]
  ]/;limqInfQ||limp1InfQ||limp2InfQ||limM0InfQ||limM1InfQ||limM2InfQ
];

System`Private`InternalSeries[ScalarD0[fs1_,fs2_,fs3_,fs4_,fs12_,fs23_,fM0_,fM1_,fM2_,fM3_],{z_,p_,nn_Integer}]:=
With[{lims1InfQ=PolynomialQ[fs1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs1,z->p]],
	  lims2InfQ=PolynomialQ[fs2,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs2,z->p]],
	  lims3InfQ=PolynomialQ[fs3,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs3,z->p]],
	  lims4InfQ=PolynomialQ[fs4,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs4,z->p]],
	  lims12InfQ=PolynomialQ[fs12,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs12,z->p]],
	  lims23InfQ=PolynomialQ[fs23,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fs23,z->p]],
	  limM0InfQ=PolynomialQ[fM0,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM0,z->p]],
	  limM1InfQ=PolynomialQ[fM1,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM1,z->p]],
	  limM2InfQ=PolynomialQ[fM2,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM2,z->p]],
	  limM3InfQ=PolynomialQ[fM3,z]&&System`SeriesDump`ExpansionPointInfinityQ[Limit[fM3,z->p]]},
  Module[{exp,functionToExpand},

	exp=Max[{Exponent[fs1,z],Exponent[fs2,z],Exponent[fs3,z],Exponent[fs4,z],
			 Exponent[fs12,z],Exponent[fs23,z],
			 Exponent[fM0^2,z],Exponent[fM1^2,z],Exponent[fM2^2,z],Exponent[fM3^2,z]}]/2;

	functionToExpand=(z^(2exp))^(-2)*PVD[0,0,0,0,fs1/z^(2exp),fs2/z^(2exp),fs3/z^(2exp),fs4/z^(2exp),fs12/z^(2exp),fs23/z^(2exp),fM0/z^exp,fM1/z^exp,fM2/z^exp,fM3/z^exp];

	System`SeriesDump`SafeSeries[functionToExpand,{z,p,nn}]
  ]/;lims1InfQ||lims2InfQ||lims3InfQ||lims4InfQ||lims12InfQ||lims23InfQ||limM0InfQ||limM1InfQ||limM2InfQ||limM3InfQ
];


(*Prevent series expansions of special functions around their sigular points*)
System`Private`InternalSeries[ScalarC0[fp1_,fq_,fp2_,fM0_,fM1_,fM2_],{z_,p_,nn_Integer}] /; ((Not[And[##]]&)@@Through[((taylorSeriesExistsQ[##][PVC]&)@@UnitVector[6,#]&/@(Flatten[Position[{fp1,fq,fp2,fM0,fM1,fM2},_?(!FreeQ[#,z]&),1]]))@@(Limit[{fp1,fq,fp2,fM0,fM1,fM2},z->p])]) := ScalarC0[fp1,fq,fp2,fM0,fM1,fM2];
System`Private`InternalSeries[ScalarD0[fs1_,fs2_,fs3_,fs4_,fs12_,fs23_,fM0_,fM1_,fM2_,fM3_],{z_,p_,nn_Integer}] /; ((Not[And[##]]&)@@Through[((taylorSeriesExistsQ[##][PVD]&)@@UnitVector[10,#]&/@(Flatten[Position[{fs1,fs2,fs3,fs4,fs12,fs23,fM0,fM1,fM2,fM3},_?(!FreeQ[#,z]&),1]]))@@(Limit[{fs1,fs2,fs3,fs4,fs12,fs23,fM0,fM1,fM2,fM3},z->p])]) := ScalarD0[fs1,fs2,fs3,fs4,fs12,fs23,fM0,fM1,fM2,fM3];

(*Code analysis of Condition used above; uncomment for better viewing*)

(*
Apply[
  (*5th Apply Not[And] to check if Taylor series doesn't exist.*)
  Not[And[##]]&,
  Through[Apply[
	  (*4th, Apply (followed by Through) to obtain
		{taylorSeriesExistsQ[1,0,0,0,0,0][PVC][fp1,fq,fp2,fm0,fm1,fm2], taylorSeriesExistsQ[1,0,0,0,0,0][PVC][p1,q,p2,m0,m1,m2][fp1,fq,fp2,fm0,fm1,fm2]}
		but with fp1...fm2 at the limit z\[Rule]p.  Each element will evaluate to a boolean.*)
	  Map[(*2nd, Map taylerSeriesExistsQ across the list of argument signatures forming e.g.
			 {taylorSeriesExistsQ[1,0,0,0,0,0][PVC], taylorSeriesExistsQ[0,0,1,0,0,0][PVC]}*)
		(taylorSeriesExistsQ[##1][PVC]&)@@UnitVector[6,#1]&,
		  (*1st, generate a list of argument signatures for which argument depends on expansion point, e.g.
			{{1,0,0,0,0,0},{0,0,1,0,0,0}}*)
		  Flatten[Position[List[fp1,fq,fp2,fM0,fM1,fM2],_?(!FreeQ[#,z]&),1]]
	  ],
	(*3rd, obtain arguments at the expansion point*)
	Limit[List[fp1,fq,fp2,fM0,fM1,fM2],Rule[z,p]]]]]
*)


Protect[System`Private`InternalSeries];


(* ::Subsubsection::Closed:: *)
(*makeSer*)


makeSer[expr_, optAnalytic_, serArgs___List]:=
 Module[{expVar, expPoint},
  Internal`InheritedBlock[{Derivative, PVA, PVB, PVC, PVD},
	(*Need to block PVA...PVD since existance of their Derivatives are being remembered without observing OptionsValue[Analytic].
	  Alternatively, could use Update[PVA];Update[PVB];Update[PVC];Update[PVD];*)

	(*Derivatives of Passrino-Veltman A functions*)
	Derivative[0,n_?Positive,Optional[_,0],Optional[_,0]][PVA][r_,m0_,opts: OptionsPattern[PVA]]/;optAnalytic||taylorSeriesExistsQ[1][PVA][m0]:=m0*Derivative[0,n-1][PVA][r-1,m0,opts]+If[n>=2,(n-1)Derivative[0,n-2][PVA][r-1,m0,opts],0];

	(*Derivatives of Passrino-Veltman B functions*)
	Derivative[0,0,ns_?Positive,nm0_,nm1_,Optional[_,0],Optional[_,0]][PVB][r_,n1_,s_,m0_,m1_, opts: OptionsPattern[PVB]]/;optAnalytic||taylorSeriesExistsQ[1,0,0][PVB][s,m0,m1]:=1/2 Derivative[0,0,ns-1,nm0,nm1][PVB][r-1,n1+2,s,m0,m1,opts]+1/2 Derivative[0,0,ns-1,nm0,nm1][PVB][r-1,n1+1,s,m0,m1,opts];
	Derivative[0,0,ns_,nm0_?Positive,nm1_,Optional[_,0],Optional[_,0]][PVB][r_,n1_,s_,m0_,m1_, opts: OptionsPattern[PVB]]/;optAnalytic||taylorSeriesExistsQ[0,1,0][PVB][s,m0,m1]:=m0*Derivative[0,0,0,nm0-1,0][PVB][r-1,n1+1,s,m0,m1,opts]+If[nm0>=2,(nm0-1)Derivative[0,0,0,nm0-2,0][PVB][r-1,n1+1,s,m0,m1,opts],0]+m0*Derivative[0,0,0,nm0-1,0][PVB][r-1,n1,s,m0,m1,opts]+If[nm0>=2,(nm0-1)Derivative[0,0,0,nm0-2,0][PVB][r-1,n1,s,m0,m1,opts],0];
	Derivative[0,0,ns_,nm0_,nm1_?Positive,Optional[_,0],Optional[_,0]][PVB][r_,n1_,s_,m0_,m1_, opts: OptionsPattern[PVB]]/;optAnalytic||taylorSeriesExistsQ[0,0,1][PVB][s,m0,m1]:=-m1*Derivative[0,0,0,nm0,nm1-1][PVB][r-1,n1+1,s,m0,m1,opts]-If[nm1>=2,(nm1-1)Derivative[0,0,0,nm0,nm1-2][PVB][r-1,n1+1,s,m0,m1,opts],0];


	(*Derivatives of Passrino-Veltman C functions*)
	Derivative[0,0,0,np1_?Positive,nq_,np2_,nm0_,nm1_,nm2_,Optional[_,0],Optional[_,0]][PVC][r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_,opts: OptionsPattern[PVC]]/;optAnalytic||taylorSeriesExistsQ[1,0,0,0,0,0][PVC][p1,q,p2,m0,m1,m2]:=1/2 Derivative[0,0,0,np1-1,nq,np2,nm0,nm1,nm2][PVC][r-1,n1+2,n2,p1,q,p2,m0,m1,m2,opts]+1/2 Derivative[0,0,0,np1-1,nq,np2,nm0,nm1,nm2][PVC][r-1,n1+1,n2+1,p1,q,p2,m0,m1,m2,opts]+1/2 Derivative[0,0,0,np1-1,nq,np2,nm0,nm1,nm2][PVC][r-1,n1+1,n2,p1,q,p2,m0,m1,m2,opts];
	Derivative[0,0,0,np1_,nq_?Positive,np2_,nm0_,nm1_,nm2_,Optional[_,0],Optional[_,0]][PVC][r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_,opts: OptionsPattern[PVC]]/;optAnalytic||taylorSeriesExistsQ[0,1,0,0,0,0][PVC][p1,q,p2,m0,m1,m2]:=-(1/2)Derivative[0,0,0,np1,nq-1,np2,nm0,nm1,nm2][PVC][r-1,n1+1,n2+1,p1,q,p2,m0,m1,m2,opts];
	Derivative[0,0,0,np1_,nq_,np2_?Positive,nm0_,nm1_,nm2_,Optional[_,0],Optional[_,0]][PVC][r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_,opts: OptionsPattern[PVC]]/;optAnalytic||taylorSeriesExistsQ[0,0,1,0,0,0][PVC][p1,q,p2,m0,m1,m2]:=1/2 Derivative[0,0,0,np1,nq,np2-1,nm0,nm1,nm2][PVC][r-1,n1,n2+2,p1,q,p2,m0,m1,m2,opts]+1/2 Derivative[0,0,0,np1,nq,np2-1,nm0,nm1,nm2][PVC][r-1,n1+1,n2+1,p1,q,p2,m0,m1,m2,opts]+1/2 Derivative[0,0,0,np1,nq,np2-1,nm0,nm1,nm2][PVC][r-1,n1,n2+1,p1,q,p2,m0,m1,m2,opts];
	Derivative[0,0,0,np1_,nq_,np2_,nm0_?Positive,nm1_,nm2_,Optional[_,0],Optional[_,0]][PVC][r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_,opts: OptionsPattern[PVC]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,1,0,0][PVC][p1,q,p2,m0,m1,m2]:=m0*(Derivative[0,0,0,np1,nq,np2,nm0-1,nm1,nm2][PVC][r-1,n1+1,n2,p1,q,p2,m0,m1,m2,opts]+Derivative[0,0,0,np1,nq,np2,nm0-1,nm1,nm2][PVC][r-1,n1,n2+1,p1,q,p2,m0,m1,m2,opts]+Derivative[0,0,0,np1,nq,np2,nm0-1,nm1,nm2][PVC][r-1,n1,n2,p1,q,p2,m0,m1,m2,opts])+(nm0-1)*If[nm0>=2,Derivative[0,0,0,np1,nq,np2,nm0-2,nm1,nm2][PVC][r-1,n1+1,n2,p1,q,p2,m0,m1,m2,opts]+Derivative[0,0,0,np1,nq,np2,nm0-2,nm1,nm2][PVC][r-1,n1,n2+1,p1,q,p2,m0,m1,m2,opts]+Derivative[0,0,0,np1,nq,np2,nm0-2,nm1,nm2][PVC][r-1,n1,n2,p1,q,p2,m0,m1,m2,opts],0];
	Derivative[0,0,0,np1_,nq_,np2_,nm0_,nm1_?Positive,nm2_,Optional[_,0],Optional[_,0]][PVC][r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_,opts: OptionsPattern[PVC]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,0,1,0][PVC][p1,q,p2,m0,m1,m2]:=-m1 Derivative[0,0,0,np1,nq,np2,nm0,nm1-1,nm2][PVC][r-1,n1+1,n2,p1,q,p2,m0,m1,m2,opts]-If[nm1>=2,(nm1-1)Derivative[0,0,0,np1,nq,np2,nm0,nm1-2,nm2][PVC][r-1,n1+1,n2,p1,q,p2,m0,m1,m2,opts],0];
	Derivative[0,0,0,np1_,nq_,np2_,nm0_,nm1_,nm2_?Positive,Optional[_,0],Optional[_,0]][PVC][r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_,opts: OptionsPattern[PVC]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,0,0,1][PVC][p1,q,p2,m0,m1,m2]:=-m2 Derivative[0,0,0,np1,nq,np2,nm0,nm1,nm2-1][PVC][r-1,n1,n2+1,p1,q,p2,m0,m1,m2,opts]-If[nm2>=2,(nm2-1)Derivative[0,0,0,np1,nq,np2,nm0,nm1,nm2-2][PVC][r-1,n1,n2+1,p1,q,p2,m0,m1,m2,opts],0];

	(*Derivatives of Passrino-Veltman D functions*)
	(*With respect to s1*)
	Derivative[0,0,0,0,ns1_?Positive,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[1,0,0,0,0,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  1/2 Derivative[0,0,0,0,ns1-1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1+2,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1-1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1+1,n2+1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1-1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1+1,n2,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1-1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1+1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts];
	(*With respect to s2*)
	Derivative[0,0,0,0,ns1_,ns2_?Positive,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,1,0,0,0,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  -(1/2)Derivative[0,0,0,0,ns1,ns2-1,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1+1,n2+1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts];
	(*With respect to s3*)
	Derivative[0,0,0,0,ns1_,ns2_,ns3_?Positive,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,0,1,0,0,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  -(1/2)Derivative[0,0,0,0,ns1,ns2,ns3-1,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1,n2+1,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts];
	(*With respect to s4*)
	Derivative[0,0,0,0,ns1_,ns2_,ns3_,ns4_?Positive,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,1,0,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4-1,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1,n2,n3+2,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4-1,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1+1,n2,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4-1,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1,n2+1,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4-1,ns12,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1,n2,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts];
	(*With respect to s12*)
	Derivative[0,0,0,0,ns1_,ns2_,ns3_,ns4_,ns12_?Positive,ns23_,nm0_,nm1_,nm2_,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,0,1,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12-1,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1,n2+2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12-1,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1+1,n2+1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12-1,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1,n2+1,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12-1,ns23,nm0,nm1,nm2,nm3][PVD][r-1,n1,n2+1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts];
	(*With respect to s23*)
	Derivative[0,0,0,0,ns1_,ns2_,ns3_,ns4_,ns12_,ns23_?Positive,nm0_,nm1_,nm2_,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,0,0,1,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  -(1/2)Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23-1,nm0,nm1,nm2,nm3][PVD][r-1,n1+1,n2,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts];
	(*With respect to m1*)
	Derivative[0,0,0,0,ns1_,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_?Positive,nm2_,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,0,0,0,0,1,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  -m1 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1-1,nm2,nm3][PVD][r-1,n1+1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]-
	  If[nm1>=2,(nm1-1)Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1-2,nm2,nm3][PVD][r-1,n1+1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts],0];
	(*With respect to m2*)
	Derivative[0,0,0,0,ns1_,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_?Positive,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,0,0,0,0,0,1,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  -m2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2-1,nm3][PVD][r-1,n1,n2+1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]-
	  If[nm2>=2,(nm2-1)Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2-2,nm3][PVD][r-1,n1,n2+1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts],0];
	(*With respect to m3*)
	Derivative[0,0,0,0,ns1_,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_?Positive,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,0,0,0,0,0,0,1][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  -m3 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3-1][PVD][r-1,n1,n2,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]-
	  If[nm3>=2,(nm3-1)Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3-2][PVD][r-1,n1,n2,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts],0];
	(*With respect to m0*)
	Derivative[0,0,0,0,ns1_,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_?Positive,nm1_,nm2_,nm3_,Optional[_,0],Optional[_,0]][PVD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts: OptionsPattern[PVD]]/;optAnalytic||taylorSeriesExistsQ[0,0,0,0,0,0,1,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]:=
	  m0*(Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-1,nm1,nm2,nm3][PVD][r-1,n1+1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-1,nm1,nm2,nm3][PVD][r-1,n1,n2+1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-1,nm1,nm2,nm3][PVD][r-1,n1,n2,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
	  Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-1,nm1,nm2,nm3][PVD][r-1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts])+
	  (nm0-1)If[nm0>=2,Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-2,nm1,nm2,nm3][PVD][r-1,n1+1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
		Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-2,nm1,nm2,nm3][PVD][r-1,n1,n2+1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
		Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-2,nm1,nm2,nm3][PVD][r-1,n1,n2,n3+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts]+
		Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-2,nm1,nm2,nm3][PVD][r-1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,opts],0];

    (*Derivatives of ScalarC0*)
	Derivative[np1_?Positive,nq_,np2_,nm0_,nm1_,nm2_][ScalarC0][p1_,q_,p2_,m0_,m1_,m2_](*/;taylorSeriesExistsQ[1,0,0,0,0,0][PVC][p1,q,p2,m0,m1,m2]*):=1/2 Derivative[0,0,0,np1-1,nq,np2,nm0,nm1,nm2][PVC][-1,+2,0,p1,q,p2,m0,m1,m2]+1/2 Derivative[0,0,0,np1-1,nq,np2,nm0,nm1,nm2][PVC][-1,+1,+1,p1,q,p2,m0,m1,m2]+1/2 Derivative[0,0,0,np1-1,nq,np2,nm0,nm1,nm2][PVC][-1,+1,0,p1,q,p2,m0,m1,m2];
	Derivative[np1_,nq_?Positive,np2_,nm0_,nm1_,nm2_][ScalarC0][p1_,q_,p2_,m0_,m1_,m2_](*/;taylorSeriesExistsQ[0,1,0,0,0,0][PVC][p1,q,p2,m0,m1,m2]*):=-(1/2)Derivative[0,0,0,np1,nq-1,np2,nm0,nm1,nm2][PVC][-1,+1,+1,p1,q,p2,m0,m1,m2];
	Derivative[np1_,nq_,np2_?Positive,nm0_,nm1_,nm2_][ScalarC0][p1_,q_,p2_,m0_,m1_,m2_](*/;taylorSeriesExistsQ[0,0,1,0,0,0][PVC][p1,q,p2,m0,m1,m2]*):=1/2 Derivative[0,0,0,np1,nq,np2-1,nm0,nm1,nm2][PVC][-1,0,+2,p1,q,p2,m0,m1,m2]+1/2 Derivative[0,0,0,np1,nq,np2-1,nm0,nm1,nm2][PVC][-1,+1,+1,p1,q,p2,m0,m1,m2]+1/2 Derivative[0,0,0,np1,nq,np2-1,nm0,nm1,nm2][PVC][-1,0,+1,p1,q,p2,m0,m1,m2];
	Derivative[np1_,nq_,np2_,nm0_?Positive,nm1_,nm2_][ScalarC0][p1_,q_,p2_,m0_,m1_,m2_](*/;taylorSeriesExistsQ[0,0,0,1,0,0][PVC][p1,q,p2,m0,m1,m2]*):=m0*(Derivative[0,0,0,np1,nq,np2,nm0-1,nm1,nm2][PVC][-1,+1,0,p1,q,p2,m0,m1,m2]+Derivative[0,0,0,np1,nq,np2,nm0-1,nm1,nm2][PVC][-1,0,+1,p1,q,p2,m0,m1,m2]+Derivative[0,0,0,np1,nq,np2,nm0-1,nm1,nm2][PVC][-1,0,0,p1,q,p2,m0,m1,m2])+(nm0-1)*If[nm0>=2,Derivative[0,0,0,np1,nq,np2,nm0-2,nm1,nm2][PVC][-1,+1,0,p1,q,p2,m0,m1,m2]+Derivative[0,0,0,np1,nq,np2,nm0-2,nm1,nm2][PVC][-1,0,+1,p1,q,p2,m0,m1,m2]+Derivative[0,0,0,np1,nq,np2,nm0-2,nm1,nm2][PVC][-1,0,0,p1,q,p2,m0,m1,m2],0];
	Derivative[np1_,nq_,np2_,nm0_,nm1_?Positive,nm2_][ScalarC0][p1_,q_,p2_,m0_,m1_,m2_](*/;taylorSeriesExistsQ[0,0,0,0,1,0][PVC][p1,q,p2,m0,m1,m2]*):=-m1 Derivative[0,0,0,np1,nq,np2,nm0,nm1-1,nm2][PVC][-1,+1,0,p1,q,p2,m0,m1,m2]-If[nm1>=2,(nm1-1)Derivative[0,0,0,np1,nq,np2,nm0,nm1-2,nm2][PVC][-1,+1,0,p1,q,p2,m0,m1,m2],0];
	Derivative[np1_,nq_,np2_,nm0_,nm1_,nm2_?Positive][ScalarC0][p1_,q_,p2_,m0_,m1_,m2_](*/;taylorSeriesExistsQ[0,0,0,0,0,1][PVC][p1,q,p2,m0,m1,m2]*):=-m2 Derivative[0,0,0,np1,nq,np2,nm0,nm1,nm2-1][PVC][-1,0,+1,p1,q,p2,m0,m1,m2]-If[nm2>=2,(nm2-1)Derivative[0,0,0,np1,nq,np2,nm0,nm1,nm2-2][PVC][-1,0,+1,p1,q,p2,m0,m1,m2],0];

	(*Derivatives of ScalarD0*)
	(*With respect to s1*)
	Derivative[ns1_?Positive,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[1,0,0,0,0,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  1/2 Derivative[0,0,0,0,ns1-1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,+2,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1-1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,+1,+1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1-1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,+1,0,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1-1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,+1,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];
	(*With respect to s2*)
	Derivative[ns1_,ns2_?Positive,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,1,0,0,0,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  -(1/2)Derivative[0,0,0,0,ns1,ns2-1,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,+1,+1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];
	(*With respect to s3*)
	Derivative[ns1_,ns2_,ns3_?Positive,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,0,1,0,0,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  -(1/2)Derivative[0,0,0,0,ns1,ns2,ns3-1,ns4,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,0,+1,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];
	(*With respect to s4*)
	Derivative[ns1_,ns2_,ns3_,ns4_?Positive,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,0,0,1,0,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4-1,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,0,0,+2,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4-1,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,+1,0,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4-1,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,0,+1,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4-1,ns12,ns23,nm0,nm1,nm2,nm3][PVD][-1,0,0,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];
	(*With respect to s12*)
	Derivative[ns1_,ns2_,ns3_,ns4_,ns12_?Positive,ns23_,nm0_,nm1_,nm2_,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,0,0,0,1,0,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12-1,ns23,nm0,nm1,nm2,nm3][PVD][-1,0,+2,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12-1,ns23,nm0,nm1,nm2,nm3][PVD][-1,+1,+1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12-1,ns23,nm0,nm1,nm2,nm3][PVD][-1,0,+1,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  1/2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12-1,ns23,nm0,nm1,nm2,nm3][PVD][-1,0,+1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];
	(*With respect to s23*)
	Derivative[ns1_,ns2_,ns3_,ns4_,ns12_,ns23_?Positive,nm0_,nm1_,nm2_,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,0,0,0,0,1,0,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  -(1/2)Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23-1,nm0,nm1,nm2,nm3][PVD][-1,+1,0,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];
	(*With respect to m1*)
	Derivative[ns1_,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_?Positive,nm2_,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,0,0,0,0,0,0,1,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  -m1 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1-1,nm2,nm3][PVD][-1,+1,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-
	  If[nm1>=2,(nm1-1)Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1-2,nm2,nm3][PVD][-1,+1,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],0];
	(*With respect to m2*)
	Derivative[ns1_,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_?Positive,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,0,0,0,0,0,0,0,1,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  -m2 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2-1,nm3][PVD][-1,0,+1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-
	  If[nm2>=2,(nm2-1)Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2-2,nm3][PVD][-1,0,+1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],0];
	(*With respect to m3*)
	Derivative[ns1_,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_,nm1_,nm2_,nm3_?Positive][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,0,0,0,0,0,0,0,0,1][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  -m3 Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3-1][PVD][-1,0,0,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-
	  If[nm3>=2,(nm3-1)Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0,nm1,nm2,nm3-2][PVD][-1,0,0,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],0];
	(*With respect to m0*)
	Derivative[ns1_,ns2_,ns3_,ns4_,ns12_,ns23_,nm0_?Positive,nm1_,nm2_,nm3_][ScalarD0][s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_](*/;taylorSeriesExistsQ[0,0,0,0,0,0,1,0,0,0][PVD][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*):=
	  m0*(Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-1,nm1,nm2,nm3][PVD][-1,+1,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-1,nm1,nm2,nm3][PVD][-1,0,+1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-1,nm1,nm2,nm3][PVD][-1,0,0,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
	  Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-1,nm1,nm2,nm3][PVD][-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])+
	  (nm0-1)If[nm0>=2,Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-2,nm1,nm2,nm3][PVD][-1,+1,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
		Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-2,nm1,nm2,nm3][PVD][-1,0,+1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
		Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-2,nm1,nm2,nm3][PVD][-1,0,0,+1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+
		Derivative[0,0,0,0,ns1,ns2,ns3,ns4,ns12,ns23,nm0-2,nm1,nm2,nm3][PVD][-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],0];

	If[{serArgs}==={},Throw[expr,"DerivativesOnly"]];

	Derivative[__][func: PVA|PVB|PVC|PVD][args: __] := Throw[{func, expVar, expPoint}, LoopRefineSeries];

	Fold[({expVar,expPoint}={#2[[1]],#2[[2]]}; Series[#1,#2,Analytic->True])&,expr,{serArgs}]
	
  ]];


(* ::Subsection::Closed:: *)
(*Exotic PVA, PVB, PVC, PVD*)


PVA::weightx = "Weight vector `1` is not a list of 1 integer.";
PVB::weightx = "Weight vector `1` is not a list of 2 integers.";
PVC::weightx = "Weight vector `1` is not a list of 3 integers.";
PVD::weightx = "Weight vector `1` is not a list of 4 integers.";

PVA::dimx = PVB::dimx = PVC::dimx = PVD::dimx = "Dimensions specifier `1` is not an even integer.";
PVA::opts = PVB::opts = PVC::opts = PVD::opts = "Default values of Weights and Dimensions of `1` cannot be changed.";

Unprotect[SetOptions];
HoldPattern[SetOptions[pv:PVA|PVB|PVC|PVD,___]]:=(Message[MessageName[pv,"opts"],pv];$Failed);
Protect[SetOptions];

(*PVA[args:PatternSequence[_,_],opts__Rule] /; Intersection[{opts},Options[PVA]]=!={} := PVA[args,##]& @@ DeleteCases[{opts},Alternatives@@Options[PVA]];
PVB[args:PatternSequence[_,_,_,_,_],opts__Rule] /; Intersection[{opts},Options[PVB]]=!={} := PVB[args,##]& @@ DeleteCases[{opts},Alternatives@@Options[PVB]];
PVC[args:PatternSequence[_,_,_,_,_,_,_,_,_],opts__Rule] /; Intersection[{opts},Options[PVC]]=!={} := PVC[args,##]& @@ DeleteCases[{opts},Alternatives@@Options[PVC]];
PVD[args:PatternSequence[_,_,_,_,_,_,_,_,_,_,_,_,_,_],opts__Rule] /; Intersection[{opts},Options[PVD]]=!={} := PVD[args,##]& @@ DeleteCases[{opts},Alternatives@@Options[PVD]];*)


(*delDimhalf = (4-dim)/2*)
weightReduceA[r_,m0_,{w0_?Positive},delDimhalf_] :=
  ((-1)^(w0-1) (-2)^(1-w0-delDimhalf))/Gamma[w0] PVA[r+1-w0-delDimhalf,m0];
weightReduceA[r_,m0_,{w0_},delDimhalf_] := 0;

weightReduceB[r_,n1_,s_,m0_,m1_,{w0_?Positive,w1_?Positive},delDimhalf_] := 
  ((-1)^(w0-1) (-2)^(2-w0-w1-delDimhalf))/(Gamma[w0] Gamma[w1]) Sum[Binomial[w0-1,j1]*PVB[r+2-w0-w1-delDimhalf,n1+w1-1+j1,s,m0,m1],{j1,0,w0-1}];
weightReduceB[r_,n1_,s_,m0_,m1_,{w0_,w1_},delDimhalf_] := 
  Which[
	Negative[w0] || Negative[n1+w1], Infinity/Infinity,
	NonPositive[w1] && Positive[n1+w1],0,
	w0===0, (2)^n1 weightReduceA[r,m1,{w1},delDimhalf],
	n1+w1===0,(2)^n1 n1! weightReduceA[r+n1,m0,{w0},delDimhalf]
  ];

weightReduceC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_,{w0_?Positive,w1_?Positive,w2_?Positive},delDimhalf_] :=
  ((-1)^(w0-1) (-2)^(3-w0-w1-w2-delDimhalf))/(Gamma[w0]Gamma[w1]Gamma[w2]) Sum[Multinomial[j1,j2,w0-1-j1-j2]*PVC[r+3-w0-w1-w2-delDimhalf,n1+w1-1+j1,n2+w2-1+j2,p1,q,p2,m0,m1,m2],{j1,0,w0-1},{j2,0,w0-1-j1}];
weightReduceC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_,{w0_,w1_,w2_},delDimhalf_] := 
  Which[
	Negative[w0] || Negative[n1+w1] || Negative[n2+w2], Infinity/Infinity,
	(NonPositive[w1] && Positive[n1+w1]) || (NonPositive[w2] && Positive[n2+w2]), 0,
	w0===0, (2)^n1 Sum[Binomial[n1,j]*weightReduceB[r,n1+n2-j,q,m1,m2,{w1,w2},delDimhalf],{j,0,n1}],
	n1+w1===0,(2)^n1 n1! weightReduceB[r+n1,n2,p2,m0,m2,{w0,w2},delDimhalf],
	n2+w2===0,(2)^n2 n2! weightReduceB[r+n2,n1,p1,m0,m1,{w0,w1},delDimhalf]
  ];

weightReduceD[r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,{w0_?Positive,w1_?Positive,w2_?Positive,w3_?Positive},delDimhalf_] :=
  ((-1)^(w0-1) (-2)^(4-w0-w1-w2-w3-delDimhalf))/(Gamma[w0]Gamma[w1]Gamma[w2]Gamma[w3]) Sum[Multinomial[j1,j2,j3,w0-1-j1-j2-j3]*PVD[r+4-w0-w1-w2-w3-delDimhalf,n1+w1-1+j1,n2+w2-1+j2,n3+w3-1+j3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{j1,0,w0-1},{j2,0,w0-1-j1},{j3,0,w0-1-j1-j2}];
weightReduceD[r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,{w0_,w1_,w2_,w3_},delDimhalf_] := 
  Which[
	Negative[w0] || Negative[n1+w1] || Negative[n2+w2] || Negative[n3+w3], Infinity/Infinity,
	(NonPositive[w1] && Positive[n1+w1]) || (NonPositive[w2] && Positive[n2+w2]) || (NonPositive[w3] && Positive[n3+w3]), 0,
	w0===0, (2)^n1 Sum[Multinomial[j,k,n1-j-k]*weightReduceC[r,n2+k,n1+n3-j-k,s2,s3,s23,m1,m2,m3,{w1,w2,w3},delDimhalf],{j,0,n1},{k,0,n1-j}],
	n1+w1===0, (2)^n1 n1! weightReduceC[r+n1,n2,n3,s12,s3,s4,m0,m2,m3,{w0,w2,w3},delDimhalf],
	n2+w2===0, (2)^n2 n2! weightReduceC[r,n1,n3,s1,s23,s4,m0,m1,m3,{w0,w1,w3},delDimhalf],
	n3+w3===0, (2)^n3 n3! weightReduceC[r,n1,n2,s1,s2,s12,m0,m1,m2,{w0,w1,w2},delDimhalf]
  ];

pvWeightReduce = {
  PVA[r_Integer,m0_, opts__Rule] /; Check[validPVmodifiers[PVA,opts], False]:> 
	weightReduceA[r,m0,OptionValue[PVA,{opts},Weights],2-OptionValue[PVA,{opts},Dimensions]/2],

  PVB[r_Integer,n1_Integer?NonNegative,s_,m0_,m1_,opts__Rule] /; Check[validPVmodifiers[PVB,opts], False]:> 
	weightReduceB[r,n1,s,m0,m1,OptionValue[PVB,{opts},Weights],2-OptionValue[PVB,{opts},Dimensions]/2],

  PVC[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,p1_,q_,p2_,m0_,m1_,m2_,opts__Rule] /; Check[validPVmodifiers[PVC,opts], False]:> 
	weightReduceC[r,n1,n2,p1,q,p2,m0,m1,m2,OptionValue[PVC,{opts},Weights],2-OptionValue[PVC,{opts},Dimensions]/2],

  PVD[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_,opts__Rule] /; Check[validPVmodifiers[PVD,opts], False]:> 
	weightReduceD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,OptionValue[PVD,{opts},Weights],2-OptionValue[PVD,{opts},Dimensions]/2]
};


validPVmodifiers[pv_,opts__] := 
  With[{expectedWeightPattern=Switch[pv,PVA,{_Integer},PVB,{_Integer,_Integer},PVC,{_Integer,_Integer,_Integer},PVD,{_Integer,_Integer,_Integer,_Integer}]},
	(*Check that weights list of integers of correct size and type*)
	If[!MatchQ[OptionValue[pv,{opts},Weights],expectedWeightPattern], Message[MessageName[pv,"weightx"],OptionValue[pv,{opts},Weights]]];
	(*Check dimensions is an even integer*)
	If[!EvenQ[OptionValue[pv,{opts},Dimensions]], Message[MessageName[pv,"dimx"],OptionValue[pv,{opts},Dimensions]]];
	True
  ];


X`Utilities`PVNormal[expr_]:=Catch[makeSer[expr,True],"DerivativesOnly"]/.pvWeightReduce;


(* ::Section::Closed:: *)
(*Reduction formulae*)


(* ::Subsection::Closed:: *)
(*Part: UV divergent*)


(*These give the coefficient of the 1/Eps pole; 
  very useful for the reduction of C- and D- functions.*)

pvADivUV[r_Integer /; r>=-1, m0_] :=pow[m0,(2(r+1))]/(2^r (r+1)!);
pvADivUV[r_Integer,m0_] := 0;

pvBDivUV[r_Integer /; r>=0, n_Integer,s_,m0_,m1_]:=
  With[{a=s,b=-s+m1^2-m0^2,c=m0^2,k3=r-k1-k2},
	(-1)^(n+2)/(2^r r!)*Sum[Multinomial[k1,k2,k3]*(pow[a,k1]pow[b,k2]pow[c,k3])/(2k1+k2+n+1),{k1,0,r},{k2,0,r-k1}]];
pvBDivUV[r_Integer,n_Integer,s_,m0_,m1_]:=0;

pvCDivUV[r_Integer /; r>=1 ,n1_Integer,n2_Integer,p1_,q_,p2_,m0_,m1_,m2_]:=
  With[{a=p1,b=p2,c=-q+p1+p2,d=-p1+m1^2-m0^2,e=-p2+m2^2-m0^2,f=m0^2,k6=r-1-k1-k2-k3-k4-k5},
	(-1)^(n1+n2)/(2^r (r-1)!) Sum[Multinomial[k1,k2,k3,k4,k5,k6]pow[a,k1]pow[b,k2]pow[c,k3]pow[d,k4]pow[e,k5]pow[f,k6]*
	  ((2 k1+k3+k4+n1)! (2 k2+k3+k5+n2)!)/(2 k1+2 k2+2 k3+k4+k5+n1+n2+2)!,
	  {k1,0,r-1},{k2,0,r-1-k1},{k3,0,r-1-k1-k2},{k4,0,r-1-k1-k2-k3},{k5,0,r-1-k1-k2-k3-k4}]];
pvCDivUV[r_Integer,n1_Integer,n2_Integer,p1_,q_,p2_,m0_,m1_,m2_] := 0;

pvDDivUV[r_Integer /; r>=2 ,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]:=
  With[{a=s1,b=s12,c=s4,d=s12+s1-s2,e=-s23+s1+s4,f=s12+s4-s3,g=-s1+m1^2-m0^2,h=-s12+m2^2-m0^2,i=-s4+m3^2-m0^2,j=m0^2,k10=r-2-k1-k2-k3-k4-k5-k6-k7-k8-k9},
	(-1)^(n1+n2+n3)/(2^r (r-2)!)*
	  Sum[Multinomial[k1,k2,k3,k4,k5,k6,k7,k8,k9,k10]*pow[a,k1]pow[b,k2]pow[c,k3]pow[d,k4]pow[e,k5]pow[f,k6]pow[g,k7]pow[h,k8]pow[i,k9]pow[j,k10]*
		((2k1+k4+k5+k7+n1)! (2k2+k4+k6+k8+n2)! (2k3+k5+k6+k9+n3)!)/(n1+n2+n3+2r-1-k7-k8-k9-2k10)!
		,{k1,0,r-2},{k2,0,r-2-k1},{k3,0,r-2-k1-k2},{k4,0,r-2-k1-k2-k3},{k5,0,r-2-k1-k2-k3-k4},{k6,0,r-2-k1-k2-k3-k4-k5},{k7,0,r-2-k1-k2-k3-k4-k5-k6},{k8,0,r-2-k1-k2-k3-k4-k5-k6-k7},{k9,0,r-2-k1-k2-k3-k4-k5-k6-k7-k8}]
	];
pvDDivUV[r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] := 0;


(* ::Subsection:: *)
(*Part: IR divergent*)


(* ::Subsubsection::Closed:: *)
(*A functions*)


irDiv[refineA][-1, 0] := -2/Eps;
irDiv[refineA][_Integer, _] := 0;


(* ::Subsubsection::Closed:: *)
(*B functions*)


irDiv[refineB][_Integer, _Integer, _, Except[0,_], Except[0,_]]  := 0;
(*irDiv[refineB][_Integer, _Integer, _, m0_, m1_] /; !PossibleZeroQ[m0] && !PossibleZeroQ[m1] := 0;*)

(*r >= 0*)
irDiv[refineB][r_Integer?Positive,n_Integer,_,_,_] := 0;

(*r = 0*)
(*Scaleless*)irDiv[refineB][0,n_Integer,0,0,0] := (-1)^(n+1)/(n+1)/Eps;
irDiv[refineB][0,n_Integer,_,_,_] := 0;

(*r < 0*)
(*Scaleless*)irDiv[refineB][r_Integer?Negative,n_Integer,0,0,0] := 0;
irDiv[refineB][-1, 0, 0, 0, m1_]            := 2/m1^2 (1/Eps);
irDiv[refineB][-1,n_Integer, 0, 0, m1_]     := 0;
irDiv[refineB][-1,n_Integer, 0, m0_, 0]     := 2(-1)^n*1/m0^2 (1/Eps);
irDiv[refineB][-1, 0, s_, 0, 0]             := -4/s (1/Eps);
irDiv[refineB][-1,n_Integer, s_, 0, 0]      := 2(-1)^(n+1)*1/s (1/Eps);

irDiv[refineB][r_Integer?Negative, n_Integer, Except[0,s_], 0, Except[0,m1_]] /; PossibleZeroQ[s-m1^2] := If[n==2Abs[r]-1,(-1)^(1-r)/2^r Gamma[-r] 1/m1^(2Abs[r]) (-(1/2)(1/Eps)),0];
irDiv[refineB][r_Integer?Negative, n_Integer, Except[0,s_], Except[0,m0_], 0]  /; PossibleZeroQ[s-m0^2] := If[n>=2Abs[r]-1,Binomial[n,2Abs[r]-1](-1)^(n+1-r)/2^r Gamma[-r] 1/m0^(2Abs[r]) (-(1/2)(1/Eps)),0];

(*irDiv[refineB][r_Integer?Negative, n_Integer, 0, Except[0,m0_], Except[0,m1_]]  /; PossibleZeroQ[m0-m1] := 0;
irDiv[refineB][r_Integer?Negative,n_Integer, 0,Except[0,m0_],Except[0,m1_]] := 0;*)

irDiv[refineB][-1, 0, s_, 0,m1_]            := -2/(s-m1^2) (1/Eps);
irDiv[refineB][-1,n_Integer,s_, 0,m1_]      := 0;
irDiv[refineB][-1,n_Integer,s_,m0_, 0]      := 2(-1)^n*1/(s-m0^2) (-(1/Eps));

(*General case*)
(*irDiv[refineB][-1,n_Integer,s_,m0_,m1_]     := (Print["Reached"];0);*)

(*Reduction for r <= -2 Det(X)!=0;*)
irDiv[refineB][r_Integer,n_Integer,s_,m0_,m1_] := 1/-Kallen\[Lambda][s,m0^2,m1^2] (2s(2(3-2Eps+2r+n)irDiv[refineB][r+1,n,s,m0,m1]-(-1)^n irDiv[refineA][r,m1]) + (-s+m1^2-m0^2)*(KroneckerDelta[n,0]irDiv[refineA][r,m0]-(-1)^n irDiv[refineA][r,m1]-Switch[n,0,0,_,2n irDiv[refineB][r+1,n-1,s,m0,m1]]));


(* ::Subsubsection::Closed:: *)
(*C functions*)


(*Shifted B-functions; due to missing unshifted propagator; identical to pvBshift, but with immediate replacement*)
irDiv[pvBs][r_Integer,n1_Integer,n2_Integer,q_,m1_,m2_]/;n1>n2 := irDiv[pvBs][r,n2,n1,q,m2,m1];
irDiv[pvBs][r_Integer,n1_Integer,n2_Integer,q_,m1_,m2_]        := (-1)^n1 Sum[Binomial[n1,idx]irDiv[refineB][r,n2+idx,q,m1,m2],{idx,0,n1}];

pvBDivUV[r_Integer,n1_Integer,n2_Integer,q_,m1_,m2_]        := (-1)^n1 Sum[Binomial[n1,idx]pvBDivUV[r,n2+idx,q,m1,m2],{idx,0,n1}];


Block[{
	n={n1,n2},
	f={p1-m1^2+m0^2,p2-m2^2+m0^2},

	gramZ={{p1,          -(q-p1-p2)/2},
    	  {-(q-p1-p2)/2,  p2}},

	detZ=-Kallen\[Lambda][p1,p2,q]/4,

	adjZ={{p2, (q-p1-p2)/2},
    	 {(q-p1-p2)/2, p1}},

	mtxX, detX, adjX0, adjXij,
	pinchB, missBDivUV,
	not,
	i,j,k,l,nn,mm},

	not[var_]=Which[var==1,2,var==2,1];

	mtxX=Expand[{{2 m0^2,f[[1]],f[[2]]},{f[[1]],2 p1,-(q-p1-p2)},{f[[2]],-(q-p1-p2),2 p2}}];
	detX=Expand[Det[mtxX]];
	
	adjX0=Expand[Table[Sum[adjZ[[j,k]]f[[k]],{k,1,2}],{j,1,2}]]; (*up to a constant: -2*)
	adjXij=Table[4*m0^2 adjZ[[i,j]]+Sum[(KroneckerDelta[i,mm]KroneckerDelta[nn,j]-KroneckerDelta[i,j]KroneckerDelta[nn,mm])f[[nn]] f[[mm]],{nn,1,2},{mm,1,2}],{i,1,2},{j,1,2}];

	(*Passarino Veltman functions with missing propagators, and their divergent parts*)
	pinchB[r_,n1_]     = {irDiv[refineB][r,n1,p2,m0,m2],irDiv[refineB][r,n1,p1,m0,m1]};
	missBDivUV[r_,n1_] = {pvBDivUV[r,n1,p2,m0,m2],pvBDivUV[r,n1,p1,m0,m1]};


	(********Case5: All elements of gramZ is zero, but f nonzero********)
	refineRulesCIRDivcase5a=Table[irDiv[passVeltC][r_?NonPositive, n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/f[[k]] (-2n[[k]]refineC[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],p1,q,p2,m0,m1,m2]+KroneckerDelta[n[[k]],0]pinchB[r,n[[not[k]]]][[k]]-pvBs[r,n1,n2,q,m1,m2]),{k,1,2}];

	(********Case4: Gram determinant and Cayley vectors vanishing; internal masses non-zero********)
	(****OK*****)
	refineRulesCIRDivcase4={irDiv[passVeltC][r_,n1_,n2_,p_,p_,0,m0_,m1_,m0_]:>(-1)^(3+n1)/(2(n2+1)) Sum[Binomial[n1,k] irDiv[refineB][r-1,n2+k+1,p,m1,m0],{k,0,n1}],
	irDiv[passVeltC][r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] :> With[{\[Alpha]=(-q+p1+p2)/(2p2)},(-1)^(n1+n2)/2 Sum[Binomial[n2,j]pow[\[Alpha],n2-j]((n1!(n2-j)!)/(n1+n2-j+1)! Sum[Binomial[j,k](-1)^(j-k) pow[\[Alpha],j-k](-1)^k irDiv[refineB][r-1,k,p2,m0,m2],{k,0,j}]+Sum[Pochhammer[-n1,k]/((n2-j+k+1)k!) ((1-\[Alpha])^(j+1) (-1)^(n2+k) irDiv[refineB][r-1,n2+k+1,q,m1,m2]+(-1)^(j+1) (\[Alpha])^(j+1) (-1)^(n2+k+1) irDiv[refineB][r-1,n2+k+1,p1,m1,m0]),{k,0,n1}]),{j,0,n2}]]};

	(********Case3: Gram determinant vanishing, but Cayley vectors X non-vanishing********)
	refineRulesCIRDivcase3a=
	Table[
	  irDiv[passVeltC][r_?Positive,0,0,p1_,q_,p2_,m0_,m1_,m2_] -> 
	    1/(1+2r)*(irDiv[pvBs][r-1,0,0,q,m1,m2]+m0^2 irDiv[passVeltC][r-1,0,0,p1,q,p2,m0,m1,m2])+
	    1/(2 (1+2r))*1/adjZ[[k,l]] Sum[(KroneckerDelta[k,mm]KroneckerDelta[nn,l]-KroneckerDelta[k,l]KroneckerDelta[mm,nn])(Sum[gramZ[[nn,j]]((1-KroneckerDelta[mm,j])pinchB[r-1,1][[mm]]-irDiv[pvBs][r-1,KroneckerDelta[j,1],KroneckerDelta[j,2],q,m1,m2]),{j,1,2}]+1/2 f[[mm]](-pinchB[r-1,0][[nn]]+irDiv[pvBs][r-1,0,0,q,m1,m2]+f[[nn]]irDiv[passVeltC][r-1,0,0,p1,q,p2,m0,m1,m2])),{nn,1,2},{mm,1,2}]
	    (*+2/(1+2r)pvCDivUV[r,0,0,p1,q,p2,m0,m1,m2]*),{k,1,2},{l,1,2}];
	refineRulesCIRDivcase3b=
	Table[
	  irDiv[passVeltC][r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/adjX0[[j]]*
	    Sum[adjZ[[j,k]](KroneckerDelta[n[[k]],0]pinchB[r,n[[not[k]]]][[k]]-irDiv[pvBs][r,n1,n2,q,m1,m2]-
	    2n[[k]]irDiv[passVeltC][r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],p1,q,p2,m0,m1,m2]),{k,1,2}],
	{j,1,2}];

	(********Reduction of triangle 1,4,5,6********)
	(****OK*****)
	(*In this case, p1=q, q=p2, m2=m0 or (p1,m1)<-->(p2,m2).*)
	refineRulesCIRDivtriangle6={
	  (*Permuted*)
	  irDiv[passVeltC][r_,n1_,n2_,p1_,s_,p2_,0,m2_,m0_] /; PossibleZeroQ[p1-m2^2] && PossibleZeroQ[p2-m0^2] && 2r+n1+n2 != 0 :> (-1)^n2/2 1/(n1+n2+2r) (1+(2Eps)/(n1+n2+2r))Sum[Binomial[n2,k]irDiv[refineB][r-1,n1+k,s,m0,m2],{k,0,n2}],
	  irDiv[passVeltC][r_,n1_,n2_,p1_,s_,p2_,0,m2_,m0_] /; PossibleZeroQ[p1-m2^2] && PossibleZeroQ[p2-m0^2] :> (-1)^n2/2 * 1/(-2Eps) Sum[Binomial[n2,k](*order1IRDiv*)refineB[r-1,n1+k,s,m0,m2],{k,0,n2}],

	  (*Nonpermuted*)
	  (*irDiv[passVeltC][r_?Positive, n1_,n2_,p1_,q_,s_,m0_,0,m2_]|irDiv[passVeltC][r_?Positive, n2_,n1_,s_,q_,p1_,m0_,m2_,0] /;PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] :> 0,*)
	  irDiv[passVeltC][r_(*?NonPositive*), n1_,n2_,p1_,q_,s_,m0_,0,m2_]|irDiv[passVeltC][r_, n2_,n1_,s_,q_,p1_,m0_,m2_,0] /;PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] :> 
		Which[
		  2r+n2>0&&2r+n1+n2+1>0, -((n1! (-1+n2+2 r)! )/(n1+n2+2 r)!)(-1) *(-1)^n1/2 * irDiv[refineB][r-1,n2,s,m0,m2],
		  2r+n2<=0&&2r+n1+n2+1<=0, + (((-1)^n1) n1! (-1-n1-n2-2 r)! )/(-n2-2 r)! (-1) * (-1)^n1/2 * irDiv[refineB][r-1,n2,s,m0,m2],
		  2r+n2<=0&&2r+n1+n2+1>0, - (((-1)^(n2+2 r) n1!)/(2 Eps (-n2-2 r)! (n1+n2+2 r)!)) (1+2Eps (-HarmonicNumber[-n2-2 r]+HarmonicNumber[n1+n2+2 r])+2 Eps^2 (HarmonicNumber[-n2-2 r]^2-2 HarmonicNumber[-n2-2 r] HarmonicNumber[n1+n2+2 r]+HarmonicNumber[n1+n2+2 r]^2+HarmonicNumber[-n2-2 r,2]+HarmonicNumber[n1+n2+2 r,2])) * (-1)^n1/2 * (*order1IRDiv*)refineB[r-1,n2,s,m0,m2]
		]
	};

	(********Reduction of triangle 2,3********)
	(****OK*****)
	refineRulesCIRDivtriangle3 = {
	  (*Permuted*)
	  (*irDiv[passVeltC][r_?Positive,n1_,n2_,p1_,0,p2_,m0_,0,0] :> 0,*)
	  irDiv[passVeltC][r_,n1_,n2_,q_,0,q_,m0_,0,0] :> Sum[Multinomial[sdx, tdx, n2-sdx-tdx] (-1)^(n2) 1/(2*(n1+tdx+1))Sum[Binomial[n1+tdx+1,k](-1)^(n1+tdx)irDiv[refineB][r-1,k+sdx,q,0,m0],{k,0,n1+tdx+1}], {sdx,0,n2},{tdx,0,n2-sdx}],
	  irDiv[passVeltC][r_,n1_,n2_,p1_,0,p2_,m0_,0,0] :> 
		With[{
		  gammaSeries=
			If[#2+1+#1>0,  (-1)^(1+#1)/((-#1)! (#2+#1)! Eps)+((-1)^#1 (HarmonicNumber[-#1]-HarmonicNumber[#2+#1]))/((-#1)! (#2+#1)!)-1/(2 ((-#1)! (#2+#1)!)) ((-1)^#1 (HarmonicNumber[-#1]^2-2 HarmonicNumber[-#1] HarmonicNumber[#2+#1]+HarmonicNumber[#2+#1]^2+HarmonicNumber[-#1,2]+HarmonicNumber[#2+#1,2])) Eps,
			  ((-1)^(1+#2) (-1-#2-#1)!)/(-#1)!+1/(-#1)! (-1)^#2 (-1-#2-#1)! (-HarmonicNumber[-1-#2-#1]+HarmonicNumber[-#1]) Eps]&,
		  fracSeries=
			If[#1+#2!=0,  (1/(#1+#2)+Eps/(#1+#2)^2),  -1/Eps]&},
			  Sum[(-1)^n2*(p1-p2)^(-1-n1-tdx)*Multinomial[sdx, n2-sdx-tdx, tdx]*(Sum[(-(1/2))*Binomial[1+n1+tdx, k]*(n1+tdx)!*gammaSeries[r, n1+tdx]*(*order1IRDiv*)refineB[-1+r, k+sdx, p2, 0, m0]*pow[p2, k]*pow[-m0^2+p2, 1-k+n1+tdx], {k, 0, 1+n1+tdx}]+Sum[(1/2)*(-1)^j*Binomial[1+j, l]*fracSeries[r, j]*Multinomial[j, k, -j-k+n1+tdx]*(*order1IRDiv*)refineB[-1+r, k+l+sdx, p1, 0, m0]*pow[p1, l]*pow[-m0^2+p1, 1+j-l]*pow[p2, k]*pow[-m0^2 + p2, -j-k+n1+tdx], {j, 0, n1+tdx}, {k, 0, -j+n1+tdx}, {l, 0, 1 + j}]), {sdx, 0, n2},{tdx, 0, n2 - sdx}]
		],

	(*Nonpermuted*)
	(*irDiv[passVeltC][r_?Positive,n1_,n2_,0,q_,p2_,0,0,m2_]|irDiv[passVeltC][r_?Positive,n2_,n1_,p2_,q_,0,0,m2_,0] :> 0,*)
	irDiv[passVeltC][r_,n1_,n2_,0,q_,q_,0,0,m2_]|irDiv[passVeltC][r_,n2_,n1_,q_,q_,0,0,m2_,0] :> 1/(2*(n1+1))Sum[Binomial[n1+1,k](-1)^(n1)irDiv[refineB][r-1,k+n2,q,0,m2],{k,0,n1+1}],
	irDiv[passVeltC][r_,n1_,n2_,0,q_,p2_,0,0,m2_]|irDiv[passVeltC][r_,n2_,n1_,p2_,q_,0,0,m2_,0] :> 
	  With[{
		gammaSeries=
		  If[#2+1+#1>0,  (-1)^(1+#1)/((-#1)! (#2+#1)! Eps)+((-1)^#1 (HarmonicNumber[-#1]-HarmonicNumber[#2+#1]))/((-#1)! (#2+#1)!)-1/(2 ((-#1)! (#2+#1)!)) ((-1)^#1 (HarmonicNumber[-#1]^2-2 HarmonicNumber[-#1] HarmonicNumber[#2+#1]+HarmonicNumber[#2+#1]^2+HarmonicNumber[-#1,2]+HarmonicNumber[#2+#1,2])) Eps,
			((-1)^(1+#2) (-1-#2-#1)!)/(-#1)!+1/(-#1)! (-1)^#2 (-1-#2-#1)! (-HarmonicNumber[-1-#2-#1]+HarmonicNumber[-#1]) Eps]&,
		fracSeries=
		  If[#1+#2!=0,  (1/(#1+#2)+Eps/(#1+#2)^2),  -1/Eps]&},
		
		1/(q-p2)^(n1+1) (Sum[-(n1!/2)*gammaSeries[r,n1]*Binomial[n1+1,k]pow[p2,k]pow[p2-m2^2,n1+1-k](*order1IRDiv*)refineB[r-1,n2+k,p2,0,m2],{k,0,n1+1}]+ Sum[(-1)^j/2 fracSeries[r,j]Multinomial[j,k,n1-j-k]Binomial[j+1,l]pow[p2,k]pow[q,l]pow[p2-m2^2,n1-j-k]pow[q-m2^2,j+1-l](*order1IRDiv*)refineB[r-1,n2+k+l,q,0,m2],{j,0,n1},{k,0,n1-j},{l,0,j+1}])
	  ]
  };


	(****Reduction formulae for negative rank r<0*****)
	(****OK*****)
	refineRulesCIRDivnegativer = {
	  (*If detX!=0 and r=0, then condition for appearance of IR divergence is not satisfied, so it is IR finite.*)
	  irDiv[passVeltC][r_?Negative,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/detX * (4*detZ*(2(2-2*Eps+n1+n2+2r)*irDiv[passVeltC][r+1,n1,n2,p1,q,p2,m0,m1,m2]-irDiv[pvBs][r,n1,n2,q,m1,m2]) + Sum[-2*adjX0[[j]]*(KroneckerDelta[n[[j]],0]*pinchB[r,n[[not[j]]]][[j]] - irDiv[pvBs][r,n1,n2,q,m1,m2] - 2*n[[j]]*irDiv[passVeltC][r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,p2,m0,m1,m2]),{j,1,2}]),
	  irDiv[passVeltC][_,_,_,_,_,_,_,_,_] -> 0};
];


irDiv[refineC][r_Integer,n1_Integer,n2_Integer,p1_,q_,p2_,m0_,m1_,m2_] :=
  Module[{
    f={p1-m1^2+m0^2,p2-m2^2+m0^2},
    gramZ={{p1, -(q-p1-p2)/2},{-(q-p1-p2)/2, p2}},
    adjZ={{p2, (q-p1-p2)/2},{(q-p1-p2)/2, p1}},
	Xij,
    adjX0,adjXij,
    i,j,k,m,n},

  Xij={{m0^2,f[[1]]/2,f[[2]]/2},{f[[1]]/2,p1,-(q-p1-p2)/2},{f[[2]]/2,-(q-p1-p2)/2,p2}};
  adjX0=Table[Sum[adjZ[[j,k]]f[[k]],{k,1,2}],{j,1,2}]; (*up to a constant: -1*)
  adjXij=Table[4m0^2 adjZ[[i,j]]+Sum[(KroneckerDelta[i,m]KroneckerDelta[n,j]-KroneckerDelta[i,j]KroneckerDelta[n,m])f[[n]] f[[m]],{n,1,2},{m,1,2}],{i,1,2},{j,1,2}];
  
  Which[
	r > 1 || (m0=!=0 && m1=!=0 && m2=!=0), 0,
	r===1 && p1===q===p2===m0===m1===m2===0, (-1)^(n1+n2+1)/2 * n1! n2!/(n1+n2+2)! 1/Eps,
	r===1, 0,
	
	(*THIS NEEDS TO BE IMPROVED*)
    X`Internal`PossibleAllZeroQ[gramZ] && !(X`Internal`PossibleAllZeroQ[f]),
    (*Print["Case 5: gramZ vanishing but f non-vanishing."];*)
      With[{siga=Which[!PossibleZeroQ[f[[1]]],1,True,2]},
        Replace[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],{refineRulesCcase5a[[siga]],refineRulesCcase5b}]
      ],
  
    PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0],
    (*Print["Case 4: detZ and adjX0 are zero"];*)
      (*KallenExpand@*)Replace[irDiv[passVeltC][r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCIRDivcase4],

    (*THIS NEEDS TO BE IMPROVED*)
    PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3: detZ=0"];*)
      With[{
        siga=Which[!PossibleZeroQ[adjZ[[1,1]]],{1,1},!PossibleZeroQ[adjZ[[2,2]]],{2,2},True,{1,2}],
        sigb=Which[!PossibleZeroQ[adjX0[[1]]],1,True,2]},
        (*Print["siga=",siga,"  sigb=",sigb, "adjZ = ", adjZ];*)
        ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],{refineRulesCcase3a[[Sequence@@siga]],refineRulesCcase3b[[sigb]]}] 
      ],


    ((PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] && PossibleZeroQ[m1]) (*(p1===m0^2 && q===m2^2 && m1===0)*)  (* p2 may or may not vanish*)
     || (PossibleZeroQ[p2-m0^2] && PossibleZeroQ[q-m1^2] && PossibleZeroQ[m2]) (*(p2===m0^2 && q===m1^2  && m2===0)*)  (* p1 may or may not vanish*)
     || (PossibleZeroQ[p1-m1^2] && PossibleZeroQ[p2-m2^2] && PossibleZeroQ[m0]) (*(p1===m1^2 && p2===m2^2  && m0===0)*)) (* q may or may not vanish*),
    (*Print["Case 2: Triangle 6; Xij=", Xij, "adjXij=",adjXij, "and adjX0j=",adjX0];*)
    Replace[irDiv[passVeltC][r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCIRDivtriangle6] ,


	((PossibleZeroQ[q] && PossibleZeroQ[m2] && PossibleZeroQ[m1]) (*(q===0 && m2===0 && m1===0)*)
	 || (PossibleZeroQ[p1] && PossibleZeroQ[m1] && PossibleZeroQ[m0]) (*(p1===0 && m1===0 && m0===0)*)
	 || (PossibleZeroQ[p2] && PossibleZeroQ[m2] && PossibleZeroQ[m0]) (*(p2===0 && m2===0 && m0===0)*)),
	(*Print["PVC for triangle 2 & 3"];*)
	Replace[irDiv[passVeltC][r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCIRDivtriangle3],

  
	NonPositive[r] && !(PossibleZeroQ[Det[Xij]]),
	(*Print["PVC for r<0: Det[X]!=0"];*)
	ReplaceRepeated[irDiv[passVeltC][r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCIRDivnegativer],


    True,
	Message[LoopRefine::leadinglandau, PVC[r,n1,n2,p1,q,p2,m0,m1,m2]];
	PVC[r,n1,n2,p1,q,p2,m0,m1,m2]

  ]
];


(* ::Subsubsection::Closed:: *)
(*D functions*)


(*Shifted C-functions; due to unshifted pinched propagator*)
irDiv[pvCs][r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_]/;(n3 < n1 && n3 < n2) := irDiv[pvCs][r,n3,n2,n1,s3,s2,s23,m3,m2,m1];
irDiv[pvCs][r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_]/;(n2 < n1 && n2 < n3) := irDiv[pvCs][r,n2,n1,n3,s2,s23,s3,m2,m1,m3];
irDiv[pvCs][r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_] := (-1)^n1 Sum[Multinomial[idx1,idx2,n1-idx1-idx2]irDiv[refineC][r,n2+idx2,n1+n3-idx1-idx2,s2,s3,s23,m1,m2,m3],{idx1,0,n1},{idx2,0,n1-idx1}];


Block[{
	n={n1, n2, n3},
	f={s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},

	gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }},

	detZ = 1/4 * Kibble\[Phi][s1,s2,s3,s4,s12,s23],

	adjZ={{-Kallen\[Lambda][s12,s3,s4]/4, 1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)), 1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4))},
		 {1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)), -Kallen\[Lambda][s23,s1,s4]/4, 1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4))},
		 {1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4)), 1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4)),-Kallen\[Lambda][s12,s1,s2]/4}},

	mtxX=({{2*m0^2,        s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
		   {s1-m1^2+m0^2,  2*s1,         s1+s12-s2,     s1-s23+s4},
		   {s12-m2^2+m0^2, s1+s12-s2,    2*s12,         s12-s3+s4},
		   {s4-m3^2+m0^2,  s1-s23+s4,    s12-s3+s4,     2*s4}}),

    adjadjZ = {{{{0,0,0},{0,0,0},{0,0,0}},{{0,-s4,1/2 (s12-s3+s4)},{s4,0,1/2 (-s1+s23-s4)},{1/2 (-s12+s3-s4),1/2 (s1-s23+s4),0}},{{0,1/2 (s12-s3+s4),-s12},{1/2 (-s12+s3-s4),0,1/2 (s1+s12-s2)},{s12,1/2 (-s1-s12+s2),0}}},{{{0,s4,1/2 (-s12+s3-s4)},{-s4,0,1/2 (s1-s23+s4)},{1/2 (s12-s3+s4),1/2 (-s1+s23-s4),0}},{{0,0,0},{0,0,0},{0,0,0}},{{0,1/2 (-s1+s23-s4),1/2 (s1+s12-s2)},{1/2 (s1-s23+s4),0,-s1},{1/2 (-s1-s12+s2),s1,0}}},{{{0,1/2 (-s12+s3-s4),s12},{1/2 (s12-s3+s4),0,1/2 (-s1-s12+s2)},{-s12,1/2 (s1+s12-s2),0}},{{0,1/2 (s1-s23+s4),1/2 (-s1-s12+s2)},{1/2 (-s1+s23-s4),0,s1},{1/2 (s1+s12-s2),-s1,0}},{{0,0,0},{0,0,0},{0,0,0}}}},
	adjX0, 
	adjXij = {{2 (-m0^4 s3-m2^4 s4-s12 (m3^4+m3^2 (s12-s3-s4)+s3 s4)+m2^2 ((s12+s3-s4) s4+m3^2 (s12-s3+s4))+m0^2 (m3^2 (s12+s3-s4)+s3 (s12-s3+s4)+m2^2 (-s12+s3+s4))),-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s12-s3+s4) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4)),(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4)-2 s12 (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))+(m0^2-m2^2+s12) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4))},{-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s1-s23+s4) (-(m0^2-m2^2+s12) (m0^2-m3^2+s4)+2 m0^2 (s12-s3+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s12-s3+s4)),2 (-m0^4 s23-m1^4 s4-s1 (m3^4+m3^2 (s1-s23-s4)+s23 s4)+m1^2 ((s1+s23-s4) s4+m3^2 (s1-s23+s4))+m0^2 (m3^2 (s1+s23-s4)+s23 (s1-s23+s4)+m1^2 (-s1+s23+s4))),-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4)+(s1+s12-s2) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m2^2+s12) (-2 s1 (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s1-s23+s4))},{(2 (m0^2-m1^2+s1) s12-(m0^2-m2^2+s12) (s1+s12-s2)) (m0^2-m3^2+s4)-(4 m0^2 s12-(m0^2-m2^2+s12)^2) (s1-s23+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4),-(-2 s1 (m0^2-m2^2+s12)+(m0^2-m1^2+s1) (s1+s12-s2)) (m0^2-m3^2+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s1-s23+s4)-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4),2 (-m1^4 s12-m0^4 s2-s1 (m2^4+m2^2 (s1-s12-s2)+s12 s2)+m1^2 (m2^2 (s1+s12-s2)+s12 (s1-s12+s2))+m0^2 ((s1+s12-s2) s2+m2^2 (s1-s12+s2)+m1^2 (-s1+s12+s2)))}},
	pinchC, missCDivUV,
	nk,kp,
	i, j, k, ndx,mdx},



	nk[idx_,cnc_] = Which[idx<cnc, n[[idx]], idx>=cnc, n[[idx+1]]]; (*This is n_{idx(cnc)}*)
	kp[idx_,cnc_] = Which[idx<cnc, idx, idx>=cnc, idx+1]; (*this is just idx(cnc)*)

	adjX0=Expand[Table[Sum[adjZ[[j,k]]f[[k]],{k,1,3}],{j,1,3}]]; (*up to a constant: -4*)

	(*Passarino Veltman functions with pinched propagators, and their divergent parts*)
	pinchC[r_,n1_,n2_]  =    {irDiv[refineC][r,n1,n2,s12,s3,s4,m0,m2,m3], irDiv[refineC][r,n1,n2,s1,s23,s4,m0,m1,m3], irDiv[refineC][r,n1,n2,s1,s2,s12,m0,m1,m2]};
	missCDivUV[r_,n1_,n2_] = {pvCDivUV[r,n1,n2,s12,s3,s4,m0,m2,m3],pvCDivUV[r,n1,n2,s1,s23,s4,m0,m1,m3],pvCDivUV[r,n1,n2,s1,s2,s12,m0,m1,m2]};

	(********Case6: All elements of gramZ is zero, AND all f are zero********)
	(*refineRulesDIRDivcase6={
	  irDiv[passVeltD][r_?Negative,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/m0^2 ((4-2Eps+2(r+n1+n2+n3))irDiv[passVeltD][r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-irDiv[pvCs][r,n1,n2,n3,s2,s3,s23,m1,m2,m3]),
	  irDiv[passVeltD][0,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/m0^2 ((4+2(n1+n2+n3))irDiv[passVeltD][1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-irDiv[pvCs][0,n1,n2,n3,s2,s3,s23,m1,m2,m3]-2 pvDDivUV[1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),
	  irDiv[passVeltD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> -(1/(2(n1+1)))irDiv[pvCs][r-1,n1+1,n2,n3,s2,s3,s23,m1,m2,m3]
	};*)

	(********Case5: All elements of gramZ is zero, but f nonzero********)	
	refineRulesDIRDivcase5a=Table[irDiv[passVeltD][r_?NonPositive,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/f[[k]] (-2n[[k]]irDiv[passVeltD][r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+KroneckerDelta[n[[k]],0]pinchC[r,nk[1,k],nk[2,k]][[k]]-irDiv[pvCs][r,n1,n2,n3,s2,s3,s23,m1,m2,m3]),{k,1,3}];
	refineRulesDIRDivcase5b = irDiv[passVeltD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 0(*1/(2+2r+2n1+2n2+2n3)*(irDiv[pvCs][r-1,n1,n2,n3,s2,s3,s23,m1,m2,m3]+m0^2 irDiv[passVeltD][r-1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])+1/(1+r+n1+n2+n3)*pvDDivUV[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]*);

	(********Case4: Gram determinant and Cayley vectors X vanishing********)
	refineRulesDIRDivcase4a=
	Flatten[Table[irDiv[passVeltD][r_?Positive, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/(2(n[[k]]+1)adjZ[[j,k]]) (-2*Sum[adjZ[[j,mdx]]*n[[mdx]]*irDiv[passVeltD][r,n1-KroneckerDelta[mdx,1]+KroneckerDelta[k,1],n2-KroneckerDelta[mdx,2]+KroneckerDelta[k,2],n3-KroneckerDelta[mdx,3]+KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{mdx,Complement[Range[1,3],{k}]}]+Sum[adjZ[[j,l]](KroneckerDelta[n[[l]]+KroneckerDelta[k,l],0]*pinchC[r-1,nk[1,l]+KroneckerDelta[kp[1,l],k],nk[2,l]+KroneckerDelta[kp[2,l],k]][[l]]-irDiv[pvCs][r-1,n1+KroneckerDelta[k,1],n2+KroneckerDelta[k,2],n3+KroneckerDelta[k,3],s2,s3,s23,m1,m2,m3]),{l,1,3}])
		,{j,1,3},{k,1,3}]];
	refineRulesDIRDivcase4b=
	Flatten[Table[irDiv[passVeltD][0, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 4*adjZ[[i,k]]/adjXij[[i,k]]*(2(1+n1+n2+n3)irDiv[passVeltD][1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-irDiv[pvCs][0,n1,n2,n3,s2,s3,s23,m1,m2,m3])+2/adjXij[[i,k]]*Sum[f[[ndx]]*adjadjZ[[ndx,i,j,k]]*(KroneckerDelta[n[[j]],0]*pinchC[0,nk[1,j],nk[2,j]][[j]]-irDiv[pvCs][0,n1,n2,n3,s2,s3,s23,m1,m2,m3]-2n[[j]]*irDiv[passVeltD][1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],n3-KroneckerDelta[j,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{j,1,3},{ndx,1,3}]
		,{i,1,3},{k,1,3}]];
	refineRulesDIRDivcase4c=
	Flatten[Table[irDiv[passVeltD][r_?Negative, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 4*adjZ[[i,k]]/adjXij[[i,k]]*(2(1-2Eps+2r+n1+n2+n3)irDiv[passVeltD][r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-irDiv[pvCs][r,n1,n2,n3,s2,s3,s23,m1,m2,m3])+2/adjXij[[i,k]]*Sum[f[[ndx]]*adjadjZ[[ndx,i,j,k]]*(KroneckerDelta[n[[j]],0]*pinchC[r,nk[1,j],nk[2,j]][[j]]-irDiv[pvCs][r,n1,n2,n3,s2,s3,s23,m1,m2,m3]-2n[[j]]*irDiv[passVeltD][r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],n3-KroneckerDelta[j,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{j,1,3},{ndx,1,3}]
		,{i,1,3},{k,1,3}]];

	(********Exceptional Case: All adjZ vanishing (doesn't matter if adjX vanishes)********)
	(*Subcase 1: If s1!=0, \[Alpha]*f2!=f3*)
	refineRulesDIRDivcaseX1={
		irDiv[passVeltD][r_?NonNegative, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> 
		With[
		 {\[Alpha]=-(1/s12)(s12-s3+s4),
		  A=-(s4-m3^2+m0^2)+1/(2s12) (s12-s3+s4)(s12-m2^2+m0^2),
		  gammaCoeff0 = Piecewise[{{-1,#1+#2+#3==0},{(-1)^(#3+1) #3!,#2+#1==1},{0,#1<2},{((-1)^(1+#2+#3) (#1+#2+#3-1)!)/((#1+#2-1)(#1-2)!),True}}]&,
		  gammaCoeff1 = Piecewise[{{0,#1+#2+#3==0},{(-1)^(#3+1) #3!(HarmonicNumber[1-#1]-HarmonicNumber[#3]),#2+#1==1},{(-1)^(#1+#2+#3+1)/(#1+#2-1) (#1+#2+#3-1)!,#1<2},{((-1)^(1+#2+#3) (#1+#2+#3-1)!)/((#1+#2-1)^2 (#1-2)!) (1+(#1+#2-1)(HarmonicNumber[#1-2]-HarmonicNumber[#1+#2+#3-1])),True}}]& },
		  Sum[Binomial[n2,jdx]((-2^(n3+jdx)pow[\[Alpha],jdx])/A^(n3+jdx+1) (n3+jdx)! irDiv[refineC][r+n3+jdx,n1,n2-jdx,s1,s2,s12,m0,m1,m2]+Sum[Multinomial[kdx,ldx0,n3+jdx-kdx-ldx0] ((-1)^(n2+jdx+ldx0) 2^(kdx+ldx0))/A^(kdx+ldx0+1) (\[Alpha]^(n2+1) (gammaCoeff0[r,kdx,ldx0] irDiv[refineC][r+kdx+ldx0,n1,n2+n3-kdx-ldx0,s1,s23,s4,m0,m1,m3]+gammaCoeff1[r,kdx,ldx0] pvCDivUV[r+kdx+ldx0,n1,n2+n3-kdx-ldx0,s1,s23,s4,m0,m1,m3])-Sum[Multinomial[ldx1,ldx2,n2+jdx-ldx1-ldx2]pow[\[Alpha],jdx](1+\[Alpha])^(ldx2+1) (gammaCoeff0[r,kdx,ldx0] irDiv[refineC][r+kdx+ldx0,n1+ldx1,n3+jdx-kdx-ldx0+ldx2,s2,s23,s3,m2,m1,m3]+gammaCoeff1[r,kdx,ldx0] pvCDivUV[r+kdx+ldx0,n1+ldx1,n3+jdx-kdx-ldx0+ldx2,s2,s23,s3,m2,m1,m3]),{ldx1,0,n2-jdx},{ldx2,0,n2-jdx-ldx1}]),{kdx,0,n3+jdx},{ldx0,0,n3+jdx-kdx}]),{jdx,0,n2}]
		],
		irDiv[passVeltD][r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> 
		With[
		 {\[Alpha]=-(1/s12)(s12-s3+s4),
		  A=-(s4-m3^2+m0^2)+1/(2s12) (s12-s3+s4)(s12-m2^2+m0^2),
		  gammaSeries = Which[
			#1>=2,((-1)^(1+#2+#3) (-1+#2+#3+#1)!)/((-1+#2+#1) (-2+#1)!)+((-1)^(1+#2+#3) Eps (-1+#2+#3+#1)! (1+(-1+#2+#1) HarmonicNumber[-2+#1]-(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1]))/((-1+#2+#1)^2 (-2+#1)!)+1/(2 (-1+#2+#1)^3 (-2+#1)!) (-1)^(#2+#3) Eps^2 (-1+#2+#3+#1)! (-2-(-1+#2+#1)^2 HarmonicNumber[-2+#1]^2+2 (-1+#2+#1) HarmonicNumber[-1+#2+#3+#1]-(-1+#2+#1)^2 HarmonicNumber[-1+#2+#3+#1]^2+2 (-1+#2+#1) HarmonicNumber[-2+#1] (-1+(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1])-(-1+#2+#1)^2 HarmonicNumber[-2+#1,2]+(-1+#2+#1)^2 HarmonicNumber[-1+#2+#3+#1,2]),
			#1+#2==1,(-1)^(1+#3) #3! (1-#1)!+(-1)^#3 Eps #3! (1-#1)! (HarmonicNumber[#3]-HarmonicNumber[1-#1])-1/2 (-1)^#3 Eps^2 #3! (1-#1)! ((HarmonicNumber[#3]-HarmonicNumber[1-#1])^2-HarmonicNumber[#3,2]-HarmonicNumber[1-#1,2]),
			1-#1-#2-#3>0,(1-#1)!/((-1+#2+#1) (-#2-#3-#1)!)+(Eps (1-#1)! (1+(-1+#2+#1) HarmonicNumber[1-#1]-(-1+#2+#1) HarmonicNumber[-#2-#3-#1]))/((-1+#2+#1)^2 (-#2-#3-#1)!)+1/(2 (-1+#2+#1)^3 (-#2-#3-#1)!) Eps^2 (1-#1)! (2+(-1+#2+#1)^2 HarmonicNumber[1-#1]^2-2 (-1+#2+#1) HarmonicNumber[-#2-#3-#1]+(-1+#2+#1)^2 HarmonicNumber[-#2-#3-#1]^2+2 (-1+#2+#1) HarmonicNumber[1-#1] (1-(-1+#2+#1) HarmonicNumber[-#2-#3-#1])-(-1+#2+#1)^2 HarmonicNumber[1-#1,2]+(-1+#2+#1)^2 HarmonicNumber[-#2-#3-#1,2]),
			True,((-1)^(1+#2+#3+#1) Eps (1-#1)! (-1+#2+#3+#1)!)/(-1+#2+#1)+1/(-1+#2+#1)^2 (-1)^(1+#2+#3+#1) Eps^2 (1-#1)! (-1+#2+#3+#1)! (1+(-1+#2+#1) HarmonicNumber[1-#1]-(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1])
			]&
		 },
		  Sum[Binomial[n2,jdx]((-2^(n3+jdx)pow[\[Alpha],jdx])/A^(n3+jdx+1) (n3+jdx)! irDiv[refineC][r+n3+jdx,n1,n2-jdx,s1,s2,s12,m0,m1,m2]+Sum[Multinomial[kdx,ldx0,n3+jdx-kdx-ldx0] ((-1)^(n2+jdx+ldx0) 2^(kdx+ldx0))/A^(kdx+ldx0+1) (\[Alpha]^(n2+1) (gammaSeries[r,kdx,ldx0] irDiv[refineC][r+kdx+ldx0,n1,n2+n3-kdx-ldx0,s1,s23,s4,m0,m1,m3])-Sum[Multinomial[ldx1,ldx2,n2+jdx-ldx1-ldx2]pow[\[Alpha],jdx](1+\[Alpha])^(ldx2+1) (gammaSeries[r,kdx,ldx0] irDiv[refineC][r+kdx+ldx0,n1+ldx1,n3+jdx-kdx-ldx0+ldx2,s2,s23,s3,m2,m1,m3]),{ldx1,0,n2-jdx},{ldx2,0,n2-jdx-ldx1}]),{kdx,0,n3+jdx},{ldx0,0,n3+jdx-kdx}]),{jdx,0,n2}]
		]};
	(*Subcase 2: If s1!=0, \[Alpha]*f2=f3*)
	refineRulesDIRDivcaseX2=
		irDiv[passVeltD][r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> 
		With[
		  {\[Alpha]=(-s12+s3-s4)/(2s12)},
			1/2 Sum[Binomial[n2,j] pow[\[Alpha],j]/(n3+j+1) (pow[-\[Alpha],n2-j]*irDiv[refineC][r-1,n1,n2+n3+1,s1,s23,s4,m0,m1,m3]+Sum[Multinomial[k1,k2,n2-j-k1-k2](-1)^(1+n2-j)pow[1+\[Alpha],k1+1]irDiv[refineC][r-1,n1+k2,n3+j+k1+1,s2,s23,s3,m2,m1,m3],{k1,0,n2-j},{k2,0,n2-j-k1}]),{j,0,n2}]
		];
	(*Subcase 3: If s1=0, m0!=m2*)
	refineRulesDIRDivcaseX3={
		irDiv[passVeltD][r_?NonNegative, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :>
		With[
		 {A=m2^2-m0^2,
		  gammaCoeff0 = Piecewise[{{-1,#1+#2+#3==0},{(-1)^(#3+1) #3!,#2+#1==1},{0,#1<2},{((-1)^(1+#2+#3) (#1+#2+#3-1)!)/((#1+#2-1)(#1-2)!),True}}]&,
		  gammaCoeff1 = Piecewise[{{0,#1+#2+#3==0},{(-1)^(#3+1) #3!(HarmonicNumber[1-#1]-HarmonicNumber[#3]),#2+#1==1},{(-1)^(#1+#2+#3+1)/(#1+#2-1) (#1+#2+#3-1)!,#1<2},{((-1)^(1+#2+#3) (#1+#2+#3-1)!)/((#1+#2-1)^2 (#1-2)!) (1+(#1+#2-1)(HarmonicNumber[#1-2]-HarmonicNumber[#1+#2+#3-1])),True}}]&},
		  (-2^n2 n2!)/A^(n2+1) irDiv[refineC][r+n2,n1,n3,s1,s23,s4,m0,m1,m3]+Sum[((-1)^(1+jdx+n2) 2^(jdx+kdx))/A^(jdx+kdx+1) Multinomial[jdx,kdx,ldx1,ldx2,n2-jdx-kdx-ldx1-ldx2](gammaCoeff0[r,jdx,kdx]irDiv[refineC][r+jdx+kdx,n1+ldx1,n3+ldx2,s2,s23,s3,m2,m1,m3]+gammaCoeff1[r,jdx,kdx]pvCDivUV[r+jdx+kdx,n1+ldx1,n3+ldx2,s2,s23,s3,m2,m1,m3]),{jdx,0,n2},{kdx,0,n2-jdx},{ldx1,0,n2-jdx-kdx},{ldx2,0,n2-jdx-kdx-ldx1}]
		],
		irDiv[passVeltD][r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :>
		With[
		 {A=m2^2-m0^2,
		  (*gammaSeries = Normal[Series[Gamma[2+Eps-#1]/((-1+#1+#2-Eps)Gamma[1+Eps-#1-#2-#3]),{Eps,0,2}]]&*)
		  gammaSeries = Which[
			#1>=2,((-1)^(1+#2+#3) (-1+#2+#3+#1)!)/((-1+#2+#1) (-2+#1)!)+((-1)^(1+#2+#3) Eps (-1+#2+#3+#1)! (1+(-1+#2+#1) HarmonicNumber[-2+#1]-(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1]))/((-1+#2+#1)^2 (-2+#1)!)+1/(2 (-1+#2+#1)^3 (-2+#1)!) (-1)^(#2+#3) Eps^2 (-1+#2+#3+#1)! (-2-(-1+#2+#1)^2 HarmonicNumber[-2+#1]^2+2 (-1+#2+#1) HarmonicNumber[-1+#2+#3+#1]-(-1+#2+#1)^2 HarmonicNumber[-1+#2+#3+#1]^2+2 (-1+#2+#1) HarmonicNumber[-2+#1] (-1+(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1])-(-1+#2+#1)^2 HarmonicNumber[-2+#1,2]+(-1+#2+#1)^2 HarmonicNumber[-1+#2+#3+#1,2]),
			#1+#2==1,(-1)^(1+#3) #3! (1-#1)!+(-1)^#3 Eps #3! (1-#1)! (HarmonicNumber[#3]-HarmonicNumber[1-#1])-1/2 (-1)^#3 Eps^2 #3! (1-#1)! ((HarmonicNumber[#3]-HarmonicNumber[1-#1])^2-HarmonicNumber[#3,2]-HarmonicNumber[1-#1,2]),
			1-#1-#2-#3>0,(1-#1)!/((-1+#2+#1) (-#2-#3-#1)!)+(Eps (1-#1)! (1+(-1+#2+#1) HarmonicNumber[1-#1]-(-1+#2+#1) HarmonicNumber[-#2-#3-#1]))/((-1+#2+#1)^2 (-#2-#3-#1)!)+1/(2 (-1+#2+#1)^3 (-#2-#3-#1)!) Eps^2 (1-#1)! (2+(-1+#2+#1)^2 HarmonicNumber[1-#1]^2-2 (-1+#2+#1) HarmonicNumber[-#2-#3-#1]+(-1+#2+#1)^2 HarmonicNumber[-#2-#3-#1]^2+2 (-1+#2+#1) HarmonicNumber[1-#1] (1-(-1+#2+#1) HarmonicNumber[-#2-#3-#1])-(-1+#2+#1)^2 HarmonicNumber[1-#1,2]+(-1+#2+#1)^2 HarmonicNumber[-#2-#3-#1,2]),
			True,((-1)^(1+#2+#3+#1) Eps (1-#1)! (-1+#2+#3+#1)!)/(-1+#2+#1)+1/(-1+#2+#1)^2 (-1)^(1+#2+#3+#1) Eps^2 (1-#1)! (-1+#2+#3+#1)! (1+(-1+#2+#1) HarmonicNumber[1-#1]-(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1])
			]&
		 },
		  (-2^n2 n2!)/A^(n2+1) irDiv[refineC][r+n2,n1,n3,s1,s23,s4,m0,m1,m3]+Sum[((-1)^(1+jdx+n2) 2^(jdx+kdx))/A^(jdx+kdx+1) Multinomial[jdx,kdx,ldx1,ldx2,n2-jdx-kdx-ldx1-ldx2](gammaSeries[r,jdx,kdx]irDiv[refineC][r+jdx+kdx,n1+ldx1,n3+ldx2,s2,s23,s3,m2,m1,m3]),{jdx,0,n2},{kdx,0,n2-jdx},{ldx1,0,n2-jdx-kdx},{ldx2,0,n2-jdx-kdx-ldx1}]
		]};
	(*Subcase 4: If s1=0, m0=m2*)
	refineRulesDIRDivcaseX4=irDiv[passVeltD][r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> (-1)^n2/(2(n2+1)) Sum[Multinomial[j,k,n2+1-j-k]*irDiv[refineC][r-1,n1+j,n3+k,s1,s23,s4,m0,m1,m3],{j,0,n2+1},{k,0,n2+1-j}];

	(********Exceptional Case: All adjX vanishing, but not adjZ********)
	(*refineRulesDcaseX5=Flatten[Table[passVeltD[r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/(2(n[[k]]+1)adjZ[[j,k]]) (-2*Sum[adjZ[[j,mdx]]*n[[mdx]]*passVeltD[r,n1-KroneckerDelta[mdx,1]+KroneckerDelta[k,1],n2-KroneckerDelta[mdx,2]+KroneckerDelta[k,2],n3-KroneckerDelta[mdx,3]+KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{mdx,Complement[Range[1,3],{k}]}]+Sum[adjZ[[j,l]](KroneckerDelta[n[[l]]+KroneckerDelta[k,l],0]*pinchC[r-1,nk[1,l]+KroneckerDelta[kp[1,l],k],nk[2,l]+KroneckerDelta[kp[2,l],k]][[l]]-pvCs[r-1,n1+KroneckerDelta[k,1],n2+KroneckerDelta[k,2],n3+KroneckerDelta[k,3],s2,s3,s23,m1,m2,m3]),{l,1,3}])
		,{j,1,3},{k,1,3}]];*)

	(********Case3: Gram determinant vanishing, but Cayley vectors X non-vanishing********)
	refineRulesDIRDivcase3a=
	Flatten[Table[
	  irDiv[passVeltD][r_?Positive,0, 0, 0, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 
	    1/(2r)*(irDiv[pvCs][r-1,0,0,0,s2,s3,s23,m1,m2,m3]+m0^2 irDiv[passVeltD][r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])+1/r*pvDDivUV[r, 0, 0, 0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] +
	    1/(4r)*1/adjZ[[k,l]] Sum[adjadjZ[[k,ndx,l,mdx]](Sum[gramZ[[ndx,j]]((1-KroneckerDelta[mdx,j])pinchC[r-1,KroneckerDelta[kp[1,mdx],j],KroneckerDelta[kp[2,mdx],j]][[mdx]]-irDiv[pvCs][r-1,KroneckerDelta[j,1],KroneckerDelta[j,2],KroneckerDelta[j,3],s2,s3,s23,m1,m2,m3]),{j,1,3}]+1/2 f[[mdx]](-pinchC[r-1,0,0][[ndx]]+irDiv[pvCs][r-1,0,0,0,s2,s3,s23,m1,m2,m3]+f[[ndx]]irDiv[passVeltD][r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])),{ndx,1,3},{mdx,1,3}] 
	  ,{k,1,3},{l,1,3}]];
	refineRulesDIRDivcase3b=
	Table[
	  irDiv[passVeltD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/adjX0[[j]]*
	    Sum[adjZ[[j,k]](KroneckerDelta[n[[k]],0]pinchC[r,nk[1,k],nk[2,k]][[k]]-irDiv[pvCs][r,n1,n2,n3,s2,s3,s23,m1,m2,m3]-
	    2n[[k]]irDiv[passVeltD][r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{k,1,3}],
	{j,1,3}];


	(****Reduction formulae for negative rank r<0*****)
	refineRulesDIRDivnegativerCase1 = {
	  irDiv[passVeltD][0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> With[{body=analD0IR[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]}, If[Head[body]===analD0IR,0,body]],
	  irDiv[passVeltD][r_?Positive,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 0,
	  irDiv[passVeltD][r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/Det[mtxX] * (8*detZ*(2(1-2*Eps+n1+n2+n3+2r)*irDiv[passVeltD][r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-irDiv[pvCs][r,n1,n2,n3,s2,s3,s23,m1,m2,m3]) + Sum[-4*adjX0[[j]]*(KroneckerDelta[n[[j]],0]*pinchC[r,nk[1,j],nk[2,j]][[j]] - irDiv[pvCs][r,n1,n2,n3,s2,s3,s23,m1,m2,m3] - 2*n[[j]]*irDiv[passVeltD][r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],n3-KroneckerDelta[j,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{j,1,3}])}

];


irDiv[refineD][r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]:=
  Module[{
    f={s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
    gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }},
    adjZ={{s12 s4-1/4 (s12-s3+s4)^2,1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4))},{1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),s1 s4-1/4 (s1-s23+s4)^2,1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4))},{1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4)),1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4)),s1 s12-1/4 (s1+s12-s2)^2}},
    (*detZ=1/4*(-s12^2 s23-s1^2 s3+s12 (-(s23-s3) (s23-s4)+s2 (s23+s4))-s2 (s23 (s3-s4)+s4 (s2-s3+s4))+s1 (s12 (-s2+s23+s3)+(s23-s3) (s3-s4)+s2 (s3+s4))),*)
	adjX0,
	adjXij = {{2 (-m0^4 s3-m2^4 s4-s12 (m3^4+m3^2 (s12-s3-s4)+s3 s4)+m2^2 ((s12+s3-s4) s4+m3^2 (s12-s3+s4))+m0^2 (m3^2 (s12+s3-s4)+s3 (s12-s3+s4)+m2^2 (-s12+s3+s4))),-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s12-s3+s4) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4)),(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4)-2 s12 (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))+(m0^2-m2^2+s12) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4))},{-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s1-s23+s4) (-(m0^2-m2^2+s12) (m0^2-m3^2+s4)+2 m0^2 (s12-s3+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s12-s3+s4)),2 (-m0^4 s23-m1^4 s4-s1 (m3^4+m3^2 (s1-s23-s4)+s23 s4)+m1^2 ((s1+s23-s4) s4+m3^2 (s1-s23+s4))+m0^2 (m3^2 (s1+s23-s4)+s23 (s1-s23+s4)+m1^2 (-s1+s23+s4))),-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4)+(s1+s12-s2) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m2^2+s12) (-2 s1 (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s1-s23+s4))},{(2 (m0^2-m1^2+s1) s12-(m0^2-m2^2+s12) (s1+s12-s2)) (m0^2-m3^2+s4)-(4 m0^2 s12-(m0^2-m2^2+s12)^2) (s1-s23+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4),-(-2 s1 (m0^2-m2^2+s12)+(m0^2-m1^2+s1) (s1+s12-s2)) (m0^2-m3^2+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s1-s23+s4)-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4),2 (-m1^4 s12-m0^4 s2-s1 (m2^4+m2^2 (s1-s12-s2)+s12 s2)+m1^2 (m2^2 (s1+s12-s2)+s12 (s1-s12+s2))+m0^2 ((s1+s12-s2) s2+m2^2 (s1-s12+s2)+m1^2 (-s1+s12+s2)))}},
    mtxX = {{2*m0^2, s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
			{s1-m1^2+m0^2, 2*s1, s1+s12-s2, s1-s23+s4},
			{s12-m2^2+m0^2, s1+s12-s2, 2*s12, s12-s3+s4},
			{s4-m3^2+m0^2, s1-s23+s4, s12-s3+s4, 2*s4}},
    j,k},
  
  (*Print[PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]];	*)

	adjX0=Table[Sum[adjZ[[j,k]]f[[k]],{k,1,3}],{j,1,3}];
  
  Which[
	r > 2 || (m0=!=0 && m1=!=0 && m2=!=0 && m3=!=0), 0,
	r===2 && SameQ[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3,0], (-1)^(n1+n2+n3+1)/4 * n1! n2! n3!/(n1+n2+n3+3)! 1/Eps,
	r >= 1, 0,

    (*X`Internal`PossibleAllZeroQ[gramZ] && X`Internal`PossibleAllZeroQ[f] && !(PossibleZeroQ[m0]),
    (*Print["Case 6: gramZ & f vanishing."];*)
      ReplaceRepeated[irDiv[passVeltD][r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineRulesDIRDivcase6],*)

    X`Internal`PossibleAllZeroQ[gramZ] && !(X`Internal`PossibleAllZeroQ[f]),
    (*Print["PVD Case 5: gramZ vanishing but f non-vanishing.  f=", f];*)
      With[{siga=First@Ordering[f,1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
		(*Print["f=", f, "  sig:", siga];*)
        ReplaceRepeated[irDiv[passVeltD][r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDIRDivcase5a[[siga]],refineRulesDIRDivcase5b}]
      ],
  
	(*Can handle PVD[0,0,0,0,m^2,m^2,m^2,m^2,4m^2,0,m,0,m,0]*)
	PossibleZeroQ[s12] && PossibleZeroQ[s3-s4] && PossibleZeroQ[s1-s2],
	  Replace[irDiv[passVeltD][r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],
		If[PossibleZeroQ[m0-m2],refineRulesDIRDivcaseX4,refineRulesDIRDivcaseX3]],

	PossibleZeroQ[s23] && PossibleZeroQ[s3-s2] && PossibleZeroQ[s1-s4],
	  Replace[Sum[(-1)^n3*Multinomial[k1,k2,k3,n3-k1-k2-k3]*irDiv[passVeltD][r,n2+k2,n1+k1,k3,s3,s2,s1,s4,s23,s12,m3,m2,m1,m0],{k1,0,n3},{k2,0,n3-k1},{k3,0,n3-k2-k1}],
		If[PossibleZeroQ[m3-m1],refineRulesDIRDivcaseX4,refineRulesDIRDivcaseX3],{0,Infinity}],

	PossibleZeroQ[s1] && PossibleZeroQ[s23-s4] && PossibleZeroQ[s12-s2],
	  Replace[irDiv[passVeltD][r,n2,n1,n3,s12,s2,s23,s4,s1,s3,m0,m2,m1,m3],
		If[PossibleZeroQ[m0-m1],refineRulesDIRDivcaseX4,refineRulesDIRDivcaseX3]],

	PossibleZeroQ[s2] && PossibleZeroQ[s1-s12] && PossibleZeroQ[s3-s23],
	  Replace[Sum[(-1)^n1*Multinomial[k1,k2,k3,n1-k1-k2-k3]*irDiv[passVeltD][r,k1,n2+k2,n3+k3,s1,s12,s3,s23,s2,s4,m1,m0,m2,m3],{k1,0,n1},{k2,0,n1-k1},{k3,0,n1-k2-k1}],
		If[PossibleZeroQ[m1-m2],refineRulesDIRDivcaseX4,refineRulesDIRDivcaseX3],{0,Infinity}],

	PossibleZeroQ[s3] && PossibleZeroQ[s23-s2] && PossibleZeroQ[s12-s4],
	  Replace[Sum[(-1)^n3*Multinomial[k1,k2,k3,n3-k1-k2-k3]*irDiv[passVeltD][r,n1+k1,n2+k2,k3,s23,s2,s12,s4,s3,s1,m3,m1,m2,m0],{k1,0,n3},{k2,0,n3-k1},{k3,0,n3-k2-k1}],
		If[PossibleZeroQ[m3-m2],refineRulesDIRDivcaseX4,refineRulesDIRDivcaseX3],{0,Infinity}],

	PossibleZeroQ[s4] && PossibleZeroQ[s1-s23] && PossibleZeroQ[s3-s12],
	  Replace[irDiv[passVeltD][r,n1,n3,n2,s1,s23,s3,s12,s4,s2,m0,m1,m3,m2],
		If[PossibleZeroQ[m0-m3],refineRulesDIRDivcaseX4,refineRulesDIRDivcaseX3]],

	PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0] && !(X`Internal`PossibleAllZeroQ[adjZ]) && !(X`Internal`PossibleAllZeroQ[adjXij]),
	(*Print["Case 4 PVD: det Z=0, adjX0=0"];*)
	  With[{siga=First@Ordering[Flatten[Simplify[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
			sigb=First@Ordering[Flatten[Simplify[adjXij]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
			(*Print["adjZ=", adjZ, "  sig:", siga];*)
			(*Print["adjXij=", adjXij, "  sig:", sigb];*)
			ReplaceRepeated[irDiv[passVeltD][r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDIRDivcase4a[[siga]],refineRulesDIRDivcase4b[[sigb]],refineRulesDIRDivcase4c[[sigb]]}]
	  ],

    
    PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3 PVD: detZ=0 && one of adjX0 nonzero."];*)
      With[{
        siga=First@Ordering[Flatten[Simplify[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
        sigb=First@Ordering[Simplify[adjX0],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
        (*Print["adjZ=", adjZ, "  sig:", siga];*)
		(*Print["adjX0=", adjX0, "  sig:", sigb];*)
        ReplaceRepeated[irDiv[passVeltD][r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDIRDivcase3a[[siga]],refineRulesDIRDivcase3b[[sigb]]}]
      ],

	!PossibleZeroQ[Det[mtxX]],
	(*Print["Det[X]!=0"];*)
	ReplaceRepeated[irDiv[passVeltD][r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineRulesDIRDivnegativerCase1],  

    True,
	Message[LoopRefine::leadinglandau, PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]];

	PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]
  ]
 
];


(* ::Subsection:: *)
(*Part: All*)


(* ::Subsubsection::Closed:: *)
(*A functions*)


(*FeynmanIRespilon = 1/Sqrt[-I \[CurlyEpsilon]] = (-1)^(1/4)/Sqrt[\[CurlyEpsilon]] *)
FeynmanIRepsilon::usage = "FeynmanIRepsilon is an internal parameter for algebraic control over power IR divergences that cannot be rendered finite in dimensional regularization.";


refineA[r_Integer?NonNegative, 0] := 0;
refineA[r_Integer?NonNegative,m0_] := (m0^2)^(r+1)/(2^r (r+1)!) (1/Eps+Log[Mu^2/m0^2]+HarmonicNumber[r+1]);


(*If r<=-1*)
(*Need to figure out how to deal with Log[FeynmanIRepsilon]*)
(*FeynmanIRespilon = (-1)^(1/4)/Sqrt[\[CurlyEpsilon]] *)
refineA[-1, 0] := 0;(*2/Eps+2Log[Mu^2/FeynmanIRepsilon^2];*)
refineA[r_Integer, 0]  := (-1)^(1+r)/2^r (-r-2)! (FeynmanIRepsilon^2)^(-1-r);
refineA[-1,m0_] := 2/Eps+2 Log[Mu^2/m0^2];
refineA[r_Integer,m0_] := (-1)^(1+r)/2^r (-r-2)! (1/m0^2)^(-1-r);


(*Negative r, through O(Eps)*)

(*Need to figure out how to deal with Log[FeynmanIRepsilon], which is non-polynomial in FeynmanIRepsilon*)
refineAorder1[-1, 0] := 0;(*2/Eps+2 Log[Mu^2/FeynmanIRepsilon^2]+Eps (\[Pi]^2/3+Log[Mu^2/FeynmanIRepsilon^2]^2);*)
refineAorder1[r_Integer, 0] /; r<-1 := (-1)^(1+r)/2^r (-r-2)! (FeynmanIRepsilon^2)^(-1-r);
refineAorder1[-1, m0_] := 2/Eps+2 Log[Mu^2/m0^2]+Eps (\[Pi]^2/6+Log[Mu^2/m0^2]^2);
refineAorder1[r_Integer,m0_] := (-1)^(1+r)/2^r (-r-2)! (1/m0^2)^(-1-r)(1+Eps*(HarmonicNumber[-2-r]+Log[Mu^2/m0^2]));


(* ::Subsubsection::Closed:: *)
(*B functions - Positive r*)


(*These are the Passarino-Veltman coefficient function B_ 111...  where r=0*)

refineB[0,n_Integer, 0, 0, 0]       := 0;
refineB[0,n_Integer,s_,m0_,m0_] /; PossibleZeroQ[s-m0^2] := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m0^2]+Sum[1/(idx1+1) 2*Sum[Binomial[n-idx1,2idx2](1/2)^(n-idx1-2idx2) (-(3/4))^idx2,{idx2,0,(n-idx1)/2}],{idx1,0,n}]-+Sum[Binomial[n+1,2idx3+1](1/2)^(n-2idx3) (-(3/4))^idx3,{idx3,0,n/2}](\[Pi]/Sqrt[3]));
refineB[0,n_Integer, 0, 0, m1_]     := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+1/(n+1));
refineB[0,n_Integer, 0, m0_, 0]     := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m0^2]+HarmonicNumber[n+1]);
refineB[0,n_Integer,s_, 0, 0]       := (-1)^n/(n+1) (1/Eps+Log[Mu^2/-s]+1/(n+1)+HarmonicNumber[n+1]);
refineB[0,n_Integer, 0, m0_, m0_]   := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m0^2]);
refineB[0,n_Integer,s_, 0, m1_] /; PossibleZeroQ[s-m1^2] := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+2/(1+n));
refineB[0,n_Integer,s_, m0_, 0] /; PossibleZeroQ[s-m0^2] := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m0^2]+2HarmonicNumber[n+1]);
refineB[0,n_Integer, 0,m0_,m1_]     := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+Sum[1/(idx1+1) (m0^2/(m0^2-m1^2))^(n-idx1),{idx1,0,n}]-(m0^2/(m0^2-m1^2))^(n+1) olog[m0^2,m1^2]);

refineB[0,n_Integer,s_, 0,m1_]      := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+1/(1+n)+Sum[1/(idx1+1) (1-m1^2/s)^(n-idx1),{idx1,0,n}]+(1-m1^2/s)^(n+1) Log[m1^2/(m1^2-s)]);
refineB[0,n_Integer,s_,m0_, 0]      := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m0^2]+HarmonicNumber[n+1]+Sum[1/(idx1+1) (m0^2/s)^(n-idx1),{idx1,0,n}]+(1-(m0^2/s)^(n+1))Log[m0^2/(m0^2-s)]);
refineB[0,n_Integer,s_,m0_,m1_] /; PossibleZeroQ[(m0+m1)^2-s]  := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+Sum[2/(idx1+1) (m0/(m0+m1))^(n-idx1),{idx1,0,n}]-(m0/(m0+m1))^(n+1)*olog[m0^2,m1^2]);
refineB[0,n_Integer,s_,m0_,m1_] /; PossibleZeroQ[(m0-m1)^2-s]  := (-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+Sum[2/(idx1+1) (m0/(m0-m1))^(n-idx1),{idx1,0,n}]-(m0/(m0-m1))^(n+1)*olog[m0^2,m1^2]);
(*refineB[0,n_Integer,s_,m0_,m1_]     := With[{k\[Lambda]=Expand[s^2+m0^4+m1^4-2*s*m0^2-2*s*m1^2-2*m0^2*m1^2]},(-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+Sum[1/(idx1+1) 2Sum[Binomial[n-idx1,2idx2] pow[(s+m0^2-m1^2)/(2s),(n-idx1-2idx2)] (k\[Lambda]/(4s^2))^idx2,{idx2,0,(n-idx1)/2}],{idx1,0,n}]-  Sum[Binomial[n+1,2idx3] pow[(s+m0^2-m1^2)/(2s),(n+1-2idx3)] (k\[Lambda]/(4s^2))^idx3,{idx3,0,(n+1)/2}]olog[m0^2,m1^2]+ Sum[Binomial[n+1,2idx3+1] pow[(s+m0^2-m1^2)/(2s),(n-2idx3)] (k\[Lambda]/(4s^2))^idx3,{idx3,0,n/2}]DiscB[s,m0,m1])];*)
refineB[0,n_Integer,s_,m0_,m1_]     := With[{k\[Lambda]=Kallen\[Lambda][s,m0^2,m1^2]},(-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+Sum[1/(idx1+1) 2Sum[Binomial[n-idx1,2idx2] pow[(s+m0^2-m1^2)/(2s),(n-idx1-2idx2)] (k\[Lambda]/(4s^2))^idx2,{idx2,0,(n-idx1)/2}],{idx1,0,n}]-  Sum[Binomial[n+1,2idx3] pow[(s+m0^2-m1^2)/(2s),(n+1-2idx3)] (k\[Lambda]/(4s^2))^idx3,{idx3,0,(n+1)/2}]olog[m0^2,m1^2]+ Sum[Binomial[n+1,2idx3+1] pow[(s+m0^2-m1^2)/(2s),(n-2idx3)] (k\[Lambda]/(4s^2))^idx3,{idx3,0,n/2}]DiscB[s,m0,m1])];
(*refineB[0,n_Integer,s_,m0_,m1_]     := With[{k\[Lambda]=Kallen\[Lambda][s,m0^2,m1^2]},(-1)^n/(n+1) (1/Eps+Log[Mu^2/m1^2]+Sum[1/(idx1+1) 2Sum[Binomial[n-idx1,2idx2] pow[(s+m0^2-m1^2)/(2s),(n-idx1-2idx2)] (k\[Lambda]/(4s^2))^idx2,{idx2,0,(n-idx1)/2}],{idx1,0,n}]-  Sum[Binomial[n+1,2idx3] pow[(s+m0^2-m1^2)/(2s),(n+1-2idx3)] (k\[Lambda]/(4s^2))^idx3,{idx3,0,(n+1)/2}]olog[m0^2,m1^2]+ Sum[Binomial[n+1,2idx3+1] pow[(s+m0^2-m1^2)/(2s),(n-2idx3)] (k\[Lambda]/(4s^2))^idx3,{idx3,0,n/2}]DiscB[s,m0,m1])];*)


(* All coefficient functions with r!=0 are determined ITERATIVELY *)
refineB[r_Integer?NonNegative,n_Integer,s_,m0_,m1_] := Sum[(-1)^k/(2^r r!) Multinomial[j,k,r-j-k]pow[s,j]pow[-s+m1^2-m0^2,k]pow[m0^2,r-j-k]refineB[0,n+2j+k,s,m0,m1],{j,0,r},{k,0,r-j}]+ Sum[(HarmonicNumber[r](-1)^k)/(2^r r!) Multinomial[j,k,r-j-k]pow[s,j]pow[-s+m1^2-m0^2,k]pow[m0^2,r-j-k]pvBDivUV[0,n+2j+k,s,m0,m1],{j,0,r},{k,0,r-j}];


(* ::Subsubsection::Closed:: *)
(*B functions - Negative r*)


(*  This is the basic integral that can be power-divergent at normal thresholds:
    powerI(r,k,0,0)=(1+Eps HarmonicNumber[-r-1])(Mu^2)^Eps Integrate[x^k/(-i\[CurlyEpsilon])^(Abs[r]+Eps),{x,0,1}]  *)
powerI[r_, k_, 0, 0, sgn_ : 1]:= 1/(k+1) FeynmanIRepsilon^(2*Abs[r]);

(*  This is the basic integral that can be power-divergent at normal thresholds:
    powerI(r,k,0,m1)=(1+Eps HarmonicNumber[-r-1])(Mu^2/m1^2)^Eps Integrate[x^k/(x^2-i\[CurlyEpsilon]/m1^2)^(Abs[r]+Eps),{x,0,1}]  *)
powerI[r_, k_, 0, m1_, sgn_ : 1] :=
	Which[
		k>2Abs[r]-1, 1/(k-2Abs[r]+1),
		k==2Abs[r]-1, -(1/2)(1/Eps+Log[Mu^2/m1^2]+HarmonicNumber[Abs[r]-1]),
		k<2Abs[r]-1, 1/(k-2Abs[r]+1)+(m1 FeynmanIRepsilon)^(2*Abs[r]-k-1) (Gamma[Abs[r]-k/2-1/2] Gamma[(1+k)/2])/(2 Gamma[Abs[r]])
	];

(*powerI(r,k,m0,m1,sgn)=(Mu^2/m0^2)^Eps Integrate[x^k/(x^2-i\[CurlyEpsilon]/m0^2)^(Abs[r]+Eps),{x, sgn*m1/m0, 1}]  *)
(*expression for 'a=-m1/m0 < 0' in my notes. [threshold]*)
powerI[r_,k_,m0_,m1_, -1]:=
	Which[
		k>2Abs[r]-1, 1/(k-2 Abs[r]+1) (1-(-m1/m0)^(k-2 Abs[r]+1)),
		k==2Abs[r]-1, -(1/2)olog[m1^2,m0^2],
		k<2Abs[r]-1, (1-(-m1/m0)^(k-2 Abs[r]+1))/(k-2 Abs[r]+1)+(1+(-1)^k) ((m0 FeynmanIRepsilon)^(2 Abs[r]-k-1) (Gamma[Abs[r]-k/2-1/2] Gamma[(1+k)/2]))/(2 Gamma[Abs[r]])
	];
(*expression for 'a=+m1/m0 > 0' in my notes. [pseudothreshold]*)
powerI[r_,k_,m0_,m1_, +1]:=
	Which[
		k!=2Abs[r]-1, 1/(k-2 Abs[r]+1) (1-(m1/m0)^(k-2 Abs[r]+1)),
		k==2Abs[r]-1, -(1/2)olog[m1^2,m0^2]
	];


(*Needed for the reduction of case 4 of C functions (DetX=DetZ=0) and IR-divergent C functions.*)
(*Algebraic B function (for r=-1)*)

(*Scaleless*)refineB[r_Integer?Negative,n_Integer, 0, 0, 0] := (-1)^(2+r+n)/2^r (-r-1)! powerI[r, n, 0, 0];

refineB[-1, 0, 0, 0, m1_]            := 2/m1^2 (1/Eps+Log[Mu^2/m1^2]);
refineB[-1,n_Integer, 0, 0, m1_]     := 2(-1)^(n+1)*1/(m1^2 n);
refineB[-1,n_Integer, 0, m0_, 0]     := 2(-1)^n*1/m0^2 (1/Eps+Log[Mu^2/m0^2]+HarmonicNumber[n]);
refineB[-1, 0, s_, 0, 0]             := -4/s (1/Eps+Log[Mu^2/-s]);
refineB[-1,n_Integer, s_, 0, 0]      := 2(-1)^(n+1)*1/s (1/Eps+Log[Mu^2/-s]+HarmonicNumber[n-1]);

(*Threshold*) refineB[r_Integer?Negative, n_Integer, Except[0,s_], 0, Except[0,m1_]] /; PossibleZeroQ[s-m1^2]:=(-1)^(2+r+n)/2^r Gamma[-r] 1/m1^(2Abs[r]) powerI[r,n,0,m1];
(*Threshold*) refineB[r_Integer?Negative, n_Integer, Except[0,s_], Except[0,m0_], 0]  /; PossibleZeroQ[s-m0^2] := Sum[Binomial[n,k](-1)^n refineB[r,k,s,0,m0],{k,0,n}];

(*Pseudothreshold*) refineB[r_Integer?Negative, n_Integer, 0, Except[0,m0_], Except[0,m1_]] /; PossibleZeroQ[m0-m1]:= ((-1)^(2+n+r) 2^-r)/(1+n) (-1-r)! (1/m0^2)^-r;
refineB[r_Integer?Negative,n_Integer, 0,Except[0,m0_],Except[0,m1_]]     := ((-1)^(2+r+n) (-r-1)!)/(2^r (m0^2)^-r) (m0^2/(m0^2-m1^2))^(n+1) Sum[If[k!=-r-1,(-1)^k/(-r-k-1) Binomial[n,k]((m0^2/m1^2)^(-r-k-1)-1),(-1)^(-r-1) Binomial[n,-r-1] olog[m0^2,m1^2]],{k,0,n}];
refineB[-1, 0, s_, 0,m1_]            := -2/(s-m1^2) (1/Eps+Log[Mu^2/m1^2]+2*Log[m1^2/(-s+m1^2)]);
refineB[-1,n_Integer,s_, 0,m1_]      := 2(-1)^(n+1)*With[{x=(s-m1^2)/s},1/s (Sum[x^(n-2-k)/(k+1),{k,0,n-2}]+x^(n-1) Log[m1^2/(-s+m1^2)])];
refineB[-1,n_Integer,s_,m0_, 0]      := 2(-1)^n*1/(s-m0^2) (-(1/Eps)-Log[Mu^2/(-s+m0^2)]+Sum[(m0^2/s)^(n-1-k)/(k+1),{k,0,n-1}]-(m0^2/s)^n Log[m0^2/(-s+m0^2)]-HarmonicNumber[n]);

(*Threshold*) refineB[r_Integer?Negative, n_Integer,Except[0,s_],Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[s-(m0+m1)^2] := (-1)^(2+r+n) Gamma[-r]/(2^r (m0^2)^-r) (m0/(m0+m1))^(n+1) (Sum[Binomial[n,k](-1)^k powerI[r,k,m0,m1,-1],{k,0,n}]);
(*Pseudothreshold*)refineB[r_Integer?Negative, n_Integer,Except[0,s_],Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[s-(m0-m1)^2] := (-1)^(2+r+n) Gamma[-r]/(2^r (m0^2)^-r) (m0/(m0-m1))^(n+1) (Sum[Binomial[n,k](-1)^k powerI[r,k,m0,m1,1],{k,0,n}]);

(*General case*)
refineB[-1,n_Integer,s_,m0_,m1_]     := 2(-1)^(n+1)*1/s*With[{a=(s+m0^2-m1^2)/(2s),b=(Kallen\[Lambda][s,m0^2,m1^2]/(4 s^2))},Sum[1/(k+1) Sum[Binomial[n-1-k,2j+1] pow[a,n-k-2j-2] pow[b,j],{j,0,Floor[(n-1-k)/2]}],{k,0,n-1}]+1/2 Sum[Binomial[n,2k-1] pow[a,n-2k+1] pow[b,k-1] olog[m1^2,m0^2],{k,1,Floor[(n+1)/2]}]+1/2 Sum[Binomial[n,2k]pow[a,n-2k] pow[b,k]*4 s^2/Kallen\[Lambda][s,m0^2,m1^2]* DiscB[s,m0,m1],{k,0,n/2}]];


(*Reduction for r <= -2 Det(X)!=0;*)
refineB[r_Integer,n_Integer,s_,m0_,m1_] := 1/-Kallen\[Lambda][s,m0^2,m1^2] (2s(2(3-2Eps+2r+n)refineB[r+1,n,s,m0,m1]-(-1)^n refineA[r,m1]) + (-s+m1^2-m0^2)*(KroneckerDelta[n,0]refineA[r,m0]-(-1)^n refineA[r,m1]-Switch[n,0,0,_,2n refineB[r+1,n-1,s,m0,m1]]));


(* ::Subsubsection::Closed:: *)
(*B functions - Negative r through O(\[Epsilon])*)


(*Needed for the reduction of IR-divergent C functions with negative r*)
(*Scaleless*)refineBorder1[r_Integer?Negative,n_Integer, 0, 0, 0] := (-1)^(2+r+n )/2^r (-r-1)!/(n+1) FeynmanIRepsilon^(2*Abs[r]) (*+ Eps If[FeynmanIRepsilon=!=0, Missing, 0]*);


refineBorder1[r_Integer?Negative, n_Integer, 0, 0, Except[0,m1_]]  := 
  ((-1)^(2+r+n) (-r-1)!)/(2^r (m1^2)^-r)*
	Which[
		n+r>-1,  1/(1+n+r)+((1+(1+n+r) HarmonicNumber[-1-r]+(1+n+r) Log[Mu^2/m1^2]) Eps)/(1+n+r)^2,
		n+r==-1,  -(1/Eps)+(-HarmonicNumber[-1-r]-Log[Mu^2/m1^2])+1/6 (-\[Pi]^2/2-3 HarmonicNumber[-1-r]^2+3 HarmonicNumber[-1-r,2]-6 HarmonicNumber[-1-r] Log[Mu^2/m1^2]-3 Log[Mu^2/m1^2]^2) Eps,
		True,  1/(1+n+r)+(m1^2)^(-1-n-r) FeynmanIRepsilon^(2(-1-n-r)) (n!(-r-n-2)!)/(-r-1)!+1/(1+n+r)^2*((1+(1+n+r) HarmonicNumber[-1-r]+(1+n+r) Log[Mu^2/m1^2](* + If[FeynmanIRepsilon=!=0, Missing, 0]*)) Eps)
	];
refineBorder1[r_Integer?Negative, n_Integer, 0, Except[0,m0_], 0]  := Sum[Binomial[n,k](-1)^n refineBorder1[r,k,0,0,m0],{k,0,n}];


refineBorder1[-1, n_, s_, 0,  0]  := If[n==0,-(4/(s Eps))-4/s Log[-(Mu^2/s)]-2 Eps/s Log[-(Mu^2/s)]^2 + \[Pi]^2 Eps/(3 s), (2(-1)^n)/s (-(1/Eps)-HarmonicNumber[-1+n]-Log[-(Mu^2/s)]+1/2 Eps (\[Pi]^2/6-HarmonicNumber[-1+n]^2-3 HarmonicNumber[-1+n,2]-2 HarmonicNumber[-1+n] Log[-(Mu^2/s)]-Log[-(Mu^2/s)]^2))];


(*Threshold*) refineBorder1[r_Integer?Negative, n_Integer, Except[0,s_], 0, Except[0,m1_]] /; PossibleZeroQ[s-m1^2] :=
	(-1)^(2+r+n)/(2^r (m1^2)^-r) (-r-1)!*
	Which[
		n>-2r-1,1/(n+2r+1)+Eps 1/(n+2r+1) (2/(n+2r+1)+HarmonicNumber[-r-1]+Log[Mu^2/m1^2]),
		n==-2r-1,-(1/(2Eps))-1/2 Log[Mu^2/m1^2]-1/2 HarmonicNumber[-r-1]-1/12 Eps(\[Pi]^2/2+3(HarmonicNumber[-r-1])^2-3HarmonicNumber[-r-1,2])-1/2 Eps HarmonicNumber[-r-1]Log[Mu^2/m1^2]-1/4 Eps Log[Mu^2/m1^2]^2,
		True,1/(n+2r+1)+(m1^(-n+2 Abs[r]-1) FeynmanIRepsilon^(-n+2 Abs[r]-1) (2^(1-2 Abs[r]) \[Pi] (2 (-1+Abs[r]-n/2))! n!))/((-1+Abs[r])! (-1+Abs[r]-n/2)! (n/2)!)+Eps/(n+2r+1) (2/(n+2r+1)(*+If[FeynmanIRepsilon=!=0, Missing, 0]*)+HarmonicNumber[-r-1]+Log[Mu^2/m1^2])
	];

refineBorder1[r_Integer?Negative, n_Integer, Except[0,s_], Except[0,m0_], 0] /; PossibleZeroQ[s-m0^2] := Sum[Binomial[n,k](-1)^n refineBorder1[r,k,s,0,m0],{k,0,n}];


(*Pseudothreshold*) refineBorder1[r_Integer?Negative,n_Integer,0,Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[m0-m1] := (-1)^(2+r+n)/(2^r (m0^2)^-r) (-r-1)!/(n+1) (1+Eps*(HarmonicNumber[-r-1]+Log[Mu^2/m0^2]));


refineBorder1[r_Integer?Negative, n_Integer, 0, Except[0,m0_], Except[0,m1_]] := 
	With[{
		orderZero = Sum[If[k!=-r-1,(-1)^k/(-r-k-1) Binomial[n,k]((m0^2/m1^2)^(-r-k-1)-1),(-1)^(-r-1) Binomial[n,-r-1] olog[m0^2,m1^2]],{k,0,n}], 
		orderOne = Sum[If[k!=-r-1,(-1)^k/(-r-k-1)^2 Binomial[n,k](1+(m0^2/m1^2)^(-r-k-1) (-1+(-r-k-1)olog[m0^2,m1^2])),(-1)^(-r-1) Binomial[n,-r-1] 1/2 (olog[m0^2,m1^2])^2],{k,0,n}]},
		((-1)^(2+r+n) (-r-1)!)/(2^r (m0^2)^-r) (m0^2/(m0^2-m1^2))^(n+1) (orderZero + Eps(HarmonicNumber[-r-1]+Log[Mu^2/m0^2])orderZero+Eps orderOne)
	];


refineBorder1[-1, 0, Except[0,s_], 0, Except[0,m1_]] := 2/((m1^2-s) Eps)+2/(m1^2-s) (2 Log[m1^2/(m1^2-s)]+Log[Mu^2/m1^2])+Eps/(m1^2-s) (\[Pi]^2/6+2 Log[m1^2/(m1^2-s)]^2+4 Log[m1^2/(m1^2-s)] Log[Mu^2/m1^2]+ Log[Mu^2/m1^2]^2-4 PolyLog[2,s/(-m1^2+s)]) ;
refineBorder1[-1, n_Integer, Except[0,s_], 0, Except[0,m1_]] (*n!=0*) := 
	With[{
		orderZero=1/s ((-m1^2+s)/s)^(-1+n) Log[m1^2/(m1^2-s)]+1/s Sum[((-m1^2+s)/s)^(-2-k+n)/(1+k),{k,0,-2+n}],
		orderOne=Sum[((-1)^(k+n) ((m1^2-s)/s)^(-1-k+n))/(k^2 s),{k,1,-1+n}]+Sum[((-1)^(-1-k+n) (1-(m1^2/(m1^2-s))^k) ((m1^2-s)/s)^n Binomial[-1+n,k])/(k^2 (m1^2-s)),{k,1,-1+n}]+Sum[((-1)^(-1-k+n) ((m1^2-s)/s)^n Binomial[-1+n,k] (-(m1^2/(m1^2-s))^k Log[Mu^2/m1^2]+Log[Mu^2/(m1^2-s)]))/(k (m1^2-s)),{k,1,-1+n}]+1/2 (-1)^(1+n) (m1^2-s)^(-1+n) s^-n (Log[Mu^2/m1^2]^2-Log[Mu^2/(m1^2-s)]^2)+((-1)^(1+n) ((m1^2-s)/s)^(-1+n) PolyLog[2,s/(s-m1^2)])/s},
		2 (-1)^(1+n)  (orderZero - Eps orderOne)
	];
refineBorder1[-1, n_Integer, Except[0,s_], Except[0,m0_], 0] := Sum[Binomial[n,k](-1)^n refineBorder1[-1,k,s,0,m0],{k,0,n}];


(*Threshold*) refineBorder1[r_?Negative,n_,Except[0,s_],Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[s-(m0+m1)^2] := 
	With[{
		orderZero = Sum[If[k!=2Abs[r]-1,Binomial[n,k] (-1)^k/(k-2 Abs[r]+1) (1-(-(m1/m0))^(k-2Abs[r]+1)), 1/2 Binomial[n,2 Abs[r]-1]olog[m1^2,m0^2]],{k,0,n}] + Sum[Binomial[n,k] (-1)^k ((1+(-1)^k) (m0^(-k+2 Abs[r]-1) FeynmanIRepsilon^(-k+2 Abs[r]-1) (2^(1-2 Abs[r]) \[Pi] (2 (-1+Abs[r]-k/2))! k!)))/((-1+Abs[r])! (-1+Abs[r]-k/2)! (k/2)!),{k,0,2Abs[r]-2}],
		orderOne = Sum[If[k!=2Abs[r]-1,Binomial[n,k] (-1)^k/(k-2 Abs[r]+1)^2 (2+(-m1/m0)^(k-2Abs[r]+1) (-2+(k-2Abs[r]+1)olog[m1^2,m0^2])),-(1/4) Binomial[n,2Abs[r]-1] olog[m1^2,m0^2]^2],{k,0,n}] (*+ If[FeynmanIRepsilon=!=0,Sum[Binomial[n,k] (-1)^k Missing,{k,0,2Abs[r]-2}],0]*)},

		(-1)^(2+r+n)(-r-1)!/(2^r (m0^2)^-r) (m0/(m0+m1))^(n+1) (orderZero + Eps(HarmonicNumber[-r-1]+Log[Mu^2/m0^2])orderZero+Eps orderOne)
	];
(*Pseudothreshold*) refineBorder1[r_?Negative,n_,Except[0,s_],Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[s-(m0-m1)^2] := 
	With[{
		orderZero = Sum[If[k!=2Abs[r]-1,Binomial[n,k] (-1)^k/(k-2Abs[r]+1) (1-(m1/m0)^(k-2Abs[r]+1)), 1/2 Binomial[n,2Abs[r]-1]olog[m1^2,m0^2]],{k,0,n}], 
		orderOne = Sum[If[k!=2Abs[r]-1, Binomial[n,k] (-1)^k/(k-2Abs[r]+1)^2 (2+(m1/m0)^(k-2Abs[r]+1) (-2+(k-2Abs[r]+1)olog[m1^2,m0^2])), -(1/4)Binomial[n,2Abs[r]-1]olog[m1^2,m0^2]^2],{k,0,n}]},
		(-1)^(2+r+n)(-r-1)!/(2^r (m0^2)^-r) (m0/(m0-m1))^(n+1) (orderZero + Eps(HarmonicNumber[-r-1]+Log[Mu^2/m0^2])orderZero+Eps orderOne)
	];


(*General case for r=-1, contains ScalarC0IR6*)
refineBorder1[-1,0,s_,m0_,m1_] := -((4 s DiscB[s,m0,m1])/Kallen\[Lambda][m0^2,m1^2,s]) + Eps((2 s DiscB[s,m0,m1])/Kallen\[Lambda][m0^2,m1^2,s] (-Log[Mu^2/m0^2]-Log[Mu^2/m1^2])-4*ScalarC0IR6[s,m0,m1]);

(*General case for r \[LessEqual] -2, but n positive*)
refineBorder1[r_Integer,n_Integer?Positive, Except[0,s_], Except[0,m0_], Except[0,m1_]] := 1/(2s)*(KroneckerDelta[n,1]refineAorder1[r,m0]+(-1)^n * refineAorder1[r,m1] - (s-m1^2+m0^2)refineBorder1[r,n-1,s,m0,m1] - Switch[(n-1),0,0,_,2(n-1)refineBorder1[r+1,n-2,s,m0,m1]]);
(*Reduction for r <= -2, for n=0, and requires Det(X)!=0 ;*)
refineBorder1[r_Integer,n_Integer?NonNegative, s_, m0_, m1_] /; r<0 := 1/-Kallen\[Lambda][s,m0^2,m1^2] (2s(2(3-2Eps+2r+n)refineBorder1[r+1,n,s,m0,m1]-(-1)^n refineAorder1[r,m1]) + (-s+m1^2-m0^2)*(KroneckerDelta[n,0]refineAorder1[r,m0]-(-1)^n refineAorder1[r,m1]-Switch[n,0,0,_,2n refineBorder1[r+1,n-1,s,m0,m1]]));


(* ::Subsubsection::Closed:: *)
(*C functions*)


(*Shifted B-functions; due to missing unshifted propagator; identical to pvBshift, but with immediate replacement*)
pvBs[r_Integer,n1_Integer,n2_Integer,q_,m1_,m2_]/;n1>n2 := pvBs[r,n2,n1,q,m2,m1];
pvBs[r_Integer,n1_Integer,n2_Integer,q_,m1_,m2_]        := (-1)^n1 Sum[Binomial[n1,idx]refineB[r,n2+idx,q,m1,m2],{idx,0,n1}];


(*Canonical ordering*)
(*PVC[r_Integer,n1_Integer,n2_Integer,p1_,q_,p2_,m0_,m1_,m2_]/;n2>n1 := PVC[r,n2,n1,p2,q,p1,m0,m2,m1];*)


(*Define C-function reduction rules: 6 of them in total*)
Block[{
	n={n1,n2},
	f={p1-m1^2+m0^2,p2-m2^2+m0^2},

	gramZ={{p1,          -(q-p1-p2)/2},
    	  {-(q-p1-p2)/2,  p2}},

	detZ=-Kallen\[Lambda][p1,p2,q]/4,

	adjZ={{p2, (q-p1-p2)/2},
    	 {(q-p1-p2)/2, p1}},

	mtxX, detX, adjX0, adjXij,
	pinchB, missBDivUV,
	not,
	i,j,k,l,nn,mm},

	not[var_]=Which[var==1,2,var==2,1];

	mtxX=Expand[{{2 m0^2,f[[1]],f[[2]]},{f[[1]],2 p1,-(q-p1-p2)},{f[[2]],-(q-p1-p2),2 p2}}];
	detX=Expand[Det[mtxX]];
	
	adjX0=Expand[Table[Sum[adjZ[[j,k]]f[[k]],{k,1,2}],{j,1,2}]]; (*up to a constant: -2*)
	adjXij=Table[4*m0^2 adjZ[[i,j]]+Sum[(KroneckerDelta[i,mm]KroneckerDelta[nn,j]-KroneckerDelta[i,j]KroneckerDelta[nn,mm])f[[nn]] f[[mm]],{nn,1,2},{mm,1,2}],{i,1,2},{j,1,2}];

	(*Passarino Veltman functions with missing propagators, and their divergent parts*)
	pinchB[r_,n1_]     = {refineB[r,n1,p2,m0,m2],refineB[r,n1,p1,m0,m1]};
	missBDivUV[r_,n1_] = {pvBDivUV[r,n1,p2,m0,m2],pvBDivUV[r,n1,p1,m0,m1]};


	(********Case6: All elements of gramZ is zero, AND f is zero********)
	refineRulesCcase6={
	  passVeltC[r_?Negative,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_](*/;r<0*) -> 1/m0^2(2(2-Eps+n1+n2+r)passVeltC[r+1,n1,n2,p1,q,p2,m0,m1,m2]-pvBs[r,n1,n2,q,m1,m2]),
	  passVeltC[0, n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/m0^2 ((4+2(n1+n2))passVeltC[1,n1,n2,p1,q,p2,m0,m1,m2]-pvBs[0,n1,n2,q,m1,m2]-2 pvCDivUV[1,n1,n2,p1,q,p2,m0,m1,m2]),
	  passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> -(1/(2(n1+1)))pvBs[r-1,n1+1,n2,q,m1,m2]
	};

	(********Case5: All elements of gramZ is zero, but f nonzero********)
	refineRulesCcase5a=Table[passVeltC[r_?NonPositive, n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_](*/;r<=0*) -> 1/f[[k]] (-2n[[k]]passVeltC[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],p1,q,p2,m0,m1,m2]+KroneckerDelta[n[[k]],0]pinchB[r,n[[not[k]]]][[k]]-pvBs[r,n1,n2,q,m1,m2]),{k,1,2}];
	refineRulesCcase5b=passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/(2+2r+2n1+2n2)*(pvBs[r-1,n1,n2,q,m1,m2]+m0^2 passVeltC[r-1,n1,n2,p1,q,p2,m0,m1,m2]) + 1/(1+r+n1+n2)*pvCDivUV[r,n1,n2,p1,q,p2,m0,m1,m2];

	(********Case4: Gram determinant and Cayley vectors vanishing; internal masses non-zero********)
	refineRulesCcase4={passVeltC[r_,n1_,n2_,p_,p_,0,m0_,m1_,m0_]:>(-1)^(3+n1)/(2(n2+1)) Sum[Binomial[n1,k]refineB[r-1,n2+k+1,p,m1,m0],{k,0,n1}],
	passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] :> With[{\[Alpha]=(-q+p1+p2)/(2p2)},(-1)^(n1+n2)/2 Sum[Binomial[n2,j]pow[\[Alpha],n2-j]((n1!(n2-j)!)/(n1+n2-j+1)! Sum[Binomial[j,k](-1)^(j-k) pow[\[Alpha],j-k](-1)^k refineB[r-1,k,p2,m0,m2],{k,0,j}]+Sum[Pochhammer[-n1,k]/((n2-j+k+1)k!) ((1-\[Alpha])^(j+1) (-1)^(n2+k) refineB[r-1,n2+k+1,q,m1,m2]+(-1)^(j+1) (\[Alpha])^(j+1) (-1)^(n2+k+1) refineB[r-1,n2+k+1,p1,m1,m0]),{k,0,n1}]),{j,0,n2}]]};

	(********Case3: Gram determinant vanishing, but Cayley vectors X non-vanishing********)
	refineRulesCcase3a=
	Table[
	  passVeltC[r_?Positive,0,0,p1_,q_,p2_,m0_,m1_,m2_] -> 
	    1/(1+2r)*(pvBs[r-1,0,0,q,m1,m2]+m0^2 passVeltC[r-1,0,0,p1,q,p2,m0,m1,m2])+
	    1/(2 (1+2r))*1/adjZ[[k,l]] Sum[(KroneckerDelta[k,mm]KroneckerDelta[nn,l]-KroneckerDelta[k,l]KroneckerDelta[mm,nn])(Sum[gramZ[[nn,j]]((1-KroneckerDelta[mm,j])pinchB[r-1,1][[mm]]-pvBs[r-1,KroneckerDelta[j,1],KroneckerDelta[j,2],q,m1,m2]),{j,1,2}]+1/2 f[[mm]](-pinchB[r-1,0][[nn]]+pvBs[r-1,0,0,q,m1,m2]+f[[nn]]passVeltC[r-1,0,0,p1,q,p2,m0,m1,m2])),{nn,1,2},{mm,1,2}]+
	    +2/(1+2r)pvCDivUV[r,0,0,p1,q,p2,m0,m1,m2],{k,1,2},{l,1,2}];
	refineRulesCcase3b=
	Table[
	  passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/adjX0[[j]]*
	    Sum[adjZ[[j,k]](KroneckerDelta[n[[k]],0]pinchB[r,n[[not[k]]]][[k]]-pvBs[r,n1,n2,q,m1,m2]-
	    2n[[k]]passVeltC[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],p1,q,p2,m0,m1,m2]),{k,1,2}],
	{j,1,2}];

	(********Reduction of triangle 1,4,5,6********)

	(*In this case, p1=q, q=p2, m2=m0 or (p1,m1)<-->(p2,m2).*)
	refineRulesCtriangle6={
	  (*Permuted*)
	  passVeltC[r_,n1_,n2_,p1_,s_,p2_,0,m2_,m0_] /; PossibleZeroQ[p1-m2^2] && PossibleZeroQ[p2-m0^2] && 2r+n1+n2 != 0 :> If[2r+n1+n2<0,(-1)^(r+n1+n2+3)/2^r * FeynmanIRepsilon^(-2r-n1-n2)*Gamma[(n1+n2+2)/2]*Gamma[-(2r+n1+n2)/2](* * PVB*),0] + (-1)^n2/2 1/(n1+n2+2r) (1+(2Eps)/(n1+n2+2r))Sum[Binomial[n2,k]refineB[r-1,n1+k,s,m0,m2],{k,0,n2}],
	  passVeltC[r_,n1_,n2_,p1_,s_,p2_,0,m2_,m0_] /; PossibleZeroQ[p1-m2^2] && PossibleZeroQ[p2-m0^2] :> (-1)^n2/2 * 1/(-2Eps) Sum[Binomial[n2,k]refineBorder1[r-1,n1+k,s,m0,m2],{k,0,n2}],

	  (*Nonpermuted*)
	  passVeltC[r_?Positive, n1_,n2_,p1_,q_,s_,m0_,0,m2_]|passVeltC[r_?Positive, n2_,n1_,s_,q_,p1_,m0_,m2_,0] /;PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] :> (-1)^n1/2 (n1!(n2+2r-1)!)/(n1+n2+2r)! (1+2Eps(HarmonicNumber[n1+n2+2r]-HarmonicNumber[n2+2r-1]))refineB[r-1,n2,s,m0,m2],
	  passVeltC[r_(*?NonPositive*), n1_,n2_,p1_,q_,s_,m0_,0,m2_]|passVeltC[r_, n2_,n1_,s_,q_,p1_,m0_,m2_,0] /;PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] :> 
		Which[
			2r+n2>0&&2r+n1+n2+1>0, -((n1! (-1+n2+2 r)! )/(n1+n2+2 r)!)(-1+2 Eps (HarmonicNumber[-1+n2+2 r]- HarmonicNumber[n1+n2+2 r])) *(-1)^n1/2 * refineB[r-1,n2,s,m0,m2],
			2r+n2<=0&&2r+n1+n2+1<=0, + (((-1)^n1) n1! (-1-n1-n2-2 r)! )/(-n2-2 r)! (-1+2 Eps(HarmonicNumber[-n2-2 r]-HarmonicNumber[-1-n1-n2-2 r])) * (-1)^n1/2 * refineB[r-1,n2,s,m0,m2],
			2r+n2<=0&&2r+n1+n2+1>0, - (((-1)^(n2+2 r) n1!)/(2 Eps (-n2-2 r)! (n1+n2+2 r)!)) (1+2Eps (-HarmonicNumber[-n2-2 r]+HarmonicNumber[n1+n2+2 r])+2 Eps^2 (HarmonicNumber[-n2-2 r]^2-2 HarmonicNumber[-n2-2 r] HarmonicNumber[n1+n2+2 r]+HarmonicNumber[n1+n2+2 r]^2+HarmonicNumber[-n2-2 r,2]+HarmonicNumber[n1+n2+2 r,2])) * (-1)^n1/2 * refineBorder1[r-1,n2,s,m0,m2]
		  ]
	};

	(********Reduction of triangle 2,3********)
	refineRulesCtriangle3 = {
	  (*Permuted*)
	  passVeltC[r_?Positive,n1_,n2_,p1_,0,p2_,m0_,0,0] :> Sum[(-1)^(n2)*(p1-p2)^(-1-n1-tdx)*Multinomial[sdx, n2 - sdx - tdx, tdx]*(Sum[-((1/(2*(n1+r+tdx)!))*(Binomial[1+n1+tdx,k]*(-1+r)!*(n1+tdx)!*pow[p2, k]*pow[-m0^2+p2, 1-k+n1+tdx]*(refineB[-1+r, k+sdx, p2, 0, m0]+(-HarmonicNumber[-1+r]+HarmonicNumber[n1+r+tdx])*pvBDivUV[-1+r, k+sdx, p2, 0, m0]))), {k, 0, 1+n1+tdx}]+Sum[(1/(2*(j+r)))*((-1)^j*Binomial[1+j, l]*Multinomial[j, k, -j-k+n1+tdx]*pow[p1, l]*pow[-m0^2+p1, 1+j-l]*pow[p2, k]*pow[-m0^2+p2, -j-k+n1+tdx]*(refineB[-1+r, k+l+sdx, p1, 0, m0] + pvBDivUV[-1+r, k+l+sdx, p1, 0, m0]/(j + r))), {j, 0, n1 + tdx}, {k, 0, -j+n1+tdx}, {l, 0, 1 + j}]), {sdx, 0, n2}, {tdx, 0, n2 - sdx}],

	  passVeltC[r_,n1_,n2_,p1_,0,p2_,m0_,0,0] :> 
		With[{
		  gammaSeries=
			If[#2+1+#1>0,  (-1)^(1+#1)/((-#1)! (#2+#1)! Eps)+((-1)^#1 (HarmonicNumber[-#1]-HarmonicNumber[#2+#1]))/((-#1)! (#2+#1)!)-1/(2 ((-#1)! (#2+#1)!)) ((-1)^#1 (HarmonicNumber[-#1]^2-2 HarmonicNumber[-#1] HarmonicNumber[#2+#1]+HarmonicNumber[#2+#1]^2+HarmonicNumber[-#1,2]+HarmonicNumber[#2+#1,2])) Eps,
			  ((-1)^(1+#2) (-1-#2-#1)!)/(-#1)!+1/(-#1)! (-1)^#2 (-1-#2-#1)! (-HarmonicNumber[-1-#2-#1]+HarmonicNumber[-#1]) Eps]&,
		  fracSeries=
			If[#1+#2!=0,  (1/(#1+#2)+Eps/(#1+#2)^2),  -1/Eps]&},
			Sum[(-1)^n2*(p1-p2)^(-1-n1-tdx)*Multinomial[sdx, n2-sdx-tdx, tdx]*(Sum[(-(1/2))*Binomial[1+n1+tdx, k]*(n1+tdx)!*gammaSeries[r, n1+tdx]*refineBorder1[-1+r, k+sdx, p2, 0, m0]*pow[p2, k]*pow[-m0^2+p2, 1-k+n1+tdx], {k, 0, 1+n1+tdx}]+Sum[(1/2)*(-1)^j*Binomial[1+j, l]*fracSeries[r, j]*Multinomial[j, k, -j-k+n1+tdx]*refineBorder1[-1+r, k+l+sdx, p1, 0, m0]*pow[p1, l]*pow[-m0^2+p1, 1+j-l]*pow[p2, k]*pow[-m0^2 + p2, -j-k+n1+tdx], {j, 0, n1+tdx}, {k, 0, -j+n1+tdx}, {l, 0, 1 + j}]), {sdx, 0, n2},{tdx, 0, n2 - sdx}]
		],

	  (*Nonpermuted*)
	  passVeltC[r_?Positive,n1_,n2_,0,q_,p2_,0,0,m2_]|passVeltC[r_?Positive,n2_,n1_,p2_,q_,0,0,m2_,0] :> 
		1/(q-p2)^(n1+1) (Sum[-(n1!/2) (r-1)!/(r+n1)! Binomial[n1+1,k]pow[p2,k]pow[p2-m2^2,n1+1-k](refineB[r-1,n2+k,p2,0,m2]+(HarmonicNumber[r+n1]-HarmonicNumber[r-1])pvBDivUV[r-1,n2+k,p2,0,m2]),{k,0,n1+1}]+Sum[(-1)^j/(2(r+j)) Multinomial[j,k,n1-j-k]Binomial[j+1,l]pow[p2,k]pow[q,l]pow[p2-m2^2,n1-j-k]pow[q-m2^2,j+1-l](refineB[r-1,n2+k+l,q,0,m2]+1/(r+j)pvBDivUV[r-1,n2+k+l,q,0,m2]),{j,0,n1},{k,0,n1-j},{l,0,j+1}]),

	  passVeltC[r_,n1_,n2_,0,q_,p2_,0,0,m2_]|passVeltC[r_,n2_,n1_,p2_,q_,0,0,m2_,0] :> 
		With[{
		  gammaSeries=
			If[#2+1+#1>0,  (-1)^(1+#1)/((-#1)! (#2+#1)! Eps)+((-1)^#1 (HarmonicNumber[-#1]-HarmonicNumber[#2+#1]))/((-#1)! (#2+#1)!)-1/(2 ((-#1)! (#2+#1)!)) ((-1)^#1 (HarmonicNumber[-#1]^2-2 HarmonicNumber[-#1] HarmonicNumber[#2+#1]+HarmonicNumber[#2+#1]^2+HarmonicNumber[-#1,2]+HarmonicNumber[#2+#1,2])) Eps,
			  ((-1)^(1+#2) (-1-#2-#1)!)/(-#1)!+1/(-#1)! (-1)^#2 (-1-#2-#1)! (-HarmonicNumber[-1-#2-#1]+HarmonicNumber[-#1]) Eps]&,
		  fracSeries=
			If[#1+#2!=0,  (1/(#1+#2)+Eps/(#1+#2)^2),  -1/Eps]&},
			1/(q-p2)^(n1+1) (Sum[-(n1!/2)*gammaSeries[r,n1]*Binomial[n1+1,k]pow[p2,k]pow[p2-m2^2,n1+1-k]refineBorder1[r-1,n2+k,p2,0,m2],{k,0,n1+1}]+ Sum[(-1)^j/2 fracSeries[r,j]Multinomial[j,k,n1-j-k]Binomial[j+1,l]pow[p2,k]pow[q,l]pow[p2-m2^2,n1-j-k]pow[q-m2^2,j+1-l]refineBorder1[r-1,n2+k+l,q,0,m2],{j,0,n1},{k,0,n1-j},{l,0,j+1}])
		]
	};

	(********Case1: Gram determinant non-vanishing [most general] ********)
	(*In this case, PVC[n1,n2]/;n2>n1=PVC[n2,n1] is used.  See refineC function.*)
	refineRulesCcase1={
	  passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_]/; n2>n1 -> passVeltC[r,n2,n1,p2,q,p1,m0,m2,m1],
	  passVeltC[r_?Positive,0,0,p1_,q_,p2_,m0_,m1_,m2_] -> 
	    1/(4r)*(pvBs[r-1,0,0,q,m1,m2]+2m0^2 passVeltC[r-1,0,0,p1,q,p2,m0,m1,m2]+f[[1]] passVeltC[r-1,1,0,p1,q,p2,m0,m1,m2]+f[[2]] passVeltC[r-1,0,1,p1,q,p2,m0,m1,m2]) +
	    1/r*(pvCDivUV[r,0,0,p1,q,p2,m0,m1,m2]),
	  passVeltC[r_,n1_?Positive,n2_,p1_,q_,p2_,m0_,m1_,m2_] ->
	    1/(2*detZ) Sum[adjZ[[1,j]]*(If[n[[j]]-KroneckerDelta[1,j]==0,Evaluate[pinchB[r,n[[not[j]]]-KroneckerDelta[not[j],1]][[j]]],0]-
	    pvBs[r,n1-1,n2,q,m1,m2]-f[[j]]passVeltC[r,n1-1,n2,p1,q,p2,m0,m1,m2]-If[n[[j]]-KroneckerDelta[1,j]==0,0,Evaluate[2(n[[j]]-KroneckerDelta[1,j])passVeltC[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,p2,m0,m1,m2]]]),{j,1,2}]
	};

	(****Reduction formulae for negative rank r<0*****)
	refineRulesCnegativer = Prepend[refineRulesCcase1, passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] /; r<0 -> 1/detX * (4*detZ*(2(2-2*Eps+n1+n2+2r)*passVeltC[r+1,n1,n2,p1,q,p2,m0,m1,m2]-pvBs[r,n1,n2,q,m1,m2]) + Sum[-2*adjX0[[j]]*(KroneckerDelta[n[[j]],0]*pinchB[r,n[[not[j]]]][[j]] - pvBs[r,n1,n2,q,m1,m2] - 2*n[[j]]*passVeltC[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,p2,m0,m1,m2]),{j,1,2}])];
];


refineC[r_Integer,n1_Integer,n2_Integer,p1_,q_,p2_,m0_,m1_,m2_] :=
  Module[{
    f={p1-m1^2+m0^2,p2-m2^2+m0^2},
    gramZ={{p1, -(q-p1-p2)/2},{-(q-p1-p2)/2, p2}},
    adjZ={{p2, (q-p1-p2)/2},{(q-p1-p2)/2, p1}},
	Xij,
    adjX0,adjXij,
    i,j,k,m,n},

  Xij={{m0^2,f[[1]]/2,f[[2]]/2},{f[[1]]/2,p1,-(q-p1-p2)/2},{f[[2]]/2,-(q-p1-p2)/2,p2}};
  adjX0=Table[Sum[adjZ[[j,k]]f[[k]],{k,1,2}],{j,1,2}]; (*up to a constant: -1*)
  adjXij=Table[4m0^2 adjZ[[i,j]]+Sum[(KroneckerDelta[i,m]KroneckerDelta[n,j]-KroneckerDelta[i,j]KroneckerDelta[n,m])f[[n]] f[[m]],{n,1,2},{m,1,2}],{i,1,2},{j,1,2}];
  
  Which[

	
    X`Internal`PossibleAllZeroQ[gramZ] && X`Internal`PossibleAllZeroQ[f] && (m0=!=0),
    (*Print["Case 6: gramZ & f vanishing."];*)
      ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCcase6],

    X`Internal`PossibleAllZeroQ[gramZ] && !(X`Internal`PossibleAllZeroQ[f]),
    (*Print["Case 5: gramZ vanishing but f non-vanishing."];*)
      With[{siga=Which[!PossibleZeroQ[f[[1]]],1,True,2]},
        ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],{refineRulesCcase5a[[siga]],refineRulesCcase5b}]
      ],
  
    PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0],
    (*Print["Case 4: detZ and adjX0 are zero"];*)
      (*KallenExpand@*)Replace[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCcase4],
    
    PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3: detZ=0"];*)
      With[{
        siga=Which[!PossibleZeroQ[adjZ[[1,1]]],{1,1},!PossibleZeroQ[adjZ[[2,2]]],{2,2},True,{1,2}],
        sigb=Which[!PossibleZeroQ[adjX0[[1]]],1,True,2]},
        (*Print["siga=",siga,"  sigb=",sigb, "adjZ = ", adjZ];*)
        passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2] = Dot[Together[Coefficient[#,Eps,{-2,-1,0}]],{1/Eps^2,1/Eps,1}] &@ ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],{refineRulesCcase3a[[Sequence@@siga]],refineRulesCcase3b[[sigb]]}]
      ],


    ((PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] && PossibleZeroQ[m1]) (*(p1===m0^2 && q===m2^2 && m1===0)*)  (* p2 may or may not vanish*)
     || (PossibleZeroQ[p2-m0^2] && PossibleZeroQ[q-m1^2] && PossibleZeroQ[m2]) (*(p2===m0^2 && q===m1^2  && m2===0)*)  (* p1 may or may not vanish*)
     || (PossibleZeroQ[p1-m1^2] && PossibleZeroQ[p2-m2^2] && PossibleZeroQ[m0]) (*(p1===m1^2 && p2===m2^2  && m0===0)*)) (* q may or may not vanish*),
    (*Print["Case 2: Triangle 6; Xij=", Xij, "adjXij=",adjXij, "and adjX0j=",adjX0];*)
    passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2] = Dot[Together[Coefficient[#,Eps,{-2,-1,0}]],{1/Eps^2,1/Eps,1}] &@ Replace[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCtriangle6],


	((PossibleZeroQ[q] && PossibleZeroQ[m2] && PossibleZeroQ[m1]) (*(q===0 && m2===0 && m1===0)*)
	 || (PossibleZeroQ[p1] && PossibleZeroQ[m1] && PossibleZeroQ[m0]) (*(p1===0 && m1===0 && m0===0)*)
	 || (PossibleZeroQ[p2] && PossibleZeroQ[m2] && PossibleZeroQ[m0]) (*(p2===0 && m2===0 && m0===0)*)),
	(*Print["PVC for triangle 2 & 3"];*)
	Replace[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCtriangle3],


    Positive[r](* && !(PossibleZeroQ[Det[gramZ]])*) || r===0 && PossibleZeroQ[Det[Xij]],
    (*Print["Case 1: detZ nonZero; r=", r];*)
    passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2] = Dot[Together[Coefficient[#,Eps,{-2,-1,0}]],{1/Eps^2,1/Eps,1}] &@ ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCcase1],

  
	NonPositive[r] && !(PossibleZeroQ[Det[Xij]]),
	(*Print["PVC for r<0: Det[X]!=0"];*)
	ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],refineRulesCnegativer],


    True,
	Message[LoopRefine::leadinglandau, PVC[r,n1,n2,p1,q,p2,m0,m1,m2]];
	PVC[r,n1,n2,p1,q,p2,m0,m1,m2]

  ]
];


(* ::Subsubsection::Closed:: *)
(*D functions*)


(*Shifted C-functions; due to unshifted pinched propagator*)
pvCs[r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_]/;(n3 < n1 && n3 < n2) := pvCs[r,n3,n2,n1,s3,s2,s23,m3,m2,m1];
pvCs[r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_]/;(n2 < n1 && n2 < n3) := pvCs[r,n2,n1,n3,s2,s23,s3,m2,m1,m3];
pvCs[r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_] := (-1)^n1 Sum[Multinomial[idx1,idx2,n1-idx1-idx2]refineC[r,n2+idx2,n1+n3-idx1-idx2,s2,s3,s23,m1,m2,m3],{idx1,0,n1},{idx2,0,n1-idx1}];


(*Define D-function reduction rules*)
Block[{
	n={n1, n2, n3},
	f={s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},

	gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }},

	detZ = 1/4 * Kibble\[Phi][s1,s2,s3,s4,s12,s23],

	adjZ={{-Kallen\[Lambda][s12,s3,s4]/4, 1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)), 1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4))},
		 {1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)), -Kallen\[Lambda][s23,s1,s4]/4, 1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4))},
		 {1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4)), 1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4)),-Kallen\[Lambda][s12,s1,s2]/4}},

	mtxX=({{2*m0^2,        s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
		   {s1-m1^2+m0^2,  2*s1,         s1+s12-s2,     s1-s23+s4},
		   {s12-m2^2+m0^2, s1+s12-s2,    2*s12,         s12-s3+s4},
		   {s4-m3^2+m0^2,  s1-s23+s4,    s12-s3+s4,     2*s4}}),

    adjadjZ = {{{{0,0,0},{0,0,0},{0,0,0}},{{0,-s4,1/2 (s12-s3+s4)},{s4,0,1/2 (-s1+s23-s4)},{1/2 (-s12+s3-s4),1/2 (s1-s23+s4),0}},{{0,1/2 (s12-s3+s4),-s12},{1/2 (-s12+s3-s4),0,1/2 (s1+s12-s2)},{s12,1/2 (-s1-s12+s2),0}}},{{{0,s4,1/2 (-s12+s3-s4)},{-s4,0,1/2 (s1-s23+s4)},{1/2 (s12-s3+s4),1/2 (-s1+s23-s4),0}},{{0,0,0},{0,0,0},{0,0,0}},{{0,1/2 (-s1+s23-s4),1/2 (s1+s12-s2)},{1/2 (s1-s23+s4),0,-s1},{1/2 (-s1-s12+s2),s1,0}}},{{{0,1/2 (-s12+s3-s4),s12},{1/2 (s12-s3+s4),0,1/2 (-s1-s12+s2)},{-s12,1/2 (s1+s12-s2),0}},{{0,1/2 (s1-s23+s4),1/2 (-s1-s12+s2)},{1/2 (-s1+s23-s4),0,s1},{1/2 (s1+s12-s2),-s1,0}},{{0,0,0},{0,0,0},{0,0,0}}}},
	adjX0, 
	adjXij = {{2 (-m0^4 s3-m2^4 s4-s12 (m3^4+m3^2 (s12-s3-s4)+s3 s4)+m2^2 ((s12+s3-s4) s4+m3^2 (s12-s3+s4))+m0^2 (m3^2 (s12+s3-s4)+s3 (s12-s3+s4)+m2^2 (-s12+s3+s4))),-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s12-s3+s4) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4)),(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4)-2 s12 (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))+(m0^2-m2^2+s12) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4))},{-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s1-s23+s4) (-(m0^2-m2^2+s12) (m0^2-m3^2+s4)+2 m0^2 (s12-s3+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s12-s3+s4)),2 (-m0^4 s23-m1^4 s4-s1 (m3^4+m3^2 (s1-s23-s4)+s23 s4)+m1^2 ((s1+s23-s4) s4+m3^2 (s1-s23+s4))+m0^2 (m3^2 (s1+s23-s4)+s23 (s1-s23+s4)+m1^2 (-s1+s23+s4))),-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4)+(s1+s12-s2) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m2^2+s12) (-2 s1 (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s1-s23+s4))},{(2 (m0^2-m1^2+s1) s12-(m0^2-m2^2+s12) (s1+s12-s2)) (m0^2-m3^2+s4)-(4 m0^2 s12-(m0^2-m2^2+s12)^2) (s1-s23+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4),-(-2 s1 (m0^2-m2^2+s12)+(m0^2-m1^2+s1) (s1+s12-s2)) (m0^2-m3^2+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s1-s23+s4)-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4),2 (-m1^4 s12-m0^4 s2-s1 (m2^4+m2^2 (s1-s12-s2)+s12 s2)+m1^2 (m2^2 (s1+s12-s2)+s12 (s1-s12+s2))+m0^2 ((s1+s12-s2) s2+m2^2 (s1-s12+s2)+m1^2 (-s1+s12+s2)))}},
	pinchC, missCDivUV,
	nk,kp,
	i, j, k, ndx,mdx},

	nk[idx_,cnc_] = Which[idx<cnc, n[[idx]], idx>=cnc, n[[idx+1]]]; (*This is n_{idx(cnc)}*)
	kp[idx_,cnc_] = Which[idx<cnc, idx, idx>=cnc, idx+1]; (*this is just idx(cnc)*)

	adjX0=Expand[Table[Sum[adjZ[[j,k]]f[[k]],{k,1,3}],{j,1,3}]]; (*up to a constant: -4*)

	(*Passarino Veltman functions with pinched propagators, and their divergent parts*)
	pinchC[r_,n1_,n2_]  =    {refineC[r,n1,n2,s12,s3,s4,m0,m2,m3], refineC[r,n1,n2,s1,s23,s4,m0,m1,m3], refineC[r,n1,n2,s1,s2,s12,m0,m1,m2]};
	missCDivUV[r_,n1_,n2_] = {pvCDivUV[r,n1,n2,s12,s3,s4,m0,m2,m3],pvCDivUV[r,n1,n2,s1,s23,s4,m0,m1,m3],pvCDivUV[r,n1,n2,s1,s2,s12,m0,m1,m2]};

	(********Case6: All elements of gramZ is zero, AND all f are zero********)
	refineRulesDcase6={
	  passVeltD[r_?Negative,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/m0^2 ((4-2Eps+2(r+n1+n2+n3))passVeltD[r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]),
	  passVeltD[0,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/m0^2 ((4+2(n1+n2+n3))passVeltD[1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-pvCs[0,n1,n2,n3,s2,s3,s23,m1,m2,m3]-2 pvDDivUV[1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),
	  passVeltD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> -(1/(2(n1+1)))pvCs[r-1,n1+1,n2,n3,s2,s3,s23,m1,m2,m3]
	};

	(********Case5: All elements of gramZ is zero, but f nonzero********)
	refineRulesDcase5a=Table[passVeltD[r_?NonPositive,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/f[[k]] (-2n[[k]]passVeltD[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+KroneckerDelta[n[[k]],0]pinchC[r,nk[1,k],nk[2,k]][[k]]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]),{k,1,3}];
	refineRulesDcase5b = passVeltD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/(2+2r+2n1+2n2+2n3)*(pvCs[r-1,n1,n2,n3,s2,s3,s23,m1,m2,m3]+m0^2 passVeltD[r-1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])+1/(1+r+n1+n2+n3)*pvDDivUV[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];

	(********Case4: Gram determinant and Cayley vectors X vanishing********)
	refineRulesDcase4a=
	Flatten[Table[passVeltD[r_?Positive, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/(2(n[[k]]+1)adjZ[[j,k]]) (-2*Sum[adjZ[[j,mdx]]*n[[mdx]]*passVeltD[r,n1-KroneckerDelta[mdx,1]+KroneckerDelta[k,1],n2-KroneckerDelta[mdx,2]+KroneckerDelta[k,2],n3-KroneckerDelta[mdx,3]+KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{mdx,Complement[Range[1,3],{k}]}]+Sum[adjZ[[j,l]](KroneckerDelta[n[[l]]+KroneckerDelta[k,l],0]*pinchC[r-1,nk[1,l]+KroneckerDelta[kp[1,l],k],nk[2,l]+KroneckerDelta[kp[2,l],k]][[l]]-pvCs[r-1,n1+KroneckerDelta[k,1],n2+KroneckerDelta[k,2],n3+KroneckerDelta[k,3],s2,s3,s23,m1,m2,m3]),{l,1,3}])
		,{j,1,3},{k,1,3}]];
	refineRulesDcase4b=
	Flatten[Table[passVeltD[0, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 4*adjZ[[i,k]]/adjXij[[i,k]]*(2(1+n1+n2+n3)passVeltD[1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-pvCs[0,n1,n2,n3,s2,s3,s23,m1,m2,m3])+2/adjXij[[i,k]]*Sum[f[[ndx]]*adjadjZ[[ndx,i,j,k]]*(KroneckerDelta[n[[j]],0]*pinchC[0,nk[1,j],nk[2,j]][[j]]-pvCs[0,n1,n2,n3,s2,s3,s23,m1,m2,m3]-2n[[j]]*passVeltD[1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],n3-KroneckerDelta[j,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{j,1,3},{ndx,1,3}]
		,{i,1,3},{k,1,3}]];
	refineRulesDcase4c=
	Flatten[Table[passVeltD[r_?Negative, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 4*adjZ[[i,k]]/adjXij[[i,k]]*(2(1-2Eps+2r+n1+n2+n3)passVeltD[r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3])+2/adjXij[[i,k]]*Sum[f[[ndx]]*adjadjZ[[ndx,i,j,k]]*(KroneckerDelta[n[[j]],0]*pinchC[r,nk[1,j],nk[2,j]][[j]]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]-2n[[j]]*passVeltD[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],n3-KroneckerDelta[j,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{j,1,3},{ndx,1,3}]
		,{i,1,3},{k,1,3}]];

	(********Exceptional Case: All adjZ vanishing (doesn't matter if adjX vanishes)********)
	(*Subcase 3: If s1=0, m0!=m2*)
	refineRulesDcaseX3={
		passVeltD[r_?NonNegative, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :>
		With[
		 {A=m2^2-m0^2,
		  gammaCoeff0 = Piecewise[{{-1,#1+#2+#3==0},{(-1)^(#3+1) #3!,#2+#1==1},{0,#1<2},{((-1)^(1+#2+#3) (#1+#2+#3-1)!)/((#1+#2-1)(#1-2)!),True}}]&,
		  gammaCoeff1 = Piecewise[{{0,#1+#2+#3==0},{(-1)^(#3+1) #3!(HarmonicNumber[1-#1]-HarmonicNumber[#3]),#2+#1==1},{(-1)^(#1+#2+#3+1)/(#1+#2-1) (#1+#2+#3-1)!,#1<2},{((-1)^(1+#2+#3) (#1+#2+#3-1)!)/((#1+#2-1)^2 (#1-2)!) (1+(#1+#2-1)(HarmonicNumber[#1-2]-HarmonicNumber[#1+#2+#3-1])),True}}]&},
		  (-2^n2 n2!)/A^(n2+1) refineC[r+n2,n1,n3,s1,s23,s4,m0,m1,m3]+Sum[((-1)^(1+jdx+n2) 2^(jdx+kdx))/A^(jdx+kdx+1) Multinomial[jdx,kdx,ldx1,ldx2,n2-jdx-kdx-ldx1-ldx2](gammaCoeff0[r,jdx,kdx]refineC[r+jdx+kdx,n1+ldx1,n3+ldx2,s2,s23,s3,m2,m1,m3]+gammaCoeff1[r,jdx,kdx]pvCDivUV[r+jdx+kdx,n1+ldx1,n3+ldx2,s2,s23,s3,m2,m1,m3]),{jdx,0,n2},{kdx,0,n2-jdx},{ldx1,0,n2-jdx-kdx},{ldx2,0,n2-jdx-kdx-ldx1}]
		],
		passVeltD[r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :>
		With[
		 {A=m2^2-m0^2,
		  (*gammaSeries = Normal[Series[Gamma[2+Eps-#1]/((-1+#1+#2-Eps)Gamma[1+Eps-#1-#2-#3]),{Eps,0,2}]]&*)
		  gammaSeries = Which[
			#1>=2,((-1)^(1+#2+#3) (-1+#2+#3+#1)!)/((-1+#2+#1) (-2+#1)!)+((-1)^(1+#2+#3) Eps (-1+#2+#3+#1)! (1+(-1+#2+#1) HarmonicNumber[-2+#1]-(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1]))/((-1+#2+#1)^2 (-2+#1)!)+1/(2 (-1+#2+#1)^3 (-2+#1)!) (-1)^(#2+#3) Eps^2 (-1+#2+#3+#1)! (-2-(-1+#2+#1)^2 HarmonicNumber[-2+#1]^2+2 (-1+#2+#1) HarmonicNumber[-1+#2+#3+#1]-(-1+#2+#1)^2 HarmonicNumber[-1+#2+#3+#1]^2+2 (-1+#2+#1) HarmonicNumber[-2+#1] (-1+(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1])-(-1+#2+#1)^2 HarmonicNumber[-2+#1,2]+(-1+#2+#1)^2 HarmonicNumber[-1+#2+#3+#1,2]),
			#1+#2==1,(-1)^(1+#3) #3! (1-#1)!+(-1)^#3 Eps #3! (1-#1)! (HarmonicNumber[#3]-HarmonicNumber[1-#1])-1/2 (-1)^#3 Eps^2 #3! (1-#1)! ((HarmonicNumber[#3]-HarmonicNumber[1-#1])^2-HarmonicNumber[#3,2]-HarmonicNumber[1-#1,2]),
			1-#1-#2-#3>0,(1-#1)!/((-1+#2+#1) (-#2-#3-#1)!)+(Eps (1-#1)! (1+(-1+#2+#1) HarmonicNumber[1-#1]-(-1+#2+#1) HarmonicNumber[-#2-#3-#1]))/((-1+#2+#1)^2 (-#2-#3-#1)!)+1/(2 (-1+#2+#1)^3 (-#2-#3-#1)!) Eps^2 (1-#1)! (2+(-1+#2+#1)^2 HarmonicNumber[1-#1]^2-2 (-1+#2+#1) HarmonicNumber[-#2-#3-#1]+(-1+#2+#1)^2 HarmonicNumber[-#2-#3-#1]^2+2 (-1+#2+#1) HarmonicNumber[1-#1] (1-(-1+#2+#1) HarmonicNumber[-#2-#3-#1])-(-1+#2+#1)^2 HarmonicNumber[1-#1,2]+(-1+#2+#1)^2 HarmonicNumber[-#2-#3-#1,2]),
			True,((-1)^(1+#2+#3+#1) Eps (1-#1)! (-1+#2+#3+#1)!)/(-1+#2+#1)+1/(-1+#2+#1)^2 (-1)^(1+#2+#3+#1) Eps^2 (1-#1)! (-1+#2+#3+#1)! (1+(-1+#2+#1) HarmonicNumber[1-#1]-(-1+#2+#1) HarmonicNumber[-1+#2+#3+#1])
			]&
		 },
		  (-2^n2 n2!)/A^(n2+1) refineC[r+n2,n1,n3,s1,s23,s4,m0,m1,m3]+Sum[((-1)^(1+jdx+n2) 2^(jdx+kdx))/A^(jdx+kdx+1) Multinomial[jdx,kdx,ldx1,ldx2,n2-jdx-kdx-ldx1-ldx2](gammaSeries[r,jdx,kdx]refineC[r+jdx+kdx,n1+ldx1,n3+ldx2,s2,s23,s3,m2,m1,m3]),{jdx,0,n2},{kdx,0,n2-jdx},{ldx1,0,n2-jdx-kdx},{ldx2,0,n2-jdx-kdx-ldx1}]
		]};
	(*Subcase 4: If s1=0, m0=m2*)
	refineRulesDcaseX4=passVeltD[r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> (-1)^n2/(2(n2+1)) Sum[Multinomial[j,k,n2+1-j-k]*refineC[r-1,n1+j,n3+k,s1,s23,s4,m0,m1,m3],{j,0,n2+1},{k,0,n2+1-j}];

	(********Exceptional Case: All adjX vanishing, but not adjZ********)
	(*refineRulesDcaseX5=Flatten[Table[passVeltD[r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/(2(n[[k]]+1)adjZ[[j,k]]) (-2*Sum[adjZ[[j,mdx]]*n[[mdx]]*passVeltD[r,n1-KroneckerDelta[mdx,1]+KroneckerDelta[k,1],n2-KroneckerDelta[mdx,2]+KroneckerDelta[k,2],n3-KroneckerDelta[mdx,3]+KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{mdx,Complement[Range[1,3],{k}]}]+Sum[adjZ[[j,l]](KroneckerDelta[n[[l]]+KroneckerDelta[k,l],0]*pinchC[r-1,nk[1,l]+KroneckerDelta[kp[1,l],k],nk[2,l]+KroneckerDelta[kp[2,l],k]][[l]]-pvCs[r-1,n1+KroneckerDelta[k,1],n2+KroneckerDelta[k,2],n3+KroneckerDelta[k,3],s2,s3,s23,m1,m2,m3]),{l,1,3}])
		,{j,1,3},{k,1,3}]];*)

	(********Case3: Gram determinant vanishing, but Cayley vectors X non-vanishing********)
	refineRulesDcase3a=
	Flatten[Table[
	  passVeltD[r_?Positive,0, 0, 0, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 
	    1/(2r)*(pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+m0^2 passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])+1/r*pvDDivUV[r, 0, 0, 0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] +
	    1/(4r)*1/adjZ[[k,l]] Sum[adjadjZ[[k,ndx,l,mdx]](Sum[gramZ[[ndx,j]](If[mdx==j,0,Evaluate[pinchC[r-1,KroneckerDelta[kp[1,mdx],j],KroneckerDelta[kp[2,mdx],j]][[mdx]]]]-pvCs[r-1,KroneckerDelta[j,1],KroneckerDelta[j,2],KroneckerDelta[j,3],s2,s3,s23,m1,m2,m3]),{j,1,3}]+1/2 f[[mdx]](-pinchC[r-1,0,0][[ndx]]+pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+f[[ndx]]passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])),{ndx,1,3},{mdx,1,3}] 
	  ,{k,1,3},{l,1,3}]];
	refineRulesDcase3b=
	Table[
	  passVeltD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/adjX0[[j]]*
	    Sum[adjZ[[j,k]](If[n[[k]]==0,Evaluate[pinchC[r,nk[1,k],nk[2,k]][[k]]],0]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]-
	    If[n[[k]]==0,0,Evaluate[2n[[k]]passVeltD[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]]]),{k,1,3}],
	{j,1,3}];

	(********Case1: Gram determinant non-vanishing [most general] ********)
	refineRulesDcase1={
	  passVeltD[r_?Positive, 0, 0, 0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]-> 
	    1/(4r-2)*(pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+2m0^2 passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[1]] passVeltD[r-1,1,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[2]] passVeltD[r-1,0,1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[3]] passVeltD[r-1,0,0,1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]) +
	    2/(2r-1)*(pvDDivUV[r, 0, 0, 0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),
	  passVeltD[r_,n1_?Positive,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[1,k]]*(If[n[[k]]-KroneckerDelta[1,k]==0,Evaluate[pinchC[r,nk[1,k]-(1-KroneckerDelta[k,1]),nk[2,k]][[k]]],0]-
	    pvCs[r,n1-1,n2,n3,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1-1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-If[n[[k]]-KroneckerDelta[1,k]==0,0,Evaluate[2(n[[k]]-KroneckerDelta[1,k])passVeltD[r+1,n1-1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]]]),{k,1,3}],
	  passVeltD[r_,n1_,n2_?Positive,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[2,k]]*(If[n[[k]]-KroneckerDelta[2,k]==0,Evaluate[pinchC[r,nk[1,k]-KroneckerDelta[k,1],nk[2,k]-KroneckerDelta[k,3]][[k]]],0]-
	    pvCs[r,n1,n2-1,n3,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1,n2-1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-If[n[[k]]-KroneckerDelta[2,k]==0,0,Evaluate[2(n[[k]]-KroneckerDelta[2,k])passVeltD[r+1,n1-KroneckerDelta[k,1],n2-1-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]]]),{k,1,3}],
	  passVeltD[r_,n1_,n2_,n3_?Positive,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[3,k]]*(If[n[[k]]-KroneckerDelta[3,k]==0,Evaluate[pinchC[r,nk[1,k],nk[2,k]-(1-KroneckerDelta[k,3])][[k]]],0]-
	    pvCs[r,n1,n2,n3-1,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1,n2,n3-1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-If[n[[k]]-KroneckerDelta[3,k]==0,0,Evaluate[2(n[[k]]-KroneckerDelta[3,k])passVeltD[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-1-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]]]),{k,1,3}]
	  (*,passVeltD[0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> With[{body=analD0IR[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]},body/; Head[body]=!=analD0IR]*)
	};

	(****Reduction formulae for negative rank r<0*****)
	refineRulesDnegativerCase1 = 
	  Join[
		{(*passVeltD[0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> With[{body=analD0IR[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]},body/; Head[body]=!=analD0IR],*)
		 passVeltD[r_?Negative,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/Det[mtxX] * (8*detZ*(2(1-2*Eps+n1+n2+n3+2r)*passVeltD[r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]) + Sum[-4*adjX0[[j]]*(KroneckerDelta[n[[j]],0]*pinchC[r,nk[1,j],nk[2,j]][[j]] - pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3] - 2*n[[j]]*passVeltD[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],n3-KroneckerDelta[j,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{j,1,3}])},
	     refineRulesDcase1]

];


refineD[r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]:=
  Module[{
    f={s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
    gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }},
    adjZ={{s12 s4-1/4 (s12-s3+s4)^2,1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4))},{1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),s1 s4-1/4 (s1-s23+s4)^2,1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4))},{1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4)),1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4)),s1 s12-1/4 (s1+s12-s2)^2}},
    (*detZ=1/4*(-s12^2 s23-s1^2 s3+s12 (-(s23-s3) (s23-s4)+s2 (s23+s4))-s2 (s23 (s3-s4)+s4 (s2-s3+s4))+s1 (s12 (-s2+s23+s3)+(s23-s3) (s3-s4)+s2 (s3+s4))),*)
	adjX0,
	adjXij = {{2 (-m0^4 s3-m2^4 s4-s12 (m3^4+m3^2 (s12-s3-s4)+s3 s4)+m2^2 ((s12+s3-s4) s4+m3^2 (s12-s3+s4))+m0^2 (m3^2 (s12+s3-s4)+s3 (s12-s3+s4)+m2^2 (-s12+s3+s4))),-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s12-s3+s4) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4)),(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4)-2 s12 (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))+(m0^2-m2^2+s12) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4))},{-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s1-s23+s4) (-(m0^2-m2^2+s12) (m0^2-m3^2+s4)+2 m0^2 (s12-s3+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s12-s3+s4)),2 (-m0^4 s23-m1^4 s4-s1 (m3^4+m3^2 (s1-s23-s4)+s23 s4)+m1^2 ((s1+s23-s4) s4+m3^2 (s1-s23+s4))+m0^2 (m3^2 (s1+s23-s4)+s23 (s1-s23+s4)+m1^2 (-s1+s23+s4))),-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4)+(s1+s12-s2) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m2^2+s12) (-2 s1 (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s1-s23+s4))},{(2 (m0^2-m1^2+s1) s12-(m0^2-m2^2+s12) (s1+s12-s2)) (m0^2-m3^2+s4)-(4 m0^2 s12-(m0^2-m2^2+s12)^2) (s1-s23+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4),-(-2 s1 (m0^2-m2^2+s12)+(m0^2-m1^2+s1) (s1+s12-s2)) (m0^2-m3^2+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s1-s23+s4)-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4),2 (-m1^4 s12-m0^4 s2-s1 (m2^4+m2^2 (s1-s12-s2)+s12 s2)+m1^2 (m2^2 (s1+s12-s2)+s12 (s1-s12+s2))+m0^2 ((s1+s12-s2) s2+m2^2 (s1-s12+s2)+m1^2 (-s1+s12+s2)))}},
    mtxX = {{2*m0^2, s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
			{s1-m1^2+m0^2, 2*s1, s1+s12-s2, s1-s23+s4},
			{s12-m2^2+m0^2, s1+s12-s2, 2*s12, s12-s3+s4},
			{s4-m3^2+m0^2, s1-s23+s4, s12-s3+s4, 2*s4}},
    j,k},

	adjX0=Table[Sum[adjZ[[j,k]]f[[k]],{k,1,3}],{j,1,3}];
  
  Which[
    X`Internal`PossibleAllZeroQ[gramZ] && X`Internal`PossibleAllZeroQ[f] && !(PossibleZeroQ[m0]),
    (*Print["Case 6: gramZ & f vanishing."];*)
      ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineRulesDcase6],

    X`Internal`PossibleAllZeroQ[gramZ] && !(X`Internal`PossibleAllZeroQ[f]),
    (*Print["Case 5: gramZ vanishing but f non-vanishing.  f=", f];*)
      With[{siga=First@Ordering[f,1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
		(*Print["f=", f, "  sig:", siga];*)
        ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDcase5a[[siga]],refineRulesDcase5b}]
      ],
  
	(*Can handle PVD[0,0,0,0,m^2,m^2,m^2,m^2,4m^2,0,m,0,m,0]*)
	PossibleZeroQ[s12] && PossibleZeroQ[s3-s4] && PossibleZeroQ[s1-s2],
	  Replace[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],
		(*Print["Exceptional-1"];*)
		If[PossibleZeroQ[m0-m2],refineRulesDcaseX4,refineRulesDcaseX3]],

	PossibleZeroQ[s23] && PossibleZeroQ[s3-s2] && PossibleZeroQ[s1-s4],
	  Replace[Sum[(-1)^n3*Multinomial[k1,k2,k3,n3-k1-k2-k3]*passVeltD[r,n2+k2,n1+k1,k3,s3,s2,s1,s4,s23,s12,m3,m2,m1,m0],{k1,0,n3},{k2,0,n3-k1},{k3,0,n3-k2-k1}],
		(*Print["Exceptional-2"];*)
		If[PossibleZeroQ[m3-m1],refineRulesDcaseX4,refineRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s1] && PossibleZeroQ[s23-s4] && PossibleZeroQ[s12-s2],
	  Replace[passVeltD[r,n2,n1,n3,s12,s2,s23,s4,s1,s3,m0,m2,m1,m3],
		(*Print["Exceptional-3"];*)
		If[PossibleZeroQ[m0-m1],refineRulesDcaseX4,refineRulesDcaseX3]],

	PossibleZeroQ[s2] && PossibleZeroQ[s1-s12] && PossibleZeroQ[s3-s23],
	  Replace[Sum[(-1)^n1*Multinomial[k1,k2,k3,n1-k1-k2-k3]*passVeltD[r,k1,n2+k2,n3+k3,s1,s12,s3,s23,s2,s4,m1,m0,m2,m3],{k1,0,n1},{k2,0,n1-k1},{k3,0,n1-k2-k1}],
		(*Print["Exceptional-4"];*)
		If[PossibleZeroQ[m1-m2],refineRulesDcaseX4,refineRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s3] && PossibleZeroQ[s23-s2] && PossibleZeroQ[s12-s4],
	  (*Print["Exceptional-5"];*)
	  Replace[Sum[(-1)^n3*Multinomial[k1,k2,k3,n3-k1-k2-k3]*passVeltD[r,n1+k1,n2+k2,k3,s23,s2,s12,s4,s3,s1,m3,m1,m2,m0],{k1,0,n3},{k2,0,n3-k1},{k3,0,n3-k2-k1}],
		If[PossibleZeroQ[m3-m2],refineRulesDcaseX4,refineRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s4] && PossibleZeroQ[s1-s23] && PossibleZeroQ[s3-s12],
	  (*Print["Exceptional-6"];*)
	  Replace[passVeltD[r,n1,n3,n2,s1,s23,s3,s12,s4,s2,m0,m1,m3,m2],
		If[PossibleZeroQ[m0-m3],refineRulesDcaseX4,refineRulesDcaseX3]],

	(*Can't use the following, because all adjXij vanishing implies detX vanishing [leading Landau singularity].
	Then derivation of reduction formula becomes faulty if the leading singularity is on the physical sheet.*)

	(*
	PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0] && !(X`Internal`PossibleAllZeroQ[adjZ]) && X`Internal`PossibleAllZeroQ[adjXij],
	(*Print["EXCEPTIONAL-2; adjZ=", adjZ,";   adjXij=", adjXij];*)
	  With[{siga=First@Ordering[Flatten[adjZ],1,If[#1===0,Infinity,LeafCount[#1]]<If[#2===0,Infinity,LeafCount[#2]]&]},
			(*Print["adjZ=", adjZ, "  sig:", siga];*)
			ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineRulesDcaseX5[[siga]]]
	  ],
	*)

	PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0] && !(X`Internal`PossibleAllZeroQ[adjZ]) && !(X`Internal`PossibleAllZeroQ[adjXij]),
	(*Print["Case 4 PVD: det Z=0, adjX0=0"];*)
	  With[{siga=First@Ordering[Flatten[Simplify[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
			sigb=First@Ordering[Flatten[Simplify[adjXij]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
			(*Print["adjZ=", adjZ, "  sig:", siga];*)
			(*Print["adjXij=", adjXij, "  sig:", sigb];*)
			ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDcase4a[[siga]],refineRulesDcase4b[[sigb]],refineRulesDcase4c[[sigb]]}]
	  ],

    
    PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3 PVD: detZ=0 && one of adjX0 nonzero."];*)
      With[{
        siga=First@Ordering[Flatten[Together[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
        sigb=First@Ordering[Together[adjX0],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
        (*Print["adjZ=", adjZ, "  sig:", siga];*)
		(*Print["adjX0=", adjX0, "  sig:", sigb];*)
        passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = (*KallenExpand@*)(Dot[Together[Coefficient[#,Eps,{-2,-1,0}]],{1/Eps^2,1/Eps,1}] &@ ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineRulesDcase3a[[siga]],refineRulesDcase3b[[sigb]]}])
      ],

    Positive[r] && !(PossibleZeroQ[Det[gramZ]]),
    (*Print["Case 1:, DetZ=", Det[gramZ],",  adjZ=", MatrixForm[adjZ],";  adjXij=", adjXij];*)
    passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = Dot[Together[Coefficient[#,Eps,{-2,-1,0}]],{1/Eps^2,1/Eps,1}] &@(*Normal[Series[#,{Eps,0,0}]]&@*) ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineRulesDcase1],

	NonPositive[r] && !PossibleZeroQ[Det[mtxX]],
	(*Print["PVD r<=0: Det[X]!=0"];*)
	passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = Dot[Together[Coefficient[#,Eps,{-2,-1,0}]],{1/Eps^2,1/Eps,1}] &@(*Normal[Series[#,{Eps,0,0}]]&@*) ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineRulesDnegativerCase1],  

    True,
	Message[LoopRefine::leadinglandau, PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]];

	PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]
  ]
 
];


(* ::Subsection:: *)
(*Part: Discontinuity*)


(* ::Subsubsection::Closed:: *)
(*B functions*)


disc[refineB][0,n_Integer, 0, 0, 0]       := 0;
disc[refineB][0,n_Integer,chnl[s_],m0_,m0_] /; PossibleZeroQ[s-m0^2] := 0;
disc[refineB][0,n_Integer, 0, 0, m1_]     := 0;
disc[refineB][0,n_Integer, 0, m0_, 0]     := 0;
disc[refineB][0,n_Integer,chnl[s_], 0, 0]       := (-1)^n/(n+1) 2*\[Pi]*I HeavisideTheta[s];
disc[refineB][0,n_Integer, 0, m0_, m0_]   := 0;
disc[refineB][0,n_Integer,chnl[s_], 0, m1_] /; PossibleZeroQ[s-m1^2] := 0;
disc[refineB][0,n_Integer,chnl[s_], m0_, 0] /; PossibleZeroQ[s-m0^2] := 0;
disc[refineB][0,n_Integer, 0,m0_,m1_]     := 0;

disc[refineB][0,n_Integer,chnl[s_], 0,m1_]      := (-1)^n/(n+1) (1-m1^2/s)^(n+1) 2*\[Pi]*I HeavisideTheta[s-m1^2];
disc[refineB][0,n_Integer,chnl[s_],m0_, 0]      := (-1)^n/(n+1) (1-(m0^2/s)^(n+1)) 2*\[Pi]*I HeavisideTheta[s-m0^2];
disc[refineB][0,n_Integer,chnl[s_],m0_,m1_] /; PossibleZeroQ[(m0+m1)^2-s]  := 0;
disc[refineB][0,n_Integer,chnl[s_],m0_,m1_] /; PossibleZeroQ[(m0-m1)^2-s]  := 0;
disc[refineB][0,n_Integer,chnl[s_],m0_,m1_]     := With[{k\[Lambda]=Kallen\[Lambda][s,m0^2,m1^2]},(-1)^n/(n+1) Sum[Binomial[n+1,2idx3+1] pow[(s+m0^2-m1^2)/(2s),(n-2idx3)] (k\[Lambda]/(4s^2))^idx3,{idx3,0,n/2}] Sqrt[Kallen\[Lambda][m0^2,m1^2,s]]/s*2*\[Pi]*I*HeavisideTheta[s-(m0+m1)^2]];

(* All coefficient functions with r!=0 are determined ITERATIVELY *)
disc[refineB][r_Integer?NonNegative,n_Integer,chnl[s_],m0_,m1_] := Sum[(-1)^k/(2^r r!) Multinomial[j,k,r-j-k]pow[s,j]pow[-s+m1^2-m0^2,k]pow[m0^2,r-j-k]disc[refineB][0,n+2j+k,chnl[s],m0,m1],{j,0,r},{k,0,r-j}];


(* ::Subsubsection::Closed:: *)
(*B functions - Negative r*)


(*  NEGATIVE r  *)

(*  This is the basic integral that can be power-divergent at normal thresholds:
    powerI(r,k,0,0)=(1+Eps HarmonicNumber[-r-1])(Mu^2)^Eps Integrate[x^k/(-i\[CurlyEpsilon])^(Abs[r]+Eps),{x,0,1}]  *)
disc[powerI][r_, k_, 0, 0, sgn_ : 1]:= 1/(k+1) FeynmanIRepsilon^(2*Abs[r]);

(*  This is the basic integral that can be power-divergent at normal thresholds:
    powerI(r,k,0,m1)=(1+Eps HarmonicNumber[-r-1])(Mu^2/m1^2)^Eps Integrate[x^k/(x^2-i\[CurlyEpsilon]/m1^2)^(Abs[r]+Eps),{x,0,1}]  *)
disc[powerI][r_, k_, 0, m1_, sgn_ : 1] :=
	Which[
		k>=2Abs[r]-1, 0,
		k<2Abs[r]-1, 1/(k-2Abs[r]+1)+(m1 FeynmanIRepsilon)^(2*Abs[r]-k-1) (Gamma[Abs[r]-k/2-1/2] Gamma[(1+k)/2])/(2 Gamma[Abs[r]])
	];

(*powerI(r,k,m0,m1,sgn)=(Mu^2/m0^2)^Eps Integrate[x^k/(x^2-i\[CurlyEpsilon]/m0^2)^(Abs[r]+Eps),{x, sgn*m1/m0, 1}]  *)
(*expression for 'a=-m1/m0 < 0' in my notes. [threshold]*)
disc[powerI][r_,k_,m0_,m1_, -1]:=
	Which[
		k>=2Abs[r]-1, 0,
		k<2Abs[r]-1, (1-(-m1/m0)^(k-2 Abs[r]+1))/(k-2 Abs[r]+1)+(1+(-1)^k) ((m0 FeynmanIRepsilon)^(2 Abs[r]-k-1) (Gamma[Abs[r]-k/2-1/2] Gamma[(1+k)/2]))/(2 Gamma[Abs[r]])
	];
(*expression for 'a=+m1/m0 > 0' in my notes. [pseudothreshold]*)
disc[powerI][r_,k_,m0_,m1_, +1]:=0;


(*Needed for the reduction of case 4 of C functions (DetX=DetZ=0) and IR-divergent C functions.*)
(*Algebraic B function (for r=-1)*)

(*Scaleless*)disc[refineB][r_Integer?Negative,n_Integer, chnl[0], 0, 0] := (-1)^(2+r+n)/2^r (-r-1)! disc[powerI][r, n, 0, 0];

disc[refineB][-1, 0, chnl[0], 0, m1_]            := 0;
disc[refineB][-1,n_Integer, chnl[0], 0, m1_]     := 0;
disc[refineB][-1,n_Integer, chnl[0], m0_, 0]     := 0;
disc[refineB][-1, 0, chnl[s_], 0, 0]             := -4/s * 2*\[Pi]*I*HeavisideTheta[s];
disc[refineB][-1,n_Integer, chnl[s_], 0, 0]      := 2(-1)^(n+1)*1/s * 2*\[Pi]*I*HeavisideTheta[s];

(*Threshold*) disc[refineB][r_Integer?Negative, n_Integer, Except[chnl[0],chnl[s_]], 0, Except[0,m1_]] /; PossibleZeroQ[s-m1^2]:=(-1)^(2+r+n)/2^r Gamma[-r] 1/m1^(2Abs[r]) disc[powerI][r,n,0,m1];
(*Threshold*) disc[refineB][r_Integer?Negative, n_Integer, Except[chnl[0],chnl[s_]], Except[0,m0_], 0]  /; PossibleZeroQ[s-m0^2] := Sum[Binomial[n,k](-1)^n disc[refineB][r,k,chnl[s],0,m0],{k,0,n}];

disc[refineB][r_Integer?Negative,n_Integer, chnl[0],Except[0,m0_],Except[0,m1_]]     := 0;
disc[refineB][-1, 0, chnl[s_], 0,m1_]            := -2/(s-m1^2) 2*2*\[Pi]*I*HeavisideTheta[s-m1^2];
disc[refineB][-1,n_Integer,chnl[s_], 0,m1_]      := 2(-1)^(n+1)*With[{x=(s-m1^2)/s},1/s * x^(n-1) 2*\[Pi]*I*HeavisideTheta[s-m1^2]];
disc[refineB][-1,n_Integer,chnl[s_],m0_, 0]      := 2(-1)^n*1/(s-m0^2) (-2*\[Pi]*I*HeavisideTheta[s-m0^2]-(m0^2/s)^n 2*\[Pi]*I*HeavisideTheta[s-m0^2]);

(*Threshold*) disc[refineB][r_Integer?Negative, n_Integer,Except[chnl[0],chnl[s_]],Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[s-(m0+m1)^2] := (-1)^(2+r+n) Gamma[-r]/(2^r (m0^2)^-r) (m0/(m0+m1))^(n+1) (Sum[Binomial[n,k](-1)^k disc[powerI][r,k,m0,m1,-1],{k,0,n}]);
(*Pseudothreshold*)disc[refineB][r_Integer?Negative, n_Integer,Except[chnl[0],chnl[s_]],Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[s-(m0-m1)^2] := 0;

(*General case*)
disc[refineB][-1,n_Integer,chnl[s_],m0_,m1_]     := 2(-1)^(n+1)*1/s*With[{a=(s+m0^2-m1^2)/(2s),b=((*(m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2)*)Kallen\[Lambda][s,m0^2,m1^2]/(4 s^2))},1/2 Sum[Binomial[n,2k]pow[a,n-2k] pow[b,k]*4 s/Sqrt[Kallen\[Lambda][s,m0^2,m1^2]]*2*\[Pi]*I*HeavisideTheta[s-(m0+m1)^2],{k,0,n/2}]];

disc[refineB][r_Integer,n_Integer,chnl[s_],m0_,m1_] := 1/-Kallen\[Lambda][s,m0^2,m1^2] (2s(2(3-2Eps+2r+n)disc[refineB][r+1,n,chnl[s],m0,m1]) + (-s+m1^2-m0^2)*(-Switch[n,0,0,_,2n disc[refineB][r+1,n-1,chnl[s],m0,m1]]));


(* ::Subsubsection::Closed:: *)
(*B functions - Negative r through O(\[Epsilon])*)


(*  NEGATIVE r through O(Eps)  *)

(*Needed for the reduction of IR-divergent C functions with negative r.*)
(*Scaleless*)disc[refineBorder1][r_Integer?Negative,n_Integer, chnl[0], 0, 0] := (-1)^(2+r+n )/2^r (-r-1)!/(n+1) FeynmanIRepsilon^(2*Abs[r]);

disc[refineBorder1][r_Integer?Negative, n_Integer, chnl[0], 0, Except[0,m1_]]  := 
  ((-1)^(2+r+n) (-r-1)!)/(2^r (m1^2)^-r)*
	Which[
		n+r>=-1,  0,
		True,  1/(1+n+r)+(m1^2)^(-1-n-r) FeynmanIRepsilon^(2(-1-n-r)) (n!(-r-n-2)!)/(-r-1)!+1/(1+n+r)^2*((1+(1+n+r) HarmonicNumber[-1-r]+(1+n+r) Log[Mu^2/m1^2]) Eps)
	];
disc[refineBorder1][r_Integer?Negative, n_Integer, chnl[0], Except[0,m0_], 0]  := Sum[Binomial[n,k](-1)^n disc[refineBorder1][r,k,chnl[0],0,m0],{k,0,n}];

disc[refineBorder1][-1, n_, chnl[s_], 0,  0]  := 
  If[n==0,
	-((8 I \[Pi] HeavisideTheta[s] (1+Eps (Log[Mu^2/$tarScaleSq] + Log[$tarScaleSq/s])))/s), 
	-((4 I (-1)^n \[Pi] HeavisideTheta[s] (1+Eps HarmonicNumber[-1+n]+Eps (Log[Mu^2/$tarScaleSq]+Log[$tarScaleSq/s])))/s)
  ];

(*Threshold*) disc[refineBorder1][r_Integer?Negative, n_Integer, Except[chnl[0],chnl[s_]], 0, Except[0,m1_]] /; PossibleZeroQ[s-m1^2] :=
	(-1)^(2+r+n)/(2^r (m1^2)^-r) (-r-1)!*
	Which[
		n>=-2r-1,0,
		True,1/(1+n+2 r)+(2^(1-2 Abs[r]) FeynmanIRepsilon^(-1-n+2 Abs[r]) m1^(-1-n+2 Abs[r]) \[Pi] n! (-2-n+2 Abs[r])!)/((n/2)! (-1+Abs[r])! (-1-n/2+Abs[r])!)+Eps ((2+(1+n+2 r) HarmonicNumber[-1-r])/(1+n+2 r)^2+Log[Mu^2/m1^2]/(1+n+2 r))
	];

disc[refineBorder1][r_Integer?Negative, n_Integer, Except[chnl[0],chnl[s_]], Except[0,m0_], 0] /; PossibleZeroQ[s-m0^2] := Sum[Binomial[n,k](-1)^n disc[refineBorder1][r,k,chnl[s],0,m0],{k,0,n}];

disc[refineBorder1][r_Integer?Negative, n_Integer, chnl[0], Except[0,m0_], Except[0,m1_]] := 0;

disc[refineBorder1][-1, 0,         Except[chnl[0],chnl[s_]], 0, Except[0,m1_]] := (8 I \[Pi] HeavisideTheta[-m1^2+s] (1+Eps Log[s*$tarScaleSq/(-m1^2+s)^2]+Eps Log[Mu^2/$tarScaleSq]))/(m1^2-s) ;
disc[refineBorder1][-1, n_Integer, Except[chnl[0],chnl[s_]], 0, Except[0,m1_]] (*n!=0*) := 4 I (-1)^(2 n) \[Pi] (m1^2-s)^(-1+n) s^-n HeavisideTheta[-m1^2+s] (1+Eps HarmonicNumber[-1+n]+Eps Log[s*$tarScaleSq/(-m1^2+s)^2]+Eps Log[Mu^2/$tarScaleSq]);

disc[refineBorder1][-1, n_Integer, Except[chnl[0],chnl[s_]], Except[0,m0_], 0] := Sum[Binomial[n,k](-1)^n disc[refineBorder1][-1,k,chnl[s],0,m0],{k,0,n}];

(*Threshold*) disc[refineBorder1][r_?Negative,n_,Except[chnl[0],chnl[s_]],Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[s-(m0+m1)^2] := 
	With[{
		orderZero = Sum[Binomial[n,k] (-1)^k ((1+(-1)^k) (m0^(-k+2 Abs[r]-1) FeynmanIRepsilon^(-k+2 Abs[r]-1) (2^(1-2 Abs[r]) \[Pi] (2 (-1+Abs[r]-k/2))! k!)))/((-1+Abs[r])! (-1+Abs[r]-k/2)! (k/2)!),{k,0,2Abs[r]-2}]
		},

		(-1)^(2+r+n)(-r-1)!/(2^r (m0^2)^-r) (m0/(m0+m1))^(n+1) (orderZero + Eps(HarmonicNumber[-r-1]+Log[Mu^2/m0^2])orderZero)
	];
(*Pseudothreshold*) disc[refineBorder1][r_?Negative,n_,Except[chnl[0],chnl[s_]],Except[0,m0_],Except[0,m1_]] /; PossibleZeroQ[s-(m0-m1)^2] := 0;

(*General case*)
disc[refineBorder1][-1,0,chnl[s_],m0_,m1_] := -8*\[Pi]*I/Sqrt[Kallen\[Lambda][s,m0^2,m1^2]]*(1+Eps*(Log[Mu^2/$tarScaleSq]+Log[s*$tarScaleSq/Kallen\[Lambda][s,m0^2,m1^2]]))HeavisideTheta[s-(m0+m1)^2];

(*General case for r \[LessEqual] -2, but n positive*)
disc[refineBorder1][r_Integer,n_Integer?Positive, Except[chnl[0],chnl[s_]], Except[0,m0_], Except[0,m1_]] := 1/(2s)*( - (s-m1^2+m0^2)disc[refineBorder1][r,n-1,chnl[s],m0,m1] - Switch[(n-1),0,0,_,2(n-1)disc[refineBorder1][r+1,n-2,chnl[s],m0,m1]]);
(*Reduction for r <= -2, for n=0, and requires Det(X)!=0 ;*)
disc[refineBorder1][r_Integer,n_Integer?NonNegative, chnl[s_], m0_, m1_] /; r<0 := 1/-Kallen\[Lambda][s,m0^2,m1^2] (2s(2(3-2Eps+2r+n)disc[refineBorder1][r+1,n,chnl[s],m0,m1]) + (-s+m1^2-m0^2)*(-Switch[n,0,0,_,2n disc[refineBorder1][r+1,n-1,chnl[s],m0,m1]]));


(*Default*)
disc[refineB][args__] := 0;
disc[refineBorder1][args__] := 0;


(* ::Subsubsection::Closed:: *)
(*C functions*)


(*C function reduction*)

(*Shifted B-functions; due to missing unshifted propagator; identical to pvBshift, but with immediate replacement*)
disc[pvBs][r_Integer,n1_Integer,n2_Integer,chnl[q_],m1_,m2_]/;n1>n2 := disc[pvBs][r,n2,n1,chnl[q],m2,m1];
disc[pvBs][r_Integer,n1_Integer,n2_Integer,chnl[q_],m1_,m2_]        := (-1)^n1 Sum[Binomial[n1,idx]disc[refineB][r,n2+idx,chnl[q],m1,m2],{idx,0,n1}];


(*Define C-function reduction rules: 6 of them in total*)
Block[{
	n={n1,n2},
	f={p1-m1^2+m0^2,p2-m2^2+m0^2},

	gramZ={{p1,          -(q-p1-p2)/2},
    	  {-(q-p1-p2)/2,  p2}},

	detZ=-Kallen\[Lambda][p1,p2,q]/4,

	adjZ={{p2, (q-p1-p2)/2},
    	 {(q-p1-p2)/2, p1}},

	mtxX, detX, adjX0, adjXij,
	(*pinchB, missBDivUV,*)
	not,
	i,j,k,l,nn,mm},

	not[var_]=Which[var==1,2,var==2,1];

	mtxX=Expand[{{2 m0^2,f[[1]],f[[2]]},{f[[1]],2 p1,-(q-p1-p2)},{f[[2]],-(q-p1-p2),2 p2}}];
	detX=Expand[Det[mtxX]];
	
	adjX0=Expand[Table[Sum[adjZ[[j,k]]f[[k]],{k,1,2}],{j,1,2}]]; (*up to a constant: -2*)
	(*adjXij=Table[4*m0^2 adjZ[[i,j]]+Sum[(KroneckerDelta[i,mm]KroneckerDelta[nn,j]-KroneckerDelta[i,j]KroneckerDelta[nn,mm])f[[nn]] f[[mm]],{nn,1,2},{mm,1,2}],{i,1,2},{j,1,2}];*)

	(*Passarino Veltman functions with missing propagators, and their divergent parts*)
	(*disc[pinchB][r_,n1_]     = {disc[refineB][r,n1,chnl[p2],m0,m2],disc[refineB][r,n1,chnl[p1],m0,m1]};*)

	(********Reduction of triangle 1,4,5,6********)

	(*In this case, p1=q, q=p2, m2=m0 or (p1,m1)<-->(p2,m2).*)
	refineDiscRulesCtriangle6={
	  (*Permuted*)
	  passVeltCdisc[r_,n1_,n2_,p1_,chnl[s_],p2_,0,m2_,m0_] /; PossibleZeroQ[p1-m2^2] && PossibleZeroQ[p2-m0^2] && 2r+n1+n2 != 0 :> If[2r+n1+n2<0,(-1)^(r+n1+n2+3)/2^r * FeynmanIRepsilon^(-2r-n1-n2)*Gamma[(n1+n2+2)/2]*Gamma[-(2r+n1+n2)/2](* * PVB*),0] + (-1)^n2/2 1/(n1+n2+2r) (1+(2Eps)/(n1+n2+2r))Sum[Binomial[n2,k]disc[refineB][r-1,n1+k,chnl[s],m0,m2],{k,0,n2}],
	  passVeltCdisc[r_,n1_,n2_,p1_,chnl[s_],p2_,0,m2_,m0_] /; PossibleZeroQ[p1-m2^2] && PossibleZeroQ[p2-m0^2] :> (-1)^n2/2 * 1/(-2Eps) Sum[Binomial[n2,k]disc[refineBorder1][r-1,n1+k,chnl[s],m0,m2],{k,0,n2}],

	  (*Nonpermuted*)
	  passVeltCdisc[r_?Positive, n1_,n2_,p1_,q_,chnl[s_],m0_,0,m2_]|passVeltCdisc[r_?Positive, n2_,n1_,chnl[s_],q_,p1_,m0_,m2_,0] /;PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] :> (-1)^n1/2 (n1!(n2+2r-1)!)/(n1+n2+2r)! (1+2Eps(HarmonicNumber[n1+n2+2r]-HarmonicNumber[n2+2r-1]))disc[refineB][r-1,n2,chnl[s],m0,m2],
	  passVeltCdisc[r_(*?NonPositive*), n1_,n2_,p1_,q_,chnl[s_],m0_,0,m2_]|passVeltCdisc[r_, n2_,n1_,chnl[s_],q_,p1_,m0_,m2_,0] /;PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] :> 
		Which[
			2r+n2>0&&2r+n1+n2+1>0, -((n1! (-1+n2+2 r)! )/(n1+n2+2 r)!)(-1+2 Eps (HarmonicNumber[-1+n2+2 r]- HarmonicNumber[n1+n2+2 r])) *(-1)^n1/2 * disc[refineB][r-1,n2,chnl[s],m0,m2],
			2r+n2<=0&&2r+n1+n2+1<=0, + (((-1)^n1) n1! (-1-n1-n2-2 r)! )/(-n2-2 r)! (-1+2 Eps(HarmonicNumber[-n2-2 r]-HarmonicNumber[-1-n1-n2-2 r])) * (-1)^n1/2 * disc[refineB][r-1,n2,chnl[s],m0,m2],
			2r+n2<=0&&2r+n1+n2+1>0, - (((-1)^(n2+2 r) n1!)/(2 Eps (-n2-2 r)! (n1+n2+2 r)!)) (1+2Eps (-HarmonicNumber[-n2-2 r]+HarmonicNumber[n1+n2+2 r])) * (-1)^n1/2 * disc[refineBorder1][r-1,n2,chnl[s],m0,m2]
		  ]
	};

	(********Reduction of triangle 2,3********)
	refineDiscRulesCtriangle3 = {
	  (*Permuted*)
	  (*p1-channel discontinuity*)
	  passVeltCdisc[r_?Positive,n1_,n2_,chnl[p1_],0,p2_,m0_,0,0] :> Sum[(-1)^(n2)*(p1-p2)^(-1-n1-tdx)*Multinomial[sdx, n2 - sdx - tdx, tdx]*(Sum[(1/(2*(j+r)))*((-1)^j*Binomial[1+j, l]*Multinomial[j, k, -j-k+n1+tdx]*pow[p1, l]*pow[-m0^2+p1, 1+j-l]*pow[p2, k]*pow[-m0^2+p2, -j-k+n1+tdx]*(disc[refineB][-1+r, k+l+sdx, chnl[p1], 0, m0])), {j, 0, n1 + tdx}, {k, 0, -j+n1+tdx}, {l, 0, 1 + j}]), {sdx, 0, n2}, {tdx, 0, n2 - sdx}],
	  
	  passVeltCdisc[r_,n1_,n2_,chnl[p1_],0,p2_,m0_,0,0] :> 
		With[{
		  fracSeries=
			If[#1+#2!=0,  (1/(#1+#2)+Eps/(#1+#2)^2),  -1/Eps]&},
			Sum[(-1)^n2*(p1-p2)^(-1-n1-tdx)*Multinomial[sdx, n2-sdx-tdx, tdx]*(Sum[(1/2)*(-1)^j*Binomial[1+j, l]*fracSeries[r, j]*Multinomial[j, k, -j-k+n1+tdx]*disc[refineBorder1][-1+r, k+l+sdx, chnl[p1], 0, m0]*pow[p1, l]*pow[-m0^2+p1, 1+j-l]*pow[p2, k]*pow[-m0^2 + p2, -j-k+n1+tdx], {j, 0, n1+tdx}, {k, 0, -j+n1+tdx}, {l, 0, 1 + j}]), {sdx, 0, n2},{tdx, 0, n2 - sdx}]
		],
	  (*p2-channel discontinuity*)
	  passVeltCdisc[r_?Positive,n1_,n2_,p1_,0,chnl[p2_],m0_,0,0] :> Sum[(-1)^(n2)*(p1-p2)^(-1-n1-tdx)*Multinomial[sdx, n2 - sdx - tdx, tdx]*(Sum[-((1/(2*(n1+r+tdx)!))*(Binomial[1+n1+tdx,k]*(-1+r)!*(n1+tdx)!*pow[p2, k]*pow[-m0^2+p2, 1-k+n1+tdx]*disc[refineB][-1+r, k+sdx, chnl[p2], 0, m0])), {k, 0, 1+n1+tdx}]), {sdx, 0, n2}, {tdx, 0, n2 - sdx}],

	  passVeltCdisc[r_,n1_,n2_,p1_,0,chnl[p2_],m0_,0,0] :> 
		With[{
		  gammaSeries=
			If[#2+1+#1>0,  (-1)^(1+#1)/((-#1)! (#2+#1)! Eps)+((-1)^#1 (HarmonicNumber[-#1]-HarmonicNumber[#2+#1]))/((-#1)! (#2+#1)!)-1/(2 ((-#1)! (#2+#1)!)) ((-1)^#1 (HarmonicNumber[-#1]^2-2 HarmonicNumber[-#1] HarmonicNumber[#2+#1]+HarmonicNumber[#2+#1]^2+HarmonicNumber[-#1,2]+HarmonicNumber[#2+#1,2])) Eps,
			  ((-1)^(1+#2) (-1-#2-#1)!)/(-#1)!+1/(-#1)! (-1)^#2 (-1-#2-#1)! (-HarmonicNumber[-1-#2-#1]+HarmonicNumber[-#1]) Eps]&},
			Sum[(-1)^n2*(p1-p2)^(-1-n1-tdx)*Multinomial[sdx, n2-sdx-tdx, tdx]*(Sum[(-(1/2))*Binomial[1+n1+tdx, k]*(n1+tdx)!*gammaSeries[r, n1+tdx]*disc[refineBorder1][-1+r, k+sdx, chnl[p2], 0, m0]*pow[p2, k]*pow[-m0^2+p2, 1-k+n1+tdx], {k, 0, 1+n1+tdx}]), {sdx, 0, n2},{tdx, 0, n2 - sdx}]
		],

	  (*Nonpermuted*)
	  (*q-channel discontinuity*)
	  passVeltCdisc[r_?Positive,n1_,n2_,0,chnl[q_],p2_,0,0,m2_]|passVeltCdisc[r_?Positive,n2_,n1_,p2_,chnl[q_],0,0,m2_,0] :> 
		1/(q-p2)^(n1+1) (Sum[(-1)^j/(2(r+j)) Multinomial[j,k,n1-j-k]Binomial[j+1,l]pow[p2,k]pow[q,l]pow[p2-m2^2,n1-j-k]pow[q-m2^2,j+1-l]disc[refineB][r-1,n2+k+l,chnl[q],0,m2],{j,0,n1},{k,0,n1-j},{l,0,j+1}]),

	  passVeltCdisc[r_,n1_,n2_,0,chnl[q_],p2_,0,0,m2_]|passVeltCdisc[r_,n2_,n1_,p2_,chnl[q_],0,0,m2_,0] :> 
		With[{
		  fracSeries=
			If[#1+#2!=0,  (1/(#1+#2)+Eps/(#1+#2)^2),  -1/Eps]&},
			1/(q-p2)^(n1+1) (Sum[(-1)^j/2 fracSeries[r,j]Multinomial[j,k,n1-j-k]Binomial[j+1,l]pow[p2,k]pow[q,l]pow[p2-m2^2,n1-j-k]pow[q-m2^2,j+1-l]disc[refineBorder1][r-1,n2+k+l,chnl[q],0,m2],{j,0,n1},{k,0,n1-j},{l,0,j+1}])
		],
	  (*p2-channel discontinuity*)
	  passVeltCdisc[r_?Positive,n1_,n2_,0,q_,chnl[p2_],0,0,m2_]|passVeltCdisc[r_?Positive,n2_,n1_,chnl[p2_],q_,0,0,m2_,0] :> 
		1/(q-p2)^(n1+1) Sum[-(n1!/2) (r-1)!/(r+n1)! Binomial[n1+1,k]pow[p2,k]pow[p2-m2^2,n1+1-k]disc[refineB][r-1,n2+k,chnl[p2],0,m2],{k,0,n1+1}],

	  passVeltCdisc[r_,n1_,n2_,0,q_,chnl[p2_],0,0,m2_]|passVeltCdisc[r_,n2_,n1_,chnl[p2_],q_,0,0,m2_,0] :> 
		With[{
		  gammaSeries=
			If[#2+1+#1>0,  (-1)^(1+#1)/((-#1)! (#2+#1)! Eps)+((-1)^#1 (HarmonicNumber[-#1]-HarmonicNumber[#2+#1]))/((-#1)! (#2+#1)!)-1/(2 ((-#1)! (#2+#1)!)) ((-1)^#1 (HarmonicNumber[-#1]^2-2 HarmonicNumber[-#1] HarmonicNumber[#2+#1]+HarmonicNumber[#2+#1]^2+HarmonicNumber[-#1,2]+HarmonicNumber[#2+#1,2])) Eps,
			  ((-1)^(1+#2) (-1-#2-#1)!)/(-#1)!+1/(-#1)! (-1)^#2 (-1-#2-#1)! (-HarmonicNumber[-1-#2-#1]+HarmonicNumber[-#1]) Eps]&},
			1/(q-p2)^(n1+1) Sum[-(n1!/2)*gammaSeries[r,n1]*Binomial[n1+1,k]pow[p2,k]pow[p2-m2^2,n1+1-k]disc[refineBorder1][r-1,n2+k,chnl[p2],0,m2],{k,0,n1+1}]
		]
	};


	(********Case1: Gram determinant non-vanishing [most general] ********)
	(*In this case, PVC[n1,n2]/;n2>n1=PVC[n2,n1] is used.  See refineC function.*)
	refineDiscRulesCcase1={
	  passVeltCdisc[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_]/; n2>n1 -> passVeltCdisc[r,n2,n1,p2,q,p1,m0,m2,m1],

	  passVeltCdisc[r_?Positive,0,0,chnl[p1_],q_,p2_,m0_,m1_,m2_] -> 
	    1/(4r)*(2m0^2 passVeltCdisc[r-1,0,0,chnl[p1],q,p2,m0,m1,m2]+f[[1]] passVeltCdisc[r-1,1,0,chnl[p1],q,p2,m0,m1,m2]+f[[2]] passVeltCdisc[r-1,0,1,chnl[p1],q,p2,m0,m1,m2]),
	  passVeltCdisc[r_,n1_?Positive,n2_,chnl[p1_],q_,p2_,m0_,m1_,m2_] ->
	    1/(2*detZ) (adjZ[[1,2]]*If[n2==0,disc[refineB][r,n1-1,chnl[p1],m0,m1],0] +
		Sum[adjZ[[1,j]]*(-f[[j]]passVeltCdisc[r,n1-1,n2,chnl[p1],q,p2,m0,m1,m2]-If[n[[j]]-KroneckerDelta[1,j]==0,0,Evaluate[2(n[[j]]-KroneckerDelta[1,j])passVeltCdisc[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],chnl[p1],q,p2,m0,m1,m2]]]),{j,1,2}]),

	  passVeltCdisc[r_?Positive,0,0,p1_,chnl[q_],p2_,m0_,m1_,m2_] -> 
	    1/(4r)*(disc[pvBs][r-1,0,0,chnl[q],m1,m2]+2m0^2 passVeltCdisc[r-1,0,0,p1,chnl[q],p2,m0,m1,m2]+f[[1]] passVeltCdisc[r-1,1,0,p1,chnl[q],p2,m0,m1,m2]+f[[2]] passVeltCdisc[r-1,0,1,p1,chnl[q],p2,m0,m1,m2]),
	  passVeltCdisc[r_,n1_?Positive,n2_,p1_,chnl[q_],p2_,m0_,m1_,m2_] ->
	    1/(2*detZ) (Sum[adjZ[[1,j]]*(-disc[pvBs][r,n1-1,n2,chnl[q],m1,m2]-f[[j]]passVeltCdisc[r,n1-1,n2,p1,chnl[q],p2,m0,m1,m2]-If[n[[j]]-KroneckerDelta[1,j]==0,0,Evaluate[2(n[[j]]-KroneckerDelta[1,j])passVeltCdisc[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,chnl[q],p2,m0,m1,m2]]]),{j,1,2}]),

	  passVeltCdisc[r_?Positive,0,0,p1_,q_,chnl[p2_],m0_,m1_,m2_] -> 
	    1/(4r)*(2m0^2 passVeltCdisc[r-1,0,0,p1,q,chnl[p2],m0,m1,m2]+f[[1]] passVeltCdisc[r-1,1,0,p1,q,chnl[p2],m0,m1,m2]+f[[2]] passVeltCdisc[r-1,0,1,p1,q,chnl[p2],m0,m1,m2]),
	  passVeltCdisc[r_,n1_?Positive,n2_,p1_,q_,chnl[p2_],m0_,m1_,m2_] ->
	    1/(2*detZ) (adjZ[[1,1]]*(If[n1-1==0,disc[refineB][r,n2,chnl[p2],m0,m2],0]) + 
		Sum[adjZ[[1,j]]*(-f[[j]]passVeltCdisc[r,n1-1,n2,p1,q,chnl[p2],m0,m1,m2]-If[n[[j]]-KroneckerDelta[1,j]==0,0,Evaluate[2(n[[j]]-KroneckerDelta[1,j])passVeltCdisc[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,chnl[p2],m0,m1,m2]]]),{j,1,2}])

	};

	(****Reduction formulae for negative rank r<0*****)
	refineDiscRulesCnegativer={
	  passVeltCdisc[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_]/; n2>n1 -> passVeltCdisc[r,n2,n1,p2,q,p1,m0,m2,m1],

	  passVeltCdisc[r_,n1_,n2_,chnl[p1_],q_,p2_,m0_,m1_,m2_] /; r<0 -> 1/detX * (4*detZ*(2(2-2*Eps+n1+n2+2r)*passVeltCdisc[r+1,n1,n2,chnl[p1],q,p2,m0,m1,m2]) -2*adjX0[[2]]*If[n2==0,disc[refineB][r,n1,chnl[p1],m0,m1],0] + Sum[-2*adjX0[[j]]*(- 2*n[[j]]*passVeltCdisc[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],chnl[p1],q,p2,m0,m1,m2]),{j,1,2}]),
	  passVeltCdisc[r_?Positive,0,0,chnl[p1_],q_,p2_,m0_,m1_,m2_] -> 
	    1/(4r)*(2m0^2 passVeltCdisc[r-1,0,0,chnl[p1],q,p2,m0,m1,m2]+f[[1]] passVeltCdisc[r-1,1,0,chnl[p1],q,p2,m0,m1,m2]+f[[2]] passVeltCdisc[r-1,0,1,chnl[p1],q,p2,m0,m1,m2]),
	  passVeltCdisc[r_,n1_?Positive,n2_,chnl[p1_],q_,p2_,m0_,m1_,m2_] ->
	    1/(2*detZ) (adjZ[[1,2]]*If[n2==0,disc[refineB][r,n1-1,chnl[p1],m0,m1],0] +
		Sum[adjZ[[1,j]]*(-f[[j]]passVeltCdisc[r,n1-1,n2,chnl[p1],q,p2,m0,m1,m2]-If[n[[j]]-KroneckerDelta[1,j]==0,0,Evaluate[2(n[[j]]-KroneckerDelta[1,j])passVeltCdisc[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],chnl[p1],q,p2,m0,m1,m2]]]),{j,1,2}]),

	  passVeltCdisc[r_,n1_,n2_,p1_,chnl[q_],p2_,m0_,m1_,m2_] /; r<0 -> 1/detX * (4*detZ*(2(2-2*Eps+n1+n2+2r)*passVeltCdisc[r+1,n1,n2,p1,chnl[q],p2,m0,m1,m2]-disc[pvBs][r,n1,n2,chnl[q],m1,m2]) + Sum[-2*adjX0[[j]]*( - disc[pvBs][r,n1,n2,chnl[q],m1,m2] - 2*n[[j]]*passVeltCdisc[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,chnl[q],p2,m0,m1,m2]),{j,1,2}]),
	  passVeltCdisc[r_?Positive,0,0,p1_,chnl[q_],p2_,m0_,m1_,m2_] -> 
	    1/(4r)*(disc[pvBs][r-1,0,0,chnl[q],m1,m2]+2m0^2 passVeltCdisc[r-1,0,0,p1,chnl[q],p2,m0,m1,m2]+f[[1]] passVeltCdisc[r-1,1,0,p1,chnl[q],p2,m0,m1,m2]+f[[2]] passVeltCdisc[r-1,0,1,p1,chnl[q],p2,m0,m1,m2]),
	  passVeltCdisc[r_,n1_?Positive,n2_,p1_,chnl[q_],p2_,m0_,m1_,m2_] ->
	    1/(2*detZ) (Sum[adjZ[[1,j]]*(-disc[pvBs][r,n1-1,n2,chnl[q],m1,m2]-f[[j]]passVeltCdisc[r,n1-1,n2,p1,chnl[q],p2,m0,m1,m2]-If[n[[j]]-KroneckerDelta[1,j]==0,0,Evaluate[2(n[[j]]-KroneckerDelta[1,j])passVeltCdisc[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,chnl[q],p2,m0,m1,m2]]]),{j,1,2}]),

	  passVeltCdisc[r_,n1_,n2_,p1_,q_,chnl[p2_],m0_,m1_,m2_] /; r<0 -> 1/detX * (4*detZ*(2(2-2*Eps+n1+n2+2r)*passVeltCdisc[r+1,n1,n2,p1,q,chnl[p2],m0,m1,m2]) -2*adjX0[[1]]*If[n1==0,disc[refineB][r,n2,chnl[p2],m0,m2],0] + Sum[-2*adjX0[[j]]*(- 2*n[[j]]*passVeltCdisc[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,chnl[p2],m0,m1,m2]),{j,1,2}]),
	  passVeltCdisc[r_?Positive,0,0,p1_,q_,chnl[p2_],m0_,m1_,m2_] -> 
	    1/(4r)*(2m0^2 passVeltCdisc[r-1,0,0,p1,q,chnl[p2],m0,m1,m2]+f[[1]] passVeltCdisc[r-1,1,0,p1,q,chnl[p2],m0,m1,m2]+f[[2]] passVeltCdisc[r-1,0,1,p1,q,chnl[p2],m0,m1,m2]),
	  passVeltCdisc[r_,n1_?Positive,n2_,p1_,q_,chnl[p2_],m0_,m1_,m2_] ->
	    1/(2*detZ) (adjZ[[1,1]]*(If[n1-1==0,disc[refineB][r,n2,chnl[p2],m0,m2],0]) + 
		Sum[adjZ[[1,j]]*(-f[[j]]passVeltCdisc[r,n1-1,n2,p1,q,chnl[p2],m0,m1,m2]-If[n[[j]]-KroneckerDelta[1,j]==0,0,Evaluate[2(n[[j]]-KroneckerDelta[1,j])passVeltCdisc[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,chnl[p2],m0,m1,m2]]]),{j,1,2}])

	};

];


disc[refineC][r_Integer,n1_Integer,n2_Integer,p1_,q_,p2_,m0_,m1_,m2_] /; Count[{p1,q,p2},_chnl]==1 :=
  Module[{
    f={p1-m1^2+m0^2,p2-m2^2+m0^2},
    gramZ={{p1, -(q-p1-p2)/2},{-(q-p1-p2)/2, p2}},
    adjZ={{p2, (q-p1-p2)/2},{(q-p1-p2)/2, p1}},
	Xij,
    adjX0,adjXij,
    i,j,k,m,n},

  Xij={{m0^2,f[[1]]/2,f[[2]]/2},{f[[1]]/2,p1,-(q-p1-p2)/2},{f[[2]]/2,-(q-p1-p2)/2,p2}};
  adjX0=Table[Sum[adjZ[[j,k]]f[[k]],{k,1,2}],{j,1,2}]; (*up to a constant: -1*)
  adjXij=Table[4m0^2 adjZ[[i,j]]+Sum[(KroneckerDelta[i,m]KroneckerDelta[n,j]-KroneckerDelta[i,j]KroneckerDelta[n,m])f[[n]] f[[m]],{n,1,2},{m,1,2}],{i,1,2},{j,1,2}];
  
  Which[

	PossibleZeroQ[Det[gramZ]/.chnl:>Identity],0,

    ((PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] && PossibleZeroQ[m1]) (*(p1===m0^2 && q===m2^2 && m1===0)*)  (* p2 may or may not vanish*)
     || (PossibleZeroQ[p2-m0^2] && PossibleZeroQ[q-m1^2] && PossibleZeroQ[m2]) (*(p2===m0^2 && q===m1^2  && m2===0)*)  (* p1 may or may not vanish*)
     || (PossibleZeroQ[p1-m1^2] && PossibleZeroQ[p2-m2^2] && PossibleZeroQ[m0]) (*(p1===m1^2 && p2===m2^2  && m0===0)*)) (* q may or may not vanish*),
    (*Print["Case 2: Triangle 6; Xij=", Xij, "adjXij=",adjXij, "and adjX0j=",adjX0];*)
    passVeltCdisc[r,n1,n2,p1,q,p2,m0,m1,m2] = Replace[passVeltCdisc[r,n1,n2,p1,q,p2,m0,m1,m2],refineDiscRulesCtriangle6] ,


	((PossibleZeroQ[q] && PossibleZeroQ[m2] && PossibleZeroQ[m1]) (*(q===0 && m2===0 && m1===0)*)
	 || (PossibleZeroQ[p1] && PossibleZeroQ[m1] && PossibleZeroQ[m0]) (*(p1===0 && m1===0 && m0===0)*)
	 || (PossibleZeroQ[p2] && PossibleZeroQ[m2] && PossibleZeroQ[m0]) (*(p2===0 && m2===0 && m0===0)*)),
	(*Print["PVC for triangle 2 & 3"];*)
	Replace[passVeltCdisc[r,n1,n2,p1,q,p2,m0,m1,m2],refineDiscRulesCtriangle3],

    Positive[r](* && !(PossibleZeroQ[Det[gramZ]])*) || r===0 && PossibleZeroQ[Det[Xij]/.chnl:>Identity],
    (*Print["Case 1: detZ nonZero; r=", r];*)
    passVeltCdisc[r,n1,n2,p1,q,p2,m0,m1,m2] = ReplaceRepeated[passVeltCdisc[r,n1,n2,p1,q,p2,m0,m1,m2],refineDiscRulesCcase1] ,
  
	NonPositive[r] && !(PossibleZeroQ[Det[Xij]/.chnl:>Identity]),
	(*Print["PVC for r<0: Det[X]!=0"];*)
	passVeltCdisc[r,n1,n2,p1,q,p2,m0,m1,m2] = ReplaceRepeated[passVeltCdisc[r,n1,n2,p1,q,p2,m0,m1,m2],refineDiscRulesCnegativer],

	True,
	Message[LoopRefine::leadinglandau, PVC[r,n1,n2,p1,q,p2,m0,m1,m2]/.chnl->Identity]; 
	PVC[r,n1,n2,p1,q,p2,m0,m1,m2]/.chnl->Identity
  ]
];

disc[refineC][r_Integer,n1_Integer,n2_Integer,p1_,q_,p2_,m0_,m1_,m2_] := 0;


(* ::Subsubsection::Closed:: *)
(*D functions*)


(*Shifted C-functions; due to unshifted pinched propagator*)
disc[pvCs][r_,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_]/;(n3 < n1 && n3 < n2) := disc[pvCs][r,n3,n2,n1,s3,s2,s23,m3,m2,m1];
disc[pvCs][r_,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_]/;(n2 < n1 && n2 < n3) := disc[pvCs][r,n2,n1,n3,s2,s23,s3,m2,m1,m3];
disc[pvCs][r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_] := (-1)^n1 Sum[Multinomial[idx1,idx2,n1-idx1-idx2]disc[refineC][r,n2+idx2,n1+n3-idx1-idx2,s2,s3,s23,m1,m2,m3],{idx1,0,n1},{idx2,0,n1-idx1}];

(*Construct the rules from the full reduction formula:
  Eliminate passvelt functions independent of channel variable (these don't exhibit a cut),
  Wrap passVeltD,pvCs,refineC with disc (accomplished with MapAt),
  Wrap channel variables with chnl*)

discHead=Switch[#,passVeltD,passVeltDdisc,pvCs,disc[pvCs],refineC,disc[refineC]]& ;

refineDiscRulesDcase4a := refineDiscRulesDcase4a=
  Transpose@List[ refineRulesDcase4a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s1],0,MapAt[discHead,(expr/.{Verbatim[s1_]:>chnl[s1_],s1->chnl[s1]}),0]]],
		refineRulesDcase4a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s2],0,MapAt[discHead,(expr/.{Verbatim[s2_]:>chnl[s2_],s2->chnl[s2]}),0]]],
		refineRulesDcase4a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s3],0,MapAt[discHead,(expr/.{Verbatim[s3_]:>chnl[s3_],s3->chnl[s3]}),0]]],
		refineRulesDcase4a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s4],0,MapAt[discHead,(expr/.{Verbatim[s4_]:>chnl[s4_],s4->chnl[s4]}),0]]],
		refineRulesDcase4a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s12],0,MapAt[discHead,(expr/.{Verbatim[s12_]:>chnl[s12_],s12->chnl[s12]}),0]]],
		refineRulesDcase4a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s23],0,MapAt[discHead,(expr/.{Verbatim[s23_]:>chnl[s23_],s23->chnl[s23]}),0]]]] /. {_pvDDivUV:>RuleCondition[0],HoldPattern[If[_, 0, 0]]:>RuleCondition[0]};

refineDiscRulesDcase4b := refineDiscRulesDcase4b=
  Transpose@List[ refineRulesDcase4b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s1],0,MapAt[discHead,(expr/.{Verbatim[s1_]:>chnl[s1_],s1->chnl[s1]}),0]]],
		refineRulesDcase4b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s2],0,MapAt[discHead,(expr/.{Verbatim[s2_]:>chnl[s2_],s2->chnl[s2]}),0]]],
		refineRulesDcase4b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s3],0,MapAt[discHead,(expr/.{Verbatim[s3_]:>chnl[s3_],s3->chnl[s3]}),0]]],
		refineRulesDcase4b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s4],0,MapAt[discHead,(expr/.{Verbatim[s4_]:>chnl[s4_],s4->chnl[s4]}),0]]],
		refineRulesDcase4b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s12],0,MapAt[discHead,(expr/.{Verbatim[s12_]:>chnl[s12_],s12->chnl[s12]}),0]]],
		refineRulesDcase4b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s23],0,MapAt[discHead,(expr/.{Verbatim[s23_]:>chnl[s23_],s23->chnl[s23]}),0]]]] /. {_pvDDivUV:>RuleCondition[0],HoldPattern[If[_, 0, 0]]:>RuleCondition[0]};

refineDiscRulesDcase4c := refineDiscRulesDcase4c=
  Transpose@List[ refineRulesDcase4c /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s1],0,MapAt[discHead,(expr/.{Verbatim[s1_]:>chnl[s1_],s1->chnl[s1]}),0]]],
		refineRulesDcase4c /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s2],0,MapAt[discHead,(expr/.{Verbatim[s2_]:>chnl[s2_],s2->chnl[s2]}),0]]],
		refineRulesDcase4c /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s3],0,MapAt[discHead,(expr/.{Verbatim[s3_]:>chnl[s3_],s3->chnl[s3]}),0]]],
		refineRulesDcase4c /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s4],0,MapAt[discHead,(expr/.{Verbatim[s4_]:>chnl[s4_],s4->chnl[s4]}),0]]],
		refineRulesDcase4c /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s12],0,MapAt[discHead,(expr/.{Verbatim[s12_]:>chnl[s12_],s12->chnl[s12]}),0]]],
		refineRulesDcase4c /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s23],0,MapAt[discHead,(expr/.{Verbatim[s23_]:>chnl[s23_],s23->chnl[s23]}),0]]]] /. {_pvDDivUV:>RuleCondition[0],HoldPattern[If[_, 0, 0]]:>RuleCondition[0]};


refineDiscRulesDcase3a := refineDiscRulesDcase3a=
  Transpose@List[ refineRulesDcase3a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s1],0,MapAt[discHead,(expr/.{Verbatim[s1_]:>chnl[s1_],s1->chnl[s1]}),0]]],
		refineRulesDcase3a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s2],0,MapAt[discHead,(expr/.{Verbatim[s2_]:>chnl[s2_],s2->chnl[s2]}),0]]],
		refineRulesDcase3a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s3],0,MapAt[discHead,(expr/.{Verbatim[s3_]:>chnl[s3_],s3->chnl[s3]}),0]]],
		refineRulesDcase3a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s4],0,MapAt[discHead,(expr/.{Verbatim[s4_]:>chnl[s4_],s4->chnl[s4]}),0]]],
		refineRulesDcase3a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s12],0,MapAt[discHead,(expr/.{Verbatim[s12_]:>chnl[s12_],s12->chnl[s12]}),0]]],
		refineRulesDcase3a /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s23],0,MapAt[discHead,(expr/.{Verbatim[s23_]:>chnl[s23_],s23->chnl[s23]}),0]]]] /. {_pvDDivUV:>RuleCondition[0],HoldPattern[If[_, 0, 0]]:>RuleCondition[0]};

refineDiscRulesDcase3b := refineDiscRulesDcase3b=
  Transpose@List[ refineRulesDcase3b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s1],0,MapAt[discHead,(expr/.{Verbatim[s1_]:>chnl[s1_],s1->chnl[s1]}),0]]],
		refineRulesDcase3b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s2],0,MapAt[discHead,(expr/.{Verbatim[s2_]:>chnl[s2_],s2->chnl[s2]}),0]]],
		refineRulesDcase3b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s3],0,MapAt[discHead,(expr/.{Verbatim[s3_]:>chnl[s3_],s3->chnl[s3]}),0]]],
		refineRulesDcase3b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s4],0,MapAt[discHead,(expr/.{Verbatim[s4_]:>chnl[s4_],s4->chnl[s4]}),0]]],
		refineRulesDcase3b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s12],0,MapAt[discHead,(expr/.{Verbatim[s12_]:>chnl[s12_],s12->chnl[s12]}),0]]],
		refineRulesDcase3b /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s23],0,MapAt[discHead,(expr/.{Verbatim[s23_]:>chnl[s23_],s23->chnl[s23]}),0]]]] /. {_pvDDivUV:>RuleCondition[0],HoldPattern[If[_, 0, 0]]:>RuleCondition[0]};

refineDiscRulesDcase1 := refineDiscRulesDcase1=
  Join[ refineRulesDcase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s1],0,MapAt[discHead,(expr/.{Verbatim[s1_]:>chnl[s1_],s1->chnl[s1]}),0]]],
		refineRulesDcase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s2],0,MapAt[discHead,(expr/.{Verbatim[s2_]:>chnl[s2_],s2->chnl[s2]}),0]]],
		refineRulesDcase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s3],0,MapAt[discHead,(expr/.{Verbatim[s3_]:>chnl[s3_],s3->chnl[s3]}),0]]],
		refineRulesDcase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s4],0,MapAt[discHead,(expr/.{Verbatim[s4_]:>chnl[s4_],s4->chnl[s4]}),0]]],
		refineRulesDcase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s12],0,MapAt[discHead,(expr/.{Verbatim[s12_]:>chnl[s12_],s12->chnl[s12]}),0]]],
		refineRulesDcase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s23],0,MapAt[discHead,(expr/.{Verbatim[s23_]:>chnl[s23_],s23->chnl[s23]}),0]]]] /. {_pvDDivUV:>RuleCondition[0],HoldPattern[If[_, 0, 0]]:>RuleCondition[0]};

refineDiscRulesDnegativerCase1 := refineDiscRulesDnegativerCase1=
  Join[ refineRulesDnegativerCase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s1],0,MapAt[discHead,(expr/.{Verbatim[s1_]:>chnl[s1_],s1->chnl[s1]}),0]]],
		refineRulesDnegativerCase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s2],0,MapAt[discHead,(expr/.{Verbatim[s2_]:>chnl[s2_],s2->chnl[s2]}),0]]],
		refineRulesDnegativerCase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s3],0,MapAt[discHead,(expr/.{Verbatim[s3_]:>chnl[s3_],s3->chnl[s3]}),0]]],
		refineRulesDnegativerCase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s4],0,MapAt[discHead,(expr/.{Verbatim[s4_]:>chnl[s4_],s4->chnl[s4]}),0]]],
		refineRulesDnegativerCase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s12],0,MapAt[discHead,(expr/.{Verbatim[s12_]:>chnl[s12_],s12->chnl[s12]}),0]]],
		refineRulesDnegativerCase1 /. expr:(passVeltD|pvCs|refineC)[___] :> RuleCondition[If[FreeQ[expr,s23],0,MapAt[discHead,(expr/.{Verbatim[s23_]:>chnl[s23_],s23->chnl[s23]}),0]]]] /. {_pvDDivUV:>RuleCondition[0],HoldPattern[If[_, 0, 0]]:>RuleCondition[0]};

refineDoubleDiscRulesD := refineDoubleDiscRulesD=
  Join[ refineRulesDnegativerCase1 /. expr: passVeltD[___] :> RuleCondition[If[FreeQ[expr,s1]||FreeQ[expr,s3],0,MapAt[discHead,(expr/.{Verbatim[s1_]:>chnl[s1_],s1->chnl[s1],Verbatim[s3_]:>chnl[s3_],s3->chnl[s3]}),0]]],
		refineRulesDnegativerCase1 /. expr: passVeltD[___] :> RuleCondition[If[FreeQ[expr,s2]||FreeQ[expr,s4],0,MapAt[discHead,(expr/.{Verbatim[s2_]:>chnl[s2_],s2->chnl[s2],Verbatim[s4_]:>chnl[s4_],s4->chnl[s4]}),0]]],
		refineRulesDnegativerCase1 /. expr: passVeltD[___] :> RuleCondition[If[FreeQ[expr,s12]||FreeQ[expr,s23],0,MapAt[discHead,(expr/.{Verbatim[s12_]:>chnl[s12_],s12->chnl[s12],Verbatim[s23_]:>chnl[s23_],s23->chnl[s23]}),0]]]
  ] /. {_pvDDivUV|_pvCs|_refineC:>RuleCondition[0],HoldPattern[If[_, 0, 0]]:>RuleCondition[0]};


disc[refineD][r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] /; Count[{s1,s2,s3,s4,s12,s23},_chnl]==1 :=
  Module[{
	position = First[First[Position[{s1,s2,s3,s4,s12,s23},chnl[_],1,1]]],
    f={s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2}/.chnl:>Identity,
    gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }}/.chnl:>Identity,
    adjZ={{s12 s4-1/4 (s12-s3+s4)^2,1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4))},{1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),s1 s4-1/4 (s1-s23+s4)^2,1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4))},{1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4)),1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4)),s1 s12-1/4 (s1+s12-s2)^2}}/.chnl:>Identity,
    (*detZ=1/4*(-s12^2 s23-s1^2 s3+s12 (-(s23-s3) (s23-s4)+s2 (s23+s4))-s2 (s23 (s3-s4)+s4 (s2-s3+s4))+s1 (s12 (-s2+s23+s3)+(s23-s3) (s3-s4)+s2 (s3+s4))),*)
	adjX0,
	adjXij = {{2 (-m0^4 s3-m2^4 s4-s12 (m3^4+m3^2 (s12-s3-s4)+s3 s4)+m2^2 ((s12+s3-s4) s4+m3^2 (s12-s3+s4))+m0^2 (m3^2 (s12+s3-s4)+s3 (s12-s3+s4)+m2^2 (-s12+s3+s4))),-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s12-s3+s4) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4)),(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4)-2 s12 (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))+(m0^2-m2^2+s12) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4))},{-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s1-s23+s4) (-(m0^2-m2^2+s12) (m0^2-m3^2+s4)+2 m0^2 (s12-s3+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s12-s3+s4)),2 (-m0^4 s23-m1^4 s4-s1 (m3^4+m3^2 (s1-s23-s4)+s23 s4)+m1^2 ((s1+s23-s4) s4+m3^2 (s1-s23+s4))+m0^2 (m3^2 (s1+s23-s4)+s23 (s1-s23+s4)+m1^2 (-s1+s23+s4))),-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4)+(s1+s12-s2) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m2^2+s12) (-2 s1 (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s1-s23+s4))},{(2 (m0^2-m1^2+s1) s12-(m0^2-m2^2+s12) (s1+s12-s2)) (m0^2-m3^2+s4)-(4 m0^2 s12-(m0^2-m2^2+s12)^2) (s1-s23+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4),-(-2 s1 (m0^2-m2^2+s12)+(m0^2-m1^2+s1) (s1+s12-s2)) (m0^2-m3^2+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s1-s23+s4)-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4),2 (-m1^4 s12-m0^4 s2-s1 (m2^4+m2^2 (s1-s12-s2)+s12 s2)+m1^2 (m2^2 (s1+s12-s2)+s12 (s1-s12+s2))+m0^2 ((s1+s12-s2) s2+m2^2 (s1-s12+s2)+m1^2 (-s1+s12+s2)))}}/.chnl:>Identity,
    mtxX = {{2*m0^2, s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
			{s1-m1^2+m0^2, 2*s1, s1+s12-s2, s1-s23+s4},
			{s12-m2^2+m0^2, s1+s12-s2, 2*s12, s12-s3+s4},
			{s4-m3^2+m0^2, s1-s23+s4, s12-s3+s4, 2*s4}}/.chnl:>Identity,
    j,k},

	adjX0=Table[Sum[adjZ[[j,k]]f[[k]],{k,1,3}],{j,1,3}];
 
  Which[

	X`Internal`PossibleAllZeroQ[gramZ], 0,

	PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0] && !(X`Internal`PossibleAllZeroQ[adjXij]),
	(*Print["Case 4 PVD: det Z=0, adjX0=0"];*)
	  With[{siga=First@Ordering[Flatten[Factor[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
			sigb=First@Ordering[Flatten[Factor[adjXij]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
			(*Print["adjZ=", adjZ, "  sig:", siga];*)
			(*Print["adjXij=", adjXij, "  sig:", sigb];*)
			passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = ReplaceRepeated[passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineDiscRulesDcase4a[[siga,position]],refineDiscRulesDcase4b[[sigb,position]],refineDiscRulesDcase4c[[sigb,position]]}]
	  ],

	PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3 PVD: detZ=0 && one of adjX0 nonzero."];*)
      With[{
        siga=First@Ordering[Flatten[Factor[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
        sigb=First@Ordering[Factor[adjX0],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
        (*Print["adjZ=", adjZ, "  sig a:", siga];
		Print["adjX0=", adjX0, "  sig b:", sigb];*)
        passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = Dot[Together[Coefficient[#,Eps,{-1,0}]],{1/Eps,1}] &@ ReplaceRepeated[passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{refineDiscRulesDcase3a[[siga,position]],refineDiscRulesDcase3b[[sigb,position]]}]
      ],
	
	PossibleZeroQ[Det[mtxX]], Message[LoopRefine::leadinglandau, PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]/.chnl->Identity]; PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]/.chnl->Identity, 

    Positive[r],
    (*Print["Case 1:, DetZ=", Det[gramZ],",  adjZ=", MatrixForm[adjZ],";  adjXij=", adjXij];*)
    passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = Dot[Together[Coefficient[#,Eps,{-1,0}]],{1/Eps,1}] &@ ReplaceRepeated[passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineDiscRulesDcase1],

	NonPositive[r],
	(*Print["PVD r<=0: Det[X]!=0"];*)
	passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = Dot[Together[Coefficient[#,Eps,{-1,0}]],{1/Eps,1}] &@ ReplaceRepeated[passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineDiscRulesDnegativerCase1]

  ]
 
];

disc[refineD][r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] := 0;


(*Mandelstam double spectral*)

disc[refineD][r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] /; Count[{s1,s2,s3,s4,s12,s23},_chnl]==2 :=
  Module[{

    gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }}/.chnl:>Identity,
    
    mtxX = {{2*m0^2, s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
			{s1-m1^2+m0^2, 2*s1, s1+s12-s2, s1-s23+s4},
			{s12-m2^2+m0^2, s1+s12-s2, 2*s12, s12-s3+s4},
			{s4-m3^2+m0^2, s1-s23+s4, s12-s3+s4, 2*s4}}/.chnl:>Identity
	},
 
  Which[

	PossibleZeroQ[Det[gramZ]], 0,
	PossibleZeroQ[Det[mtxX]], Message[LoopRefine::leadinglandau, PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]/.chnl->Identity]; PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]/.chnl->Identity, 

    True,
    (*Print["Case 1:, DetZ=", Det[gramZ],",  adjZ=", MatrixForm[adjZ],";  adjXij=", adjXij];*)
    passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = ReplaceRepeated[passVeltDdisc[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],refineDoubleDiscRulesD]

  ]
 
];

disc[refineD][r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] := 0;


(* ::Section::Closed:: *)
(*LoopRefine*)


(* ::Subsection::Closed:: *)
(*OptimizeExpression*)


(*Helper function for collectEpsilonLog below*)
(*For 1/Eps terms*)
(*Collect restTimes\[Epsilon] / Eps + restTimesLog Lop[scale/Mu^2]*)
(*The reason to Simplify[KallenExpand[Times[restTimes\[Epsilon]]]] is to bring to polynomial form*)
collectEpsilonOrderMinus1Log = 
	Function[expr,
	  If[FreeQ[expr,Power[Eps,-1]],
		(*If expression is free of 1/Eps pole, then check if there is only one logarithm dependent on Mu*)
		(*With[{tHooftLogs=Union[Cases[expr, Log[scale_. Power[Mu,exp_]],{0,Infinity}]]},
		  If[Length[tHooftLogs]==1,  expr/.First[tHooftLogs]:>0, expr]
		]*)expr,
		Replace[expr,
		  RuleDelayed[
			Plus[restPlus_.,Times[restTimes\[Epsilon]_.,Power[Eps,-1]],  Times[restTimesLog_.,Log[Times[scale_.,Power[Mu,exp_]]]]] /; PossibleZeroQ[Times[restTimes\[Epsilon]]-Sign[exp]Times[restTimesLog]],
			Plus[restPlus,Times[restTimes\[Epsilon],Plus[Power[Eps,-1],Sign[exp]Log[Times[scale,Power[Mu,exp]]]]]]
		  ]
		]
	  ]
	];

(*For 1/Eps^2 terms*)
collectEpsilonLog=
	Function[expr,
		If[FreeQ[expr,Power[Eps,-2]] (*Are there 1/Eps^2 terms? *),
			collectEpsilonOrderMinus1Log[expr] (*If not, just collect 1/Eps + Log terms.*),
			(*First, expand out 1/Eps terms.*)
			(*Then, take restPlus + restTimes\[Epsilon]2/Eps^2 + restTimes\[Epsilon]*Log[scale/Mu^2]/Eps, check that restTimes\[Epsilon]2 === restTimes\[Epsilon] ...
			  and collect:  restPlus + restTimes\[Epsilon]2(1/Eps^2+Log[scale/Mu^2]/Eps) ... *)
			Replace[expr/.Times[(restTimes_+c_. Log[scale_ Power[Mu,exp_]]),Power[Eps,-1]]:>restTimes*Power[Eps,-1]+c Log[scale Power[Mu,exp]]*Power[Eps,-1],
			  RuleDelayed[
				Plus[restPlus_.,Times[restTimes\[Epsilon]2_.,Power[Eps,-2]],Times[restTimes\[Epsilon]_.,Power[Eps,-1],Log[Times[scale_.,Power[Mu,exp_]]]],Times[restTimes\[Epsilon]0_.,Power[Log[Times[scale_.,Power[Mu,exp_]]],2]]]/;PossibleZeroQ[Times[restTimes\[Epsilon]2]-Sign[exp]Times[restTimes\[Epsilon]]]&&PossibleZeroQ[Times[restTimes\[Epsilon]2]-2*Times[restTimes\[Epsilon]0]],
				(*And, on the restPlus, collect (1/Eps + Log[scale/Mu^2])*) 
				Plus[collectEpsilonOrderMinus1Log[Collect[Plus[restPlus],Eps]], restTimes\[Epsilon]2(Power[Eps,-2]+Power[Eps,-1] Log[scale Power[Mu,exp]]+Log[scale Power[Mu,exp]]^2/2)]
			  ]
			]
		]
	];


(*The arguments of logarithms to be matched are expanded in case they are compound expressions,
  involving gauge-dependence or sin^2w*)

logExchangeFunction=
	Function[{i,j,k,intMass},
	  With[
		{log1=olog[intMass[[i]]^2,intMass[[j]]^2],
		 log2=olog[intMass[[i]]^2,intMass[[k]]^2],
		 log3=olog[intMass[[k]]^2,intMass[[j]]^2]},

	  Collect[ReplaceAll[#,Rule[log1, log2+log3]], {Log[__]}, rationalCoefficientSimplify]&
	]
  ];


expressionOptimizer[expr_, intMass_(*List*), {1}(*Tensor structures (Ununsed)*),"FunctionExpand"] := 
  Collect[expr/.Log[x_]:>Log[Together[x]] ,{_ScalarC0,_DiLog,_PolyLog,_DiscB,_Ln,_Log,\[Pi]},rationalCoefficientSimplify];


expressionOptimizer[expr_, intMass_(*List*), tensorStructures_(*List*),"Discontinuity"] := 
  Module[{answer, rationalCoefficientSimplify = (FactorSquareFree@(Expand[Numerator[#]]*Expand[Denominator[#]]^(-1)&)@(Together[#] /. {e:Power[_Kallen\[Lambda], Rational[1,2]|(_?Negative)]:>e, Power[Kallen\[Lambda][a_,b_,c_], Rational[p_,2]]:>((a^2+b^2+c^2-2a b-2b c-2a c)^Floor[p/2])Kallen\[Lambda][a,b,c]^(1/2), Kallen\[Lambda][a_,b_,c_]:>a^2+b^2+c^2-2a b-2b c-2a c, Kibble\[Phi][s1_,s2_,s3_,s4_,s12_,s23_]:>-s12^2 s23-s1^2 s3+s12 (-(s23-s3) (s23-s4)+s2 (s23+s4))-s2 (s23 (s3-s4)+s4 (s2-s3+s4))+s1 (s12 (-s2+s23+s3)+(s23-s3) (s3-s4)+s2 (s3+s4))} ))&},

	(*Collect first time to simplify the rational functions, multiplying *)
	answer=Collect[expr, {Eps,_Log}, rationalCoefficientSimplify];

	2 \[Pi] I collectEpsilonOrderMinus1Log[Collect[answer/(2 \[Pi] I),{Eps,_Log,Power[_Kallen\[Lambda]|_Kibble\[Phi],_Rational]},Collect[#,tensorStructures,rationalCoefficientSimplify]&]]
  ];


expressionOptimizer[expr_, intMass_(*List*), tensorStructures_(*List*)] := 
  Module[{specialFunctions=Sequence[_ScalarD0IR16,_ScalarD0IR13,_ScalarD0IR12,_ScalarD0,_ScalarC0IR6,_ScalarC0,_DiLog,_PolyLog,_DiscB,_Ln,_Log],
		  answer, posLog, posLogTransFuncts, posLogSimplify, restSimplify},

	(*Expand arguments of logarithms to facilitate matching of logarithms with positive mass variables.
	  This is necessary when masses are compound expressions involving gauge-dependence or sin^2w*)
	answer=expr/.Log[x_]:>Log[Together[x]];

	(*answer=expr;*)
	answer=Collect[answer, {Eps,Log[Times[_,Power[Mu,exp_]]],specialFunctions}];

	If[Length[intMass]<3 || Head[answer]=!=Plus,
	  (*If there are less than 3 positive variables with which to make logarithms*)
	  (*Or contains just one term*)
	  collectEpsilonLog@Collect[answer,{Eps,Log[Times[___,Power[Mu,exp_]]],specialFunctions,\[Pi]},Collect[#,tensorStructures,rationalCoefficientSimplify]&]
	  
	   ,

	  (*If there are 3 or more positive variables with which to make logarithms*)
	  posLog=Alternatives@@Flatten[Table[(Log[#1*#2^(-1)]&)@@Sort[{intMass[[i]]^2,intMass[[j]]^2}],{i,1,Length[intMass]},{j,i+1,Length[intMass]}]/.Log[NArg_]:>Log[Expand[NArg]]];
	  posLogTransFuncts= 
		Flatten[
		  Table[
			logExchangeFunction[i,j,k,intMass]
			  ,{i,1,Length[intMass]},{j,i+1,Length[intMass]},{k,Delete[Range[Length[intMass]],{{i},{j}}]}
		  ]
		];

		posLogSimplify = Collect[Plus[Simplify[#,TransformationFunctions->posLogTransFuncts,ComplexityFunction->LeafCount,Assumptions->True]],{_Log}~Join~tensorStructures,Together]& ;
		restSimplify = Collect[Plus[#],{Eps,Log[Times[___,Power[Mu,exp_]]],specialFunctions,\[Pi]},Collect[#,tensorStructures,rationalCoefficientSimplify]&] &;

		(*It is known that Head[answer]==Plus because it was tested above*)
		answer = (posLogSimplify[Plus@@#] + restSimplify[Plus@@Complement[List@@answer,#]])&[Cases[answer, _.(posLog)]] ;

		(*Finally, bring the epsilon poles together with the mu-dependent logarithms*)
		collectEpsilonLog@answer
		
	]
  ];


(* ::Subsection::Closed:: *)
(*Helper functions*)


exactExpressionQ = Function[If[FreeQ[#, _Real|_Complex(*?InexactNumberQ*), {-1}],True,Message[LoopRefine::inexact,#];Throw[Fail, "InexactPV"];False]];


(*Check that the input expression is a polynomial in Eps,Dim.
  If so, just use coefficient (which is fast) to pick out the coefficients in the Laurent Eps-expansion.
  If not, need to do it carefuly with Series. *)

(*Cannot take Set[FeynmanIRepsilon,0], otherwise memoization gets confused*)
limitDto4dimensions=Function[{inputExpr, expr, dim, ord},
 Block[{Dim=dim-2Eps},
  If[TrueQ[Internal`PolynomialFunctionQ[inputExpr, Eps]],
	Total[Sum[Coefficient[expr,Eps,p]/Eps^(-p),{p,-2,ord}]],
	Total[Normal[Series[expr,{Eps,0,ord},Analytic->False]]]
  ]
 ]
];


(*With Analytic\[Rule]False, check for the dependence on FeynmanIRepsilon (signaling the presence of a power IR divergence).
  If FeynmanIRepsilon has cancelled away, or Analytic\[Rule]True, set FeynmanIRepsilon\[Rule]0. *)

clearFeynmanIRepsilon=Function[{expr, optAnalytic},
  If[!optAnalytic && !FreeQ[expr,FeynmanIRepsilon],
	If[!(PossibleZeroQ[D[expr,FeynmanIRepsilon]]),
		Message[LoopRefine::irdiv];
		Throw[ComplexInfinity, "PowerIRSingularity"],
		expr/.FeynmanIRepsilon->0
	  ],
  expr/.FeynmanIRepsilon->0
  ]];


(*With Analytic\[Rule]False, check for the dependence on FeynmanIRepsilon (signaling the presence of a power IR divergence).
  If FeynmanIRepsilon has cancelled away, or Analytic\[Rule]True, set FeynmanIRepsilon\[Rule]0. *)

tHooftLogTransform = Function[{expr, internalMasses, optTargetScale},
  With[{tar=
	Switch[
	  optTargetScale,
	  Automatic,
	  (*If there are internalMasses AND there is more than one type of logarithm, 
		then default value is first element in internalMasses; otherwise default is Mu (which does nothing).*)
		If[internalMasses=!={} && Length[DeleteDuplicates@Cases[expr, Log[Times[Power[Mu,2],_]], Infinity]]>1, 
		  First[internalMasses], Mu],
	  _,
	  (*If the user has defined a symbol for Target scale, then set tar equal to that.*)
		optTargetScale
	]},
	

	If[tar=!=Mu,
	  (*If targetScale is NOT Mu, begin to reorganize expression*)
      With[{positiveVariablesAssumptions=And@@(Greater[#,0]&/@((Append[internalMasses,tar])^2))},
	  (*Using TrueQ to force 'False' if cannot be decided that y_ is positive*)
		expr/.Log[Times[Power[Mu,2],y_]]:>(Log[Mu^2/tar^2] +
		  If[TrueQ[Assuming[positiveVariablesAssumptions,Refine[Times[y]>0]]],
			olog[tar^2,Times[y]^-1], Log[Times[y]*tar^2]])
	  ],
	  expr
	]
  ]

];


(* ::Subsection:: *)
(*Internal LoopRefine*)


(* ::Subsubsection::Closed:: *)
(*Part: Discontinuity*)


(****** Discontinuity ******)
internalLoopRefine[tensorStructures_, optionValueTargetScale_, dim_, optionValueExplicitC0_, optionValueOrganization_, Discontinuity[var_], optionValueAnalytic_] =
Function[{expr},
  Module[{answer,checkRatFunList,internalMasses},

	If[!FreeQ[expr,PVA|PVB|PVC|PVD|_DiscB|_ScalarC0|_ScalarC0IR6|_ScalarD0|_ScalarD0IR12|_ScalarD0IR13|_ScalarD0IR16],
	  If[optionValueAnalytic,
		{answer, checkRatFunList}=Reap[Collect[Catch[makeSer[expr,True],"DerivativesOnly"]/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD,_Kibble\[Phi],_Kallen\[Lambda],_DiscB,_ScalarC0,_ScalarC0IR6,_ScalarD0,_ScalarD0IR12,_ScalarD0IR13,_ScalarD0IR16}, (Sow[Internal`RationalFunctionQ[#,Variables[var]]];Together[#])&]],
		{answer, checkRatFunList}=Reap[Collect[expr/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD,_Kibble\[Phi],_Kallen\[Lambda],_DiscB,_ScalarC0,_ScalarC0IR6,_ScalarD0,_ScalarD0IR12,_ScalarD0IR13,_ScalarD0IR16}, (Sow[Internal`RationalFunctionQ[#,Variables[var]]];Together[#])&]]
	  ],
	  {answer, checkRatFunList}={expr,{{}}}
	];

	(*Check if input is a rational function of channel variable.*)
	If[!(And@@(checkRatFunList[[1]])), Message[LoopRefine::discpoly, var]];

	(*Enclose each PV function in a list*)
	answer=If[Head[answer]===Plus, List@@answer, List@answer];

	{answer,internalMasses}=Reap[Replace[answer,{
		coeff_. (e:PVD[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_])?exactExpressionQ :> 
		  With[{args={Expand[s1],Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23]}},
			If[Count[args,var]<=1,coeff*(disc[refineD][r,n1,n2,n3,##,Sow[m0],Sow[m1],Sow[m2],Sow[m3]]& @@ Replace[args,s:HoldPattern[var]:>chnl[s],{1}]),Message[LoopRefine::discmult,var,e];0]],
		  
		coeff_. (e:ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_])?exactExpressionQ :> 
		  With[{args={Expand[s1],Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23]}},
			If[Count[args,var]<=1,coeff*(disc[refineD][0,0,0,0,##,Sow[m0],Sow[m1],Sow[m2],Sow[m3]]& @@Replace[args,s:HoldPattern[var]:>chnl[s],{1}]),Message[LoopRefine::discmult,var,e];0]],

		coeff_. (e:ScalarD0IR12[s2_,s3_,s12_,s23_,m2_,m3_])?exactExpressionQ :> 
		  With[{args={Expand[s2],Expand[s3],Expand[s12],Expand[s23]}},
			If[Count[args,var]<=1,coeff*(disc[ScalarD0IR12][##,Sow[m2],Sow[m3]]& @@Replace[args,s:HoldPattern[var]:>chnl[s],{1}]),Message[LoopRefine::discmult,var,e];0]],

		coeff_. (e:ScalarD0IR13[s2_,s3_,s4_,s12_,s23_,m2_,m3_])?exactExpressionQ :> 
		  With[{args={Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23]}},
			If[Count[args,var]<=1,coeff*(disc[ScalarD0IR13][##,Sow[m2],Sow[m3]]& @@Replace[args,s:HoldPattern[var]:>chnl[s],{1}]),Message[LoopRefine::discmult,var,e];0]],

		coeff_. (e:ScalarD0IR16[s2_,s3_,s12_,s23_,m1_,m2_,m3_])?exactExpressionQ :> 
		  With[{args={Expand[s2],Expand[s3],Expand[s12],Expand[s23]}},
			If[Count[args,var]<=1,coeff*(disc[ScalarD0IR16][##,Sow[m1],Sow[m2],Sow[m3]]& @@Replace[args,s:HoldPattern[var]:>chnl[s],{1}]),Message[LoopRefine::discmult,var,e];0]],

		coeff_. (e:PVC[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,p1_,q_,p2_,m0_,m1_,m2_])?exactExpressionQ :> 
		  With[{args={Expand[p1],Expand[q],Expand[p2]}},
			If[Count[args,var]<=1,coeff*(disc[refineC][r, n1, n2, ##,Sow[m0],Sow[m1],Sow[m2]]& @@Replace[args,s:HoldPattern[var]:>chnl[s],{1}]),Message[LoopRefine::discmult,var,e];0]],

		coeff_. (e:ScalarC0[p1_,q_,p2_,m0_,m1_,m2_])?exactExpressionQ :> 
		  With[{args={Expand[p1],Expand[q],Expand[p2]}},
			If[Count[args,var]<=1,coeff*(disc[refineC][0,0,0,##,Sow[m0],Sow[m1],Sow[m2]]& @@Replace[args,s:HoldPattern[var]:>chnl[s],{1}]),Message[LoopRefine::discmult,var,e];0]],

		coeff_. ScalarC0IR6[var,m0_,m1_] :> coeff disc[ScalarC0IR6][chnl[var],Sow[m0],Sow[m1]],

        coeff_. PVB[r_Integer,n_Integer?NonNegative,s:HoldPattern[var],m0_,m1_]?exactExpressionQ :> coeff*disc[refineB][r,n,chnl[s],Sow[m0],Sow[m1]],

		coeff_. DiscB[s:HoldPattern[var],m0_,m1_] :> coeff disc[DiscB][chnl[s],Sow[m0],Sow[m1]],

        coeff_. PVA[r_Integer,m0_]?exactExpressionQ :>(Sow[m0];0),
		_:>0},{1}]
	  ];

	internalMasses = DeleteCases[DeleteDuplicates[Flatten[internalMasses]],0];

	Block[{$tarScaleSq = Switch[optionValueTargetScale,Automatic,var,_,optionValueTargetScale^2]},
	answer=answer/.
	  {passVeltCdisc[0,0,0,p1_,q_,p2_,m0_,m1_,m2_] :> disc[ScalarC0][p1,q,p2,m0,m1,m2],
	   passVeltDdisc[0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> disc[analD0][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]};
	];


	answer = limitDto4dimensions[expr, answer, dim, 0];

	answer = clearFeynmanIRepsilon[answer, optionValueAnalytic];


	(*Final organization -- by function or by Lorentz tensor structures
		optionValueOrganization = Function if called by LoopRefine
		optionValueOrganization = user-defined if called by LoopRefineSeries*)
	Switch[
	  optionValueOrganization,
	  None, Null,
	  LTensor,   answer = Collect[answer, tensorStructures~Join~{_HeavisideTheta} ,expressionOptimizer[#, internalMasses, {1}, "Discontinuity"]&],
	  Function,  answer = Collect[answer, _HeavisideTheta, expressionOptimizer[#, internalMasses, tensorStructures, "Discontinuity"]&]
	];

	answer
  ],{Listable}
];


(****** Mandelstam double spectral function ******)
internalLoopRefine[tensorStructures_, optionValueTargetScale_, dim_, optionValueExplicitC0_, optionValueOrganization_, Discontinuity[var1_,var2_], optionValueAnalytic_] =
Function[{expr},
  Module[{answer,checkRatFunList,internalMasses},

	If[!FreeQ[expr,PVA|PVB|PVC|PVD|_DiscB|_ScalarC0|_ScalarC0IR6|_ScalarD0|_ScalarD0IR12|_ScalarD0IR13|_ScalarD0IR16],
	  {answer, checkRatFunList}=Reap[Collect[expr/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD,_Kibble\[Phi],_Kallen\[Lambda],_DiscB,_ScalarC0,_ScalarC0IR6,_ScalarD0,_ScalarD0IR12,_ScalarD0IR13,_ScalarD0IR16}, (Sow[Internal`RationalFunctionQ[#,Variables[{var1,var2}]]];Together[#])&]],
	  {answer, checkRatFunList}={expr,{{}}}
	];

	(*Check if input is a rational function of channel variable.*)
	If[!(And@@(checkRatFunList[[1]])), Message[LoopRefine::discpoly, {var1,var2}]];

	(*Enclose each PV function in a list*)
	answer=If[Head[answer]===Plus, List@@answer, List@answer];

	{answer,internalMasses}=Reap[Replace[answer,{
		coeff_. PVD[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]?exactExpressionQ :> 
		  With[{args={Expand[s1],Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23],Sow[m0],Sow[m1],Sow[m2],Sow[m3]}},
			If[Count[args,var1|var2]==2,coeff*(disc[refineD][r, n1, n2, n3, ##]& @@ Replace[args,var:(HoldPattern[var1|var2]):>chnl[var],{1}]),0]],
		  
		coeff_. ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]?exactExpressionQ :> 
		  With[{args={0,0,0,0,Expand[s1],Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23],Sow[m0],Sow[m1],Sow[m2],Sow[m3]}},
		    If[Count[args,var1|var2]==2,coeff*(disc[refineD][##]& @@Replace[args,var:(HoldPattern[var1|var2]):>chnl[var],{1}]),0]],

		coeff_. ScalarD0IR12[s2_,s3_,s12_,s23_,m2_,m3_] :> 
		  With[{args={Expand[s2],Expand[s3],Expand[s12],Expand[s23],Sow[m2],Sow[m3]}},
			If[Count[args,var1|var2]==2,coeff*(disc[ScalarD0IR12][##]& @@Replace[args,var:(HoldPattern[var1|var2]):>chnl[var],{1}]),0]],

		coeff_. ScalarD0IR13[s2_,s3_,s4_,s12_,s23_,m2_,m3_] :> 
		  With[{args={Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23],Sow[m2],Sow[m3]}},
		    If[Count[args,var1|var2]==2,coeff*(disc[ScalarD0IR13][##]& @@Replace[args,var:(HoldPattern[var1|var2]):>chnl[var],{1}]),0]],

		coeff_. ScalarD0IR16[s2_,s3_,s12_,s23_,m1_,m2_,m3_] :> 
		  With[{args={Expand[s2],Expand[s3],Expand[s12],Expand[s23],Sow[m1],Sow[m2],Sow[m3]}},
			If[Count[args,var1|var2]==2,coeff*(disc[ScalarD0IR16][##]& @@Replace[args,var:(HoldPattern[var1|var2]):>chnl[var],{1}]),0]],

		_:>0},{1}]
	  ];

	internalMasses = DeleteCases[DeleteDuplicates[Flatten[internalMasses]],0];
	
	Block[{$tarScaleSq = Switch[optionValueTargetScale,Automatic,var,_,optionValueTargetScale^2]},
	  answer=answer/.passVeltDdisc[0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> disc[analD0][s1,s2,s3,s4,s12,s23,m0,m1,m2,m3];
	];

	answer = limitDto4dimensions[expr, answer, dim, 0];

	answer = clearFeynmanIRepsilon[answer, optionValueAnalytic];


	(*Final organization -- by function or by Lorentz tensor structures
		optionValueOrganization = Function if called by LoopRefine
		optionValueOrganization = user-defined if called by LoopRefineSeries*)
	(*Echo[AbsoluteTiming[
	],"Organization",#\[LeftDoubleBracket]1\[RightDoubleBracket]&];*)
	Switch[
	  optionValueOrganization,
	  None, Null,
	  LTensor,   answer = Collect[answer, tensorStructures~Join~{_HeavisideTheta} ,expressionOptimizer[#, internalMasses, {1}, "Discontinuity"]&],
	  Function,  answer = Collect[answer, _HeavisideTheta, expressionOptimizer[#, internalMasses, tensorStructures, "Discontinuity"]&]
	];

	answer
  ],{Listable}
];


(* ::Subsubsection::Closed:: *)
(*Part: UVDivergent*)


(****** UVDivergent part ******)
internalLoopRefine[tensorStructures_, optionValueTargetScale_, dim_, optionValueExplicitC0_, optionValueOrganization_, UVDivergent, optionValueAnalytic_] =
Function[{expr},
  Module[{answer},

	If[!FreeQ[expr,PVA|PVB|PVC|PVD],
	  If[optionValueAnalytic,
		answer=Collect[Catch[makeSer[expr,True],"DerivativesOnly"]/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD}, Together],
		answer=Collect[expr/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD}, Together]
	  ],
	  answer=expr
	];

	answer = Block[{Dim=dim-2Eps}, answer];
	answer = answer /. {
	  PVD[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]?exactExpressionQ :> 
		pvDDivUV[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]/Eps,
	  ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]?exactExpressionQ :> 0,
	  PVC[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,p1_,q_,p2_,m0_,m1_,m2_]?exactExpressionQ :> 
		pvCDivUV[r,n1,n2,p1,q,p2,m0,m1,m2]/Eps,
	  ScalarC0[p1_,q_,p2_,m0_,m1_,m2_]?exactExpressionQ :> 0,
	  PVB[r_Integer,n_Integer?NonNegative,s_,m0_,m1_]?exactExpressionQ :> 
		pvBDivUV[r,n,s,m0,m1]/Eps,
	  PVA[r_Integer,m0_]?exactExpressionQ :> pvADivUV[r,m0]/Eps};
	X`Utilities`CollectByTensorStructures[SeriesCoefficient[answer,{Eps,0,-1}]/Eps, Simplify]

  ],{Listable}
];


(* ::Subsubsection::Closed:: *)
(*Part: IR Divergent*)


(****** IRDivergent part ******)
internalLoopRefine[tensorStructures_, optionValueTargetScale_, dim_, optionValueExplicitC0_, optionValueOrganization_, IRDivergent, optionValueAnalytic_] =
Function[{expr},
  Module[{answer,internalMasses},

	If[!FreeQ[expr,PVA|PVB|PVC|PVD],
	  If[optionValueAnalytic,
		answer=Collect[Catch[makeSer[expr,True],"DerivativesOnly"]/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD}, Together],
		answer=Collect[expr/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD}, Together]
	  ],
	  answer=expr
	];

	(*Enclose each PV function in a list*)
	answer=If[Head[answer]===Plus, List@@answer, List@answer];

	(*PrintTemporary["Performing the reduction..."];*)
	{answer,internalMasses}=
	  Reap[answer/.{
		PVD[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]?exactExpressionQ :>
		  irDiv[refineD][r,n1,n2,n3,Expand[s1],Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23],Sow[m0],Sow[m1],Sow[m2],Sow[m3]],
		ScalarD0[_,_,_,_,_,_,_,_,_,_]:>0,
        PVC[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,p1_,q_,p2_,m0_,m1_,m2_]?exactExpressionQ :> 
		  irDiv[refineC][r,n1,n2,Expand[p1],Expand[q],Expand[p2],Sow[m0],Sow[m1],Sow[m2]],
		ScalarC0[_,_,_,_,_,_]:>0,
		PVB[r_Integer?Positive,n1_Integer?NonNegative,_,_,_]?exactExpressionQ :>0,
        PVB[r_Integer,n_Integer?NonNegative,s_,m0_,m1_]?exactExpressionQ :> 
		  irDiv[refineB][r,n,Expand[s],Sow[m0],Sow[m1]],
        PVA[r_Integer,m0_]?exactExpressionQ :>irDiv[refineA][r,Sow[m0]]}
	  ];

	internalMasses = DeleteCases[DeleteDuplicates[Flatten[internalMasses]],0];

	answer = limitDto4dimensions[expr, answer, dim, -1];

	answer = clearFeynmanIRepsilon[answer, True];

	answer = tHooftLogTransform[answer, internalMasses, optionValueTargetScale];

	(*Final organization -- by function or by Lorentz tensor structures
		optionValueOrganization = Function if called by LoopRefine
		optionValueOrganization = user-defined if called by LoopRefineSeries*)
	Switch[
	  optionValueOrganization,
	  None, Null,
	  LTensor,   answer = Collect[answer, tensorStructures ,expressionOptimizer[#, internalMasses, {1}]&],
	  Function,  answer = expressionOptimizer[answer, internalMasses, tensorStructures]
	];

	answer
  ],{Listable}
];


(* ::Subsubsection::Closed:: *)
(*Part: All*)


(****** All ******)
internalLoopRefine[tensorStructures_, optionValueTargetScale_, dim_, optionValueExplicitC0_, optionValueOrganization_, All, optionValueAnalytic_] =
Function[{expr},
  Module[{answer,internalMasses={}},

	If[!FreeQ[expr,PVA|PVB|PVC|PVD],
	  If[optionValueAnalytic,
		answer=Collect[Catch[makeSer[expr,True],"DerivativesOnly"]/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD}, Together],
		answer=Collect[expr/.pvWeightReduce, {_PVA,_PVB,_PVC,_PVD}, Together]
	  ],
	  answer=expr
	];

	(*Enclose each PV function in a list*)
	answer=If[Head[answer]===Plus, List@@answer, List@answer];

	(*PrintTemporary["Performing the reduction..."];*)
	{answer,internalMasses}=
	  Reap[
		(*Expand[*)answer/.{
		  PVD[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]?exactExpressionQ:>
            refineD[r,n1,n2,n3,Expand[s1],Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23],Sow@m0,Sow@m1,Sow@m2,Sow@m3],
		  ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]?exactExpressionQ:>
            refineD[0,0,0,0,Expand[s1],Expand[s2],Expand[s3],Expand[s4],Expand[s12],Expand[s23],Sow@m0,Sow@m1,Sow@m2,Sow@m3],
          PVC[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,p1_,q_,p2_,m0_,m1_,m2_]?exactExpressionQ:>
            refineC[r,n1,n2,Expand[p1],Expand[q],Expand[p2],Sow@m0,Sow@m1,Sow@m2],
          ScalarC0[p1_,q_,p2_,m0_,m1_,m2_]?exactExpressionQ:>
            refineC[0,0,0,Expand[p1],Expand[q],Expand[p2],Sow@m0,Sow@m1,Sow@m2],
          PVB[r_Integer,n_Integer?NonNegative,s_,m0_,m1_]?exactExpressionQ:>
            refineB[r,n,Expand[s],Sow@m0,Sow@m1],
          PVA[r_Integer,m0_]?exactExpressionQ:>
            refineA[r,Sow@m0]}(*]*)
	  ];

	internalMasses = DeleteCases[DeleteDuplicates[Flatten[internalMasses]],0];

	(*PrintTemporary["Converting scalar D0 functions..."];*)
	(*Convert scalar Passarino-Veltman D0 function to ScalarD0*)
	answer=answer/.{(passVeltD[0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> With[{body=analD0IR[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]},body/; Head[body]=!=analD0IR]),
				    (passVeltD[0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> ScalarD0[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])};

	(*Convert scalar Passarino-Veltman C0 function to explicit analytic expressions in simple cases ONLY.
      More complicated cases done at the very end to avoid needless processing. *)
	(*PrintTemporary["Converting scalar C0 functions..."];*)
	Which[
	  optionValueExplicitC0=!=None && FreeQ[expr,_PVD|_ScalarD0|_ScalarD0IR12|_ScalarD0IR13|_ScalarD0IR16],
	  answer=answer/.
		{(passVeltC[0,0,0,p1_,q_,p2_,m0_,m1_,m2_] :> With[{body=analC0[{p1,m2},{p2,m1},{q,m0}]},body/;Head[body]=!=analC0]),
		 (passVeltC[0,0,0,p1_,q_,p2_,m0_,m1_,m2_] :> ScalarC0[p1,q,p2,m0,m1,m2])},
	  True,
		answer=answer/.(passVeltC[0,0,0,p1_,q_,p2_,m0_,m1_,m2_] :> ScalarC0[p1,q,p2,m0,m1,m2])
	];

	(*PrintTemporary["Limiting to d=4 dimensions."];*)
	answer = limitDto4dimensions[expr, answer, dim, 0];

	answer = clearFeynmanIRepsilon[answer, optionValueAnalytic];

	answer = tHooftLogTransform[answer, internalMasses, optionValueTargetScale];


	(*Final organization -- by function or by Lorentz tensor structures
		optionValueOrganization = Function if called by LoopRefine
		optionValueOrganization = user-defined if called by LoopRefineSeries*)
	(*PrintTemporary["Final organization..."];*)
	Switch[
	  optionValueOrganization,
	  None, Null,
	  LTensor,   answer = Collect[answer, tensorStructures, expressionOptimizer[#, internalMasses, {1}]&],
	  Function,  answer = expressionOptimizer[answer, internalMasses, tensorStructures]
	];

	(*Convert COMPLICATED scalar Passarino-Veltman C0 function to explicit analytic expressions.*)
	If[optionValueExplicitC0===All,
	  answer=answer/.{ScalarC0[p1_,q_,p2_,m0_,m1_,m2_] :> With[{body=analC0[{p1,m2},{p2,m1},{q,m0}]},body/;(Head[body]=!=analC0)],
					  ScalarC0[p1_,q_,p2_,m0_,m1_,m2_] :> analC0force[{p1,m2},{p2,m1},{q,m0}],
					  ScalarC0IR6[s_,m0_,m2_]:>pvC0IR6force[s,m0,m2]}
	];

	answer
  ],{Listable}
];


(* ::Subsection::Closed:: *)
(*Front end LoopRefine/LoopRefineSeries*)


LoopRefine::optdisc = "Expecting 1 or 2 arguments for option setting Part -> Discontinuity.";
LoopRefine::irdiv = "Non-logarithmic (power) infrared singularity encountered.  Try moving away from threshold and inspect behavior as kinematic point is reached, or set option Analytic -> True.";
LoopRefine::inexact = "Unable to convert Passarino\[Hyphen]Veltman function `1` with inexact or complex arguments.";
LoopRefine::discvar = "`1` is not a valid channel variable.";
LoopRefine::discargx = "`1` is not a valid channel variable.";
LoopRefine::discmult = "Warning: Multiple occurrences of channel variable `1` found in `2` and will be dropped.";
LoopRefine::discpoly = "Warning: input expression contains non-polynomial dependence on channel variable `1` outside of Passarino-Veltman functions.  Possible discontinuities arising from non-polynomial sources will be dropped.";
LoopRefine::discdup = "Value of option Part->`1` has duplicated channel variables.";
LoopRefine::leadinglandau = "Calculation of `1` at leading Landau singularity is attempted where no reduction methods are known.  Result is likely (power) infrared divergent and/or outside the physical region.  Try moving away from threshold and inspect behavior as kinematic point is reached.";


SetAttributes[LoopRefine,Listable];
HoldPattern[LoopRefine[SeriesData[Except[Eps,var_],p_,l_,rest___],opts___]] := SeriesData[var,p,LoopRefine[l,opts],rest];

LoopRefine[expr_, opts:OptionsPattern[]?(X`Internal`ValidOptionsQ[LoopRefine])] /; Check[loopRefineOptionsCheck[opts],False] :=
  RuleCondition[Catch[
	Which[
	  OptionValue[Organization] === None,
		internalLoopRefine[{1}, OptionValue[TargetScale], OptionValue[Dimensions], OptionValue[ExplicitC0], None, OptionValue[Part], OptionValue[Analytic]][expr],
	  OptionValue[Organization] === Function || OptionValue[Part] === UVDivergent,
		internalLoopRefine[X`Utilities`TensorStructures[expr], OptionValue[TargetScale], OptionValue[Dimensions], OptionValue[ExplicitC0], Function, OptionValue[Part], OptionValue[Analytic]][expr],
	  OptionValue[Organization] === LTensor,
		X`Utilities`CollectByTensorStructures[expr, internalLoopRefine[{1}, OptionValue[TargetScale], OptionValue[Dimensions], OptionValue[ExplicitC0], Function, OptionValue[Part], OptionValue[Analytic]]]
	],"PowerIRSingularity"|"InexactPV"
  ]]; 

LHS_LoopRefine:=RuleCondition[X`Internal`CheckArgumentCount[LHS,1,1];Fail];


invalidDiscontinuityVariable[x_]:=(NumericQ[x] || !FreeQ[x,Except[X`LDot,f_Symbol/;Context[f]==="X`"]]);
Options[loopRefineOptionsCheck]:=Options[LoopRefine];
loopRefineOptionsCheck[OptionsPattern[]] :=
	(
		If[!EvenQ[OptionValue[Dimensions]], Message[LoopRefine::optvg,Dimensions,OptionValue[Dimensions],"an even integer"]];
		If[!MatchQ[OptionValue[ExplicitC0], All|Automatic|None], Message[LoopRefine::optvg, ExplicitC0, OptionValue[ExplicitC0], "Automatic, All, or None"]];
		If[!MatchQ[OptionValue[Organization], Function|LTensor|None], Message[LoopRefine::optvg, Organization, OptionValue[Organization], "Function, LTensor, or None"]];
		If[!MatchQ[OptionValue[Part], All|UVDivergent|IRDivergent|Discontinuity[_]|Discontinuity[_,_](*|Rational*)], 
		  If[MatchQ[OptionValue[Part],Discontinuity],
			Message[LoopRefine::optdisc],
			Message[LoopRefine::optv, Part, OptionValue[Part]]]];

		If[MatchQ[OptionValue[Part],_Discontinuity],
		  If[Cases[OptionValue[Part],_?invalidDiscontinuityVariable,1,1]=!={}, Message[LoopRefine::discvar, First[Cases[OptionValue[Part],_?invalidDiscontinuityVariable,1,1]]]];
		  If[!DuplicateFreeQ[OptionValue[Part]],Message[LoopRefine::discdup,OptionValue[Part]]]
		];

		If[!MatchQ[OptionValue[Analytic], True|False], Message[LoopRefine::opttf, Analytic, OptionValue[Analytic]]];
		True
	);


LoopRefineSeries::notaylor = "Taylor series of `1` does not exist near \!\(`2` = `3`\).";

LoopRefineSeries[expr_, serArgs__List, opts:OptionsPattern[]?(X`Internal`ValidOptionsQ[LoopRefineSeries])] /; Check[Series[1,serArgs];True,False] && Check[loopRefineOptionsCheck[opts],False] :=
  RuleCondition[Catch[Module[{result},

	With[{tensorStructures = X`Utilities`TensorStructures[expr]},
	  If[OptionValue[Part]===UVDivergent(*|Rational*),
	    (*For UV divergent or rational parts, faster to first insert expression and then make a series expansion*)
		result = internalLoopRefine[tensorStructures, OptionValue[TargetScale],OptionValue[Dimensions],OptionValue[ExplicitC0],OptionValue[Organization],UVDivergent,OptionValue[Analytic]][expr];
		Series[result,serArgs]
	  ,
		(*All other parts*)
		If[OptionValue[Organization]===LTensor && !FreeQ[tensorStructures, Alternatives@@{serArgs}[[All,1]]],
		  (*If tensor structures contain expansion parameter, then they will not be touched by SeriesData, and can be organized by them.*)
		  Collect[expr, tensorStructures,
			(Catch[makeSer[Collect[#, {_PVA,_PVB,_PVC,_PVD}, Simplify], OptionValue[Analytic], serArgs], LoopRefineSeries, (Message[LoopRefineSeries::notaylor, #[[1]],#[[2]],#[[3]]];Return[$Failed,Module])&] /. HoldPattern[ser_SeriesData] /; FreeQ[ser[[3]], _SeriesData] :> MapAt[internalLoopRefine[tensorStructures, OptionValue[TargetScale],OptionValue[Dimensions],OptionValue[ExplicitC0],OptionValue[Organization],OptionValue[Part],OptionValue[Analytic]],ser,3])&]
		,

	      result = Collect[expr, {_PVA,_PVB,_PVC,_PVD}, Simplify];
		  result = Catch[makeSer[result, OptionValue[Analytic], serArgs], LoopRefineSeries, (Message[LoopRefineSeries::notaylor, #[[1]],#[[2]],#[[3]]];Return[$Failed,Module])&];

		  If[FreeQ[result, _SeriesData],
			(*Annoyingly, SeriesData is not generated if Series is applied to an expression independent of expansion variable.
			  In this case, apply internalLoopRefine to the whole expression*)
			internalLoopRefine[tensorStructures, OptionValue[TargetScale],OptionValue[Dimensions],OptionValue[ExplicitC0],OptionValue[Organization],OptionValue[Part],OptionValue[Analytic]][result],
			result /. HoldPattern[ser_SeriesData] /; FreeQ[ser[[3]], _SeriesData] :> MapAt[internalLoopRefine[tensorStructures, OptionValue[TargetScale],OptionValue[Dimensions],OptionValue[ExplicitC0],OptionValue[Organization],OptionValue[Part],OptionValue[Analytic]],ser,3]
		  ]
		]
	  ]
	]],"PowerIRSingularity"|"InexactPV"
  ]];

LHS_LoopRefineSeries:=RuleCondition[X`Internal`CheckArgumentCount[LHS,2,Infinity];Fail];


Options[loopRefineSeriesOptionsCheck]:=Options[LoopRefine];

loopRefineSeriesOptionsCheck[OptionsPattern[]] :=
	Module[{},
		If[!EvenQ[OptionValue[Dimensions]], Message[LoopRefineSeries::optvg,Dimensions,OptionValue[Dimensions],"an even integer"]];
		If[!MatchQ[OptionValue[ExplicitC0], All|Automatic|None], Message[LoopRefineSeries::optvg, ExplicitC0, OptionValue[ExplicitC0], "Automatic, All, or None"]];
		If[!MatchQ[OptionValue[Organization], Function|LTensor|None], Message[LoopRefineSeries::optvg, Organization, OptionValue[Organization], "Function, LTensor, or None"]];
		If[!MatchQ[OptionValue[Part], All|UVDivergent|IRDivergent], Message[LoopRefineSeries::optv, Part, OptionValue[Part]]];
		If[!MatchQ[OptionValue[Analytic], True|False], Message[LoopRefineSeries::opttf, Analytic, OptionValue[Analytic]]];

		True
	];


(* ::Section::Closed:: *)
(*End*)


SetAttributes[internalLoopRefine,Unevaluated@{Protected, ReadProtected, Locked}];


(*Protecting Functions*)
SetAttributes[LoopRefine, Unevaluated@{Protected, ReadProtected}];
SetAttributes[LoopRefineSeries, Unevaluated@{Protected, ReadProtected}];
SetAttributes[{IRDivergent,UVDivergent}, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[TargetScale, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[ExplicitC0, Unevaluated@{Protected, ReadProtected, Locked}];
SetAttributes[Organization, Unevaluated@{Protected, ReadProtected, Locked}];

SetAttributes[{Eps,Mu},Unevaluated@{Protected,ReadProtected}];

SetAttributes[{PVA,PVB,PVC,PVD},Unevaluated@{Protected, ReadProtected, NHoldAll}];

SetAttributes[{Ln, DiLog, ContinuedDiLog, 
	Kallen\[Lambda], KallenExpand, 
	Kibble\[Phi], KibbleExpand, 
	DiscB, DiscExpand, 
	ScalarC0, ScalarC0IR6, C0Expand, 
	ScalarD0, ScalarD0IR12, ScalarD0IR13, ScalarD0IR16, D0Expand}, Unevaluated@{Protected, ReadProtected, Locked}];

SetAttributes[{X`Utilities`SimplifyLn, X`Utilities`SimplifyDiLog, X`Utilities`ContinuedDiLogExpand, X`Utilities`SimplifyContinuedDiLog, X`Utilities`EquivalentAlternatives, X`Utilities`PermutePVD, X`Utilities`PVNormal}, Unevaluated@{Protected, ReadProtected, Locked}];


End[];


(*EndPackage[]*)

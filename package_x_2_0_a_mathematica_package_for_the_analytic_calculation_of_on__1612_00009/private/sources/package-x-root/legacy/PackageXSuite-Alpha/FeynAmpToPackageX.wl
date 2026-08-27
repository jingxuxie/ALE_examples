(* ::Package:: *)

BeginPackage["FeynAmpToPackageX`",{"FeynArts`"}]


Print["FeynAmpToPackageX v0.1.1."];


Clear[FeynAmpToPackageX];
Options[FeynAmpToPackageX]={"LoopFunction"->Inactive[X`LoopIntegrate]};
FeynAmpToPackageX::usage = "\!\(FeynAmpToPackageX[\(\*StyleBox[\"FeynAmpList\",\"TI\"]\)]\) converts Feynarts object \*StyleBox[\"FeynAmpList\",\"TI\"] to Package\[Hyphen]X syntax.  LoopIntegrate and Spur are generated in Inactive form."


Begin["FeynAmpToPackageX`Private`"];


restoreUnitMtx[expr_Plus]:=If[FreeQ[#,X`Dirac1|X`DiracG5|X`DiracPL|X`DiracPR|X`LDot[X`DiracG,_]|X`LTensor[X`DiracG,_Symbol]|_X`DiracMatrix],#*X`Dirac1,#]&/@expr;
restoreUnitMtx[expr_]:=If[FreeQ[expr,X`Dirac1|X`DiracG5|X`DiracPL|X`DiracPR|X`LDot[X`DiracG,_]|X`LTensor[X`DiracG,_Symbol]|_X`DiracMatrix],expr*X`Dirac1,expr];


fourMomentumParser={
  FeynArts`FourMomentum[FeynArts`Incoming,n_Integer]:>Symbol["Global`p"<>ToString[n]],
  FeynArts`FourMomentum[FeynArts`Outgoing,n_Integer]:>Symbol["Global`k"<>ToString[n]],
  FeynArts`FourMomentum[FeynArts`Internal,n_Integer]:>Symbol["Global`q"<>ToString[n]]
};

tensorParser={
  HoldPattern[Global`FourVector[mom_,FeynArts`Index[Global`Lorentz,n_Integer]]]:>X`LTensor[mom,Symbol["Global`\[Mu]"<>ToString[n]]],
  HoldPattern[Global`MetricTensor[FeynArts`Index[Global`Lorentz,n1_Integer],FeynArts`Index[Global`Lorentz,n2_Integer]]]:>X`LTensor[X`MetricG,Symbol["Global`\[Mu]"<>ToString[n1]],Symbol["Global`\[Mu]"<>ToString[n2]]],
  HoldPattern[Global`PolarizationVector[type_,mom_,FeynArts`Index[Global`Lorentz,n_Integer]]]:>X`LTensor[X`PolVecE[mom,TheMass[type](*First[Cases[FeynAmpHeaderData[FeynArts`Process],{type,_,mass_,_}:>mass,{1,Infinity},1]]*)],Symbol["Global`\[Mu]"<>ToString[n]]],
  HoldPattern[Conjugate[Global`PolarizationVector][type_,mom_,FeynArts`Index[Global`Lorentz,n_Integer]]]:>X`LTensor[X`PolVecEC[mom,TheMass[type](*First[Cases[FeynAmpHeaderData[FeynArts`Process],{type,_,mass_,_}:>mass,{1,Infinity},1]]*)],Symbol["Global`\[Mu]"<>ToString[n]]]
};

diracObjectsParser={
  c_. Global`ChiralityProjector[1]:>c X`DiracPR,
  c_. Global`ChiralityProjector[-1]:>c X`DiracPL,
  c_. Global`DiracSlash[vec_]:>c X`LDot[X`DiracG,vec],
  c_. Global`DiracMatrix[FeynArts`Index[Global`Lorentz,n_Integer]]:>c X`LTensor[X`DiracG,Symbol["Global`\[Mu]"<>ToString[n]]],
  c_. FeynArts`NonCommutative[mtx__]:> c diracMatrixParser[mtx],
  c_. FeynArts`MatrixTrace:> c (Inactive[X`Spur]@@diracMatrixParser[mtx]),
  c_ :> c X`Dirac1
};

itemParser[item_]:=
  With[{expandedItem=Expand[item]},
	Switch[
	  expandedItem,
	  _Plus, Map[#/.diracObjectsParser&, expandedItem],
	  _, expandedItem/.diracObjectsParser
	]
  ]

diracMatrixParser[mtx__]:=itemParser /@ Unevaluated[X`DiracMatrix[mtx]];

fermionChainParser={
  HoldPattern[FeynArts`MatrixTrace[mtx___]]:>itemParser /@ Unevaluated[Inactive[X`Spur][mtx]],
  (*on shell fermion chain*)
  HoldPattern[FeynArts`FermionChain[FeynArts`NonCommutative[(Global`DiracSpinor|Global`MajoranaSpinor)[mom2_,mass2_]],mtx__,FeynArts`NonCommutative[(Global`DiracSpinor|Global`MajoranaSpinor)[mom1_,mass1_]]]]:>
	X`FermionLine[
	  If[Internal`SyntacticNegativeQ[mom2],{-1,-mom2,mass2},{1,mom2,mass2}],
	  If[Internal`SyntacticNegativeQ[mom1],{-1,-mom1,mass1},{1,mom1,mass1}],
	  diracMatrixParser[mtx]
	],
  (*off shell fermion chain*)
  HoldPattern[FeynArts`FermionChain[mtx__]]:>diracMatrixParser[mtx]
};


Clear[FeynAmpToPackageX];
FeynAmpToPackageX[expr_,OptionsPattern[]]/;Head[Head[expr]]===FeynArts`FeynAmpList:=
  Block[{FeynAmpHeaderData=Association@@Head[expr]},
	Module[{result, loopFunction},
	  Internal`InheritedBlock[{Inactive,FeynArts`FeynAmpDenominator},
	  
	  FeynArts`FeynAmpDenominator /: FeynArts`FeynAmpDenominator[args1___]*FeynArts`FeynAmpDenominator[args2___]:=FeynArts`FeynAmpDenominator[args1,args2];
	  loopFunction=OptionValue["LoopFunction"];
	  
	  (*Do I need this???*)
	  Unprotect[Inactive];
	  Inactive[X`Spur][left___, c_?(FreeQ[X`Dirac1|X`DiracG5|X`DiracPL|X`DiracPR|X`LDot[X`DiracG,_]|X`LTensor[X`DiracG|X`DiracS,__]|_X`DiracMatrix]) mtx_, right___] := c Inactive[X`Spur][left, mtx, right];
	  Inactive[X`Spur][left___, X`DiracMatrix[mtx___], right___] := Inactive[X`Spur][left, mtx, right];
	  Protect[Inactive];
	  
	  (*Put each Feynman diagram in a list*)
	  result = List@@expr;

	  (*Make the replacement*)
	  result = result/.fourMomentumParser;
	  result = result/.tensorParser;
	  result = result/.fermionChainParser;
	  result = result/.Global`ScalarProduct[x_,y_]:>X`LDot[x,y];

	  result = ((Expand[#[[3]],_FeynArts`FeynAmpDenominator]/.{(num_. den_FeynArts`FeynAmpDenominator):>loopFunction[num,List@@#[[2]],List@@List@@@den]})&/@result);
	  
	  result = result /. {FeynArts`PropagatorDenominator[0,0]:>0, FeynArts`PropagatorDenominator[mom_,mass_]:>(X`LDot[mom,mom]-mass^2)^-1}

	]
  ]/;MatchQ[FeynAmpHeaderData[FeynArts`AmplitudeLevel],{FeynArts`Particles}|{FeynArts`Classes}]
]


FeynAmpToPackageX::wronghead = "Expecting head FeynAmpList.";


FeynAmpToPackageX[expr_] := $Failed/;Message[FeynAmpToPackageX::wronghead];


(* ::Subsection:: *)
(*End*)


End[];
EndPackage[];

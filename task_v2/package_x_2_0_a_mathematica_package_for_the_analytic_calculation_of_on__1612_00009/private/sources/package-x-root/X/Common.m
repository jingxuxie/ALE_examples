(* ::Package:: *)

(*Not needed in Version 10.0 and above*)
Off[Except::named];


(* ::Subsection:: *)
(*Usages*)


(* ::Subsubsection::Closed:: *)
(*Lorentz.m*)


If[Not[$VersionNumber==9.0] && $Notebooks,
	Contract::usage="\!\(Contract[\*StyleBox[\"expr\", \"TI\"]]\) gives the form of \!\(\*StyleBox[\"expr\", \"TI\"]\) where repeated indices attached to multiplying tensors are contracted.";
    Transverse::usage="\!\(Transverse[\*StyleBox[\"tensor\", \"TI\"]]\) gives the transverse scalar projection of the rank\[Hyphen]two \*StyleBox[\"tensor\", \"TI\"] containing only one four\[Hyphen]vector.
\!\(Transverse[\*StyleBox[\"tensor\", \"TI\"],\*StyleBox[\"v\", \"TI\"]]\) gives the scalar projection of the rank\[Hyphen]two \*StyleBox[\"tensor\", \"TI\"] transverse to vector \*StyleBox[\"v\", \"TI\"].
\!\(Transverse[\*StyleBox[\"tensor\", \"TI\"],\*StyleBox[\"v\", \"TI\"],{\*StyleBox[\"\[Mu]\", \"TI\"],\*StyleBox[\"\[Nu]\", \"TI\"]}]\) gives the rank \!\(\*StyleBox[\"P\", \"TI\"]\*StyleBox[\"-2\", \"TR\"]\) tensor projection of the rank \*StyleBox[\"P\", \"TI\"] \*StyleBox[\"tensor\", \"TI\"] transverse to \*StyleBox[\"v\", \"TI\"] along indices \*StyleBox[\"\[Mu]\", \"TI\"] and \*StyleBox[\"\[Nu]\", \"TI\"].";
    Longitudinal::usage="\!\(Longitudinal[\*StyleBox[\"tensor\", \"TI\"]]\) gives the longitudinal scalar projection of the rank\[Hyphen]two \*StyleBox[\"tensor\", \"TI\"] containing only one four\[Hyphen]vector.
\!\(Longitudinal[\*StyleBox[\"tensor\", \"TI\"],\*StyleBox[\"v\", \"TI\"]]\) gives the scalar projection of the rank\[Hyphen]two \*StyleBox[\"tensor\", \"TI\"] longitudinal to vector \*StyleBox[\"v\", \"TI\"].
\!\(Longitudinal[\*StyleBox[\"tensor\", \"TI\"],\*StyleBox[\"v\", \"TI\"],{\*StyleBox[\"\[Mu]\", \"TI\"],\*StyleBox[\"\[Nu]\", \"TI\"]}]\) gives the rank \!\(\*StyleBox[\"P\", \"TI\"]\*StyleBox[\"-2\", \"TR\"]\) tensor projection of the rank \*StyleBox[\"P\", \"TI\"] \*StyleBox[\"tensor\", \"TI\"] longitudinal to \*StyleBox[\"v\", \"TI\"] along indices \*StyleBox[\"\[Mu]\", \"TI\"] and \*StyleBox[\"\[Nu]\", \"TI\"] . ";
    LDot::usage="\!\(LDot[\(\*StyleBox[\"a\", \"TI\"]\),\(\*StyleBox[\"b\", \"TI\"]\)]\) or \!\(\*RowBox[{\(\*StyleBox[\"a\",\"TI\"]\),\".\",\(\*StyleBox[\"b\",\"TI\"]\)}]\) represents the Lorentz 4\[Hyphen]vector dot product \!\(\*StyleBox[\"a\", \"TI\"]\)\[ThinSpace]\[CenterDot]\[ThinSpace]\!\(\*StyleBox[\"b\", \"TI\"]\).";
	LTensor::usage="\!\(LTensor[\(\*StyleBox[\"p\", \"TI\"]\),\(\*StyleBox[\"\[Mu]\", \"TR\"]\),\[Ellipsis]]\) or \!\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),\(\*RowBox[{\(\*StyleBox[\"\[Mu]\", \"TR\"]\),\",\",\"\[Ellipsis]\"}]\)]\) represents the Lorentz tensor \!\(\*SubscriptBox[\(\*StyleBox[\"p\", \"TI\"]\),\(\*RowBox[{\(\*StyleBox[\"\[Mu]\", \"TR\"]\),\"\[Ellipsis]\"}]\)]\).";
	LScalarQ::usage = "\!\(LScalarQ[\(\*StyleBox[\"expr\", \"TI\"]\)]\) gives True if \*StyleBox[\"expr\", \"TI\"] is a Lorentz scalar expression, and False otherwise.  Assigning \!\(LScalarQ[\*StyleBox[\"symb\", \"TI\"]]=True\) declares \*StyleBox[\"symb\", \"TI\"] to be a Lorentz scalar.";
	MandelstamRelations::usage="\!\(MandelstamRelations[{\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),4],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),4]}\[Rule]{\*StyleBox[\"s\", \"TI\"],\*StyleBox[\"t\", \"TI\"],\*StyleBox[\"u\", \"TI\"]}]\) gives a list of replacement rules expressing dot products of incoming \!\(\"4\[Hyphen]vectors\"\) \!\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),2]\) and outgoing \!\(\"4\[Hyphen]vectors\"\) \!\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),4]\) as Mandelstam invariants \!\(\*StyleBox[\"s\", \"TI\"],\*StyleBox[\"t\", \"TI\"],\*StyleBox[\"u\", \"TI\"]\) and masses \!\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),4]\).";

	LoopIntegrate::usage="\!\(LoopIntegrate[\*StyleBox[\"num\", \"TI\"],\*StyleBox[\"k\", \"TI\"],{\*SubscriptBox[\(\*StyleBox[\"q\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0]},{\*SubscriptBox[\(\*StyleBox[\"q\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1]},\[Ellipsis]]\) expresses the \!\(\"one\[Hyphen]loop\"\) tensor integral over integration variable \*StyleBox[\"k\", \"TI\"] with numerator \*StyleBox[\"num\", \"TI\"] and denominator factors \!\((\*SubsuperscriptBox[\(\*StyleBox[\"q\",\"TI\"]\),0,2]-\*SubsuperscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0,2])(\*SubsuperscriptBox[\(\*StyleBox[\"q\",\"TI\"]\),1,2]-\*SubsuperscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1,2])\[Ellipsis]\) in terms of \!\(\"Passarino\[Hyphen]Veltman\"\) functions.
\!\(LoopIntegrate[\*StyleBox[\"num\", \"TI\"],\*StyleBox[\"k\", \"TI\"],{\*SubscriptBox[\(\*StyleBox[\"q\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"w\",\"TI\"]\),0]},{\*SubscriptBox[\(\*StyleBox[\"q\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"w\",\"TI\"]\),1]},\[Ellipsis]]\) expresses the \!\(\"one\[Hyphen]loop\"\) tensor integral in terms of \!\(\"Passarino\[Hyphen]Veltman\"\) functions with weights \!\(\*SubscriptBox[\(\*StyleBox[\"w\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"w\",\"TI\"]\),1],\[Ellipsis]\).";
	PVX::usage="\!\(PVX[\*StyleBox[\"r\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),2],\[Ellipsis],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),\"01\"],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),\"12\"],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),\"23\"],\[Ellipsis],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\[Ellipsis]]\) is the general \!\(\"Passarino\[Hyphen]Veltman\"\) coefficient function \!\(\*SubscriptBox[\(\*StyleBox[\"X\", \"TB\"]\), RowBox[{UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"0...0\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"2r\", \"TI\"]\)],UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"1...1\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"n1\", \"TI\"]\)],UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"2...2\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"n2\", \"TI\"]\)],\[CenterEllipsis]}]](\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),\"01\"],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),\"12\"],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),\"23\"],\[Ellipsis]\";\"\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\[Ellipsis])\).";

	LeviCivitaE::usage="\!\(\*RowBox[{\"LTensor\",\"[\",\(\*RowBox[{\"LeviCivitaE\",\",\",\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Rho]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[FinalSigma]\",\"TR\"]\)}]\),\"]\"}]\) or \!\(\*SubscriptBox[\"\[CurlyEpsilon]\",\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Rho]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[FinalSigma]\",\"TR\"]\)}]\)]\) represents the \!\(Levi\[Hyphen]Civita\) antisymmetric symbol \!\(\*SuperscriptBox[\(\*StyleBox[\"\[CurlyEpsilon]\",\"TR\"]\),\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\(\*StyleBox[\"\[Nu]\",\"TR\"]\),\(\*StyleBox[\"\[Rho]\",\"TR\"]\),\(\*StyleBox[\"\[FinalSigma]\",\"TR\"]\)}]\)]\) near 4 spacetime dimensions.";
	MetricG::usage="\!\(\*RowBox[{\"LTensor\",\"[\",\(\*RowBox[{\"MetricG\",\",\",\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\),\"]\"}]\) or \!\(\*SubscriptBox[\"\[DoubleStruckG]\",\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\)]\) represents the \!\(\*StyleBox[\"d\",\"TI\"]\[Hyphen]dimensional\) flat space Minkowski metric \!\(\*SuperscriptBox[\(\*StyleBox[\"\[ScriptG]\",\"TR\"]\),\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\)]\).";
	Dim::usage="\!\(\"Dim\"\) or \!\(\"\[ScriptD]\"\) is the number of non\[Hyphen]integer number of spacetime dimensions.";

	X`Utilities`EnableFancyIO::usage = "\!\(X`Utilities`EnableFancyIO[\*SubscriptBox[StyleBox[\"symbol\", \"TI\"],1],\*SubscriptBox[StyleBox[\"symbol\", \"TI\"],2],\[Ellipsis]]\) enables the StandardForm parsing and formatting for the Package\[Hyphen]X functions \*SubscriptBox[StyleBox[\"symbol\", \"TI\"],StyleBox[\"i\", \"TI\"]].  Possible \*StyleBox[StyleBox[\"symbol\", \"TI\"]]s are LDot, LTensor, LoopIntegrate, FermionLine, and FermionLineProduct.";
	X`Utilities`DisableFancyIO::usage = "\!\(X`Utilities`DisableFancyIO[\*SubscriptBox[StyleBox[\"symbol\", \"TI\"],1],\*SubscriptBox[StyleBox[\"symbol\", \"TI\"],2],\[Ellipsis]]\) disables all StandardForm parsing of special input boxes and output formatting for the Package\[Hyphen]X functions \*SubscriptBox[StyleBox[\"symbol\", \"TI\"],StyleBox[\"i\", \"TI\"]].  Possible \*StyleBox[StyleBox[\"symbol\", \"TI\"]]s are LDot, LTensor, LoopIntegrate, FermionLine, and FermionLineProduct.";
	X`Utilities`Uncontract::usage = "\!\(X`Utilities`Uncontract[\*StyleBox[\"expr\", \"TI\"],\*StyleBox[\"k\", \"TI\"]]\) gives the form of \*StyleBox[\"expr\", \"TI\"] where Lorentz products involving four\[Hyphen]vector \*StyleBox[\"k\", \"TI\"] are uncontracted.";
	X`Utilities`TensorStructures::usage = "\!\(X`Utilities`TensorStructures[\*StyleBox[\"expr\", \"TI\"]]\) generates a list of tensor structures appearing in \*StyleBox[\"expr\", \"TI\"].";
	X`Utilities`CollectByTensorStructures::usage = "\!\(X`Utilities`CollectByTensorStructures[\*StyleBox[\"expr\", \"TI\"]]\) organizes \*StyleBox[\"expr\", \"TI\"] by the tensor structures appearing in \*StyleBox[\"expr\", \"TI\"].
\!\(X`Utilities`CollectByTensorStructures[\*StyleBox[\"expr\", \"TI\"],\*StyleBox[\"f\", \"TI\"]]\) applies \*StyleBox[\"f\", \"TI\"] to each coefficient.
\!\(X`Utilities`CollectByTensorStructures[\*StyleBox[\"expr\", \"TI\"],\*StyleBox[\"f\", \"TI\"],\*StyleBox[\"g\", \"TI\"]]\) applies \*StyleBox[\"g\", \"TI\"] to the tensor structures.";
	X`Utilities`ClearDuplicatedTensors::usage = "\!\(X`Utilities`ClearDuplicatedTensors[\*StyleBox[\"expr\", \"TI\"]]\) returns the form of \*StyleBox[\"expr\", \"TI\"] in which formally equivalent tensor structures are identified and consolidated.";
	X`Utilities`FreeIndices::usage = "\!\(X`Utilities`FreeIndices[\*StyleBox[\"expr\", \"TI\"]]\) generates a list of free indices in \*StyleBox[\"expr\", \"TI\"].";
	X`Utilities`DummyIndices::usage = "\!\(X`Utilities`DummyIndices[\*StyleBox[\"expr\", \"TI\"]]\) generates a list of dummy indices in the monomial expression \*StyleBox[\"expr\", \"TI\"].";
	X`Utilities`PassarinoVeltmanTensor::usage="\!\(X`Utilities`PassarinoVeltmanTensor[{{\*SubscriptBox[StyleBox[\"v\", \"TI\"],1],\*SubscriptBox[StyleBox[\"n\", \"TI\"],1]},\[Ellipsis],{\*SubscriptBox[StyleBox[\"v\", \"TI\"],StyleBox[\"j\", \"TI\"]],\*SubscriptBox[StyleBox[\"n\", \"TI\"],StyleBox[\"j\", \"TI\"]]}},{\*SubscriptBox[\[Mu],1],\[Ellipsis],\*SubscriptBox[\[Mu],StyleBox[\"P\", \"TI\"]]}]\) gives the fully symmetric Passarino\[Hyphen]Veltman rank\[Hyphen]P tensor \!\(\*SuperscriptBox[\({\*SuperscriptBox[\(\*RowBox[{\"[\",\(\*SubscriptBox[StyleBox[\"v\", \"TI\"],1]\),\"]\"}]\),\(\*SubscriptBox[StyleBox[\"n\", \"TI\"],1]\)]\[Ellipsis]\*SuperscriptBox[\(\*RowBox[{\"[\",\(\*SubscriptBox[StyleBox[\"v\", \"TI\"],StyleBox[\"j\", \"TI\"]]\),\"]\"}]\),\(\*SubscriptBox[StyleBox[\"n\", \"TI\"],StyleBox[\"j\", \"TI\"]]\)] \*SuperscriptBox[\(\*RowBox[{\"[\",\[ScriptG],\"]\"}]\),\(\*FractionBox[1,2](\*StyleBox[\"P\", \"TI\"]-(\(\*SubscriptBox[StyleBox[\"n\", \"TI\"],1]+\[Ellipsis]+\*SubscriptBox[StyleBox[\"n\", \"TI\"],StyleBox[\"j\", \"TI\"]]\)))\)]}\),\(\*SubscriptBox[\[Mu],1]\[Ellipsis]\*SubscriptBox[\[Mu],P]\)]\).";

	,
(*For version 9, or without Front End*)
	Contract::usage="Contract[expr] gives the form of expr where repeated indices attached to multiplying tensors are contracted.";
    Transverse::usage="Transverse[tensor] gives the transverse scalar projection of the rank\[Hyphen]two tensor containing only one four\[Hyphen]vector.\nTransverse[tensor,v] gives the scalar projection of the rank\[Hyphen]two tensor transverse to vector v.\nTransverse[tensor,v,{\[Mu],\[Nu]}] gives the rank P-2 tensor projection of the rank P tensor transverse to v along indices \[Mu] and \[Nu].";
    Longitudinal::usage="Longitudinal[tensor] gives the longitudinal scalar projection of the rank\[Hyphen]two tensor containing only one four\[Hyphen]vector.\nLongitudinal[tensor,v] gives the scalar projection of the rank\[Hyphen]two tensor longitudinal to vector v.\nLongitudinal[tensor,v,{\[Mu],\[Nu]}] gives the rank P-2 tensor projection of the rank P tensor longitudinal to v along indices \[Mu] and \[Nu] . ";
	LDot::usage="LDot[a,b] represents the Lorentz 4\[Hyphen]vector dot product a\[ThinSpace]\[CenterDot]\[ThinSpace]b.";
	LTensor::usage="LTensor[p,\[Mu],\[Ellipsis]] represents the Lorentz tensor p(\[Mu],\[Ellipsis]).";
	LScalarQ::usage = "LScalarQ[expr] gives True if 'expr' is a Lorentz scalar expression, and False otherwise.  Assigning LScalarQ[symb]=True declares 'symb' to be a Lorentz scalar.";
	MandelstamRelations::usage="MandelstamRelations[{p1,p2,p3,p4,m1,m2,m3,m4}->{s,t,u}] gives a list of replacement rules expressing dot products of incoming 4\[Hyphen]vectors p1, p2 and outgoing 4\[Hyphen]vectors p3, p4 as Mandelstam invariants s, t, u, and masses m1, m2, m3, m4.";

	LoopIntegrate::usage="LoopIntegrate[num,k,{q0,m0},{q1,m1},\[Ellipsis]] expresses the one\[Hyphen]loop tensor integral over integration variable k with numerator num and denominator factors (q0^2-m0^2)(q1^2-m1^2)\[Ellipsis] in terms of Passarino\[Hyphen]Veltman functions.\nLoopIntegrate[num,k,{q0,m0,w0},{q1,m1,w1},\[Ellipsis]] expresses the one\[Hyphen]loop tensor integral in terms of Passarino\[Hyphen]Veltman functions with weights w0,w1,\[Ellipsis].";
	PVX::usage="PVX[r,n1,n2,\[Ellipsis],s01,s12,s23,\[Ellipsis],m0,m1,m2,\[Ellipsis]] is the general Passarino\[Hyphen]Veltman coefficient function X(0...01...12...2\[CenterEllipsis])(s01,s12,s23,\[Ellipsis];m0,m1,m2,\[Ellipsis]).";

	LeviCivitaE::usage="LTensor[LeviCivitaE,\[Mu],\[Nu],\[Rho],\[FinalSigma]] represents the Levi\[Hyphen]Civita antisymmetric symbol near 4 spacetime dimensions.";
	MetricG::usage="LTensor[MetricG,\[Mu],\[Nu]] represents the d\[Hyphen]dimensional flat space Minkowski metric \[ScriptG]^(\[Mu]\[Nu]).";
	Dim::usage="Dim is the number of non\[Hyphen]integer number of spacetime dimensions.";

	X`Utilities`EnableFancyIO::usage="X`Utilities`EnableFancyIO[symbol1,symbol2,\[Ellipsis]] enables the StandardForm parsing and formatting for the Package\[Hyphen]X functions symbol_i.  Possible symbols are LDot, LTensor, LoopIntegrate, FermionLine, and FermionLineProduct.";
	X`Utilities`DisableFancyIO::usage="X`Utilities`DisableFancyIO[symbol1,symbol2,\[Ellipsis]] disables all StandardForm parsing of special input boxes and output formatting for the Package\[Hyphen]X functions symbol_i.  Possible symbols are LDot, LTensor, LoopIntegrate, FermionLine, and FermionLineProduct.";
	X`Utilities`Uncontract::usage="X`Utilities`Uncontract[expr,k] gives the form of expr where Lorentz products involving four\[Hyphen]vector k are uncontracted.";
	X`Utilities`TensorStructures::usage="X`Utilities`TensorStructures[expr] generates a list of tensor structures appearing in expr.";
	X`Utilities`CollectByTensorStructures::usage="X`Utilities`CollectByTensorStructures[expr] organizes expr by the tensor structures appearing in expr.\nX`Utilities`CollectByTensorStructures[expr,f] applies f to each coefficient.\nX`Utilities`CollectByTensorStructures[expr,f,g] applies g to the tensor structures.";
	X`Utilities`ClearDuplicatedTensors::usage="X`Utilities`ClearDuplicatedTensors[expr] returns the form of expr in which formally equivalent tensor structures are identified and consolidated.";
	X`Utilities`FreeIndices::usage="X`Utilities`FreeIndices[expr] generates a list of free indices in expr.";
	X`Utilities`DummyIndices::usage="X`Utilities`DummyIndices[expr] generates a list of dummy indices in the monomial expression expr.";
	X`Utilities`PassarinoVeltmanTensor::usage="X`Utilities`PassarinoVeltmanTensor[{{v1,n1},\[Ellipsis],{vj,nj}},{\[Mu]1,\[Ellipsis],\[Mu]P}] gives the fully symmetric Passarino\[Hyphen]Veltman rank\[Hyphen]P tensor {[v1]^n1\[Ellipsis][vj]^nj [g]^((1/2)(P-(n1+\[Ellipsis]+nj)))}^(\[Mu]1\[Ellipsis]\[Mu]P).";

];

DiracAlgebra::usage = "DiracAlgebra is an option to LoopIntegrate that specifies whether to use the Dirac algebra simplify the numerator.";
Cancel::usage = If[ValueQ[Cancel::usage], Cancel::usage <> "\n" <> #, #] &@ "Cancel is an option to Package\[Hyphen]X function LoopIntegrate that specifies whether to expand and cancel out common scalar products between the numerator and the denominator.";
Apart::usage = If[ValueQ[Apart::usage], Apart::usage <> "\n" <> #, #] &@ "Apart is an option to Package\[Hyphen]X function LoopIntegrate that specifies whether to perform a partial fraction expansion of the denominator factors.";


(* ::Subsubsection::Closed:: *)
(*Dirac.m*)


If[Not[$VersionNumber==9.0] && $Notebooks,
	Dirac1::usage="\!\(\"Dirac1\"\) or \!\(\"\[DoubleStruckOne]\"\) represents the unit matrix in spinor space.";
	DiracG::usage="\!\(\*RowBox[{\"LTensor\",\"[\",\(\*RowBox[{\"DiracG\",\",\",\(\*StyleBox[\"\[Mu]\",\"TR\"]\)}]\),\"]\"}]\) or \!\(\*SubscriptBox[\"\[Gamma]\",\(\*StyleBox[\"\[Mu]\",\"TR\"]\)]\) represents the Dirac gamma matrix with index \!\(\*StyleBox[\"\[Mu]\",\"TR\"]\).
\!\(\*RowBox[{\"LDot\",\"[\",\(\*RowBox[{\"DiracG\",\",\",\(\*StyleBox[\"p\",\"TI\"]\)}]\),\"]\"}]\) or \!\(\*RowBox[{\"\[Gamma]\",\".\",\(\*StyleBox[\"p\",\"TI\"]\)}]\) represents the Feynman slash \!\(\*OverlayBox[{\(\*StyleBox[\"p\",\"TI\"]\),\"\<\[ThinSpace]/\>\"},Alignment->{Center,Center}]\).";
	DiracG5::usage="\!\(\"DiracG5\"\) or \!\(\"\[Gamma]5\"\) represents the fifth Dirac gamma matrix \!\(\*SubscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"5\",\"TR\"]\)]\[ThinSpace]=\[ThinSpace]\*StyleBox[\"i\",\"TI\"] \*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"0\",\"TR\"]\)]\*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"1\",\"TR\"]\)]\*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"2\",\"TR\"]\)]\*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"3\",\"TR\"]\)]\).";
	DiracPL::usage="\!\(\"DiracPL\"\) or \!\(\"\[DoubleStruckCapitalP]L\"\) represents the left chiral projector \!\(\*RowBox[{\(\*FractionBox[\"1\",\"2\",Beveled->True]\),\"(\",\(\*RowBox[{\(\*StyleBox[\"1\",\"TR\"]\),\(\*StyleBox[\"-\",\"TR\"]\),\(\*SubscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"5\",\"TR\"]\)]\)}]\),\")\"}]\).";
	DiracPR::usage="\!\(\"DiracPR\"\) or \!\(\"\[DoubleStruckCapitalP]R\"\) represents the left chiral projector \!\(\*RowBox[{\(\*FractionBox[\"1\",\"2\",Beveled->True]\),\"(\",\(\*RowBox[{\(\*StyleBox[\"1\",\"TR\"]\),\(\*StyleBox[\"+\",\"TR\"]\),\(\*SubscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"5\",\"TR\"]\)]\)}]\),\")\"}]\).";
	DiracS::usage="\!\(\*RowBox[{\"LTensor\",\"[\",\(\*RowBox[{\"DiracS\",\",\",\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\),\"]\"}]\) or \!\(\*SubscriptBox[\"\[Sigma]\",\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\)]\) represents the gamma matrix commutator \!\(\*SuperscriptBox[\[Sigma],\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\)]=\*FractionBox[\(\*StyleBox[\"i\",\"TI\"]\),\(\*StyleBox[\"2\",\"TR\"]\),Beveled->True][\*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"\[Mu]\",\"TR\"]\)], \*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"\[Nu]\",\"TR\"]\)]]\).";
	Spur::usage="\!\(Spur[\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),1],\[Ellipsis],\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),\(\*StyleBox[\"n\",\"TI\"]\)]]\) takes the trace of the product of Dirac matrices \!\(\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),1],\[Ellipsis],\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),\(\*StyleBox[\"n\",\"TI\"]\)]\).";
	DiracMatrix::usage="\!\(DiracMatrix[\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),1],\[Ellipsis],\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),\(\*StyleBox[\"n\",\"TI\"]\)]]\) represents a product of objects in spinors space.";
	Projector::usage="\!\(Projector[\(\*StyleBox[\"name\",\"TI\"]\)][\({\*StyleBox[\"p\",\"TI\"]\),\(\*StyleBox[\"m\",\"TI\"]}\)]\) gives the projector for the off shell \!\(\"self\[Hyphen]energy\"\) form factor associated with \!\(\*StyleBox[\"name\",\"TI\"]\).
\!\(Projector[\(\*StyleBox[\"name\",\"TI\"]\)][{\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1]},{\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2]}]\) gives the projector for the \!\(\"on shell\"\) scalar/pseduoscalar density form factor associated with \!\(\*StyleBox[\"name\",\"TI\"]\).
\!\(Projector[\(\*StyleBox[\"name\",\"TI\"]\),\[Mu]][{\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1]},{\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2]}]\) gives the projector for the \!\(\"on shell\"\) vector/\!\(\"axial-vector\"\) form factor associated with \!\(\*StyleBox[\"name\",\"TI\"]\) and index \[Mu].";


	FermionLine::usage="\!\(FermionLine[{\*SubscriptBox[\(\*StyleBox[\"sgn\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\[Ellipsis]},{\*SubscriptBox[\(\*StyleBox[\"sgn\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\[Ellipsis]},DiracMatrix[\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),1],\[Ellipsis],\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),\(\*StyleBox[\"n\",\"TI\"]\)]]]\) or \!\(\*RowBox[{\"\[LeftAngleBracket]\",\(\*RowBox[{\(\*StyleBox[\"w\",\"TI\"]\),\"[\",\(\*RowBox[{\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),\(\*StyleBox[\"2\",\"TR\"]\)]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),\(\*StyleBox[\"2\",\"TR\"]\)]\),\",\",\"\[Ellipsis]\"}]\),\"]\",\",\",\(\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),\(\*StyleBox[\"1\",\"TR\"]\)]\),\",\",\"\[Ellipsis]\",\",\",\(\*SubscriptBox[\(\*StyleBox[\"mtx\",\"TI\"]\),\(\*StyleBox[\"n\",\"TI\"]\)]\),\",\",\(\*StyleBox[\"w\",\"TI\"]\),\"[\",\(\*RowBox[{\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),\(\*StyleBox[\"1\",\"TR\"]\)]\),\",\",\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),\(\*StyleBox[\"1\",\"TR\"]\)]\),\",\",\"\[Ellipsis]\"}]\),\"]\"}]\),\"\[RightAngleBracket]\"}]\) represents a product of Dirac matrices sandwiched between spinors \!\(\(\*StyleBox[\"\!\(\*OverscriptBox[\(w\), \(_\)]\)\",\"TI\"]\)(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\[Ellipsis])\) and \!\(\(\*StyleBox[\"w\",\"TI\"]\)(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\[Ellipsis])\) corresponding to frequency sign \!\(\*SubscriptBox[\(\*StyleBox[\"sgn\",\"TI\"]\),\(\*StyleBox[\"k\",\"TI\"]\)]\), \!\(\"4\[Hyphen]momentum\"\) \!\(\*SubscriptBox[\(\*StyleBox[\"p\",\"TI\"]\),\(\*StyleBox[\"k\",\"TI\"]\)]\), mass \!\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),\(\*StyleBox[\"k\",\"TI\"]\)]\),\[Ellipsis].";
	FermionLineExpand::usage="\!\(FermionLineExpand[\(\*StyleBox[\"expr\",\"TI\"]\)]\) expands out DiracMatrix, FermionLine, and FermionLineProduct objects in \!\(\*StyleBox[\"expr\",\"TI\"]\).";
	SpinorU::usage = "\!\(SpinorU[\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"]]\) represents the \!\(\"positive\[Hyphen]frequency\"\) Dirac spinor \!\(\*StyleBox[\"u\",\"TI\"](\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"])\) with momentum \!\(\*StyleBox[\"p\",\"TI\"]\), mass \!\(\*StyleBox[\"m\",\"TI\"]\), and unspecified helicity.
\!\(SpinorU[\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"],\*StyleBox[\"\[Lambda]\",\"TI\"]]\) represents the spinor with helicity \!\(\*StyleBox[\"\[Lambda]\",\"TI\"]\).
\!\(SpinorU[\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"],\*StyleBox[\"\[Lambda]\",\"TI\"],\[Ellipsis]]\) represents the spinor with additional labels.";
	SpinorV::usage = "\!\(SpinorV[\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"]]\) represents the \!\(\"negative\[Hyphen]frequency\"\) Dirac spinor \!\(\*StyleBox[\"v\",\"TI\"](\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"])\) with momentum \!\(\*StyleBox[\"p\",\"TI\"]\), mass \!\(\*StyleBox[\"m\",\"TI\"]\), and unspecified helicity.
\!\(SpinorV[\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"],\*StyleBox[\"\[Lambda]\",\"TI\"]]\) represents the spinor with helicity \!\(\*StyleBox[\"\[Lambda]\",\"TI\"]\).
\!\(SpinorV[\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"],\*StyleBox[\"\[Lambda]\",\"TI\"],\[Ellipsis]]\) represents the spinor with additional labels.";
	FermionLineProduct::usage="\!\(FermionLineProduct[\*SubscriptBox[\(\*StyleBox[\"fLine\",\"TI\"]\),1], \*SubscriptBox[\(\*StyleBox[\"fLine\",\"TI\"]\),2],\[Ellipsis]]\) or \!\(\*RowBox[{\(\*SubscriptBox[\(\*StyleBox[\"fLine\",\"TI\"]\),1]\),\"\[CircleTimes]\",\(\*SubscriptBox[\(\*StyleBox[\"fLine\",\"TI\"]\),2]\),\"\[CircleTimes]\",\"\[Ellipsis]\"}]\) represents the direct product of FermionLine objects \!\(\*SubscriptBox[\(\*StyleBox[\"fLine\",\"TI\"]\),1]\), \!\(\*SubscriptBox[\(\*StyleBox[\"fLine\",\"TI\"]\),2]\), \!\(\*StyleBox[\"etc\",\"TI\"]\).";

	$DiracAlgebra::usage = "$DiracAlgebra toggles the use of \[ScriptD]\[Hyphen]dimensional Dirac algebra in tensor algebraic functions like LoopIntegrate, Contract and FermionLineExpand.";
  ,

(*For version 9, or without Front End*)
	Dirac1::usage="Dirac1 represents the unit matrix in spinor space.";
	DiracG::usage="LTensor[DiracG,\[Mu]] represents the Dirac gamma matrix \[Gamma] with index \[Mu].\nLDot[DiracG,p] represents the Feynman slash \[Gamma].p.";
	DiracG5::usage="DiracG5 represents the fifth Dirac gamma matrix \[Gamma]5\[ThinSpace]=\[ThinSpace]i \[Gamma]0 \[Gamma]1 \[Gamma]2 \[Gamma]3.";
	DiracPL::usage="DiracPL represents the left chiral projector (1-\[Gamma]5)/2.";
	DiracPR::usage="DiracPR represents the left chiral projector (1+\[Gamma]5)/2.";
	DiracS::usage="LTensor[DiracS,\[Mu],\[Nu]] represents the gamma matrix commutator \[Sigma](\[Mu]\[Nu])=(i/2)[\[Gamma]\[Mu], \[Gamma]\[Nu]].";
	Spur::usage="Spur[mtx1,\[Ellipsis],mtxn] takes the trace of the product of Dirac matrices mtx1,\[Ellipsis],mtxn.";
	DiracMatrix::usage="DiracMatrix[mtx1,\[Ellipsis],mtxn] represents a product of objects in spinors space.";
	Projector::usage="Projector[name][{p,m}] gives the projector for the off shell self\[Hyphen]energy form factor associated with name.\nProjector[name][{p1,m1},{p2,m2}] gives the projector for the on shell scalar/pseduoscalar density form factor associated with name.\nProjector[name,\[Mu]][{p1,m1},{p2,m2}] gives the projector for the on shell vector/axial-vector form factor associated with name and index \[Mu].";

	FermionLine::usage="FermionLine[{sgn2,p2,m2,\[Ellipsis]},{sgn1,p1,m1,\[Ellipsis]},DiracMatrix[mtx1,\[Ellipsis],mtxn]] represents a product of Dirac matrices sandwiched between spinors w-bar(p2,m2,\[Ellipsis]) and w(p1,m1,\[Ellipsis]) corresponding to frequency sign sgnk, 4\[Hyphen]momentum pk, mass mk,\[Ellipsis].";
	FermionLineExpand::usage="FermionLineExpand[expr] expands out DiracMatrix, FermionLine, and FermionLineProduct objects in expr.";
	SpinorU::usage="SpinorU[p,m] represents the positive\[Hyphen]frequency Dirac spinor u(p,m) with momentum p, mass m, and unspecified helicity.\nSpinorU[p,m,\[Lambda]] represents the spinor with helicity \[Lambda].\nSpinorU[p,m,\[Lambda],\[Ellipsis]] represents the spinor with additional labels.";
	SpinorV::usage="SpinorV[p,m] represents the negative\[Hyphen]frequency Dirac spinor v(p,m) with momentum p, mass m, and unspecified helicity.\nSpinorV[p,m,\[Lambda]] represents the spinor with helicity \[Lambda].\nSpinorV[p,m,\[Lambda],\[Ellipsis]] represents the spinor with additional labels.";
	FermionLineProduct::usage="FermionLineProduct[fLine1, fLine2,\[Ellipsis]] represents the direct product of FermionLine objects fLine1, fLine2, etc.";

	$DiracAlgebra::usage = "$DiracAlgebra toggles the use of d\[Hyphen]dimensional Dirac algebra in tensor algebraic functions like LoopIntegrate, Contract and FermionLineExpand."
];


ChiralBasis::usage = "ChiralBasis is an option to FermionLineExpand that specifies whether to perform the Dirac algebra in the chiral basis, and to generate a result in terms of left/right chiral projectors.";
ChisholmExpand::usage = "ChisholmExpand is an option to FermionLineExpand that specifies whether to make a Chisholm expansion of products of Dirac matrices in 4 dimensions.";
GordonIdentity::usage = "GordonIdentity is an option to FermionLineExpand that specifies whether to eliminate vector (axial-vector) convective transition currents in favor of Dirac (anapole) and Pauli (EDM) transition currents.";
(*SirlinExpand::usage = "SirlinExpand is an option to FermionLineExpand that specifies whether to apply the four dimensional Sirlin identities to expand contracted Dirac matrices across different products of DiracMatrices.";*)


(* ::Subsubsection::Closed:: *)
(*OneLoop.m*)


If[Not[$VersionNumber==9.0] && $Notebooks,
  Mu::usage = "\!\(\"Mu\"\) or \[Micro] is the 't Hooft mass parameter in dimensionally regulated integrals.";
  Eps::usage = "\!\(\"Eps\"\) or \[Epsilon] is the small parameter of dimensional regularization \!\(\*RowBox[{\"\[ScriptD]\",\"=\",\"4\",\"-\",\"2\",\"\[Epsilon]\"}]\).";
  PVA::usage="\!\(PVA[\*StyleBox[\"r\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0]]\) is the \!\(\"Passarino\[Hyphen]Veltman\"\) coefficient function \!\(\*SubscriptBox[\(\*StyleBox[\"A\", \"TB\"]\), RowBox[{UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"0\[Ellipsis]0\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"2r\", \"TI\"]\)]}]](\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0])\).";
  PVB::usage="\!\(PVB[\*StyleBox[\"r\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),1],\*StyleBox[\"s\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1]]\) is the \!\(\"Passarino\[Hyphen]Veltman\"\) coefficient function \!\(\*SubscriptBox[\(\*StyleBox[\"B\", \"TB\"]\), RowBox[{UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"0\[Ellipsis]0\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"2r\", \"TI\"]\)],UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"1\[Ellipsis]1\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"n1\", \"TI\"]\)]}]](\*StyleBox[\"s\", \"TI\"]\";\"\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1])\).";
  ScalarC0::usage="\!\(ScalarC0[\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2]]\) gives the scalar \!\(\"Passarino\[Hyphen]Veltman\"\) \!\(\"three\[Hyphen]point\"\) function \!\(\*SubscriptBox[\(\*StyleBox[\"C\",\"TI\"]\),0](\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2]\";\"\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2])\) for real external invariants \!\(\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2]\) and real positive masses \!\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2]\).";
  PVC::usage="\!\(PVC[\*StyleBox[\"r\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2]]\) is the \!\(\"Passarino\[Hyphen]Veltman\"\) coefficient function \!\(\*SubscriptBox[\(\*StyleBox[\"C\", \"TB\"]\), RowBox[{UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"0\[Ellipsis]0\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"2r\", \"TI\"]\)],UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"1\[Ellipsis]1\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"n1\", \"TI\"]\)],UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"2\[Ellipsis]2\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"n2\", \"TI\"]\)]}]](\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2]\";\"\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2])\).";
  PVD::usage="\!\(PVD[\*StyleBox[\"r\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]]\) is the \!\(\"Passarino\[Hyphen]Veltman\"\) coefficient function \!\(\*SubscriptBox[\(\*StyleBox[\"D\", \"TB\"]\), RowBox[{UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"0\[Ellipsis]0\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"2r\", \"TI\"]\)],UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"1\[Ellipsis]1\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"n1\", \"TI\"]\)],UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"2\[Ellipsis]2\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"n2\", \"TI\"]\)],UnderscriptBox[UnderscriptBox[\(\*StyleBox[\(\"3\[Ellipsis]3\"\), \"TR\"]\), \(\[UnderBrace]\)], \(\*StyleBox[\"n3\", \"TI\"]\)]}]](\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4]\";\"\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]\";\"\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3])\).";
  ScalarD0::usage="\!\(ScalarD0[\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]]\) gives the scalar \!\(\"Passarino\[Hyphen]Veltman\"\) \!\(\"four\[Hyphen]point function\"\) \*SubscriptBox[\(\*StyleBox[\"D\",\"TI\"]\),0](\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1], \*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2], \*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3], \*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4]; \*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12], \*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]; \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0], \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1], \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2], \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]) for real external invariants \!\(\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]\) and real positive masses \!\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]\).";
  ScalarC0IR6::usage="\!\(ScalarC0IR6[\*StyleBox[\"s\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1]]\) gives the finite part of \!\(\"Ellis\[Hyphen]Zanderighi\"\) \!\(\"IR\[Hyphen]divergent\"\) triangle 6, \*SubsuperscriptBox[\(\*StyleBox[\"I\",\"TI\"]\),\(\*StyleBox[\"C6\",\"TR\"]\),\(\*StyleBox[\"fin\",\"TR\"]\)](\*StyleBox[\"s\", \"TI\"];\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1]) for real \*StyleBox[\"s\", \"TI\"] and positive \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0] and \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1].";
  ScalarD0IR12::usage="\!\(ScalarD0IR12[\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]]\) gives the finite part of \!\(\"Ellis\[Hyphen]Zanderighi\"\) soft and collinear singular \!\(\"box 12\"\), \!\(\*SubsuperscriptBox[\(\*StyleBox[\"I\",\"TI\"]\),\(\*StyleBox[\"D12\",\"TR\"]\),\(\*StyleBox[\"fin\",\"TR\"]\)](\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3]\";\"\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]\";\"\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3])\) for real \!\(\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]\) and positive \!\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2] \"and\" \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]\).";
  ScalarD0IR13::usage="\!\(ScalarD0IR13[\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]]\) gives the finite part of \!\(\"Ellis\[Hyphen]Zanderighi\"\) collinear \!\(\"box 13\"\), \!\(\*SubsuperscriptBox[\(\*StyleBox[\"I\",\"TI\"]\),\(\*StyleBox[\"D13\",\"TR\"]\),\(\*StyleBox[\"fin\",\"TR\"]\)](\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4]\";\"\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]\";\"\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3])\) for real \!\(\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2], \*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]\) and positive \!\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2] \"and\" \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]\).";
  ScalarD0IR16::usage="\!\(ScalarD0IR16[\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]]\) gives the finite part of \!\(\"Ellis\[Hyphen]Zanderighi\"\) \!\(\"IR\[Hyphen]divergent\"\) \!\(\"box 16\"\), \!\(\*SubsuperscriptBox[\(\*StyleBox[\"I\",\"TI\"]\),\(\*StyleBox[\"D16\",\"TR\"]\),\(\*StyleBox[\"fin\",\"TR\"]\)](\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3]\";\"\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]\";\"\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3])\) for real \!\(\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),4],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),23]\) and positive \!\(\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),2] \"and\" \*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),3]\).";
  Kallen\[Lambda]::usage="\!\(Kallen\[Lambda][\*StyleBox[\"a\", \"TI\"],\*StyleBox[\"b\", \"TI\"],\*StyleBox[\"c\", \"TI\"]]\) gives the K\[ADoubleDot]ll\[EAcute]n kinematic (triangle) polynomial \!\(\*StyleBox[\"\[Lambda]\", \"TI\"](\*StyleBox[\"a\", \"TI\"],\*StyleBox[\"b\", \"TI\"],\*StyleBox[\"c\", \"TI\"]) = \*SuperscriptBox[\(\*StyleBox[\"a\", \"TI\"]\),\(\*StyleBox[\"2\", \"TR\"]\)]+\*SuperscriptBox[\(\*StyleBox[\"b\", \"TI\"]\),\(\*StyleBox[\"2\", \"TR\"]\)]+\*SuperscriptBox[\(\*StyleBox[\"c\", \"TI\"]\),\(\*StyleBox[\"2\", \"TR\"]\)]-\*StyleBox[\"2\", \"TR\"] \*StyleBox[\"a b\", \"TI\"]-\*StyleBox[\"2\", \"TR\"] \*StyleBox[\"a c\", \"TI\"]-\*StyleBox[\"2\", \"TR\"] \*StyleBox[\"b c\", \"TI\"]\).";
  Kibble\[Phi]::usage="\!\(Kibble\[Phi][\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),4],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),23]]\) gives the Kibble kinematic polynomial \!\(\*StyleBox[\"\[Phi]\", \"TI\"](\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),3],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),4];\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),12],\*SubscriptBox[\(\*StyleBox[\"s\", \"TI\"]\),23])\).";
  DiscB::usage="\!\(DiscB[\*StyleBox[\"s\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1]]\) gives the part of the \!\(\"Passarino\[Hyphen]Veltman\"\) \*SubscriptBox[\(\*StyleBox[\"B\",\"TI\"]\),0] function containing the \*StyleBox[\"s\",\"TI\"]\[Hyphen]plane branch cut, \*StyleBox[\"\[CapitalLambda]\",\"TI\"](\*StyleBox[\"s\",\"TI\"];\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"m\",\"TI\"]\),1]).";
  DiscExpand::usage="\!\(DiscExpand[\*StyleBox[\"expr\", \"TI\"]]\) replaces DiscB everywhere inside \!\(\*StyleBox[\"expr\", \"TI\"]\) with its explicit definition.";
  KallenExpand::usage="\!\(KallenExpand[\*StyleBox[\"expr\", \"TI\"]]\) replaces Kallen\[Lambda] everywhere inside \!\(\*StyleBox[\"expr\", \"TI\"]\) with its explicit definition.";
  KibbleExpand::usage="\!\(KibbleExpand[\*StyleBox[\"expr\", \"TI\"]]\) replaces Kibble\[Phi] everywhere inside \!\(\*StyleBox[\"expr\", \"TI\"]\) with its explicit definition.";
  C0Expand::usage="\!\(C0Expand[\*StyleBox[\"expr\", \"TI\"]]\) replaces ScalarC0 and ScalarC0IR6 everywhere inside \!\(\*StyleBox[\"expr\", \"TI\"]\) with their explicit expressions.";
  D0Expand::usage="\!\(D0Expand[\*StyleBox[\"expr\", \"TI\"]]\) replaces ScalarD0, ScalarD0IR12, ScalarD0IR13, and ScalarD0IR16 everywhere inside \!\(\*StyleBox[\"expr\", \"TI\"]\) with their explicit expressions.";
  ContinuedDiLog::usage="\!\(ContinuedDiLog[{\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"\[Alpha]\",\"TI\"]\),1]},{\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),2],\*SubscriptBox[\(\*StyleBox[\"\[Alpha]\",\"TI\"]\),2]}]\) gives the two variable Beenakker\[Dash]Denner continued dilogarithm function \!\(\*SubscriptBox[\"\[ScriptCapitalL]\[ScriptI]\",\(\*StyleBox[\"2\",\"TR\"]\)](\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),1] + \*StyleBox[\"i\", \"TI\"] \*SubscriptBox[\(\*StyleBox[\"\[Alpha]\",\"TI\"]\),1] \[CurlyEpsilon], \*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),2] + \*StyleBox[\"i\", \"TI\"] \*SubscriptBox[\(\*StyleBox[\"\[Alpha]\",\"TI\"]\),2] \[CurlyEpsilon])\).";
  DiLog::usage="\!\(DiLog[\*StyleBox[\"x\", \"TI\"],\[Alpha]]\) gives the dilogarithm function, which for real \!\(x>1\) evaluates on the side of the branch prescribed by \*UnderscriptBox[\(lim\), \(\[CurlyEpsilon] \[Rule] \*SuperscriptBox[\"0\", \"+\"]\),LimitsPositioning->False]\[ThinSpace]\*SubscriptBox[Li,2](\*RowBox[{\(\*StyleBox[\"x\", \"TI\"]+\*StyleBox[\"i\", \"TI\"] \[Alpha] \[CurlyEpsilon]\)}]).";
  Ln::usage="\!\(Ln[\*StyleBox[\"x\", \"TI\"],\[Alpha]]\) gives the natural logarithm, which for real \!\(x<0\) evaluates on the side of the branch prescribed by \*UnderscriptBox[\(lim\), \(\[CurlyEpsilon] \[Rule] \*SuperscriptBox[\"0\", \"+\"]\),LimitsPositioning->False]\[ThinSpace]log(\*RowBox[{\(\*StyleBox[\"x\", \"TI\"]+\*StyleBox[\"i\", \"TI\"] \[Alpha] \[CurlyEpsilon]\)}]).";
  LoopRefine::usage = "\!\(LoopRefine[\*StyleBox[\"expr\", \"TI\"]]\) converts the \!\(\"Passarino\[Hyphen]Veltman\"\) coefficient functions in \*StyleBox[\"expr\",\"TI\"] to analytic expressions that can be numerically evaluated.";
  LoopRefineSeries::usage="\!\(LoopRefineSeries[\*StyleBox[\"f\", \"TI\"],{\*StyleBox[\"s\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),0],\*StyleBox[\"n\", \"TI\"]}]\) generates a Taylor series expansion of \*StyleBox[\"f\", \"TI\"] containing \!\(\"Passarino\[Hyphen]Veltman\"\) functions about the point \!\(\*StyleBox[\"s\", \"TI\"]=\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),0]\) to order \*SuperscriptBox[\((\*StyleBox[\"s\", \"TI\"]-\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),0])\),\(\*StyleBox[\"n\",\"TI\"]\)].
\!\(LoopRefineSeries[\*StyleBox[\"f\", \"TI\"],{\*StyleBox[\"s\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"s\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),\(\*StyleBox[\"s\",\"TI\"]\)]},{\*StyleBox[\"t\", \"TI\"],\*SubscriptBox[\(\*StyleBox[\"t\",\"TI\"]\),0],\*SubscriptBox[\(\*StyleBox[\"n\",\"TI\"]\),\(\*StyleBox[\"t\",\"TI\"]\)]},\*StyleBox[\"\[Ellipsis]\", \"TR\"]]\) successively finds Taylor series expansions with respect to \*StyleBox[\"s\",\"TI\"], then \*StyleBox[\"t\",\"TI\"], etc.";
Discontinuity::usage="\!\(Discontinuity[\*StyleBox[\"s\", \"TI\"]]\) is a setting for Part to LoopRefine to compute the discontinuity across the normal threshold cut in channel \*StyleBox[\"s\",\"TI\"].
\!\(Discontinuity[\*StyleBox[\"s\", \"TI\"],\*StyleBox[\"t\", \"TI\"]]\) computes the Mandelstam double spectral function in overlapping channels \*StyleBox[\"s\",\"TI\"] and \*StyleBox[\"t\",\"TI\"].";(*;
Rational::usage = If[ValueQ[Rational::usage], Rational::usage <> "\n" <> #, #] &@ "Rational is a setting for Part to Package-X function LoopRefine that limits the calculation to the part that is not cut-constructible."*)

  X`Utilities`SimplifyLn::usage="\!\(X`Utilities`SimplifyLn[\*StyleBox[\"expr\", \"TI\"]]\) attempts to simplify all instances of Ln[\*StyleBox[\"x\", \"TI\"], \*StyleBox[\"a\", \"TI\"]] in \*StyleBox[\"expr\", \"TI\"], assuming all variables in \*StyleBox[\"x\", \"TI\"] are real.
\!\(X`Utilities`SimplifyLn[\*StyleBox[\"expr\", \"TI\"],{\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),2],\[Ellipsis]}]\) simplifies all instances of Ln[\*StyleBox[\"x\", \"TI\"], \*StyleBox[\"a\", \"TI\"]] assuming the \*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),2],\[Ellipsis] are complex.";
  X`Utilities`SimplifyDiLog::usage="\!\(X`Utilities`SimplifyDiLog[\*StyleBox[\"expr\", \"TI\"]]\) attempts to simplify all instances of DiLog[\*StyleBox[\"x\", \"TI\"], \*StyleBox[\"a\", \"TI\"]] in \*StyleBox[\"expr\", \"TI\"], assuming all variables in \*StyleBox[\"x\", \"TI\"] are real.
\!\(X`Utilities`SimplifyDiLog[\*StyleBox[\"expr\", \"TI\"],{\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),2],\[Ellipsis]}]\) simplifies all instances of DiLog[\*StyleBox[\"x\", \"TI\"], \*StyleBox[\"a\", \"TI\"]] assuming the \*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),1],\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),2],\[Ellipsis] are complex.";
  X`Utilities`SimplifyContinuedDiLog::usage="\!\(X`Utilities`SimplifyContinuedDiLog[\*StyleBox[\"expr\", \"TI\"]]\) attempts to simplify all instances of \!\(ContinuedDiLog[\[Ellipsis],{\*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),\(\*StyleBox[\"i\",\"TI\"]\)], \*SubscriptBox[\(\*StyleBox[\"a\",\"TI\"]\),\(\*StyleBox[\"i\",\"TI\"]\)]},\[Ellipsis]]\) in expr, assuming all variables in the \*SubscriptBox[\(\*StyleBox[\"x\",\"TI\"]\),\(\*StyleBox[\"i\",\"TI\"]\)] are real.";
  X`Utilities`ContinuedDiLogExpand::usage="\!\(X`Utilities`ContinuedDiLogExpand[\*StyleBox[\"expr\", \"TI\"]]\) expands ContinuedDiLog everywhere inside \*StyleBox[\"expr\", \"TI\"] in terms of DiLog and Ln functions.";
  X`Utilities`EquivalentAlternatives::usage = "\!\(X`Utilities`EquivalentAlternatives[\*StyleBox[\"f\", \"TI\"][\*StyleBox[\"args\", \"TI\"]]]\) generates all equivalent permutations of the pattern \!\(\*StyleBox[\"f\", \"TI\"][\*StyleBox[\"args\", \"TI\"]]\) consistent with the invariances of \!\(\"Package\[Hyphen]X\"\) symbol \*StyleBox[\"f\", \"TI\"] in the form of Alternatives, which can be used in the left hand side of a Rule.";
  X`Utilities`PermutePVD::usage="\!\(X`Utilities`PermutePVD[\*StyleBox[\"s\", \"TI\"],\*StyleBox[\"t\", \"TI\"]][\*StyleBox[\"expr\", \"TI\"]]\) permutes the arguments of PVD, ScalarD0 and related four-point functions in \*StyleBox[\"expr\", \"TI\"] so that channel invariants \*StyleBox[\"s\", \"TI\"] and \*StyleBox[\"t\", \"TI\"] corresponding to Mandelstam invariants are moved to the 5th and 6th kinematic positions.";
  X`Utilities`PVNormal::usage="\!\(X`Utilities`PVNormal[\*StyleBox[\"expr\", \"TI\"]]\) converts derivatives of weighted n\[Hyphen]dimensional Passarino\[Hyphen]Veltman coefficient functions in \*StyleBox[\"expr\", \"TI\"] to undifferentiated unweighted 4\[Minus]2\[Epsilon]\[Hyphen]dimensional coefficient functions.";
  X`Utilities`$PVShortForm::usage="X`Utilities`$PVShortForm specifies whether to omit the kinematic arguments of symbolic functions PVA, PVB, PVC and PVD in TraditionalForm.";
,  
(*For version 9, or without Front End*)
  Mu::usage = "Mu is the 't Hooft mass parameter \[Micro] in dimensionally regulated integrals.";
  Eps::usage = "Eps is the small parameter \[Epsilon] of dimensional regularization d=4-2\[Epsilon].";
  PVA::usage="PVA[r,m0] is the Passarino\[Hyphen]Veltman coefficient function A('0'\[Times]2r)(m0).";
  PVB::usage="PVB[r,n1,s,m0,m1] is the Passarino\[Hyphen]Veltman coefficient function B('0'\[Times]2r)('1'\[Times]n1)(s;m0,m1).";
  ScalarC0::usage="ScalarC0[s1,s12,s2,m0,m1,m2] gives the scalar Passarino\[Hyphen]Veltman three\[Hyphen]point function C0(s1,s12,s2;m0,m1,m2) for real external invariants s1,s12,s2 and real positive masses m0,m1,m2.";
  PVC::usage="PVC[r,n1,n2,s1,s12,s2,m0,m1,m2] is the Passarino\[Hyphen]Veltman coefficient function C('0'\[Times]2r)('1'\[Times]n1)('2'\[Times]n2)(s1,s12,s2;m0,m1,m2).";
  PVD::usage="PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] is the Passarino\[Hyphen]Veltman coefficient function D('0'\[Times]2r)('1'\[Times]n1)('2'\[Times]n2)('3'\[Times]n3)(s1,s2,s3,s4;s12,s23;m0,m1,m2,m3).";
  ScalarD0::usage="ScalarD0[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] gives the scalar Passarino\[Hyphen]Veltman four\[Hyphen]point function D0(s1, s2, s3, s4; s12, s23; m0, m1, m2, m3) for real external invariants s1,s2,s3,s4,s12,s23 and real positive masses m0,m1,m2,m3.";
  ScalarC0IR6::usage="ScalarC0IR6[s,m0,m1] gives the finite part of Ellis\[Hyphen]Zanderighi IR\[Hyphen]divergent triangle 6, IC6(fin)(s;m0,m1) for real s and positive m0 and m1.";
  ScalarD0IR12::usage="ScalarD0IR12[s2,s3,s12,s23,m2,m3] gives the finite part of Ellis\[Hyphen]Zanderighi soft and collinear singular box 12, ID12(fin)(s2,s3;s12,s23;m2,m3) for real s2,s3,s12,s23 and positive m2 and m3.";
  ScalarD0IR13::usage="ScalarD0IR13[s2,s3,s4,s12,s23,m2,m3] gives the finite part of Ellis\[Hyphen]Zanderighi collinear box 13, ID13(fin)(s2,s3,s4;s12,s23;m2,m3) for real s2, s3,s4,s12,s23 and positive m2 and m3.";
  ScalarD0IR16::usage="ScalarD0IR16[s2,s3,s12,s23,m1,m2,m3] gives the finite part of Ellis\[Hyphen]Zanderighi IR\[Hyphen]divergent box 16, ID16(fin)(s2,s3;s12,s23;m1,m2,m3) for real s3,s4,s12,s23 and positive m1,m2 and m3.";
  Kallen\[Lambda]::usage="Kallen\[Lambda][a,b,c] gives the K\[ADoubleDot]ll\[EAcute]n kinematic (triangle) polynomial \[Lambda](a,b,c) = a^2 + b^2 + c^2 - 2ab - 2ac - 2bc.";
  Kibble\[Phi]::usage="Kibble\[Phi][s1,s2,s3,s4,s12,s23] gives the Kibble kinematic polynomial \[Phi](s1,s2,s3,s4;s12,s23).";
  DiscB::usage="DiscB[s,m0,m1] gives the part of the Passarino\[Hyphen]Veltman B0 function containing the s\[Hyphen]plane branch cut, \[CapitalLambda](s;m0,m1).";
  DiscExpand::usage="DiscExpand[expr] replaces DiscB everywhere inside expr with its explicit definition.";
  KallenExpand::usage="KallenExpand[expr] replaces Kallen\[Lambda] everywhere inside expr with its explicit definition.";
  KibbleExpand::usage="KibbleExpand[expr] replaces Kibble\[Phi] everywhere inside expr with its explicit definition.";
  C0Expand::usage="C0Expand[expr] replaces ScalarC0 and ScalarC0IR6 everywhere inside expr with their explicit expressions.";
  D0Expand::usage="D0Expand[expr] replaces ScalarD0, ScalarD0IR12, ScalarD0IR13, and ScalarD0IR16 everywhere inside expr with their explicit expressions.";
  ContinuedDiLog::usage="ContinuedDiLog[{x1,\[Alpha]1},{x2,\[Alpha]2}] gives the two variable Beenakker\[Dash]Denner continued dilogarithm function Li2(x1 + i \[Alpha]1 \[CurlyEpsilon], x2 + i \[Alpha]2 \[CurlyEpsilon]).";
  DiLog::usage="DiLog[x,\[Alpha]] gives the dilogarithm function, which for real x>1 evaluates on the side of the branch prescribed by lim\[ThinSpace](\[CurlyEpsilon]->0+)\[ThinSpace]Li2(x+i \[Alpha] \[CurlyEpsilon]).";
  Ln::usage="Ln[x,\[Alpha]] gives the natural logarithm, which for real x<0 evaluates on the side of the branch prescribed by lim\[ThinSpace](\[CurlyEpsilon]->0+)log(x+i \[Alpha] \[CurlyEpsilon]).";
  LoopRefine::usage="LoopRefine[expr] converts the Passarino\[Hyphen]Veltman coefficient functions in expr to analytic expressions that can be numerically evaluated.";
  LoopRefineSeries::usage="LoopRefineSeries[f,{s,s0,n}] generates a Taylor series expansion of f containing Passarino\[Hyphen]Veltman functions about the point s=s0 to order (s-s0)^n.\nLoopRefineSeries[f,{s,s0,ns},{t,t0,nt},\[Ellipsis]] successively finds Taylor series expansions with respect to s, then t, etc.";
  Discontinuity::usage="Discontinuity[s] is a setting for Part to LoopRefine to compute the discontinuity across the normal threshold cut in channel s.\nDiscontinuity[s,t] computes the Mandelstam double spectral function in overlapping channels s and t.";
(*
Rational::usage = If[ValueQ[Rational::usage], Rational::usage <> "\n" <> #, #] &@ "Rational is a setting for Part to Package-X function LoopRefine that limits the calculation to the part that is not cut-constructible.";
*)

  X`Utilities`SimplifyLn::usage="X`Utilities`SimplifyLn[expr] attempts to simplify all instances of Ln[x, a] in expr, assuming all variables in x are real.\nX`Utilities`SimplifyLn[expr,{x1,x2,\[Ellipsis]}] simplifies all instances of Ln[x, a] assuming the x1,x2,\[Ellipsis] are complex.";
  X`Utilities`SimplifyDiLog::usage="X`Utilities`SimplifyDiLog[expr] attempts to simplify all instances of DiLog[x, a] in expr, assuming all variables in x are real.\nX`Utilities`SimplifyDiLog[expr,{x1,x2,\[Ellipsis]}] simplifies all instances of DiLog[x, a] assuming the x1,x2,\[Ellipsis] are complex.";
  X`Utilities`SimplifyContinuedDiLog::usage="X`Utilities`SimplifyContinuedDiLog[expr] attempts to simplify all instances of ContinuedDiLog[\[Ellipsis],{xi, ai},\[Ellipsis]] in expr, assuming all variables in the xi are real.";
  X`Utilities`ContinuedDiLogExpand::usage="X`Utilities`ContinuedDiLogExpand[expr] expands ContinuedDiLog everywhere inside expr in terms of DiLog and Ln functions.";
  X`Utilities`EquivalentAlternatives::usage="X`Utilities`EquivalentAlternatives[f[args]] generates all equivalent permutations of the pattern f[args] consistent with the invariances of Package\[Hyphen]X symbol f in the form of Alternatives, which can be used in the left hand side of a Rule.";
  X`Utilities`PermutePVD::usage="X`Utilities`PermutePVD[s,t][expr] permutes the arguments of PVD, ScalarD0 and related four-point functions in expr so that channel invariants s and t corresponding to Mandelstam invariants are moved to the 5th and 6th kinematic positions.";
  X`Utilities`PVNormal::usage="X`Utilities`PVNormal[expr] converts derivatives of weighted n\[Hyphen]dimensional Passarino\[Hyphen]Veltman coefficient functions in expr to undifferentiated unweighted 4\[Minus]2\[Epsilon]\[Hyphen]dimensional coefficient functions.";
  X`Utilities`$PVShortForm::usage="X`Utilities`$PVShortForm specifies whether to omit the kinematic arguments of symbolic functions PVA, PVB, PVC and PVD in TraditionalForm.";

];

Analytic::usage = "Analytic is an option for Limit and Series, and for Package-X functions LoopRefine and LoopRefineSeries.";
TargetScale::usage = "TargetScale is an option for LoopRefine and LoopRefineSeries that sets the mass variable with which the ratio of \!\(\*SuperscriptBox[\[Micro],2]\) is to be taken.";
ExplicitC0::usage = "ExplicitC0 is an option for LoopRefine and LoopRefineSeries that sets the threshold of complexity for inserting explicit analytic expressions for ScalarC0.";
Organization::usage = "Organization is an option for LoopIntegrate, LoopRefine and LoopRefineSeries that specifies how the final result should be organized.";

Part::usage = If[ValueQ[Part::usage], Part::usage <> "\n" <> #, #] &@ "Part is an option to Package-X function LoopRefine that specifies the part of the full result that should be calculated.";
UVDivergent::usage = "UVDivergent is a setting for Part to LoopRefine that limits the calculation to the (logarithmic) ultraviolet divergent part.";
IRDivergent::usage = "IRDivergent is a setting for Part to LoopRefine that limits the calculation to the (logarithmic) soft and collinear divergent part.";





(* ::Subsubsection::Closed:: *)
(*Linking to Documentation Center and Templates*)


(*X`Private`\[CurlyEpsilon]::usage="\!\(\*SubscriptBox[\"\[CurlyEpsilon]\",\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Rho]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[FinalSigma]\",\"TR\"]\)}]\)]\) represents the \!\(Levi\[Hyphen]Civita\) antisymmetric symbol near 4 spacetime dimensions.";
X`Private`\[DoubleStruckG]::usage="\!\(\*SubscriptBox[\"\[DoubleStruckG]\",\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\)]\) represents the \!\(\*StyleBox[\"d\",\"TI\"]\[Hyphen]dimensional\) flat space Minkowski metric \!\(\*SuperscriptBox[\(\*StyleBox[\"\[ScriptG]\",\"TR\"]\),\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\)]\).";
X`Private`\[ScriptD]::usage="\!\(\"\[ScriptD]\"\) represents the non\[Hyphen]integer number of spacetime dimensions.";

X`Private`\[Micro]::usage = "\!\(\"\[Micro]\"\) is the 't Hooft mass parameter in dimensionally regulated integrals.";
X`Private`\[Epsilon]::usage = "\!\(\"\[Epsilon]\"\) is the small parameter of dimensional regularization \!\(\*RowBox[{\"\[ScriptD]\",\"=\",\"4\",\"-\",\"2\",\"\[Epsilon]\"}]\).";

X`Private`\[DoubleStruckOne]::usage="Dirac1 represents the unit matrix \[DoubleStruckOne] in spinor space.";

X`Private`\[Gamma]::usage="\!\(\*SubscriptBox[\"\[Gamma]\",\(\*StyleBox[\"\[Mu]\",\"TR\"]\)]\) represents the Dirac gamma matrix with index \!\(\*StyleBox[\"\[Mu]\",\"TR\"]\).
\!\(\*RowBox[{\"\[Gamma]\",\".\",\(\*StyleBox[\"p\",\"TI\"]\)}]\) or \!\(\*RowBox[{\(\*StyleBox[\"p\",\"TI\"]\),\".\",\"\[Gamma]\"}]\) represents the Feynman slash \!\(\*OverlayBox[{\(\*StyleBox[\"p\",\"TI\"]\),\"/\"}]\).";
X`Private`\[Gamma]5::usage="\!\(\"\[Gamma]5\"\) or DiracG5 represents the fifth Dirac gamma matrix \!\(\*SubscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"5\",\"TR\"]\)]\[ThinSpace]=\[ThinSpace]\*StyleBox[\"i\",\"TI\"] \*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"0\",\"TR\"]\)]\*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"1\",\"TR\"]\)]\*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"2\",\"TR\"]\)]\*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"3\",\"TR\"]\)]\).";
X`Private`\[DoubleStruckCapitalP]L::usage="\!\(\"\[DoubleStruckCapitalP]L\"\) or DiracPL represents the left chiral projector \!\(\*RowBox[{\(\*FractionBox[\"1\",\"2\",Beveled->True]\),\"(\",\(\*RowBox[{\(\*StyleBox[\"1\",\"TR\"]\),\(\*StyleBox[\"-\",\"TR\"]\),\(\*SubscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"5\",\"TR\"]\)]\)}]\),\")\"}]\).";
X`Private`\[DoubleStruckCapitalP]R::usage="\!\(\"\[DoubleStruckCapitalP]R\"\) or DiracPR represents the left chiral projector \!\(\*RowBox[{\(\*FractionBox[\"1\",\"2\",Beveled->True]\),\"(\",\(\*RowBox[{\(\*StyleBox[\"1\",\"TR\"]\),\(\*StyleBox[\"+\",\"TR\"]\),\(\*SubscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"5\",\"TR\"]\)]\)}]\),\")\"}]\).";
X`Private`\[Sigma]::usage="\!\(\*SubscriptBox[\"\[Sigma]\",\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\",\",\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\)]\) represents the gamma matrix commutator \!\(\*SuperscriptBox[\[Sigma],\(\*RowBox[{\(\*StyleBox[\"\[Mu]\",\"TR\"]\),\(\*StyleBox[\"\[Nu]\",\"TR\"]\)}]\)]=\*FractionBox[\(\*StyleBox[\"i\",\"TI\"]\),\(\*StyleBox[\"2\",\"TR\"]\),Beveled->True][\*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"\[Mu]\",\"TR\"]\)], \*SuperscriptBox[\(\*StyleBox[\"\[Gamma]\",\"TR\"]\),\(\*StyleBox[\"\[Nu]\",\"TR\"]\)]]\).";

X`Private`\[ScriptU]::usage = "\!\(\[ScriptU][\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"]]\) represents the \!\(\"positive\[Hyphen]frequency\"\) Dirac spinor \!\(\*StyleBox[\"u\",\"TI\"](\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"])\) with momentum \!\(\*StyleBox[\"p\",\"TI\"]\), mass \!\(\*StyleBox[\"m\",\"TI\"]\), and unspecified helicity.
\!\(\[ScriptU][\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"],\*StyleBox[\"\[Lambda]\",\"TI\"]]\) represents the spinor with helicity \!\(\*StyleBox[\"\[Lambda]\",\"TI\"]\).
\!\(\[ScriptU][\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"],\*StyleBox[\"\[Lambda]\",\"TI\"],\[Ellipsis]]\) represents the spinor with additional labels.";

X`Private`\[ScriptV]::usage = "\!\(\[ScriptV][\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"]]\) represents the \!\(\"negative\[Hyphen]frequency\"\) Dirac spinor \!\(\*StyleBox[\"v\",\"TI\"](\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"])\) with momentum \!\(\*StyleBox[\"p\",\"TI\"]\), mass \!\(\*StyleBox[\"m\",\"TI\"]\), and unspecified helicity.
\!\(\[ScriptV][\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"],\*StyleBox[\"\[Lambda]\",\"TI\"]]\) represents the spinor with helicity \!\(\*StyleBox[\"\[Lambda]\",\"TI\"]\).
\!\(\[ScriptV][\*StyleBox[\"p\",\"TI\"],\*StyleBox[\"m\",\"TI\"],\*StyleBox[\"\[Lambda]\",\"TI\"],\[Ellipsis]]\) represents the spinor with additional labels.";*)


If[$Notebooks,
  Unprotect[Documentation`CreateMessageLink];
	Documentation`CreateMessageLink["X`", "DiracAlgebra", "usage", "English"] := Documentation`CreateMessageLink["X`", "LoopIntegrate", "usage", "English"];
	Documentation`CreateMessageLink["X`", "Kallen\[Lambda]", "usage", "English"] := Documentation`CreateMessageLink["X`", "KallenLambda", "usage", "English"];	
	Documentation`CreateMessageLink["X`", "Kibble\[Phi]", "usage", "English"] := Documentation`CreateMessageLink["X`", "KibblePhi", "usage", "English"];
	Documentation`CreateMessageLink["X`", "SpinorU", "usage", "English"] := Documentation`CreateMessageLink["X`", "FermionLine", "usage", "English"];
	Documentation`CreateMessageLink["X`", "SpinorV", "usage", "English"] := Documentation`CreateMessageLink["X`", "FermionLine", "usage", "English"];  
  Protect[Documentation`CreateMessageLink];

  (*The following makes autocomplete insert template for FermionLine with "DiracMatrix" instead of a placeholder.*)
  FE`systemQ[FE`s_]:=StringMatchQ[Quiet[Check[Context[FE`s],""]],"System`"|"X`"];
  (*The following makes autocomplete insert template for \[Gamma] \[Sigma] instead of a placeholder.*)
  FE`lowcaseQ[FE`s_]:=StringMatchQ[FE`s,Except["\[Gamma]"|"\[Sigma]"|"\[CurlyEpsilon]",RegularExpression["[\[Alpha]\[Beta]\[Delta]\[Epsilon]\[CurlyEpsilon]\[Zeta]\[Eta]\[Theta]\[CurlyTheta]\[Iota]\[Kappa]\[CurlyKappa]\[Lambda]\[Mu]\[Nu]\[Xi]\[Omicron]\[Pi]\[CurlyPi]\[Rho]\[CurlyRho]\[FinalSigma]\[Tau]\[Upsilon]\[Phi]\[CurlyPhi]\[Chi]\[Psi]\[Omega]]+"]|RegularExpression["[[:lower:]]([[:alnum:]]*)"]|"\[Ellipsis]"|"\"*\""]];
  
  (*The following prompts a few strings for projetor.*)
  FE`Evaluate[FEPrivate`AddSpecialArgCompletion["Projector"->{{"Dirac","Pauli","Anapole","EDM","SachsElectric","SachsMagnetic"},0}]];
];


(* ::Subsection::Closed:: *)
(*Attributes and Options*)


SetAttributes[LDot, Orderless];


Options[MandelstamRelations] = {Eliminate->None};
Options[LoopIntegrate]={Apart->False, Cancel->Automatic, Dimensions->4, DiracAlgebra:>$DiracAlgebra, Organization->Automatic};
Options[PVA]={Weights->{1},Dimensions->4};
Options[PVB]={Weights->{1,1},Dimensions->4};
Options[PVC]={Weights->{1,1,1},Dimensions->4};
Options[PVD]={Weights->{1,1,1,1},Dimensions->4};

Options[FermionLineExpand] = {ChiralBasis->Automatic, ChisholmExpand->Automatic, GordonIdentity->True, DiracAlgebra:>$DiracAlgebra};

Options[LoopRefine]={Analytic->False, Dimensions->4, ExplicitC0->Automatic, Organization->LTensor, TargetScale->Automatic, Part->All};
Options[LoopRefineSeries]={Analytic->False, Dimensions->4, ExplicitC0->Automatic, Organization->LTensor, TargetScale->Automatic, Part->All};


(* ::Subsection::Closed:: *)
(*Syntax Information*)


SyntaxInformation[LDot]={"ArgumentsPattern"->{_,_}};
SyntaxInformation[LTensor]={"ArgumentsPattern"->{_,__}};
SyntaxInformation[MandelstamRelations]={"ArgumentsPattern"->{_,OptionsPattern[]}};
SyntaxInformation[LoopIntegrate]={"ArgumentsPattern"->{_,_,{_,_,_.}..,OptionsPattern[]}, "LocalVariables"->{"Integrate",{2,2}}};
SyntaxInformation[Transverse]={"ArgumentsPattern"->{_,Optional[Blank[]],Optional[{Blank[],Blank[]}]},"LocalVariables"->{"Solve",{2,3}}};
SyntaxInformation[Longitudinal]={"ArgumentsPattern"->{_,Optional[Blank[]],Optional[{Blank[],Blank[]}]},"LocalVariables"->{"Solve",{2,3}}};
SyntaxInformation[LScalarQ]={"ArgumentsPattern"->{_}};
SyntaxInformation[Contract]={"ArgumentsPattern"->{_}};

SyntaxInformation[X`Utilities`PassarinoVeltmanTensor]={"ArgumentsPattern"->{{{_,_}...},{___}}};


SyntaxInformation[FermionLine]={"ArgumentsPattern"->{_,_,_}};
SyntaxInformation[FermionLineExpand]={"ArgumentsPattern"->{_,OptionsPattern[]}};

(*
SyntaxInformation[SpinorU]={"ArgumentsPattern"->{_,__}};
SyntaxInformation[SpinorV]={"ArgumentsPattern"->{_,__}};
*)


SyntaxInformation[PVA]={"ArgumentsPattern"->{_,_,OptionsPattern[]}};
SyntaxInformation[PVB]={"ArgumentsPattern"->{_,_,_,_,_,OptionsPattern[]}};
SyntaxInformation[PVC]={"ArgumentsPattern"->{_,_,_,_,_,_,_,_,_,OptionsPattern[]}};
SyntaxInformation[PVD]={"ArgumentsPattern"->{_,_,_,_,_,_,_,_,_,_,_,_,_,_,OptionsPattern[]}};

SyntaxInformation[LoopRefine]={"ArgumentsPattern"->{_,OptionsPattern[]}};
SyntaxInformation[LoopRefineSeries]={"ArgumentsPattern"->{_,{_,_,_},Optional[{_,_,_}],OptionsPattern[]},"LocalVariables"->{"Plot",{2,\[Infinity]}}};

SyntaxInformation[Kallen\[Lambda]]={"ArgumentsPattern"->{_,_,_}};
SyntaxInformation[KallenExpand]={"ArgumentsPattern"->{_}};
SyntaxInformation[Kibble\[Phi]]={"ArgumentsPattern"->{_,_,_,_,_,_}};
SyntaxInformation[KibbleExpand]={"ArgumentsPattern"->{_}};
SyntaxInformation[DiscB]={"ArgumentsPattern"->{_,_,_}};
SyntaxInformation[DiscExpand]={"ArgumentsPattern"->{_}};
SyntaxInformation[DiLog]={"ArgumentsPattern"->{_,_.}};
SyntaxInformation[Ln]={"ArgumentsPattern"->{_,_.}};
SyntaxInformation[ContinuedDiLog]={"ArgumentsPattern"->{{_,_},{_,_},Optional[{_,_}]}};
SyntaxInformation[ScalarC0]={"ArgumentsPattern"->{_,_,_,_,_,_}};
SyntaxInformation[ScalarC0IR6]={"ArgumentsPattern"->{_,_,_}};
SyntaxInformation[ScalarD0]={"ArgumentsPattern"->{_,_,_,_,_,_,_,_,_,_}};
SyntaxInformation[ScalarD0IR12]={"ArgumentsPattern"->{_,_,_,_,_,_}};
SyntaxInformation[ScalarD0IR13]={"ArgumentsPattern"->{_,_,_,_,_,_,_}};
SyntaxInformation[ScalarD0IR16]={"ArgumentsPattern"->{_,_,_,_,_,_,_}};

SyntaxInformation[Discontinuity]={"ArgumentsPattern"->{_,Optional[_]}};

SyntaxInformation[X`Utilities`SimplifyLn]={"ArgumentsPattern"->{_,_.}};
SyntaxInformation[X`Utilities`SimplifyDiLog]={"ArgumentsPattern"->{_,_.}};
SyntaxInformation[X`Utilities`SimplifyContinuedDiLog]={"ArgumentsPattern"->{_}};
SyntaxInformation[X`Utilities`EquivalentAlternatives]={"ArgumentsPattern"->{_}};
SyntaxInformation[X`Utilities`PermutePVD]={"ArgumentsPattern"->{_,_}};
SyntaxInformation[X`Utilities`PVNormal]={"ArgumentsPattern"->{_}};


(* ::Subsection::Closed:: *)
(*StandardForm parsing/formatting*)


(*Need to clean this up, and resolve issue with evaluation leaks:
	1.  "0" is not necessary.
	2.  MakeBoxes[#, TraditionalForm]& /@ {a,b,c} to be replaced with BoxForm`ToTrad /@ Unevaluated[{a,b,c}].
	3.  MakeBoxes /@ {a,b,c} to be replaced with 
	4.  ToString[#, TraditionalForm]& /@ {a,b,c} to be replaced with Function[{x},ToString[Unevaluated[x],TraditionalForm],{HoldAll}] /@ Unevaluated[{a,b,c}].
*)


Begin["`Private`"];


If[$VersionNumber<10.0,
  System`Inactive;
  System`IgnoringInactive=(#&)
];


(* ::Subsubsection::Closed:: *)
(*Enable/DisableFancyIO*)


X`Utilities`EnableFancyIO::noenab = "Special input/output forms for `1` are already enabled.";
X`Utilities`EnableFancyIO::noexist = "No special input/output forms for `1` are defined.";

X`Utilities`DisableFancyIO::nodisab = "Special input/output forms for `1` are already disabled.";
X`Utilities`DisableFancyIO::noexist = "No special input/output forms for `1` are defined.";


X`Utilities`EnableFancyIO[heads__] := CompoundExpression[X`Private`iEnableFancyIO /@ {heads},Null];
X`Utilities`DisableFancyIO[heads__] := CompoundExpression[iDisableFancyIO /@ {heads},Null];


(*Catch-all case: symbol not found.*)
iEnableFancyIO[s_Symbol] := Message[X`Utilities`EnableFancyIO::noexist,s];
iDisableFancyIO[s_Symbol] := Message[X`Utilities`DisableFancyIO::noexist,s];

iEnableFancyIO[s_] := Message[X`Utilities`EnableFancyIO::ssym,s];
iDisableFancyIO[s_] := Message[X`Utilities`DisableFancyIO::ssym,s];


(*Dumpload Inactive typesetting rules*)
MakeBoxes[Inactive[Integrate][Null,Null],StandardForm];


(* ::Subsubsection::Closed:: *)
(*Special glyphs*)


iEnableFancyIO["SpecialGlyphs"]:=
  If[TrueQ[$fancyInput["SpecialGlyphs"]],
	Message[X`Utilities`EnableFancyIO::noenab, "special glyphs"],

	(*Color special symbols Black, even though they have no definitions*)
	MathLink`CallFrontEnd[FrontEnd`UpdateKernelSymbolContexts[$Context,FrontEnd`Private`ResolvedContextPath[],
	  {{"X`",{},{},{"\[ScriptD]","\[Epsilon]","\[CurlyEpsilon]","\[ScriptU]","\[ScriptV]","\[DoubleStruckG]","\[DoubleStruckCapitalP]L","\[DoubleStruckCapitalP]R","\[Gamma]","\[Gamma]5","\[Sigma]","\[DoubleStruckOne]","\[Micro]"},{}}}]];

	CurrentValue[$FrontEndSession, {InputAliases, "dim"}] = "\[ScriptD]";
	CurrentValue[$FrontEndSession, {InputAliases, "11"}] = "\[DoubleStruckOne]";
	CurrentValue[$FrontEndSession, {InputAliases, "PL"}] = "\[DoubleStruckCapitalP]L";
	CurrentValue[$FrontEndSession, {InputAliases, "PR"}] = "\[DoubleStruckCapitalP]R";
	CurrentValue[$FrontEndSession, {InputAliases, "mm"}] = "\[Micro]";

	(*Interpret special glyphs and corresponding Package-X symbols*)
	Scan[
	 (MakeExpression[#1,StandardForm]:=MakeExpression[#2,StandardForm];
	  MakeExpression[RowBox[{x___,#1,y___}],StandardForm]:=MakeExpression[RowBox[{x,#2,y}],StandardForm];
	  MakeExpression[RowBox[{a___,RowBox[{x___,#1,y___}],b___}],StandardForm]:=MakeExpression[RowBox[{a,RowBox[{x,#2,y}],b}],StandardForm])& @@ # &
	,{{"\[ScriptD]","Dim"},{"\[Epsilon]","Eps"},{"\[DoubleStruckG]","MetricG"},{"\[CurlyEpsilon]","LeviCivitaE"},{"\[Micro]","Mu"},{"\[Sigma]","DiracS"},{"\[Gamma]","DiracG"},{"\[Gamma]5","DiracG5"},{"\[DoubleStruckOne]","Dirac1"},{"\[DoubleStruckCapitalP]L","DiracPL"},{"\[DoubleStruckCapitalP]R","DiracPR"},{"\[ScriptU]","SpinorU"},{"\[ScriptV]","SpinorV"},
	  {"\[ScriptD]_","X`Dim_"},{"\[Epsilon]_","X`Eps_"},{"\[Micro]_","X`Mu_"},{"\[Sigma]_","DiracS_"},{"\[Gamma]_","X`DiracG_"},{"_\[ScriptU]","_X`SpinorU"},{"_\[ScriptV]","_X`SpinorV"}}];

	(*Renders Dim,Eps,Mu,MetricG,... as glyphs in StandardForm*)
	Unprotect[Dim,Eps,Mu,MetricG,LeviCivitaE,Dirac1,DiracG,DiracG5,DiracS,DiracPL,DiracPR];
	Dim/:MakeBoxes[Dim,StandardForm]:="\[ScriptD]";                 (*Format[Dim, OutputForm] := "d";*)
	Eps/:MakeBoxes[Eps,StandardForm]:="\[Epsilon]";                 (*Format[Eps,OutputForm] := "\[Epsilon]";*)
	Mu/:MakeBoxes[Mu,StandardForm]:="\[Micro]";                   (*Format[Mu,OutputForm] := "\[Micro]";*)

	MetricG/:MakeBoxes[MetricG,StandardForm]:="\[DoubleStruckG]";         (*Format[MetricG, OutputForm] := "g";*)
	LeviCivitaE/:MakeBoxes[LeviCivitaE,StandardForm]:="\[CurlyEpsilon]"; (*Format[LeviCivitaE,OutputForm] := "\[CurlyEpsilon]";*)

	Dirac1/:MakeBoxes[Dirac1,StandardForm]:="\[DoubleStruckOne]";           (*Format[Dirac1,OutputForm] := "1";*)
	DiracG/:MakeBoxes[DiracG,StandardForm]:="\[Gamma]";           (*Format[DiracG,OutputForm] := "\[Gamma]";*)
	DiracG5/:MakeBoxes[DiracG5,StandardForm]:="\[Gamma]5";        (*Format[DiracG5,OutputForm] := "\[Gamma]5";*)
	DiracS/:MakeBoxes[DiracS,StandardForm]:="\[Sigma]";           (*Format[DiracS,OutputForm] := "\[Sigma]";*)
	DiracPL/:MakeBoxes[DiracPL,StandardForm]:="\[DoubleStruckCapitalP]L";        (*Format[DiracPL,OutputForm] := "PL";*)
	DiracPR/:MakeBoxes[DiracPR,StandardForm]:="\[DoubleStruckCapitalP]R";        (*Format[DiracPR,OutputForm] := "PR";*)

	Protect[Dim,Eps,Mu,MetricG,LeviCivitaE,Dirac1,DiracG,DiracG5,DiracS,DiracPL,DiracPR];
	$fancyInput["SpecialGlyphs"]=True;
  ];


iDisableFancyIO["SpecialGlyphs"]:=
  If[!TrueQ[$fancyInput["SpecialGlyphs"]],
	Message[X`Utilities`DisableFancyIO::nodisab, "special glyphs"],

	MathLink`CallFrontEnd[FrontEnd`UpdateKernelSymbolContexts[$Context,FrontEnd`Private`ResolvedContextPath[],
	  {{"X`",{},{"\[ScriptD]","\[Epsilon]","\[CurlyEpsilon]","\[ScriptU]","\[ScriptV]","\[DoubleStruckG]","\[DoubleStruckCapitalP]L","\[DoubleStruckCapitalP]R","\[Gamma]","\[Gamma]5","\[Sigma]","\[DoubleStruckOne]","\[Micro]"},{},{}}}]];

	CurrentValue[$FrontEndSession, {InputAliases, "dim"}] = Inherited;
	CurrentValue[$FrontEndSession, {InputAliases, "11"}] = Inherited;
	CurrentValue[$FrontEndSession, {InputAliases, "PL"}] = Inherited;
	CurrentValue[$FrontEndSession, {InputAliases, "PR"}] = Inherited;
	CurrentValue[$FrontEndSession, {InputAliases, "mm"}] = Inherited;

	Scan[
	 (MakeExpression[#1,StandardForm]=.;
	  MakeExpression[RowBox[{x___,#1,y___}],StandardForm]=.;
	  MakeExpression[RowBox[{a___,RowBox[{x___,#1,y___}],b___}],StandardForm]=.)& @@ # &
	,{{"\[ScriptD]","Dim"},{"\[Epsilon]","Eps"},{"\[DoubleStruckG]","MetricG"},{"\[CurlyEpsilon]","LeviCivitaE"},{"\[Micro]","Mu"},{"\[Sigma]","DiracS"},{"\[Gamma]","DiracG"},{"\[Gamma]5","DiracG5"},{"\[DoubleStruckOne]","Dirac1"},{"\[DoubleStruckCapitalP]L","DiracPL"},{"\[DoubleStruckCapitalP]R","DiracPR"},{"\[ScriptU]","SpinorU"},{"\[ScriptV]","SpinorV"},
	  {"\[ScriptD]_","X`Dim_"},{"\[Epsilon]_","X`Eps_"},{"\[Micro]_","X`Mu_"},{"\[Sigma]_","DiracS_"},{"\[Gamma]_","X`DiracG_"},{"_\[ScriptU]","_X`SpinorU"},{"_\[ScriptV]","_X`SpinorV"}}];

	Unprotect[Dim,Eps,Mu,MetricG,LeviCivitaE,Dirac1,DiracG,DiracG5,DiracS,DiracPL,DiracPR];
	Dim/:MakeBoxes[Dim,StandardForm]=.;         (*Format[Dim, OutputForm]=.;*)
	Eps/:MakeBoxes[Eps,StandardForm]=.;         (*Format[Eps,OutputForm]=.;*)
	Mu/:MakeBoxes[Mu,StandardForm]=.;           (*Format[Mu,OutputForm] =.;*)

	MetricG/:MakeBoxes[MetricG,StandardForm]=.; (*Format[MetricG, OutputForm]=.*)
	LeviCivitaE/:MakeBoxes[LeviCivitaE,StandardForm]=.; (*Format[LeviCivitaE,OutputForm]=.;*)

	Dirac1/:MakeBoxes[Dirac1,StandardForm]=.;   (*Format[Dirac1,OutputForm]=.*)
	DiracG/:MakeBoxes[DiracG,StandardForm]=.;   (*Format[DiracG,OutputForm]=.*)
	DiracG5/:MakeBoxes[DiracG5,StandardForm]=.; (*Format[DiracG5,OutputForm]=.*)
	DiracS/:MakeBoxes[DiracS,StandardForm]=.;   (*Format[DiracS,OutputForm]=.*)
	DiracPL/:MakeBoxes[DiracPL,StandardForm]=.; (*Format[DiracPL,OutputForm]=.*)
	DiracPR/:MakeBoxes[DiracPR,StandardForm]=.; (*Format[DiracPR,OutputForm]=.*)
	Protect[Dim,Eps,Mu,MetricG,LeviCivitaE,Dirac1,DiracG,DiracG5,DiracS,DiracPL,DiracPR];
	$fancyInput["SpecialGlyphs"]=False;
  ];


(* ::Subsubsection::Closed:: *)
(*LDot*)


iEnableFancyIO[LDot]:=
  If[TrueQ[$fancyInput[LDot]],
	Message[X`Utilities`EnableFancyIO::noenab, LDot],
	(*Format Mathematica built-in function as 'Dot'*)
	Unprotect[Dot];
	Dot /: MakeBoxes[Dot[x__], StandardForm] := RowBox[{"Dot", "[", X`Internal`ToRowBox[{x}], "]"}];
	Protect[Dot];
	(*Interprets user "." as LDot*)
	MakeExpression[RowBox[{"?","."}],StandardForm]:=MakeExpression[RowBox[{"Information","[",RowBox[{"LDot",",",RowBox[{"LongForm","\[Rule]","False"}]}],"]"}],StandardForm];
	MakeExpression[RowBox@(row : {PatternSequence[_, "."] .., _}), StandardForm] := MakeExpression[RowBox@{"LDot", "[", RowBox@Riffle[row[[1 ;; -1 ;; 2]], ","], "]"}, StandardForm];
	(*Renders LDot as '.'*)
	LDot /: MakeBoxes[LDot[x_,y_],StandardForm] := RowBox[{Parenthesize[x,StandardForm,Times,Left],".",Parenthesize[y,StandardForm,Times,Right]}];

	Unprotect[Inactive];
	(*Inactive form for Mathematica's Dot*)
	MakeBoxes[Inactive[Dot][x__], StandardForm] ^:= RowBox[{TemplateBox[{"Dot"},"InactiveHead",BaseStyle->"Inactive",SyntaxForm->"Symbol",Tooltip->"Inactive[Dot]"], "[", X`Internal`ToRowBox[{x}], "]"}];
	Protect[Inactive];
	$fancyInput[LDot]=True;
  ];


iDisableFancyIO[LDot]:=
  If[!TrueQ[$fancyInput[LDot]],
	Message[X`Utilities`DisableFancyIO::nodisab, LDot],

	Unprotect[Dot];
	Dot /: MakeBoxes[Dot[x__], StandardForm] =. ;
	Protect[Dot];
	MakeExpression[RowBox[{"?","."}],StandardForm]=.;
	MakeExpression[RowBox@(row : {PatternSequence[_, "."] .., _}), StandardForm] =. ;
	LDot /: MakeBoxes[LDot[x_,y_],StandardForm] =. ;
	(*Format[LDot[a_,b_],OutputForm] =. ;*)	

	Unprotect[Inactive];
	(*Restore Inactive form for Mathematica's Dot*)
	Inactive /: MakeBoxes[Inactive[Dot][x__], StandardForm] =. ;
	Protect[Inactive];
	
	$fancyInput[LDot]=False;
  ];


(* ::Subsubsection::Closed:: *)
(*LTensor*)


iEnableFancyIO[LTensor]:=
  If[TrueQ[$fancyInput[LTensor]],
	Message[X`Utilities`EnableFancyIO::noenab, LTensor],
	(*Interprets user subscript as LTensor*)

	If[$Notebooks, 
  	CurrentValue[$FrontEndSession, {InputAliases, "gg"}] = "\!\(\*SubscriptBox[\(\[DoubleStruckG]\), \(\[SelectionPlaceholder],\[Placeholder]\)]\)";
  	CurrentValue[$FrontEndSession, {InputAliases, "levi"}] = "\!\(\*SubscriptBox[\(\[CurlyEpsilon]\), \(\[SelectionPlaceholder],\[Placeholder],\[Placeholder],\[Placeholder]\)]\)";
	];

	MakeExpression[SubscriptBox[a_,idx_String], StandardForm] := MakeExpression[RowBox[{"LTensor", "[",RowBox[{a,",",idx}],"]"}], StandardForm];
	If[$VersionNumber>=10.0,(*Version 10 and above can use second argument of Join*)
	  MakeExpression[SubscriptBox[a_,idx_RowBox], StandardForm] := MakeExpression[RowBox[{"LTensor", "[",Join[RowBox[{a,","}],idx,2],"]"}], StandardForm],
	  MakeExpression[SubscriptBox[a_,RowBox[idx_List]], StandardForm] := MakeExpression[RowBox[{"LTensor", "[",RowBox[Join[{a,","},idx]],"]"}], StandardForm]
	];

	(*Renders LTensor as subscript*)
	LTensor /: MakeBoxes[LTensor[a_,idx__],StandardForm] := SubscriptBox[Parenthesize[a,StandardForm,Power,Left],X`Internal`ToRowBox[{idx}]];

	$fancyInput[LTensor]=True;
  ];


iDisableFancyIO[LTensor]:=
  If[!TrueQ[$fancyInput[LTensor]],
	Message[X`Utilities`DisableFancyIO::nodisab, LTensor],

	If[$Notebooks, 
	  CurrentValue[$FrontEndSession, {InputAliases, "gg"}] = "\!\(LTensor[\(MetricG\),\(\[SelectionPlaceholder],\[Placeholder]\)]\)";
	  CurrentValue[$FrontEndSession, {InputAliases, "levi"}] = "\!\(LTensor[\(LeviCivitaE\),\(\[SelectionPlaceholder],\[Placeholder],\[Placeholder],\[Placeholder]\)]\)";
	];
	
	MakeExpression[SubscriptBox[a_,idx_String], StandardForm] =. ;
	MakeExpression[SubscriptBox[a_,idx_RowBox], StandardForm] =. ;
	LTensor /: MakeBoxes[LTensor[a_,idx__],StandardForm] =.;
	(*Format[LTensor[a_,idx__],OutputForm]=.;*)
	$fancyInput[LTensor]=False;
  ];


(* ::Subsubsection::Closed:: *)
(*LoopIntegrate*)


SetAttributes[denomSpecBox,HoldAllComplete];

denomSpecBox[{0,0,weight_:1},StandardForm]:=
  TemplateBox[{"0","0",MakeBoxes[weight]}
	,"LoopIntegrateDenomSpec"
	,DisplayFunction->If[weight===1,"0"&,SuperscriptBox["0",#3]&]
	,InterpretationFunction->(RowBox[{"{",#1,",",#2,",",#3,"}"}]&)];

denomSpecBox[{mom_,0,weight_:1},StandardForm]:=
  TemplateBox[{Parenthesize[mom,StandardForm,Times,Left],"0",MakeBoxes[weight]}
	,"LoopIntegrateDenomSpec"
	,DisplayFunction->If[weight===1,
	  SuperscriptBox[#1,"2"]&,
	  SuperscriptBox[RowBox[{"(",SuperscriptBox[#1,"2"],")"}],#3]&]
	,InterpretationFunction->(RowBox[{"{",#1,",",#2,",",#3,"}"}]&)];

denomSpecBox[{0,mass_,weight_:1},StandardForm]:=
  TemplateBox[{"0",Parenthesize[mass,StandardForm,Times,Left],MakeBoxes[weight]}
	,"LoopIntegrateDenomSpec"
	,DisplayFunction->If[weight===1,
	  RowBox[{"(",RowBox[{"-",SuperscriptBox[#2,"2"]}],")"}]&,
	  SuperscriptBox[RowBox[{"(","-",SuperscriptBox[#2,"2"],")"}],#3]&]
	,InterpretationFunction->(RowBox[{"{",#1,",",#2,",",#3,"}"}]&)];

denomSpecBox[{mom_,mass_,weight_:1},StandardForm]:=
  TemplateBox[{Parenthesize[mom,StandardForm,Times,Left],Parenthesize[mass,StandardForm,Times,Left],MakeBoxes[weight]}
	,"LoopIntegrateDenomSpec"
	,DisplayFunction->If[weight===1,
	  RowBox[{"(",SuperscriptBox[#1,"2"],"-",SuperscriptBox[#2,"2"],")"}]&,
	  SuperscriptBox[RowBox[{"(",SuperscriptBox[#1,"2"],"-",SuperscriptBox[#2,"2"],")"}],#3]&]
	,InterpretationFunction->(RowBox[{"{",#1,",",#2,",",#3,"}"}]&)];

SetAttributes[ListToDenomSpecRowBox,HoldAllComplete];
ListToDenomSpecRowBox[list_,form_]:=RowBox[Map[Function[{item},denomSpecBox[item,form],{HoldAllComplete}],Unevaluated[list]]];

(*SetAttributes[ListToIntVarRowBox,HoldAllComplete];
ListToIntVarRowBox[intVar_(*List*),form_]:=RowBox[Map[Function[{item},FractionBox[RowBox[{SuperscriptBox["\[DifferentialD]","\[ScriptD]"],MakeBoxes[item,form]}],SuperscriptBox[RowBox[{"(","2","\[Pi]",")"}],"\[ScriptD]"]],{HoldAllComplete}],Unevaluated[intVar]]]*)


iEnableFancyIO[LoopIntegrate]:=
  If[TrueQ[$fancyInput[LoopIntegrate]],
	Message[X`Utilities`EnableFancyIO::noenab, LoopIntegrate],
	
	(*Output formatting for LoopIntegrate*)
	Unprotect[LoopIntegrate];
	LoopIntegrate /: HoldPattern[MakeBoxes[LoopIntegrate[num_,k_Symbol,Pattern[denom,(({_,_}|{_,_,_})..)],OptionsPattern[]],StandardForm]]:=
	  TemplateBox[{MakeBoxes[num,StandardForm],MakeBoxes[k,StandardForm],ListToDenomSpecRowBox[{denom},StandardForm]},
		"LoopIntegrate",
		DisplayFunction->(RowBox[{
		  "\[Integral]",
			FractionBox[RowBox[{SuperscriptBox["\[DifferentialD]","\[ScriptD]"],#2}],SuperscriptBox[RowBox[{"(","2","\[Pi]",")"}],"\[ScriptD]"]],
			FractionBox[#1,#3]
		  }]&),
		InterpretationFunction->(RowBox[{"LoopIntegrate","[",RowBox[Riffle[{#1,#2}~Join~Map[ToBoxes[ToExpression[#]]&,#3,{2}][[1]],","]],"]"}]&),Editable->True
	  ];
	  
	(*LoopIntegrate /: HoldPattern[MakeBoxes[LoopIntegrate[num_,intvar:{_Symbol..},Pattern[denom,(({_,_}|{_,_,_})..)],OptionsPattern[]],StandardForm]]:=
	  TemplateBox[{MakeBoxes[num,StandardForm],ListToIntVarRowBox[intvar,StandardForm],ListToDenomSpecRowBox[{denom},StandardForm]},
		"LoopIntegrate",
		DisplayFunction->(RowBox[{
		  "\[Integral]",
			#2,
			FractionBox[#1,#3]
		  }]&),
		InterpretationFunction->(RowBox[{"LoopIntegrate","[",RowBox[Riffle[{#1,#2}~Join~Map[ToBoxes[ToExpression[#]]&,#3,{2}][[1]],","]],"]"}]&),Editable->True
	  ];*)
	Protect[LoopIntegrate];
	
	(*Output formatting for Inactive[LoopIntegrate]*)
	Unprotect[Inactive];
	BoxForm`UsesPreInPostFixOperatorQ[LoopIntegrate] = True;
	PrependTo[FormatValues[Inactive],
	HoldPattern[MakeBoxes[Inactive[LoopIntegrate][num_,k_Symbol,Pattern[denom,(({_,_}|{_,_,_})..)],OptionsPattern[]],StandardForm]]:>
	  TemplateBox[{MakeBoxes[num,StandardForm],MakeBoxes[k,StandardForm],ListToDenomSpecRowBox[{denom},StandardForm]},
		"InactiveLoopIntegrate",
		DisplayFunction->(RowBox[{
		  StyleBox["\[Integral]","Inactive"],
			FractionBox[RowBox[{SuperscriptBox[StyleBox["\[DifferentialD]","Inactive"],StyleBox["\[ScriptD]","Inactive"]],#2}],
			SuperscriptBox[RowBox[{StyleBox["(","Inactive"],StyleBox["2","Inactive"],StyleBox["\[Pi]","Inactive"],StyleBox[")","Inactive"]}],StyleBox["\[ScriptD]","Inactive"]]],
			FractionBox[#1,#3]
		  }]&),
		InterpretationFunction->(RowBox[{RowBox[{"Inactive","[","LoopIntegrate","]"}],"[",RowBox[Riffle[{#1,#2}~Join~Map[ToBoxes[ToExpression[#]]&,#3,{2}][[1]],","]],"]"}]&),
		Editable->True,
		Tooltip:>"Inactive[LoopIntegrate]"
	  ]
	];
	Protect[Inactive];
	  
	$fancyInput[LoopIntegrate]=True;
  ];


iDisableFancyIO[LoopIntegrate]:=
  If[!TrueQ[$fancyInput[LoopIntegrate]],
	Message[X`Utilities`DisableFancyIO::nodisab, LoopIntegrate],

	Unprotect[LoopIntegrate];
	LoopIntegrate /: HoldPattern[MakeBoxes[LoopIntegrate[num_,k_Symbol,Pattern[denom,(({_,_}|{_,_,_})..)],OptionsPattern[]],StandardForm]]=. ;
	Protect[LoopIntegrate];	

	Unprotect[Inactive];
	BoxForm`UsesPreInPostFixOperatorQ[LoopIntegrate] =.;
	HoldPattern[MakeBoxes[Inactive[LoopIntegrate][num_,k_Symbol,Pattern[denom,(({_,_}|{_,_,_})..)],OptionsPattern[]],StandardForm]]=.;
	Protect[Inactive];

	$fancyInput[LoopIntegrate]=False;
  ];


(* ::Subsubsection::Closed:: *)
(*Derivative[0,0,1,0,0][PVB]*)


MakeExpression[RowBox[{"PVB","'"}]|SuperscriptBox["PVB","\[Prime]"],StandardForm]:=
 MakeExpression[RowBox[{RowBox[{RowBox[{"Derivative", "[", RowBox[{"0", ",", "0", ",", "1", ",", "0", ",", "0"}], "]"}], "[", "PVB", "]"}]}],StandardForm];

(*Need to HoldPattern for version 9.0 *)
HoldPattern[MakeBoxes[Derivative[0,0,1,0,0][PVB],StandardForm]]:=RowBox[{InterpretationBox[SuperscriptBox["PVB","\[Prime]",MultilineFunction->None],Derivative[0,0,1,0,0][PVB]]}];


(* ::Subsubsection::Closed:: *)
(*FermionLine*)


Sequence@@Riffle[Map[Function[{item},MakeBoxes[item,StandardForm],{HoldAllComplete}],Unevaluated[{mtx}]],","];


iEnableFancyIO[FermionLine]:=
  If[TrueQ[$fancyInput[FermionLine]],
	Message[X`Utilities`EnableFancyIO::noenab, FermionLine],

	If[$Notebooks,
	  CurrentValue[$FrontEndSession, {InputAliases, "ub"}] = "\[LeftAngleBracket]\[ScriptU][\[SelectionPlaceholder],\[Placeholder]]";
	  CurrentValue[$FrontEndSession, {InputAliases, "vb"}] = "\[LeftAngleBracket]\[ScriptV][\[SelectionPlaceholder],\[Placeholder]]";
	  CurrentValue[$FrontEndSession, {InputAliases, "u"}] = "\[ScriptU][\[SelectionPlaceholder],\[Placeholder]]\[RightAngleBracket]";
	  CurrentValue[$FrontEndSession, {InputAliases, "v"}] = "\[ScriptV][\[SelectionPlaceholder],\[Placeholder]]\[RightAngleBracket]"
	];

	(*Format Mathematica built-in function as 'AngleBracket'*)
	AngleBracket /: MakeBoxes[AngleBracket[x__], form_] := RowBox[{"AngleBracket", "[", RowBox@Riffle[MakeBoxes /@ {x}, ","], "]"}];

	Unprotect[FermionLine];
	(*Format Fermionline[...] in \[LeftAngleBracket] \[RightAngleBracket] notation *)
	FermionLine /: MakeBoxes[FermionLine[{sp2:1|-1,kin2__},{sp1:1|-1,kin1__},DiracMatrix[mtx__]],StandardForm]:=
	  With[{sf1=Switch[sp1,1,"\[ScriptU]",-1,"\[ScriptV]"],
			sf2=Switch[sp2,1,"\[ScriptU]",-1,"\[ScriptV]"]},
		RowBox[{"\[LeftAngleBracket]",RowBox[{sf2,"[",X`Internal`ToRowBox[{kin2}],"]"}],",",Sequence@@Riffle[Map[Function[{item},MakeBoxes[item,StandardForm],{HoldAllComplete}],Unevaluated[{mtx}]],","],",",RowBox[{sf1,"[",X`Internal`ToRowBox[{kin1}],"]"}],"\[RightAngleBracket]"}]
	  ];

	FermionLine /: MakeBoxes[FermionLine[{sp2:1|-1,kin2__},{sp1:1|-1,kin1__},DiracMatrix[]],StandardForm]:=
	  With[{sf1=Switch[sp1,1,"\[ScriptU]",-1,"\[ScriptV]"],
			sf2=Switch[sp2,1,"\[ScriptU]",-1,"\[ScriptV]"]},
		RowBox[{"\[LeftAngleBracket]",RowBox[{sf2,"[",X`Internal`ToRowBox[{kin2}],"]"}],",",RowBox[{sf1,"[",X`Internal`ToRowBox[{kin1}],"]"}],"\[RightAngleBracket]"}]
	  ];

	Protect[FermionLine];

	(*Parse angle-bracket notation as FermionLine*)
	(*no Dirac matrices sandwiched*)
	MakeExpression[RowBox@({"\[LeftAngleBracket]",RowBox[{spinor2_,"[",RowBox[kin2 : {PatternSequence[_, ","] .., _}],"]"}],",",RowBox[{spinor1_,"[",RowBox[kin1 : {PatternSequence[_, ","] .., _}],"]"}],"\[RightAngleBracket]"}),StandardForm]:=
	  With[{idx2=If[spinor2==="\[ScriptU]","1",RowBox[{"-","1"}]],idx1=If[spinor1==="\[ScriptU]","1",RowBox[{"-","1"}]]},
		MakeExpression[RowBox[{"FermionLine","[",RowBox[
		 {RowBox[{"{",RowBox[Join[{idx2,","},Riffle[kin2[[1 ;; -1 ;; 2]], ","]]],"}"}],",",
		  RowBox[{"{",RowBox[Join[{idx1,","},Riffle[kin1[[1 ;; -1 ;; 2]], ","]]],"}"}],",",
		  RowBox[{"DiracMatrix","[","]"}]
		 }],"]"}],StandardForm
		]
	  ]/;MatchQ[spinor2,"\[ScriptU]"|"\[ScriptV]"]&&MatchQ[spinor1,"\[ScriptU]"|"\[ScriptV]"];

	MakeExpression[RowBox@({"\[LeftAngleBracket]",RowBox[{RowBox[{spinor2_,"[",RowBox[kin2 : {PatternSequence[_, ","] .., _}],"]"}],",",RowBox[{spinor1_,"[",RowBox[kin1 : {PatternSequence[_, ","] .., _}],"]"}]}],"\[RightAngleBracket]"}),StandardForm]:=
	  With[{idx2=If[spinor2==="\[ScriptU]","1",RowBox[{"-","1"}]],idx1=If[spinor1==="\[ScriptU]","1",RowBox[{"-","1"}]]},
		MakeExpression[RowBox[{"FermionLine","[",RowBox[
		 {RowBox[{"{",RowBox[Join[{idx2,","},Riffle[kin2[[1 ;; -1 ;; 2]], ","]]],"}"}],",",
		  RowBox[{"{",RowBox[Join[{idx1,","},Riffle[kin1[[1 ;; -1 ;; 2]], ","]]],"}"}],",",
		  RowBox[{"DiracMatrix","[","]"}]
		 }],"]"}],StandardForm
		]
	  ]/;MatchQ[spinor2,"\[ScriptU]"|"\[ScriptV]"]&&MatchQ[spinor1,"\[ScriptU]"|"\[ScriptV]"];

	(*with Dirac matrices sandwiched*)
	MakeExpression[RowBox@({"\[LeftAngleBracket]",RowBox[{spinor2_,"[",RowBox[kin2 : {PatternSequence[_, ","] .., _}],"]"}],",", dMtxes : PatternSequence[_, ","] ..., RowBox[{spinor1_,"[",RowBox[kin1 : {PatternSequence[_, ","] .., _}],"]"}],"\[RightAngleBracket]"}),StandardForm]:=
	  With[{idx2=If[spinor2==="\[ScriptU]","1",RowBox[{"-","1"}]],idx1=If[spinor1==="\[ScriptU]","1",RowBox[{"-","1"}]]},
		MakeExpression[RowBox[{"FermionLine","[",RowBox[
		 {RowBox[{"{",RowBox[Join[{idx2,","},Riffle[kin2[[1 ;; -1 ;; 2]], ","]]],"}"}],",",
		  RowBox[{"{",RowBox[Join[{idx1,","},Riffle[kin1[[1 ;; -1 ;; 2]], ","]]],"}"}],",",
		  RowBox[{"DiracMatrix","[",RowBox[Riffle[{dMtxes}[[1 ;; -1 ;; 2]], ","]],"]"}]
		 }],"]"}],StandardForm
		]
	  ]/;MatchQ[spinor2,"\[ScriptU]"|"\[ScriptV]"]&&MatchQ[spinor1,"\[ScriptU]"|"\[ScriptV]"];

	MakeExpression[RowBox@({"\[LeftAngleBracket]",RowBox[{RowBox[{spinor2_,"[",RowBox[kin2 : {PatternSequence[_, ","] .., _}],"]"}],",", dMtxes : PatternSequence[_, ","] ..., RowBox[{spinor1_,"[",RowBox[kin1 : {PatternSequence[_, ","] .., _}],"]"}]}],"\[RightAngleBracket]"}),StandardForm]:=
	  With[{idx2=If[spinor2==="\[ScriptU]","1",RowBox[{"-","1"}]],idx1=If[spinor1==="\[ScriptU]","1",RowBox[{"-","1"}]]},
		MakeExpression[RowBox[{"FermionLine","[",RowBox[
		 {RowBox[{"{",RowBox[Join[{idx2,","},Riffle[kin2[[1 ;; -1 ;; 2]], ","]]],"}"}],",",
		  RowBox[{"{",RowBox[Join[{idx1,","},Riffle[kin1[[1 ;; -1 ;; 2]], ","]]],"}"}],",",
		  RowBox[{"DiracMatrix","[",RowBox[Riffle[{dMtxes}[[1 ;; -1 ;; 2]], ","]],"]"}]
		 }],"]"}],StandardForm
		]
	  ]/;MatchQ[spinor2,"\[ScriptU]"|"\[ScriptV]"]&&MatchQ[spinor1,"\[ScriptU]"|"\[ScriptV]"];

	(*Inactive formatting*)
	Unprotect[Inactive];

	BoxForm`UsesPreInPostFixOperatorQ[FermionLine] = True;

	PrependTo[FormatValues[Inactive],
	HoldPattern[MakeBoxes[Inactive[FermionLine][sp2:{sgn2:1|-1,kin2__},sp1:{sgn1:1|-1,kin1__},dmtx:((head:DiracMatrix|Inactive[DiracMatrix])[])],StandardForm]]:>
	  With[{spn1=Switch[sgn1,1,StyleBox["\[ScriptU]","Inactive"],-1,StyleBox["\[ScriptV]","Inactive"]],spn2=Switch[sgn2,1,StyleBox["\[ScriptU]","Inactive"],-1,StyleBox["\[ScriptV]","Inactive"]]}
		,TemplateBox[{MakeBoxes[sp1],MakeBoxes[sp2],MakeBoxes[dmtx],
			RowBox[{spn1,StyleBox["[","Inactive"],X`Internal`ToRowBox[{kin1}],StyleBox["]","Inactive"]}],
			RowBox[{spn2,StyleBox["[","Inactive"],X`Internal`ToRowBox[{kin2}],StyleBox["]","Inactive"]}]}
		  ,"InactiveFermionLine"
		  ,DisplayFunction->(RowBox[{StyleBox["\[LeftAngleBracket]","Inactive"],#5,",",#4,StyleBox["\[RightAngleBracket]","Inactive"]}]&)
		  ,InterpretationFunction->(RowBox[{RowBox[{"Inactive","[",FermionLine,"]"}],"[",RowBox[{#2,",",#1,",",#3}],"]"}]&)
		  ,Tooltip:>"Inactive[FermionLine]"]
	  ]
	];

	PrependTo[FormatValues[Inactive],
	HoldPattern[MakeBoxes[Inactive[FermionLine][sp2:{sgn2:1|-1,kin2__},sp1:{sgn1:1|-1,kin1__},dmtx:((head:DiracMatrix|Inactive[DiracMatrix])[mtx__])],StandardForm]]:>
	  With[{spn1=Switch[sgn1,1,StyleBox["\[ScriptU]","Inactive"],-1,StyleBox["\[ScriptV]","Inactive"]],spn2=Switch[sgn2,1,StyleBox["\[ScriptU]","Inactive"],-1,StyleBox["\[ScriptV]","Inactive"]]}
		,TemplateBox[{MakeBoxes[sp1],MakeBoxes[sp2],MakeBoxes[dmtx],
			RowBox[{spn1,StyleBox["[","Inactive"],X`Internal`ToRowBox[{kin1}],StyleBox["]","Inactive"]}],
			RowBox[{spn2,StyleBox["[","Inactive"],X`Internal`ToRowBox[{kin2}],StyleBox["]","Inactive"]}],
			Sequence@@Riffle[Map[Function[{item},MakeBoxes[item,StandardForm],{HoldAllComplete}],Unevaluated[{mtx}]],","]}
		  ,"InactiveFermionLine"
		  ,DisplayFunction->(RowBox[{StyleBox["\[LeftAngleBracket]","Inactive"],#5,",",##6,",",#4,StyleBox["\[RightAngleBracket]","Inactive"]}]&)
		  ,InterpretationFunction->(RowBox[{RowBox[{"Inactive","[",FermionLine,"]"}],"[",RowBox[{#2,",",#1,",",#3}],"]"}]&)
		  ,Tooltip:>"Inactive[FermionLine]"]
	  ]
	];

	Protect[Inactive];
	
	$fancyInput[FermionLine]=True;
  ];


iDisableFancyIO[FermionLine]:=
  If[!TrueQ[$fancyInput[FermionLine]],
	Message[X`Utilities`DisableFancyIO::nodisab, FermionLine],

	If[$Notebooks,
	  CurrentValue[$FrontEndSession, {InputAliases, "ub"}] = Inherited;
	  CurrentValue[$FrontEndSession, {InputAliases, "vb"}] = Inherited;
	  CurrentValue[$FrontEndSession, {InputAliases, "u"}] = Inherited;
	  CurrentValue[$FrontEndSession, {InputAliases, "v"}] = Inherited
	];

	AngleBracket /: MakeBoxes[AngleBracket[x__], form_] =. ;

	Unprotect[FermionLine];
	FermionLine /: MakeBoxes[FermionLine[{sp2:1|-1,kin2__},{sp1:1|-1,kin1__},DiracMatrix[mtx__]],StandardForm] =. ;
	FermionLine /: MakeBoxes[FermionLine[{sp2:1|-1,kin2__},{sp1:1|-1,kin1__},DiracMatrix[]],StandardForm] =. ;
	(*Format[FermionLine[{sp2:1|-1,kin2__},{sp1:1|-1,kin1__},DiracMatrix[mtx___]],OutputForm] =. ;*)
	Protect[FermionLine];

	MakeExpression[RowBox@({"\[LeftAngleBracket]",RowBox[{spinor2_,"[",RowBox[kin2 : {PatternSequence[_, ","] .., _}],"]"}],",",RowBox[{spinor1_,"[",RowBox[kin1 : {PatternSequence[_, ","] .., _}],"]"}],"\[RightAngleBracket]"}),StandardForm] =. ;
	MakeExpression[RowBox@({"\[LeftAngleBracket]",RowBox[{RowBox[{spinor2_,"[",RowBox[kin2 : {PatternSequence[_, ","] .., _}],"]"}],",",RowBox[{spinor1_,"[",RowBox[kin1 : {PatternSequence[_, ","] .., _}],"]"}]}],"\[RightAngleBracket]"}),StandardForm] =. ;
	MakeExpression[RowBox@({"\[LeftAngleBracket]",RowBox[{spinor2_,"[",RowBox[kin2 : {PatternSequence[_, ","] .., _}],"]"}],",", dMtxes : PatternSequence[_, ","] ..., RowBox[{spinor1_,"[",RowBox[kin1 : {PatternSequence[_, ","] .., _}],"]"}],"\[RightAngleBracket]"}),StandardForm] =. ;
	MakeExpression[RowBox@({"\[LeftAngleBracket]",RowBox[{RowBox[{spinor2_,"[",RowBox[kin2 : {PatternSequence[_, ","] .., _}],"]"}],",", dMtxes : PatternSequence[_, ","] ..., RowBox[{spinor1_,"[",RowBox[kin1 : {PatternSequence[_, ","] .., _}],"]"}]}],"\[RightAngleBracket]"}),StandardForm] =. ;

	Unprotect[Inactive];
	BoxForm`UsesPreInPostFixOperatorQ[FermionLine] =. ;
	HoldPattern[MakeBoxes[Inactive[FermionLine][sp2:{sgn2:1|-1,kin2__},sp1:{sgn1:1|-1,kin1__},dmtx:((head:DiracMatrix|Inactive[DiracMatrix])[])],StandardForm]] =. ;
	HoldPattern[MakeBoxes[Inactive[FermionLine][sp2:{sgn2:1|-1,kin2__},sp1:{sgn1:1|-1,kin1__},dmtx:((head:DiracMatrix|Inactive[DiracMatrix])[mtx__])],StandardForm]] =. ;
	Protect[Inactive];

	$fancyInput[FermionLine]=False;
  ];


(* ::Subsubsection::Closed:: *)
(*FermionLineProduct*)


iEnableFancyIO[FermionLineProduct]:=
  If[TrueQ[$fancyInput[FermionLineProduct]],
	Message[X`Utilities`EnableFancyIO::noenab, FermionLineProduct],

	(*Interprets infix notation \[CirclePlus] as FermionLineProduct*)
	MakeExpression[RowBox@(row : {PatternSequence[_, "\[CircleTimes]"] .., _}),StandardForm] := MakeExpression[RowBox@{"FermionLineProduct", "[", RowBox@Riffle[row[[1 ;; -1 ;; 2]], ","], "]"}, StandardForm];
	(*Render FermionLineProduct using infix notation*)
	Unprotect[FermionLineProduct];
	FermionLineProduct /: MakeBoxes[FermionLineProduct[p__],StandardForm]:=RowBox[Riffle[Map[Function[{item},MakeBoxes[item,StandardForm],{HoldAllComplete}],Unevaluated[{p}]],"\[CircleTimes]"]];
	Protect[FermionLineProduct];

	$fancyInput[FermionLineProduct]=True;
  ];


iDisableFancyIO[FermionLineProduct]:=
  If[!TrueQ[$fancyInput[FermionLineProduct]],
	Message[X`Utilities`DisableFancyIO::nodisab, FermionLineProduct],

	MakeExpression[RowBox@(row : {PatternSequence[_, "\[CircleTimes]"] .., _}),StandardForm] =. ;

	Unprotect[FermionLineProduct];
	FermionLineProduct /: MakeBoxes[FermionLineProduct[p__],StandardForm] =. ;
	Protect[FermionLineProduct];

	$fancyInput[FermionLineProduct]=False;
  ];


(* ::Subsection::Closed:: *)
(*OutputForm*)


(*Formatting in OutputForm*)
Format[Dim, OutputForm] := "d";
Format[Eps,OutputForm] := "\[Epsilon]";
Format[Mu,OutputForm] := "\[Micro]";
Format[MetricG, OutputForm] := "g";
Format[LeviCivitaE,OutputForm] := "\[CurlyEpsilon]";

Format[Dirac1,OutputForm] := "1";
Format[DiracG,OutputForm] := "\[Gamma]";
Format[DiracG5,OutputForm] := "\[Gamma]5";
Format[DiracS,OutputForm] := "\[Sigma]";
Format[DiracPL,OutputForm] := "PL";
Format[DiracPR,OutputForm] := "PR";


Format[LDot[a_,b_],OutputForm]:=ToString[Unevaluated[a],OutputForm]<>"."<>ToString[Unevaluated[b],OutputForm];

Format[LTensor[a_,idx__],OutputForm]:=
ToString[a,OutputForm]<>"("<>StringJoin[Riffle[Map[Function[{item},ToString[Unevaluated[item],OutputForm],{HoldAllComplete}],Unevaluated[{idx}]],","]]<>")";


Format[FermionLine[{sp2:1|-1,kin2__},{sp1:1|-1,kin1__},DiracMatrix[mtx___]],OutputForm]:=
  With[{fcy1=Switch[sp1,1,"u",-1,"v"],fcy2=Switch[sp2,1,"u",-1,"v"]},
	Format[HoldForm[AngleBracket[fcy2[kin2],mtx,fcy1[kin1]]],OutputForm]
  ];


Format[FermionLineProduct[p__],OutputForm]:=StringJoin[Riffle[Map[Function[{item},ToString[Unevaluated[item],OutputForm],{HoldAllComplete}],Unevaluated[{p}]],"\[CircleTimes]"]];


(* ::Subsection::Closed:: *)
(*TraditionalForm formatting*)


(* ::Subsubsection::Closed:: *)
(*Special glyphs*)


(*Dimensional regularization symbols*)

Dim /: MakeBoxes[Dim,TraditionalForm] := "\[ScriptD]";
Mu /: MakeBoxes[Mu,TraditionalForm] := "\[Micro]";

Unprotect[Times,Power];
Times /: MakeBoxes[c_. Power[Eps,-1],TraditionalForm]:=FractionBox[MakeBoxes[c,TraditionalForm],TooltipBox[OverscriptBox["\[Epsilon]","~"],FormBox[RowBox[{FractionBox["1","\[Epsilon]"],RowBox[{"-",RowBox[{SubscriptBox["\[Gamma]","\"E\""]}]}],"+",RowBox[{"ln","(",RowBox[{"4"," ","\[Pi]"}],")"}]}],TraditionalForm]]];
Times /: MakeBoxes[c_. Power[Eps,-2],TraditionalForm]:=FractionBox[MakeBoxes[c,TraditionalForm],TooltipBox[SuperscriptBox[OverscriptBox["\[Epsilon]","~"],"2"],FormBox[RowBox[{FractionBox["1",SuperscriptBox["\[Epsilon]","2"]],"+",FractionBox["1","\[Epsilon]"],RowBox[{"(",RowBox[{"-",SubscriptBox["\[Gamma]","\"E\""],"+",RowBox[{"ln","(",RowBox[{"4"," ","\[Pi]"}],")"}]}],")"}],"+",FractionBox[SubsuperscriptBox["\[Gamma]","\"E\"","2"],"2"],"-",RowBox[{SubscriptBox["\[Gamma]","\"E\""],RowBox[{"ln","(",RowBox[{"4"," ","\[Pi]"}],")"}]}],"+",RowBox[{FractionBox["1","2"]," ",RowBox[{SuperscriptBox["ln","2"],"(",RowBox[{"4"," ","\[Pi]"}],")"}]}]}],TraditionalForm]]];

Power /: MakeBoxes[Power[Eps,-1],TraditionalForm]:=FractionBox["1",TooltipBox[OverscriptBox["\[Epsilon]","~"],FormBox[RowBox[{FractionBox["1","\[Epsilon]"],RowBox[{"-",RowBox[{SubscriptBox["\[Gamma]","\"E\""]}]}],"+",RowBox[{"ln","(",RowBox[{"4"," ","\[Pi]"}],")"}]}],TraditionalForm]]];
Power /: MakeBoxes[Power[Eps,-2],TraditionalForm]:=FractionBox["1",TooltipBox[SuperscriptBox[OverscriptBox["\[Epsilon]","~"],"2"],FormBox[RowBox[{FractionBox["1",SuperscriptBox["\[Epsilon]","2"]],"+",FractionBox["1","\[Epsilon]"],RowBox[{"(",RowBox[{"-",SubscriptBox["\[Gamma]","\"E\""],"+",RowBox[{"ln","(",RowBox[{"4"," ","\[Pi]"}],")"}]}],")"}],"+",FractionBox[SubsuperscriptBox["\[Gamma]","\"E\"","2"],"2"],"-",RowBox[{SubscriptBox["\[Gamma]","\"E\""],RowBox[{"ln","(",RowBox[{"4"," ","\[Pi]"}],")"}]}],"+",RowBox[{FractionBox["1","2"]," ",RowBox[{SuperscriptBox["ln","2"],"(",RowBox[{"4"," ","\[Pi]"}],")"}]}]}],TraditionalForm]]];
Protect[Times,Power];

Eps /: MakeBoxes[Eps,TraditionalForm]:=OverscriptBox["\[Epsilon]","~"];


(*Spinor space objects*)
Dirac1 /: MakeBoxes[Dirac1,TraditionalForm]:="\[DoubleStruckOne]";
DiracG /: MakeBoxes[DiracG,TraditionalForm]:="\[Gamma]";
DiracG5 /: MakeBoxes[DiracG5,TraditionalForm]:=SubscriptBox["\[Gamma]","5"];
DiracS /: MakeBoxes[DiracS,TraditionalForm]:="\[Sigma]"; 
DiracPL /: MakeBoxes[DiracPL,TraditionalForm]:=SubscriptBox["\"P\"", "\"L\""];
DiracPR /: MakeBoxes[DiracPR,TraditionalForm]:=SubscriptBox["\"P\"", "\"R\""];


(* ::Subsubsection::Closed:: *)
(*LDot, LTensor*)


(*Format Mathematica's Dot as an ordinary function*)
Unprotect[Dot];
  Dot/: MakeBoxes[Dot[x__], TraditionalForm] := RowBox[{"Dot", "(", X`Internal`ToRowBox[{x},TraditionalForm], ")"}];
Protect[Dot];


LDot/: MakeBoxes[LDot[x_,x_],TraditionalForm] := MakeBoxes[x^2,TraditionalForm];
LDot/: MakeBoxes[LDot[x_,y_],TraditionalForm] := RowBox[{Parenthesize[x,TraditionalForm,Times,Left],".",Parenthesize[y,TraditionalForm,Times,Right]}];
(*Feynman slash notation*)
(*LDot /: MakeBoxes[e: LDot[DiracG,x_Symbol],TraditionalForm]:=TooltipBox[ToBoxes[Overlay[{x,"\[ThinSpace]/"}]],MakeBoxes[e,StandardForm]];*)
LDot /: MakeBoxes[e: LDot[DiracG,x_Symbol],TraditionalForm]:=TooltipBox[OverlayBox[{MakeBoxes[x,TraditionalForm],"\<\"\[ThinSpace]/\"\>"}],MakeBoxes[e,StandardForm]];


(*Tensor objects*)
LTensor /: MakeBoxes[LTensor[MetricG,idx__],TraditionalForm]:=SuperscriptBox["\[ScriptG]",X`Internal`ToInvisibleCommaRowBox[{idx}]];
LTensor /: MakeBoxes[LTensor[LeviCivitaE,idx__],TraditionalForm]:=SuperscriptBox["\[CurlyEpsilon]",X`Internal`ToInvisibleCommaRowBox[{idx}]];
LTensor/: MakeBoxes[LTensor[a_,idx__],TraditionalForm] := SuperscriptBox[Parenthesize[a,TraditionalForm,Power,Left],X`Internal`ToInvisibleCommaRowBox[{idx}]];


(* ::Subsubsection::Closed:: *)
(*LoopIntegrate*)


denomSpecBox[{0,0,weight_:1},TraditionalForm]:=
  TemplateBox[{"0","0",MakeBoxes[weight]}
	,"LoopIntegrateDenomSpec"
	,DisplayFunction->If[weight===1,"0"&,SuperscriptBox["0",#3]&]
	,InterpretationFunction->(RowBox[{"{",#1,",",#2,",",#3,"}"}]&)];

denomSpecBox[{mom_,0,weight_:1},TraditionalForm]:=
  TemplateBox[{Parenthesize[mom,TraditionalForm,Times,Left],"0",MakeBoxes[weight]}
	,"LoopIntegrateDenomSpec"
	,DisplayFunction->If[weight===1,
	  SuperscriptBox[#1,"2"]&,
	  SuperscriptBox[RowBox[{"[",SuperscriptBox[#1,"2"],"]"}],#3]&]
	,InterpretationFunction->(RowBox[{"{",#1,",",#2,",",#3,"}"}]&)];

denomSpecBox[{0,mass_,weight_:1},TraditionalForm]:=
  TemplateBox[{"0",Parenthesize[mass,TraditionalForm,Times,Left],MakeBoxes[weight]}
	,"LoopIntegrateDenomSpec"
	,DisplayFunction->If[weight===1,
	  RowBox[{"[",RowBox[{"-",SuperscriptBox[#2,"2"]}],"]"}]&,
	  SuperscriptBox[RowBox[{"[","-",SuperscriptBox[#2,"2"],"]"}],#3]&]
	,InterpretationFunction->(RowBox[{"{",#1,",",#2,",",#3,"}"}]&)];

denomSpecBox[{mom_,mass_,weight_:1},TraditionalForm]:=
  TemplateBox[{Parenthesize[mom,TraditionalForm,Times,Left],Parenthesize[mass,TraditionalForm,Times,Left],MakeBoxes[weight]}
	,"LoopIntegrateDenomSpec"
	,DisplayFunction->If[weight===1,
	  RowBox[{"[",SuperscriptBox[#1,"2"],"-",SuperscriptBox[#2,"2"],"]"}]&,
	  SuperscriptBox[RowBox[{"[",SuperscriptBox[#1,"2"],"-",SuperscriptBox[#2,"2"],"]"}],#3]&]
	,InterpretationFunction->(RowBox[{"{",#1,",",#2,",",#3,"}"}]&)];


(*Output TraditionalForm formatting for LoopIntegrate*)
LoopIntegrate /: HoldPattern[MakeBoxes[LoopIntegrate[num_,k_Symbol,Pattern[denom,(({_,_}|{_,_,_})..)],OptionsPattern[]],TraditionalForm]]:=
  TemplateBox[{MakeBoxes[num,TraditionalForm],MakeBoxes[k,TraditionalForm],ListToDenomSpecRowBox[{denom},TraditionalForm]},
	"LoopIntegrate",
	DisplayFunction->(
	  RowBox[{"\[Integral]",
		FractionBox[RowBox[{SuperscriptBox["\[DifferentialD]","\[ScriptD]"],#2}],SuperscriptBox[RowBox[{"(","2","\[Pi]",")"}],"\[ScriptD]"]],
		FractionBox[#1,#3]
	  }]&),
	InterpretationFunction->(RowBox[{"LoopIntegrate","[",RowBox[Riffle[{#1,#2}~Join~Map[ToBoxes[ToExpression[#]]&,#3,{2}][[1]],","]],"]"}]&),Editable->True
  ];
	
(*Output TraditionalForm formatting for Inactive[LoopIntegrate]*)
Unprotect[Inactive];
PrependTo[FormatValues[Inactive],
  HoldPattern[MakeBoxes[Inactive[LoopIntegrate][num_,k_Symbol,Pattern[denom,(({_,_}|{_,_,_})..)],OptionsPattern[]],TraditionalForm]]:>
	TemplateBox[{MakeBoxes[num,TraditionalForm],MakeBoxes[k,TraditionalForm],RowBox[denomSpecBox[#,TraditionalForm]&/@{denom}]},
	  "InactiveLoopIntegrate",
	  DisplayFunction->(
		RowBox[{StyleBox["\[Integral]","Inactive"],
		  FractionBox[RowBox[{SuperscriptBox[StyleBox["\[DifferentialD]","Inactive"],StyleBox["\[ScriptD]","Inactive"]],#2}],
			SuperscriptBox[RowBox[{StyleBox["(","Inactive"],StyleBox["2","Inactive"],StyleBox["\[Pi]","Inactive"],StyleBox[")","Inactive"]}],StyleBox["\[ScriptD]","Inactive"]]],
			FractionBox[#1,#3]
		  }]&),
	  InterpretationFunction->(RowBox[{RowBox[{"Inactive","[","LoopIntegrate","]"}],"[",RowBox[Riffle[{#1,#2}~Join~Map[ToBoxes[ToExpression[#]]&,#3,{2}][[1]],","]],"]"}]&),
	  Editable->True,
	  Tooltip:>"Inactive[LoopIntegrate]"
	]
  ];
Protect[Inactive];


(* ::Subsubsection::Closed:: *)
(*PVA, PVB, PVC, PVD, PVX*)


MakeBoxes[PVA[r_Integer, m0_, opts:OptionsPattern[PVA]], TraditionalForm] ^:=
With[{tensorIndices=RowBox[Riffle[If[NonNegative[r],Table["0", {Max[2*r, 1]}], {"(",r,")"}],"\[InvisibleComma]"]],
	  kinematicArguments=Sequence["(",X`Internal`ToRowBox[{m0},TraditionalForm],")"]}, 
  TooltipBox[
    If[(*Normal PVA*)OptionValue[PVA,opts,Weights]==={1},
	  RowBox[{SubscriptBox[StyleBox["A",FontSlant->Plain,FontWeight->Bold], tensorIndices], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}],
	   (*Weighted PVA*)
	  RowBox[{SubsuperscriptBox[StyleBox["A",FontSlant->Plain,FontWeight->Bold], tensorIndices,ToBoxes[OptionValue[PVA,opts,Weights]]], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}]
    ],If[X`Utilities`$PVShortForm,RowBox[{"PVA",kinematicArguments}],"PVA"]]
];


MakeBoxes[PVB[r_Integer, n_Integer?NonNegative, s_, m0_, m1_, opts:OptionsPattern[PVB]], TraditionalForm] ^:=
With[{tensorIndices=RowBox[Riffle[Which[
		r===n===0,      {"0"},
		NonNegative[r], Table["0", {2*r}],
		Negative[r],    {"(",r,")"}]~Join~Table["1", {n}],"\[InvisibleComma]"]],
	  kinematicArguments=Sequence["(",X`Internal`ToRowBox[{s},TraditionalForm],";",X`Internal`ToRowBox[{m0,m1},TraditionalForm],")"]},
  TooltipBox[
	If[(*Normal PVB*)OptionValue[PVB,opts,Weights]==={1,1},
	  RowBox[{SubscriptBox[StyleBox["B",FontSlant->Plain,FontWeight->Bold], tensorIndices],If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}],
	   (*Weighted PVB*)
	  RowBox[{SubsuperscriptBox[StyleBox["B",FontSlant->Plain,FontWeight->Bold], tensorIndices, ToBoxes[OptionValue[PVB,opts,Weights]]], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}]
    ],If[X`Utilities`$PVShortForm,RowBox[{"PVB",kinematicArguments}],"PVB"]]
];


MakeBoxes[Derivative[0,0,1,0,0][PVB][r_Integer, n_Integer?NonNegative, s_, m0_, m1_, opts:OptionsPattern[PVB]], TraditionalForm] ^:=
With[{tensorIndices=RowBox[Riffle[Which[
		r===n===0,      {"0"},
		NonNegative[r], Table["0", {2*r}],
		Negative[r],    {"(",r,")"}]~Join~Table["1", {n}],"\[InvisibleComma]"]],
	  kinematicArguments=Sequence["(",X`Internal`ToRowBox[{s},TraditionalForm],";",X`Internal`ToRowBox[{m0,m1},TraditionalForm],")"]},
  TooltipBox[
	If[(*Normal PVB*)OptionValue[PVB,opts,Weights]==={1,1},
	  RowBox[{SubsuperscriptBox[StyleBox["B",FontSlant->Plain,FontWeight->Bold], tensorIndices,"\[Prime]"], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}],
	   (*Weighted PVB*)
	  RowBox[{SubsuperscriptBox[StyleBox["B",FontSlant->Plain,FontWeight->Bold], tensorIndices, RowBox[{"\[Prime]",ToBoxes[OptionValue[PVB,opts,Weights]]}]], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}]
    ],If[X`Utilities`$PVShortForm,RowBox[{"PVB",kinematicArguments}],"PVB"]]
];


MakeBoxes[PVC[r_Integer, n1_Integer?NonNegative, n2_Integer?NonNegative, p1_, q_, p2_, m0_, m1_, m2_, opts: OptionsPattern[PVC]], TraditionalForm] ^:= 
With[{tensorIndices=RowBox[Riffle[Which[
		r===n1===n2===0, {"0"},
		NonNegative[r],  Table["0", {2*r}],
		Negative[r],     {"(",r,")"}]~Join~Join[Table["1", {n1}],Table["2", {n2}]],"\[InvisibleComma]"]],
	  kinematicArguments=Sequence["(",X`Internal`ToRowBox[{p1,q,p2},TraditionalForm],";",X`Internal`ToRowBox[{m0,m1,m2},TraditionalForm],")"]},
  TooltipBox[
	If[(*Normal PVC*)OptionValue[PVC,opts,Weights]==={1,1,1},  
	  RowBox[{SubscriptBox[StyleBox["C",FontSlant->Plain,FontWeight->Bold], tensorIndices], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}],
	   (*Weighted PVC*)
	  RowBox[{SubsuperscriptBox[StyleBox["C",FontSlant->Plain,FontWeight->Bold], tensorIndices, ToBoxes[OptionValue[PVC,opts,Weights]]], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}]
  ],If[X`Utilities`$PVShortForm,RowBox[{"PVC",kinematicArguments}],"PVC"]]
];


MakeBoxes[PVD[r_Integer, n1_Integer?NonNegative, n2_Integer?NonNegative, n3_Integer?NonNegative, s1_, s2_, s3_, s4_, s12_, s23_, m0_, m1_, m2_, m3_, opts:OptionsPattern[PVD]], TraditionalForm] ^:= 
With[{tensorIndices=RowBox[Riffle[Which[
		r===n1===n2===n3===0, {"0"},
		NonNegative[r],       Table["0", {2*r}],
		Negative[r],          {"(",r,")"}]~Join~Join[Table["1", {n1}],Table["2", {n2}],Table["3", {n3}]],"\[InvisibleComma]"]],
	  kinematicArguments=Sequence["(",X`Internal`ToRowBox[{s1,s2,s3,s4},TraditionalForm],";",X`Internal`ToRowBox[{s12,s23},TraditionalForm],";",X`Internal`ToRowBox[{m0,m1,m2,m3},TraditionalForm],")"]},
  TooltipBox[
	If[(*Normal PVD*)OptionValue[PVD,opts,Weights]==={1,1,1,1},
	  RowBox[{SubscriptBox[StyleBox["D",FontSlant->Plain,FontWeight->Bold], tensorIndices], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}],
	   (*Weighted PVD*)
	  RowBox[{SubsuperscriptBox[StyleBox["D",FontSlant->Plain,FontWeight->Bold], tensorIndices,ToBoxes[OptionValue[PVD,opts,Weights]]], If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}]
  ],If[X`Utilities`$PVShortForm,RowBox[{"PVD",kinematicArguments}],"PVD"]]
];


(*General Passarino-Veltman function*)
MakeBoxes[HoldPattern[PVX[args__]], TraditionalForm] ^:=
  With[{noDenom=(-3+Sqrt[9+8*Length[Unevaluated[{args}]]])/2}, 
	With[
	  {indices=Hold[args][[1;;noDenom]],
	   extInv=Hold[args][[1+noDenom;;(-1+noDenom)noDenom/2+noDenom]],
	   intMasses=Hold[args][[-noDenom;;]],
	   pvID=FromCharacterCode[64+noDenom]},
	  With[{tensorIndices=RowBox[Riffle[Which[
			  MatchQ[indices,Hold[(0)..]],  {"0"},
			  NonNegative[indices[[1]]], Table["0", {2*indices[[1]]}],
			  Negative[indices[[1]]],   {"(",indices[[1]],")"} ] ~Join~ (Join@@MapIndexed[ConstantArray[ToString[#2[[1]]],#1]&,List@@Rest[indices]]),"\[InvisibleComma]"]],
			kinematicArguments=Sequence["(",X`Internal`ToRowBox[extInv,TraditionalForm],";",X`Internal`ToRowBox[intMasses,TraditionalForm],")"]},

		TooltipBox[RowBox[{SubscriptBox[StyleBox[pvID,FontSlant->Plain,FontWeight->Bold], tensorIndices],If[X`Utilities`$PVShortForm,Unevaluated@Sequence[],Unevaluated@kinematicArguments]}]
		,If[X`Utilities`$PVShortForm,RowBox[{"PVX",kinematicArguments}],"PVX"]]		
	  ]/; MatchQ[indices,Hold[__Integer?NonNegative]]
	]/;argsCheckPVX[Length[Unevaluated[{args}]]]
  ];


(* ::Subsubsection::Closed:: *)
(*Spur, DiracMatrix, FermionLine, FermionLineProduct*)


Unprotect[Times];
  Times /: MakeBoxes[Times[Dirac1,a_],TraditionalForm]:=MakeBoxes[a,TraditionalForm];
  Times /: MakeBoxes[Times[DiracMatrix[],a_],TraditionalForm]:=MakeBoxes[a,TraditionalForm];
Protect[Times];

Spur /: MakeBoxes[Spur[],TraditionalForm]:=RowBox[{TooltipBox["Tr","Spur"],"[","]"}];
Spur /: MakeBoxes[Spur[mtx__],TraditionalForm]:=RowBox[{TooltipBox["Tr","Spur"],"[",MakeBoxes[DiracMatrix[mtx],TraditionalForm],"]"}];

DiracMatrix /: MakeBoxes[DiracMatrix[],TraditionalForm]:=TooltipBox["\[DoubleStruckOne]","DiracMatrix[]"];
DiracMatrix /: MakeBoxes[DiracMatrix[mtx__],TraditionalForm]:=RowBox[Map[Function[{item},Parenthesize[item,TraditionalForm,Times,Left],{HoldAllComplete}],Unevaluated[{mtx}]]];


(*FermionLine*)
FermionLine /: MakeBoxes[FermionLine[{sp2:1|-1,p2_,__},{sp1:1|-1,p1_,__},diracMtx_DiracMatrix],TraditionalForm]:=
  With[{spinor1=Switch[sp1,1,"\[ScriptU]",-1,"\[ScriptV]"],  spinor2=Switch[sp2,1,OverscriptBox["\[ScriptU]","_"],-1,OverscriptBox["\[ScriptV]","_"]]},  
	RowBox[{spinor2,"(",MakeBoxes[p2],")",
	  Switch[Unevaluated[diracMtx]
		,HoldPattern[DiracMatrix[]],Unevaluated[Sequence[]]
		,_,MakeBoxes[diracMtx,TraditionalForm]]
	  ,spinor1,"(",MakeBoxes[p1],")"}]
  ];

(*Eventually, TraditionalForm for massless spinors with helicity labels can use \[LeftAngleBracket],[,  and  \[RightAngleBracket],]*)
(*Inactive TraditionalForm formatting*)
Unprotect[Inactive];
PrependTo[
  FormatValues[Inactive],HoldPattern[MakeBoxes[Inactive[FermionLine][{sp2:1|-1,p2_,__},{sp1:1|-1,p1_,__},(head:DiracMatrix|Inactive[DiracMatrix])[mtx___]],TraditionalForm]]:>
	With[{spinor1=Switch[sp1,1, "\[ScriptU]",-1,"\[ScriptV]"], spinor2=Switch[sp2,1,OverscriptBox["\[ScriptU]","_"],-1,OverscriptBox["\[ScriptV]","_"]]},  
	  RowBox[{spinor2,"(",MakeBoxes[p2,TraditionalForm],")",MakeBoxes[head[mtx],TraditionalForm],spinor1,"(",MakeBoxes[p1,TraditionalForm],")"}]
	]
];

PrependTo[
  FormatValues[Inactive],HoldPattern[MakeBoxes[e:Inactive[Spur][mtx___],TraditionalForm]]:>
	Switch[Unevaluated[e]
	 ,HoldPattern[Inactive[Spur][]], RowBox[{TooltipBox["Tr","Inactive[Spur]"],"[","]"}]
	 ,_, RowBox[{TooltipBox["Tr","Inactive[Spur]"],"[",MakeBoxes[DiracMatrix[mtx],TraditionalForm],"]"}]]
];

PrependTo[
  FormatValues[Inactive],HoldPattern[e:MakeBoxes[Inactive[DiracMatrix][mtx__],TraditionalForm]]:>
	Switch[Unevaluated[e]
	 ,HoldPattern[Inactive[DiracMatrix][]],TooltipBox["\[DoubleStruckOne]","Inactive[DiracMatrix][]"]
	 ,_,TooltipBox[MakeBoxes[DiracMatrix[mtx],TraditionalForm],"Inactive[DiracMatrix]"]]
];

Protect[Inactive];


(*FermionLineProduct*)
SetAttributes[shorthandFermionLineBox,HoldAllComplete];
shorthandFermionLineBox[{sgn2_,p2_,_},{sgn1_,p1_,_},diracMtx_DiracMatrix]:=
With[
  {spinor2=If[Unevaluated[sgn2]===1,"\!\(\*OverscriptBox[\(\[ScriptU]\),\(_\)]\)","\!\(\*OverscriptBox[\(\[ScriptV]\),\(_\)]\)"],
   spinor1=If[Unevaluated[sgn1]===1,"\[ScriptU]","\[ScriptV]"]},
	With[{tooltipString=spinor2<>"("<>ToString[Unevaluated[p2],TraditionalForm]<>")\[Ellipsis]"<>spinor1<>"("<>ToString[Unevaluated[p1],TraditionalForm]<>")"},
	  TooltipBox[RowBox[{"\[InvisiblePrefixScriptBase]\[LeftAngleBracket]",Switch[Unevaluated[diracMtx],HoldPattern[DiracMatrix[]],"\[DoubleStruckOne]",_,MakeBoxes[diracMtx,TraditionalForm]],"\[RightAngleBracket]\[InvisiblePrefixScriptBase]"}],tooltipString]
	]
];

FermionLineProduct /: MakeBoxes[FermionLineProduct[c___FermionLine],TraditionalForm] := RowBox[shorthandFermionLineBox@@@Unevaluated[{c}]];


(* ::Subsubsection::Closed:: *)
(*Special functions*)


(*Special functions and abbreviations*)
Kibble\[Phi] /: MakeBoxes[Kibble\[Phi][a_,b_,c_,d_,s_,t_],TraditionalForm]:=TooltipBox[RowBox[{"\[Phi]","(",X`Internal`ToRowBox[{a,b,c,d},TraditionalForm],";",X`Internal`ToRowBox[{s,t},TraditionalForm],")"}],"Kibble\[Phi]"];

Kallen\[Lambda] /: MakeBoxes[Kallen\[Lambda][a_,b_,c_],TraditionalForm]:=TooltipBox[RowBox[{"\[Lambda]","(",X`Internal`ToRowBox[{a,b,c},TraditionalForm],")"}],"Kallen\[Lambda]"];

Unprotect[Power];
Power /: MakeBoxes[Power[Kallen\[Lambda][a_,b_,c_],Rational[num_,denom_]],TraditionalForm]:=TooltipBox[RowBox[{SuperscriptBox["\[Lambda]",RowBox[{MakeBoxes[num],"/",MakeBoxes[denom]}]],"(",X`Internal`ToRowBox[{a,b,c},TraditionalForm],")"}],"Kallen\[Lambda]"];
Power /: MakeBoxes[Kallen\[Lambda][a_,b_,c_]^p_,TraditionalForm]:=TooltipBox[RowBox[{SuperscriptBox["\[Lambda]",MakeBoxes[p]],"(",X`Internal`ToRowBox[{a,b,c},TraditionalForm],")"}],"Kallen\[Lambda]"];
Protect[Power];

DiscB /: MakeBoxes[DiscB[s_, m0_, m1_], TraditionalForm] := 
  TooltipBox[RowBox[{"\[CapitalLambda]", "(", X`Internal`ToRowBox[{s,m0,m1},TraditionalForm], ")"}],"DiscB"];

ScalarC0 /: MakeBoxes[ScalarC0[p1_,q_,p2_,m0_,m1_,m2_],TraditionalForm]:=
	TooltipBox[RowBox[{SubscriptBox["C","0"],"(",X`Internal`ToRowBox[{p1,q,p2},TraditionalForm],";",X`Internal`ToRowBox[{m0,m1,m2},TraditionalForm],")"}],"ScalarC0"];

ScalarC0IR6 /: MakeBoxes[ScalarC0IR6[s_,m0_,m1_],TraditionalForm]:=
	TooltipBox[RowBox[{SubsuperscriptBox["I","C6","fin"],"(",X`Internal`ToRowBox[{s,m0,m1},TraditionalForm],")"}],"ScalarC0IR6"];

ScalarD0 /: MakeBoxes[ScalarD0[s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_],TraditionalForm]:=
	TooltipBox[RowBox[{SubscriptBox["D","0"],"(",X`Internal`ToRowBox[{s1,s2,s3,s4},TraditionalForm],";",X`Internal`ToRowBox[{s12,s23},TraditionalForm],";",X`Internal`ToRowBox[{m0,m1,m2,m3},TraditionalForm],")"}],"ScalarD0"];

ScalarD0IR12 /: MakeBoxes[ScalarD0IR12[s2_,s3_,s12_,s23_,m2_,m3_],TraditionalForm]:=
	TooltipBox[RowBox[{SubsuperscriptBox["I","D12","fin"],"(",X`Internal`ToRowBox[{s2,s3},TraditionalForm],";",X`Internal`ToRowBox[{s12,s23},TraditionalForm],";",X`Internal`ToRowBox[{m2,m3},TraditionalForm],")"}],"ScalarD0IR12"];

ScalarD0IR13 /: MakeBoxes[ScalarD0IR13[s2_,s3_,s4_,s12_,s23_,m2_,m3_],TraditionalForm]:=
	TooltipBox[RowBox[{SubsuperscriptBox["I","D13","fin"],"(",X`Internal`ToRowBox[{s2,s3,s4},TraditionalForm],";",X`Internal`ToRowBox[{s12,s23},TraditionalForm],";",X`Internal`ToRowBox[{m2,m3},TraditionalForm],")"}],"ScalarD0IR13"];

ScalarD0IR16 /: MakeBoxes[ScalarD0IR16[s2_,s3_,s12_,s23_,m1_,m2_,m3_],TraditionalForm]:=
	TooltipBox[RowBox[{SubsuperscriptBox["I","D16","fin"],"(",X`Internal`ToRowBox[{s2,s3},TraditionalForm],";",X`Internal`ToRowBox[{s12,s23},TraditionalForm],";",X`Internal`ToRowBox[{m1,m2,m3},TraditionalForm],")"}],"ScalarD0IR16"];


With[{
  (*Takes arguments (z,zEps), and constructs an z + i \[CurlyEpsilon] zEps TraditionalForm Box out of it*)
  makeZPlusIEpsBox=
	Function[{z,zEps},If[Internal`SyntacticNegativeQ[Unevaluated[zEps](* && SideEffectFreeQ[zEps]*)],
	  RowBox[{MakeBoxes[z,TraditionalForm],"-","\[ImaginaryI]","\[CurlyEpsilon]",Replace[Expand[-zEps],e_:>RuleCondition[Parenthesize[e,TraditionalForm,Plus,Right]]]}],
	  RowBox[{MakeBoxes[z,TraditionalForm],"+","\[ImaginaryI]","\[CurlyEpsilon]",If[MatchQ[Unevaluated[zEps],1],Unevaluated[Sequence[]],Parenthesize[zEps,TraditionalForm,Plus,Right]]}]
	],{HoldAllComplete}]
  },

  Ln /: MakeBoxes[Ln[z_,zEps_],TraditionalForm] := 
	TooltipBox[RowBox[{"log","(",makeZPlusIEpsBox[z,zEps],")"}],"Ln"];

  DiLog /: MakeBoxes[DiLog[z_,zEps_],TraditionalForm] := 
	TooltipBox[RowBox[{SubscriptBox["Li","2"],"(",makeZPlusIEpsBox[z,zEps],")"}], "DiLog"];

  ContinuedDiLog /: MakeBoxes[ContinuedDiLog[args___List],TraditionalForm] := 
	TooltipBox[RowBox[{SubscriptBox["\[ScriptCapitalL]\[ScriptI]","2"],"(",Sequence@@Riffle[Apply[makeZPlusIEpsBox,Unevaluated[{args}],{1}],","],")"}], "ContinuedDiLog"];
];


(* ::Subsubsection::Closed:: *)
(*TeXForm extras*)


(*In Version 11, these rules are the bottom, which cases StyleBox[...Bold] to fail.*)

System`Convert`TeXFormDump`maketex[SuperscriptBox["\[ScriptG]",idx_RowBox]]:=System`Convert`TeXFormDump`maketex[SuperscriptBox["g",idx]];
System`Convert`TeXFormDump`maketex[OverlayBox[{FormBox[TemplateBox[{base_,sub_,super_},"Subsuperscript",SyntaxForm->SubsuperscriptBox],TraditionalForm],"\"\[ThinSpace]/\""}|{FormBox[SubsuperscriptBox[base_,sub_,super_],TraditionalForm],"\"\[ThinSpace]/\""}]]:="\\slashed{"<>System`Convert`TeXFormDump`MakeTeX[base]<>"}^{"<>System`Convert`TeXFormDump`MakeTeX[super]<>"}_{"<>System`Convert`TeXFormDump`MakeTeX[sub]<>"}";
System`Convert`TeXFormDump`maketex[OverlayBox[{FormBox[TemplateBox[{base_,super_},"Superscript",SyntaxForm->SuperscriptBox],TraditionalForm],"\"\[ThinSpace]/\""}|{FormBox[SuperscriptBox[base_,super_],TraditionalForm],"\"\[ThinSpace]/\""}]]:="\\slashed{"<>System`Convert`TeXFormDump`MakeTeX[base]<>"}^{"<>System`Convert`TeXFormDump`MakeTeX[super]<>"}";
System`Convert`TeXFormDump`maketex[OverlayBox[{FormBox[SubscriptBox[base_,sub_],TraditionalForm],"\"\[ThinSpace]/\""}]]:="\\slashed{"<>System`Convert`TeXFormDump`MakeTeX[base]<>"}_{"<>System`Convert`TeXFormDump`MakeTeX[sub]<>"}";
System`Convert`TeXFormDump`maketex[OverlayBox[{x_,"\"\[ThinSpace]/\""}]]:="\\slashed{"<>System`Convert`TeXFormDump`MakeTeX[x]<>"}";  (*In TeX form*)
System`Convert`TeXFormDump`maketex[SubscriptBox["\[Gamma]","5"]]:="\\gamma_5";
System`Convert`TeXFormDump`maketex[SubscriptBox["\"P\"", "\"L\""]]:="P_L";
System`Convert`TeXFormDump`maketex[SubscriptBox["\"P\"", "\"R\""]]:="P_R";

System`Convert`TeXFormDump`maketex[OverscriptBox["\[Epsilon]","~"]]="\\epsilon ";
System`Convert`TeXFormDump`maketex["\[FormalX]"]="x";
System`Convert`TeXFormDump`maketex["\[FormalY]"]="y";
System`Convert`TeXFormDump`maketex["\[FormalR]"]="r";
System`Convert`TeXFormDump`maketex["\[Function]"]:="\\longmapsto ";

System`Convert`TeXFormDump`maketex[StyleBox[x_,FontSlant->Plain,FontWeight->Bold]]:="\\mathbf{"<>x<>"}";


(* ::Subsection::Closed:: *)
(*X`Internal` functions*)


SetAttributes[{X`Internal`ToRowBox,X`Internal`ToInvisibleCommaRowBox},HoldAllComplete];
X`Internal`ToRowBox[(List|Hold)[seqOfItems___], form_:StandardForm] := RowBox[Riffle[Map[Function[{item},MakeBoxes[item,form],{HoldAllComplete}],Unevaluated[{seqOfItems}]],","]];
X`Internal`ToInvisibleCommaRowBox[list_List] := RowBox[Riffle[Map[Function[{item},MakeBoxes[item,TraditionalForm],{HoldAllComplete}],Unevaluated[list]],"\[InvisibleComma]"]];


X`Internal`FromCoefficientRules[{},vars_List] := 0;
X`Internal`FromCoefficientRules[rules_List,vars_List] := Total[#[[2]]*Inner[pow,vars,#[[1]],Times]&/@rules];

X`Internal`CoefficientRules[poly_,vars_List] := Rule@@@First[GroebnerBasis`DistributedTermsList[poly,vars]];


(*Mimics Version 10's AllTrue[mtx,PossibleZeroQ,2] function*)
X`Internal`PossibleAllZeroQ[mtx_]:=ReplaceAll[PossibleZeroQ[mtx],List->And];


X`Internal`ValidOptionsQ[symb_Symbol][x_]:=If[FilterRules[Options[symb],x]==={},Message[symb::optx,First[x],symb],True];


(*Default pattern for incorrect number of arguments*)
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


SetAttributes[
  {X`Internal`FromCoefficientRules,X`Internal`CoefficientRules,
   X`Internal`PossibleAllZeroQ,X`Internal`ValidOptionsQ,
   X`Internal`CheckArgumentCount,X`Internal`ToTargetPrecision,
   X`Internal`ToRowBox, X`Internal`ToInvisibleCommaRowBox},
{Protected,ReadProtected,Locked}];


(*Integer powers of kinematic variables*)
pow[a_,0]:=1;  pow[a_,b_]:=a^b;

(*Argument numbers are {A=2,B=5,C=9,D=14,E=20,F=27,G=35,H=44,I=54,J=65,...}*)
argsCheckPVX = MemberQ[{2,5,9,14,20,27,35,44,54,65,77,90},#] || IntegerQ[ (-3+Sqrt[9+8*#])/2] & ;

(*Helper function for Contract*)
(*pair is used when product of Levi-Civita tensors are contracted to form LDot or LTensors*)
SetAttributes[pair,Orderless];

pair[List[0]|vec[0], _] := 0;
pair[a: _List|_vec, b: _List|_vec]:=LDot[First[a],First[b]]; (*a_mu * b_mu -> a.b*)
pair[a: _List|_vec, b_Symbol|idx[b_]]:=LTensor[First[a],b];  (*a_mu * g_(mu,b) -> a_b*)
pair[a_Symbol|idx[a_], b_Symbol|idx[b_]]:=LTensor[MetricG,a,b];    (*g_(mu,a) * g_(mu,b) -> g_(a,b)*)

(*Extended rules for integer indices*)
pair[a: _List|_vec, b_Integer]:=LTensor[First[a],b];
pair[a_Symbol|idx[a_], b_Integer]:=LTensor[MetricG,a,b];
pair[a:0|1|2|3, a_]:=Switch[a,0,1,1|2|3,-1];  (*<--- this assumes both indices are down*)
pair[a_Integer, b_Integer]:=0;


(*
RestrictedReplaceAll::usage = "RestrictedReplaceAll[expr, rules, heads] applies a list of rules in an attempt to transform each subpart of an expresion 'expr' that are not inside heads.";
RestrictedReplaceRepeated::usage = "RestrictedReplaceRepeated[expr, rules, heads] repeatedly performs replacements outside of heads until expr no longer changes.";

RestrictedReplaceAll[expr_,rules_,heads_]:=expr/.Join[inert:Blank[#]:>inert&/@heads,rules];
RestrictedReplaceRepeated[expr_,rules_,heads_]:=expr//.Join[inert:Blank[#]:>inert&/@heads,rules];
*)


(* ::Subsection::Closed:: *)
(*Global Package-X settings*)


X`Utilities`$PVShortForm = False;

If[$Notebooks,
  X`Utilities`EnableFancyIO[LDot, LTensor, LoopIntegrate, FermionLine, FermionLineProduct,"SpecialGlyphs"];
  Unprotect[LoopIntegrate,FermionLine,FermionLineProduct,Dim,Eps,Mu,MetricG,LeviCivitaE,Dirac1,DiracG,DiracG5,DiracS,DiracPL,DiracPR];
];


$DiracAlgebra=True;


$LScalarList::usage = "$LScalarList is a global List containing symbols which the user has declared as Lorentz scalars using 'LScalarQ[symb] = True' in the current Mathematica session.";
$LScalarList = {Dim,Eps,Mu,Dirac1,DiracG5,DiracPL,DiracPR};


SetOptions[Simplify,ExcludedForms->{1/Eps,1/Eps^2,_FermionLine,_DiracMatrix}];
SetOptions[FullSimplify,ExcludedForms->{1/Eps,1/Eps^2,_FermionLine,_DiracMatrix}];


General::irdiv="`1` singularity encountered.";


(* ::Subsection::Closed:: *)
(*End*)


End[];

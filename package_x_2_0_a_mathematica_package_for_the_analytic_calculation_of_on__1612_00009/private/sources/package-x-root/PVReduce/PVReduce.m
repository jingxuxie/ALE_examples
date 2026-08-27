(* ::Package:: *)

BeginPackage["X`PVReduce`",{"X`"}];
Print["PVReduce v0.1.0 [BETA] initialized."];


Options[PVReduce]={Organization->LTensor, "EliminateScalelessPV"->False,"BnToB0"->True,"IRDivCToB"->False,"IRDivBToA"->True,"B00ReductionMethod"->"Recursive"};
SyntaxInformation[PVReduce]={"ArgumentsPattern"->{_,OptionsPattern[]},"OptionNames" -> {Organization,"\"EliminateScalelessPV\"","\"BnToB0\"","\"IRDivCToB\"","\"IRDivBToA\"","\"B00ReductionMethod\""}};
PVReduce::usage = "PVReduce[expr] algebraically reduces the Passarino-Veltman functions in 'expr' to scalar functions.";


Begin["`Private`"];


(* ::Subsection::Closed:: *)
(*A functions*)


reduceA[Except[-1,r_Integer], 0] := 0;
reduceA[Except[0,r_Integer],Except[0,m0_]] := (-1)^r/2^r FunctionExpand[Gamma[1-Dim/2-r]/Gamma[1-Dim/2]] m0^(2r) reduceA[0,m0];


(* ::Subsection::Closed:: *)
(*B functions*)


(*Case III*)
reduceB[r_Integer, n_Integer, 0, m0_, m0_] :=  (-1)^(n)/(2*(n+1))*reduceA[r-1, m0];

(*Case II*)
reduceB[r_Integer?NonNegative, n_Integer?NonNegative, 0, m0_, m1_] :=  1/(m0^2-m1^2)*(If[n==0,reduceA[r,m0],0]-(-1)^n reduceA[r,m1]-If[n==0,0,2n/(Dim+2r+2n-2) ((-1)^(n-1)reduceA[r,m1] + m0^2 reduceB[r,n-1,0,m0,m1])]);

(*Case I - complete reduction*)
(*reduceB[r_Integer?Positive, 0, s_, m0_, m1_] := 1/(2*(Dim+2r-3))*(reduceA[r-1,m1] + 2m0^2 reduceB[r-1,0,s,m0,m1]+(s-m1^2+m0^2)reduceB[r-1,1,s,m0,m1]);
reduceB[r_Integer?NonNegative,n_Integer?Positive,s_,m0_,m1_] := 1/(2s)*(If[n==1,reduceA[r,m0],0] + (-1)^n reduceA[r,m1] - (s-m1^2+m0^2)reduceB[r,n-1,s,m0,m1]-If[n==1,0,2*(n-1)reduceB[r+1,n-2,s,m0,m1]]);*)

(*Case I - incomplete reduction, leave as option*)
(*reduceB[r_Integer?Positive,n_Integer,s_,m0_,m1_] := -1/(2*(n+1))((-1)^(n+1) reduceA[r-1,m1] + (s-m1^2+m0^2) reduceB[r-1,n+1,s,m0,m1] + 2s reduceB[r-1,n+2,s,m0,m1]);*)


(*For r<0*)
reduceB[r_Integer?Negative,n_Integer,s_,m0_,m1_]/;!PossibleZeroQ[m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2] := 1/-(m0^4-2 m0^2 m1^2+m1^4-2 m0^2 s-2 m1^2 s+s^2)*(2s*(2(Dim+2r+n-1)*reduceB[r+1,n,s,m0,m1] - (-1)^n reduceA[r,m1]) + (-s+m1^2-m0^2)(If[n==0,reduceA[r,m0],0]-(-1)^n reduceA[r,m1] - If[n==0,0,2n*reduceB[r+1,n-1,s,m0,m1]]));
reduceB[r_Integer?Negative,n_Integer,s_,m0_,m1_] := 1/(4s*(Dim+2r+n-3))(2s (-1)^n reduceA[r-1,m1] +(s-m1^2+m0^2)(If[n==0,reduceA[r-1,m0],0] - (-1)^n reduceA[r-1,m1] - If[n==0,0,2*n*reduceB[r,n-1,s,m0,m1]]));


(* ::Subsection::Closed:: *)
(*C functions*)


(*Shifted B-functions; due to missing unshifted propagator; identical to pvBshift, but with immediate replacement*)
pvBs[r_Integer,n1_Integer,n2_Integer,q_,m1_,m2_]/;n1>n2 := pvBs[r,n2,n1,q,m2,m1];
pvBs[r_Integer,n1_Integer,n2_Integer,q_,m1_,m2_]        := (-1)^n1 Sum[Binomial[n1,idx]reduceB[r,n2+idx,q,m1,m2],{idx,0,n1}];


(*Define C-function reduction rules: 6 of them in total*)
Block[{
	n={n1,n2},
	f={p1-m1^2+m0^2,p2-m2^2+m0^2},

	gramZ={{p1,          -(q-p1-p2)/2},
    	  {-(q-p1-p2)/2,  p2}},

	detZ=-(p1^2-2 p1 p2+p2^2-2 p1 q-2 p2 q+q^2)/4,

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
	pinchB[r_,n1_]     = {reduceB[r,n1,p2,m0,m2],reduceB[r,n1,p1,m0,m1]};
	missBDivUV[r_,n1_] = {pvBDivUV[r,n1,p2,m0,m2],pvBDivUV[r,n1,p1,m0,m1]};


	(********Case6: All elements of gramZ is zero, AND f is zero********)
	reductionRulesCcase6={
	  passVeltC[r_?NonPositive,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/m0^2((Dim+2(n1+n2+r))passVeltC[r+1,n1,n2,p1,q,p2,m0,m1,m2]-pvBs[r,n1,n2,q,m1,m2]),
	  passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> -(1/(2(n1+1)))pvBs[r-1,n1+1,n2,q,m1,m2]
	};

	(********Case5: All elements of gramZ is zero, but f nonzero********)
	reductionRulesCcase5a=Table[passVeltC[r_?NonPositive, n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/f[[k]] (-2n[[k]]passVeltC[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],p1,q,p2,m0,m1,m2]+KroneckerDelta[n[[k]],0]pinchB[r,n[[not[k]]]][[k]]-pvBs[r,n1,n2,q,m1,m2]),{k,1,2}];
	reductionRulesCcase5b=passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/(Dim+2r+2n1+2n2-2)*(pvBs[r-1,n1,n2,q,m1,m2]+m0^2 passVeltC[r-1,n1,n2,p1,q,p2,m0,m1,m2]);

	(********Case4: Gram determinant and Cayley vectors vanishing; internal masses non-zero********)
	reductionRulesCcase4={passVeltC[r_,n1_,n2_,p_,p_,0,m0_,m1_,m0_]:>(-1)^(3+n1)/(2(n2+1)) Sum[Binomial[n1,k]reduceB[r-1,n2+k+1,p,m1,m0],{k,0,n1}],
	passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] :> With[{\[Alpha]=(-q+p1+p2)/(2p2)},(-1)^(n1+n2)/2 Sum[Binomial[n2,j]X`Private`pow[\[Alpha],n2-j]((n1!(n2-j)!)/(n1+n2-j+1)! Sum[Binomial[j,k](-1)^(j-k) X`Private`pow[\[Alpha],j-k](-1)^k reduceB[r-1,k,p2,m0,m2],{k,0,j}]+Sum[Pochhammer[-n1,k]/((n2-j+k+1)k!) ((1-\[Alpha])^(j+1) (-1)^(n2+k) reduceB[r-1,n2+k+1,q,m1,m2]+(-1)^(j+1) (\[Alpha])^(j+1) (-1)^(n2+k+1) reduceB[r-1,n2+k+1,p1,m1,m0]),{k,0,n1}]),{j,0,n2}]]};

	(********Case3: Gram determinant vanishing, but Cayley vectors X non-vanishing********)
	reductionRulesCcase3a=
	Table[
	  passVeltC[r_?Positive,0,0,p1_,q_,p2_,m0_,m1_,m2_] -> 
	    1/(Dim+2r-3)*(pvBs[r-1,0,0,q,m1,m2]+m0^2 passVeltC[r-1,0,0,p1,q,p2,m0,m1,m2])+
	    1/(2 (Dim+2r-3))*1/adjZ[[k,l]] Sum[(KroneckerDelta[k,mm]KroneckerDelta[nn,l]-KroneckerDelta[k,l]KroneckerDelta[mm,nn])(Sum[gramZ[[nn,j]]((1-KroneckerDelta[mm,j])pinchB[r-1,1][[mm]]-pvBs[r-1,KroneckerDelta[j,1],KroneckerDelta[j,2],q,m1,m2]),{j,1,2}]+1/2 f[[mm]](-pinchB[r-1,0][[nn]]+pvBs[r-1,0,0,q,m1,m2]+f[[nn]]passVeltC[r-1,0,0,p1,q,p2,m0,m1,m2])),{nn,1,2},{mm,1,2}],{k,1,2},{l,1,2}];
	reductionRulesCcase3b=
	Table[
	  passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> 1/adjX0[[j]]*
	    Sum[adjZ[[j,k]](KroneckerDelta[n[[k]],0]pinchB[r,n[[not[k]]]][[k]]-pvBs[r,n1,n2,q,m1,m2]-
	    2n[[k]]passVeltC[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],p1,q,p2,m0,m1,m2]),{k,1,2}],
	{j,1,2}];

	(********Reduction of triangle 1,4,5,6********)

	(*In this case, p1=q, q=p2, m2=m0 or (p1,m1)<-->(p2,m2).*)
	reductionRulesCtriangle6={
	  (*Permuted*)
	  passVeltC[r_,n1_,n2_,p1_,s_,p2_,0,m2_,m0_] /; PossibleZeroQ[p1-m2^2] && PossibleZeroQ[p2-m0^2] :> (-1)^n2/2 1/(n1+n2+2r+Dim-4) Sum[Binomial[n2,kdx]reduceB[r-1,n1+kdx,s,m0,m2],{kdx,0,n2}],

	  (*Nonpermuted*)
	  passVeltC[r_, n1_,n2_,p1_,q_,s_,m0_,0,m2_]|passVeltC[r_, n2_,n1_,s_,q_,p1_,m0_,m2_,0] /;PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] :> (-1)^n1/2 FunctionExpand[Beta[n2+Dim-4+2r,n1+1]] reduceB[r-1,n2,s,m0,m2]
	};

	(********Reduction of triangle 2,3********)
	reductionRulesCtriangle3 = {
	  (*Permuted*)
	  passVeltC[r_,n1_,n2_,p1_,0,p2_,m0_,0,0] :> Sum[(-1)^(n2)*(p1-p2)^(-1-n1-tdx)*Multinomial[sdx, n2 - sdx - tdx, tdx]*(-FunctionExpand[Gamma[r-(4-Dim)/2]/Gamma[(n1+tdx)+1+r-(4-Dim)/2]]*(n1+tdx)!/2*Sum[Binomial[(n1+tdx)+1,k]X`Private`pow[p2,k]X`Private`pow[p2-m0^2,(n1+tdx)+1-k]reduceB[r-1,sdx+k,p2,0,m0],{k,0,(n1+tdx)+1}]+Sum[(-1)^j/(2r+2j-(4-Dim)) Multinomial[j,k,(n1+tdx)-j-k]Binomial[j+1,l]X`Private`pow[p2,k]X`Private`pow[p1,l]X`Private`pow[p2-m0^2,(n1+tdx)-j-k]X`Private`pow[p1-m0^2,j+1-l]*reduceB[r-1,sdx+k+l,p1,0,m0],{j,0,(n1+tdx)},{k,0,(n1+tdx)-j},{l,0,j+1}]), {sdx, 0, n2}, {tdx, 0, n2 - sdx}],

	  (*Nonpermuted*)
	  passVeltC[r_,n1_,n2_,0,q_,p2_,0,0,m2_]|passVeltC[r_,n2_,n1_,p2_,q_,0,0,m2_,0] :> 
		1/(q-p2)^(n1+1) (-FunctionExpand[Gamma[r-(4-Dim)/2]/Gamma[n1+1+r-(4-Dim)/2]]*n1!/2*Sum[Binomial[n1+1,k]X`Private`pow[p2,k]X`Private`pow[p2-m2^2,n1+1-k]reduceB[r-1,n2+k,p2,0,m2],{k,0,n1+1}]+Sum[(-1)^j/(2r+2j-(4-Dim)) Multinomial[j,k,n1-j-k]Binomial[j+1,l]X`Private`pow[p2,k]X`Private`pow[q,l]X`Private`pow[p2-m2^2,n1-j-k]X`Private`pow[q-m2^2,j+1-l]*reduceB[r-1,n2+k+l,q,0,m2],{j,0,n1},{k,0,n1-j},{l,0,j+1}])
	};

	(********Case1: Gram determinant non-vanishing [most general] ********)
	(*In this case, PVC[n1,n2]/;n2>n1=PVC[n2,n1] is used.  See reduceC function.*)
	(*reductionRulesCcase1={
	  passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_]/; n2>n1 -> passVeltC[r,n2,n1,p2,q,p1,m0,m2,m1],
	  passVeltC[r_?Positive,0,0,p1_,q_,p2_,m0_,m1_,m2_] -> 
	    1/(2*(Dim-4+2*r))*(pvBs[r-1,0,0,q,m1,m2]+2m0^2 passVeltC[r-1,0,0,p1,q,p2,m0,m1,m2]+f[[1]] passVeltC[r-1,1,0,p1,q,p2,m0,m1,m2]+f[[2]] passVeltC[r-1,0,1,p1,q,p2,m0,m1,m2]),
	  passVeltC[r_,n1_?Positive,n2_,p1_,q_,p2_,m0_,m1_,m2_] ->
	    1/(2*detZ) Sum[adjZ[[1,j]]*(KroneckerDelta[n[[j]]-KroneckerDelta[1,j],0]pinchB[r,n[[not[j]]]-KroneckerDelta[not[j],1]][[j]]-
	    pvBs[r,n1-1,n2,q,m1,m2]-f[[j]]passVeltC[r,n1-1,n2,p1,q,p2,m0,m1,m2]-2(n[[j]]-KroneckerDelta[1,j])passVeltC[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,p2,m0,m1,m2]),{j,1,2}]
	};*)
	reductionRulesCcase1={
	  passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_]/; n2>n1 -> passVeltC[r,n2,n1,p2,q,p1,m0,m2,m1],
	  passVeltC[r_?Positive,0,0,p1_,q_,p2_,m0_,m1_,m2_] -> 
	    1/(2*(Dim-4+2*r))*(pvBs[r-1,0,0,q,m1,m2]+2m0^2 passVeltC[r-1,0,0,p1,q,p2,m0,m1,m2]+f[[1]] passVeltC[r-1,1,0,p1,q,p2,m0,m1,m2]+f[[2]] passVeltC[r-1,0,1,p1,q,p2,m0,m1,m2]),
	  passVeltC[r_,n1_?Positive,n2_,p1_,q_,p2_,m0_,m1_,m2_] ->
	    1/(2*detZ) Sum[adjZ[[1,j]]*(If[n[[j]]-KroneckerDelta[1,j]==0,Evaluate[pinchB[r,n[[not[j]]]-KroneckerDelta[not[j],1]][[j]]],0]-
	    pvBs[r,n1-1,n2,q,m1,m2]-f[[j]]passVeltC[r,n1-1,n2,p1,q,p2,m0,m1,m2]-If[n[[j]]-KroneckerDelta[1,j]==0,0,Evaluate[2(n[[j]]-KroneckerDelta[1,j])passVeltC[r+1,n1-1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,p2,m0,m1,m2]]]),{j,1,2}]
	};

	(****Reduction formulae for negative rank r<0*****)
	reductionRulesCnegativer = Prepend[reductionRulesCcase1, passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] /; r<0 -> 1/detX * (4*detZ*(2(Dim-2+n1+n2+2r)*passVeltC[r+1,n1,n2,p1,q,p2,m0,m1,m2]-pvBs[r,n1,n2,q,m1,m2]) + Sum[-2*adjX0[[j]]*(KroneckerDelta[n[[j]],0]*pinchB[r,n[[not[j]]]][[j]] - pvBs[r,n1,n2,q,m1,m2] - 2*n[[j]]*passVeltC[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],p1,q,p2,m0,m1,m2]),{j,1,2}])];

	reductionRulesCnegativerDetX = passVeltC[r_,n1_,n2_,p1_,q_,p2_,m0_,m1_,m2_] -> -1/(8*(Dim-2+n1+n2+2(r-1) detZ)) Sum[adjX0[[jdx]] (If[n[[jdx]]==0,Evaluate[pinchB[r-1,n[[not[jdx]]]][[jdx]]],0] - pvBs[r-1,n1,n2,q,m1,m2] - If[n[[jdx]]==0,0,Evaluate[2 n[[jdx]] passVeltC[r,n1-KroneckerDelta[jdx,1],n2-KroneckerDelta[jdx,2],p1,q,p2,m0,m1,m2]]]),{jdx,1,2}];

];


Options[reduceC]:={"IRDivCToB"->False};
reduceC[r_Integer,n1_Integer,n2_Integer,p1_,q_,p2_,m0_,m1_,m2_, OptionsPattern[]] :=
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
      ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],reductionRulesCcase6],

    X`Internal`PossibleAllZeroQ[gramZ] && !(X`Internal`PossibleAllZeroQ[f]),
    (*Print["Case 5: gramZ vanishing but f non-vanishing."];*)
      With[{siga=Which[!PossibleZeroQ[f[[1]]],1,True,2]},
        ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],{reductionRulesCcase5a[[siga]],reductionRulesCcase5b}]
      ],
  
    PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0],
    (*Print["Case 4: detZ and adjX0 are zero"];*)
      Replace[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],reductionRulesCcase4],
    
    PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3: detZ=0"];*)
      With[{
        siga=Which[!PossibleZeroQ[adjZ[[1,1]]],{1,1},!PossibleZeroQ[adjZ[[2,2]]],{2,2},True,{1,2}],
        sigb=Which[!PossibleZeroQ[adjX0[[1]]],1,True,2]},
        (*Print["siga=",siga,"  sigb=",sigb, "adjZ = ", adjZ];*)
        passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2] = ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],{reductionRulesCcase3a[[Sequence@@siga]],reductionRulesCcase3b[[sigb]]}]
      ],

	OptionValue["IRDivCToB"] && 
    ((PossibleZeroQ[p1-m0^2] && PossibleZeroQ[q-m2^2] && PossibleZeroQ[m1]) (*(p1===m0^2 && q===m2^2 && m1===0)*) (* p2 may or may not vanish*)
     || (PossibleZeroQ[p2-m0^2] && PossibleZeroQ[q-m1^2] && PossibleZeroQ[m2]) (*(p2===m0^2 && q===m1^2  && m2===0)*) (* p1 may or may not vanish*)
     || (PossibleZeroQ[p1-m1^2] && PossibleZeroQ[p2-m2^2] && PossibleZeroQ[m0]) (*(p1===m1^2 && p2===m2^2  && m0===0)*) (* q may or may not vanish*)),
    (*Print["Case 2: Triangle 6"];*)
    Replace[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],reductionRulesCtriangle6],

	OptionValue["IRDivCToB"] && 
	((PossibleZeroQ[q] && PossibleZeroQ[m2] && PossibleZeroQ[m1]) (*(q===0 && m2===0 && m1===0)*)
	 || (PossibleZeroQ[p1] && PossibleZeroQ[m1] && PossibleZeroQ[m0]) (*(p1===0 && m1===0 && m0===0)*)
	 || (PossibleZeroQ[p2] && PossibleZeroQ[m2] && PossibleZeroQ[m0]) (*(p2===0 && m2===0 && m0===0)*)),
	(*Print["PVC for triangle 2 & 3"];*)
	Replace[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],reductionRulesCtriangle3],


    Positive[r](* && !(PossibleZeroQ[Det[gramZ]])*) || r===0 && PossibleZeroQ[Det[Xij]],
    (*Print["Case 1: detZ nonZero; r=", r];*)
    ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],reductionRulesCcase1],

  
	NonPositive[r] && !(PossibleZeroQ[Det[Xij]]),
	(*Print["PVC for r<0: Det[X]!=0"];*)
	ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],reductionRulesCnegativer],


    True,
	(*Print["PVC for r<0: Det[X]=0"];*)
	ReplaceRepeated[passVeltC[r,n1,n2,p1,q,p2,m0,m1,m2],reductionRulesCnegativerDetX]

  ]
]


(* ::Subsection::Closed:: *)
(*D Functions*)


(*Shifted C-functions; due to unshifted pinched propagator*)
pvCs[r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_]/;(n3 < n1 && n3 < n2) := pvCs[r,n3,n2,n1,s3,s2,s23,m3,m2,m1];
pvCs[r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_]/;(n2 < n1 && n2 < n3) := pvCs[r,n2,n1,n3,s2,s23,s3,m2,m1,m3];
pvCs[r_Integer,n1_Integer,n2_Integer,n3_Integer,s2_,s3_,s23_,m1_,m2_,m3_] := (-1)^n1 Sum[Multinomial[idx1,idx2,n1-idx1-idx2]reduceC[r,n2+idx2,n1+n3-idx1-idx2,s2,s3,s23,m1,m2,m3],{idx1,0,n1},{idx2,0,n1-idx1}];


(*Define D-function reduction rules*)
Block[{
	n={n1, n2, n3},
	f={s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},

	gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }},

	detZ = 1/4 * (-s1 s12 s2+s1 s12 s23-s12^2 s23+s12 s2 s23-s12 s23^2-s1^2 s3+s1 s12 s3+s1 s2 s3+s1 s23 s3+s12 s23 s3-s2 s23 s3-s1 s3^2+s1 s2 s4+s12 s2 s4-s2^2 s4-s1 s23 s4+s12 s23 s4+s2 s23 s4+s1 s3 s4-s12 s3 s4+s2 s3 s4-s2 s4^2),

	adjZ={{1/4 (-s12^2+2 s12 s3-s3^2+2 s12 s4+2 s3 s4-s4^2),1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4))},{1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),1/4 (-s1^2+2 s1 s23-s23^2+2 s1 s4+2 s23 s4-s4^2),1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4))},{1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4)),1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4)),1/4 (-s1^2+2 s1 s12-s12^2+2 s1 s2+2 s12 s2-s2^2)}},

	mtxX=({{2*m0^2,        s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
		   {s1-m1^2+m0^2,  2*s1,         s1+s12-s2,     s1-s23+s4},
		   {s12-m2^2+m0^2, s1+s12-s2,    2*s12,         s12-s3+s4},
		   {s4-m3^2+m0^2,  s1-s23+s4,    s12-s3+s4,     2*s4}}),

    adjadjZ = {{{{0,0,0},{0,0,0},{0,0,0}},{{0,-s4,1/2 (s12-s3+s4)},{s4,0,1/2 (-s1+s23-s4)},{1/2 (-s12+s3-s4),1/2 (s1-s23+s4),0}},{{0,1/2 (s12-s3+s4),-s12},{1/2 (-s12+s3-s4),0,1/2 (s1+s12-s2)},{s12,1/2 (-s1-s12+s2),0}}},{{{0,s4,1/2 (-s12+s3-s4)},{-s4,0,1/2 (s1-s23+s4)},{1/2 (s12-s3+s4),1/2 (-s1+s23-s4),0}},{{0,0,0},{0,0,0},{0,0,0}},{{0,1/2 (-s1+s23-s4),1/2 (s1+s12-s2)},{1/2 (s1-s23+s4),0,-s1},{1/2 (-s1-s12+s2),s1,0}}},{{{0,1/2 (-s12+s3-s4),s12},{1/2 (s12-s3+s4),0,1/2 (-s1-s12+s2)},{-s12,1/2 (s1+s12-s2),0}},{{0,1/2 (s1-s23+s4),1/2 (-s1-s12+s2)},{1/2 (-s1+s23-s4),0,s1},{1/2 (s1+s12-s2),-s1,0}},{{0,0,0},{0,0,0},{0,0,0}}}},
	adjX0, 
	adjXij = {{2 (-m0^4 s3-m2^4 s4-s12 (m3^4+m3^2 (s12-s3-s4)+s3 s4)+m2^2 ((s12+s3-s4) s4+m3^2 (s12-s3+s4))+m0^2 (m3^2 (s12+s3-s4)+s3 (s12-s3+s4)+m2^2 (-s12+s3+s4))),-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s12-s3+s4) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4)),(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4)-2 s12 (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))+(m0^2-m2^2+s12) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m2^2+s12) (s1-s23+s4))},{-2 (-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) s4+(s1-s23+s4) (-(m0^2-m2^2+s12) (m0^2-m3^2+s4)+2 m0^2 (s12-s3+s4))-(m0^2-m3^2+s4) (-(s1+s12-s2) (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s12-s3+s4)),2 (-m0^4 s23-m1^4 s4-s1 (m3^4+m3^2 (s1-s23-s4)+s23 s4)+m1^2 ((s1+s23-s4) s4+m3^2 (s1-s23+s4))+m0^2 (m3^2 (s1+s23-s4)+s23 (s1-s23+s4)+m1^2 (-s1+s23+s4))),-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4)+(s1+s12-s2) (-(m0^2-m1^2+s1) (m0^2-m3^2+s4)+2 m0^2 (s1-s23+s4))-(m0^2-m2^2+s12) (-2 s1 (m0^2-m3^2+s4)+(m0^2-m1^2+s1) (s1-s23+s4))},{(2 (m0^2-m1^2+s1) s12-(m0^2-m2^2+s12) (s1+s12-s2)) (m0^2-m3^2+s4)-(4 m0^2 s12-(m0^2-m2^2+s12)^2) (s1-s23+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s12-s3+s4),-(-2 s1 (m0^2-m2^2+s12)+(m0^2-m1^2+s1) (s1+s12-s2)) (m0^2-m3^2+s4)+(-(m0^2-m1^2+s1) (m0^2-m2^2+s12)+2 m0^2 (s1+s12-s2)) (s1-s23+s4)-(4 m0^2 s1-(m0^2-m1^2+s1)^2) (s12-s3+s4),2 (-m1^4 s12-m0^4 s2-s1 (m2^4+m2^2 (s1-s12-s2)+s12 s2)+m1^2 (m2^2 (s1+s12-s2)+s12 (s1-s12+s2))+m0^2 ((s1+s12-s2) s2+m2^2 (s1-s12+s2)+m1^2 (-s1+s12+s2)))}},
	pinchC,
	nk,kp,
	i, j, k, ndx,mdx},



	nk[idx_,cnc_] = Which[idx<cnc, n[[idx]], idx>=cnc, n[[idx+1]]]; (*This is n_{idx(cnc)}*)
	kp[idx_,cnc_] = Which[idx<cnc, idx, idx>=cnc, idx+1]; (*this is just idx(cnc)*)

	adjX0=Expand[Table[Sum[adjZ[[j,k]]f[[k]],{k,1,3}],{j,1,3}]]; (*up to a constant: -4*)

	(*Passarino Veltman functions with pinched propagators, and their divergent parts*)
	pinchC[r_,n1_,n2_]  =    {reduceC[r,n1,n2,s12,s3,s4,m0,m2,m3], reduceC[r,n1,n2,s1,s23,s4,m0,m1,m3], reduceC[r,n1,n2,s1,s2,s12,m0,m1,m2]};

	(********Case6: All elements of gramZ is zero, AND all f are zero********)
	reductionRulesDcase6={
	  passVeltD[r_?NonPositive,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/m0^2 ((Dim+2(r+n1+n2+n3))passVeltD[r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]),
	  passVeltD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> -(1/(2(n1+1)))pvCs[r-1,n1+1,n2,n3,s2,s3,s23,m1,m2,m3]
	};

	(********Case5: All elements of gramZ is zero, but f nonzero********)
	reductionRulesDcase5a=Table[passVeltD[r_?NonPositive,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/f[[k]] (-2n[[k]]passVeltD[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+KroneckerDelta[n[[k]],0]pinchC[r,nk[1,k],nk[2,k]][[k]]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]),{k,1,3}];
	reductionRulesDcase5b = passVeltD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/(Dim-2+2r+2n1+2n2+2n3)*(pvCs[r-1,n1,n2,n3,s2,s3,s23,m1,m2,m3]+m0^2 passVeltD[r-1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]);

	(********Case4: Gram determinant and Cayley vectors X vanishing********)
	reductionRulesDcase4a=
	Flatten[Table[passVeltD[r_?Positive, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/(2(n[[k]]+1)adjZ[[j,k]]) (-2*Sum[adjZ[[j,mdx]]*n[[mdx]]*passVeltD[r,n1-KroneckerDelta[mdx,1]+KroneckerDelta[k,1],n2-KroneckerDelta[mdx,2]+KroneckerDelta[k,2],n3-KroneckerDelta[mdx,3]+KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{mdx,Complement[Range[1,3],{k}]}]+Sum[adjZ[[j,l]](KroneckerDelta[n[[l]]+KroneckerDelta[k,l],0]*pinchC[r-1,nk[1,l]+KroneckerDelta[kp[1,l],k],nk[2,l]+KroneckerDelta[kp[2,l],k]][[l]]-pvCs[r-1,n1+KroneckerDelta[k,1],n2+KroneckerDelta[k,2],n3+KroneckerDelta[k,3],s2,s3,s23,m1,m2,m3]),{l,1,3}])
		,{j,1,3},{k,1,3}]];
	reductionRulesDcase4b=
	Flatten[Table[passVeltD[r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 4*adjZ[[i,k]]/adjXij[[i,k]]*(2(Dim-3+2r+n1+n2+n3)passVeltD[r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3])+2/adjXij[[i,k]]*Sum[f[[ndx]]*adjadjZ[[ndx,i,j,k]]*(KroneckerDelta[n[[j]],0]*pinchC[r,nk[1,j],nk[2,j]][[j]]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]-2n[[j]]*passVeltD[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],n3-KroneckerDelta[j,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{j,1,3},{ndx,1,3}]
		,{i,1,3},{k,1,3}]];

	(********Exceptional Case: All adjZ vanishing (doesn't matter if adjZ vanishes)********)
	(*Subcase 3: If s1=0, m0!=m2*)
	reductionRulesDcaseX3=passVeltD[r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> (-2^n2 n2!)/(m2^2-m0^2)^(n2+1) reduceC[r+n2,n1,n3,s1,s23,s4,m0,m1,m3]+Sum[((-1)^(1+jdx+n2) 2^(jdx+kdx))/(m2^2-m0^2)^(jdx+kdx+1) Multinomial[jdx,kdx,ldx1,ldx2,n2-jdx-kdx-ldx1-ldx2](FunctionExpand[Gamma[2+(4-Dim)/2-r]/(Gamma[-1+r+jdx-(4-Dim)/2]Gamma[1+(4-Dim)/2-r-jdx-kdx])]reduceC[r+jdx+kdx,n1+ldx1,n3+ldx2,s2,s23,s3,m2,m1,m3]),{jdx,0,n2},{kdx,0,n2-jdx},{ldx1,0,n2-jdx-kdx},{ldx2,0,n2-jdx-kdx-ldx1}];
	(*Subcase 4: If s1=0, m0=m2*)
	reductionRulesDcaseX4=passVeltD[r_, n1_, n2_, n3_, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> (-1)^n2/(2(n2+1)) Sum[Multinomial[j,k,n2+1-j-k]*reduceC[r-1,n1+j,n3+k,s1,s23,s4,m0,m1,m3],{j,0,n2+1},{k,0,n2+1-j}];

	(********Case3: Gram determinant vanishing, but Cayley vectors X non-vanishing********)
	(*reductionRulesDcase3a=
	Flatten[Table[
	  passVeltD[r_?Positive,0, 0, 0, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 
	    1/(2r+Dim-4)*(pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+m0^2 passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]) +
	    1/(2*(2r+Dim-4))*1/adjZ[[k,l]] Sum[adjadjZ[[k,ndx,l,mdx]](Sum[gramZ[[ndx,j]]((1-KroneckerDelta[mdx,j])pinchC[r-1,KroneckerDelta[kp[1,mdx],j],KroneckerDelta[kp[2,mdx],j]][[mdx]]-pvCs[r-1,KroneckerDelta[j,1],KroneckerDelta[j,2],KroneckerDelta[j,3],s2,s3,s23,m1,m2,m3]),{j,1,3}]+1/2 f[[mdx]](-pinchC[r-1,0,0][[ndx]]+pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+f[[ndx]]passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])),{ndx,1,3},{mdx,1,3}] 
	  ,{k,1,3},{l,1,3}]];
	reductionRulesDcase3b=
	Table[
	  passVeltD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/adjX0[[j]]*
	    Sum[adjZ[[j,k]](KroneckerDelta[n[[k]],0]pinchC[r,nk[1,k],nk[2,k]][[k]]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]-
	    2n[[k]]passVeltD[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{k,1,3}],
	{j,1,3}];*)
	reductionRulesDcase3a=
	Flatten[Table[
	  passVeltD[r_?Positive,0, 0, 0, s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 
	    1/(2r+Dim-4)*(pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+m0^2 passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]) +
	    1/(2*(2r+Dim-4))*1/adjZ[[k,l]] Sum[adjadjZ[[k,ndx,l,mdx]](Sum[gramZ[[ndx,j]](If[mdx==j,0,Evaluate[pinchC[r-1,KroneckerDelta[kp[1,mdx],j],KroneckerDelta[kp[2,mdx],j]][[mdx]]]]-pvCs[r-1,KroneckerDelta[j,1],KroneckerDelta[j,2],KroneckerDelta[j,3],s2,s3,s23,m1,m2,m3]),{j,1,3}]+1/2 f[[mdx]](-pinchC[r-1,0,0][[ndx]]+pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+f[[ndx]]passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3])),{ndx,1,3},{mdx,1,3}] 
	  ,{k,1,3},{l,1,3}]];
	reductionRulesDcase3b=
	Table[
	  passVeltD[r_,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/adjX0[[j]]*
	    Sum[adjZ[[j,k]](If[n[[k]]==0,Evaluate[pinchC[r,nk[1,k],nk[2,k]][[k]]],0]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]-
	    If[n[[k]]==0,0,Evaluate[2n[[k]]passVeltD[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]]]),{k,1,3}],
	{j,1,3}];

	(********Case1: Gram determinant non-vanishing [most general] ********)
	(*reductionRulesDcase1={
	  passVeltD[r_?Positive, 0,  0,  0 ,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]-> 
	    1/(2*(Dim+2(r-1)-3))*(pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+2m0^2 passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[1]] passVeltD[r-1,1,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[2]] passVeltD[r-1,0,1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[3]] passVeltD[r-1,0,0,1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),
	  passVeltD[r_,n1_?Positive,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[1,k]]*(KroneckerDelta[n[[k]]-KroneckerDelta[1,k],0]pinchC[r,nk[1,k]-(1-KroneckerDelta[k,1]),nk[2,k]][[k]]-
	    pvCs[r,n1-1,n2,n3,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1-1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-2(n[[k]]-KroneckerDelta[1,k])passVeltD[r+1,n1-1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{k,1,3}],
	  passVeltD[r_,n1_,n2_?Positive,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[2,k]]*(KroneckerDelta[n[[k]]-KroneckerDelta[2,k],0]pinchC[r,nk[1,k]-KroneckerDelta[k,1],nk[2,k]-KroneckerDelta[k,3]][[k]]-
	    pvCs[r,n1,n2-1,n3,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1,n2-1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-2(n[[k]]-KroneckerDelta[2,k])passVeltD[r+1,n1-KroneckerDelta[k,1],n2-1-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{k,1,3}],
	  passVeltD[r_,n1_,n2_,n3_?Positive,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[3,k]]*(KroneckerDelta[n[[k]]-KroneckerDelta[3,k],0]pinchC[r,nk[1,k],nk[2,k]-(1-KroneckerDelta[k,3])][[k]]-
	    pvCs[r,n1,n2,n3-1,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1,n2,n3-1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-2(n[[k]]-KroneckerDelta[3,k])passVeltD[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-1-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{k,1,3}]
	};*)
	reductionRulesDcase1={
	  passVeltD[r_?Positive, 0, 0, 0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]-> 
	    1/(2*(Dim+2(r-1)-3))*(pvCs[r-1,0,0,0,s2,s3,s23,m1,m2,m3]+2m0^2 passVeltD[r-1,0,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[1]] passVeltD[r-1,1,0,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[2]] passVeltD[r-1,0,1,0,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]+f[[3]] passVeltD[r-1,0,0,1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),
	  passVeltD[r_,n1_?Positive,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[1,k]]*(If[n[[k]]-KroneckerDelta[1,k]==0,Evaluate[pinchC[r,nk[1,k]-(1-KroneckerDelta[k,1]),nk[2,k]][[k]]],0]-
	    pvCs[r,n1-1,n2,n3,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1-1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-2(n[[k]]-KroneckerDelta[1,k])passVeltD[r+1,n1-1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{k,1,3}],
	  passVeltD[r_,n1_,n2_?Positive,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[2,k]]*(If[n[[k]]-KroneckerDelta[2,k]==0,Evaluate[pinchC[r,nk[1,k]-KroneckerDelta[k,1],nk[2,k]-KroneckerDelta[k,3]][[k]]],0]-
	    pvCs[r,n1,n2-1,n3,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1,n2-1,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-2(n[[k]]-KroneckerDelta[2,k])passVeltD[r+1,n1-KroneckerDelta[k,1],n2-1-KroneckerDelta[k,2],n3-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{k,1,3}],
	  passVeltD[r_,n1_,n2_,n3_?Positive,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] ->
	    1/(2*detZ) Sum[adjZ[[3,k]]*(If[n[[k]]-KroneckerDelta[3,k]==0,Evaluate[pinchC[r,nk[1,k],nk[2,k]-(1-KroneckerDelta[k,3])][[k]]],0]-
	    pvCs[r,n1,n2,n3-1,s2,s3,s23,m1,m2,m3]-f[[k]]passVeltD[r,n1,n2,n3-1,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-2(n[[k]]-KroneckerDelta[3,k])passVeltD[r+1,n1-KroneckerDelta[k,1],n2-KroneckerDelta[k,2],n3-1-KroneckerDelta[k,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{k,1,3}]
	};

	(****Reduction formulae for negative rank r<0*****)
	reductionRulesDnegativerCase1 = 
	  Join[
		{passVeltD[0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] :> With[{body=analD0IR[s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]},body/; Head[body]=!=analD0IR],
		 passVeltD[r_?Negative,n1_,n2_,n3_,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_] -> 1/Det[mtxX] * (8*detZ*(2(Dim-3+n1+n2+n3+2r)*passVeltD[r+1,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]-pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3]) + Sum[-4*adjX0[[j]]*(KroneckerDelta[n[[j]],0]*pinchC[r,nk[1,j],nk[2,j]][[j]] - pvCs[r,n1,n2,n3,s2,s3,s23,m1,m2,m3] - 2*n[[j]]*passVeltD[r+1,n1-KroneckerDelta[j,1],n2-KroneckerDelta[j,2],n3-KroneckerDelta[j,3],s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]),{j,1,3}])},
	     reductionRulesDcase1]

];


reduceD[r_Integer,n1_Integer,n2_Integer,n3_Integer,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]:=
  Module[{
    f={s1-m1^2+m0^2, s12-m2^2+m0^2, s4-m3^2+m0^2},
    gramZ={{  s1,        (s1+s12-s2)/2, (s1-s23+s4)/2},
    	  {(s1+s12-s2)/2,    s12,       (s12-s3+s4)/2},
    	  {(s1-s23+s4)/2, (s12-s3+s4)/2,    s4      }},
    adjZ={{s12 s4-1/4 (s12-s3+s4)^2,1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4))},{1/4 (-2 (s1+s12-s2) s4+(s1-s23+s4) (s12-s3+s4)),s1 s4-1/4 (s1-s23+s4)^2,1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4))},{1/4 (-2 s12 (s1-s23+s4)+(s1+s12-s2) (s12-s3+s4)),1/4 ((s1+s12-s2) (s1-s23+s4)-2 s1 (s12-s3+s4)),s1 s12-1/4 (s1+s12-s2)^2}},
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
      ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],reductionRulesDcase6],

    X`Internal`PossibleAllZeroQ[gramZ] && !(X`Internal`PossibleAllZeroQ[f]),
    (*Print["Case 5: gramZ vanishing but f non-vanishing.  f=", f];*)
      With[{siga=First@Ordering[f,1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
		(*Print["f=", f, "  sig:", siga];*)
        ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{reductionRulesDcase5a[[siga]],reductionRulesDcase5b}]
      ],
  
	(*Can handle PVD[0,0,0,0,m^2,m^2,m^2,m^2,4m^2,0,m,0,m,0]*)
	PossibleZeroQ[s12] && PossibleZeroQ[s3-s4] && PossibleZeroQ[s1-s2],
	  Replace[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],
		If[PossibleZeroQ[m0-m2],reductionRulesDcaseX4,reductionRulesDcaseX3]],

	PossibleZeroQ[s23] && PossibleZeroQ[s3-s2] && PossibleZeroQ[s1-s4],
	  Replace[Sum[(-1)^n3*Multinomial[k1,k2,k3,n3-k1-k2-k3]*passVeltD[r,n2+k2,n1+k1,k3,s3,s2,s1,s4,s23,s12,m3,m2,m1,m0],{k1,0,n3},{k2,0,n3-k1},{k3,0,n3-k2-k1}],
		If[PossibleZeroQ[m3-m1],reductionRulesDcaseX4,reductionRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s1] && PossibleZeroQ[s23-s4] && PossibleZeroQ[s12-s2],
	  Replace[passVeltD[r,n2,n1,n3,s12,s2,s23,s4,s1,s3,m0,m2,m1,m3],
		If[PossibleZeroQ[m0-m1],reductionRulesDcaseX4,reductionRulesDcaseX3]],

	PossibleZeroQ[s2] && PossibleZeroQ[s1-s12] && PossibleZeroQ[s3-s23],
	  Replace[Sum[(-1)^n1*Multinomial[k1,k2,k3,n1-k1-k2-k3]*passVeltD[r,k1,n2+k2,n3+k3,s1,s12,s3,s23,s2,s4,m1,m0,m2,m3],{k1,0,n1},{k2,0,n1-k1},{k3,0,n1-k2-k1}],
		If[PossibleZeroQ[m1-m2],reductionRulesDcaseX4,reductionRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s3] && PossibleZeroQ[s23-s2] && PossibleZeroQ[s12-s4],
	  Replace[Sum[(-1)^n3*Multinomial[k1,k2,k3,n3-k1-k2-k3]*passVeltD[r,n1+k1,n2+k2,k3,s23,s2,s12,s4,s3,s1,m3,m1,m2,m0],{k1,0,n3},{k2,0,n3-k1},{k3,0,n3-k2-k1}],
		If[PossibleZeroQ[m3-m2],reductionRulesDcaseX4,reductionRulesDcaseX3],{0,Infinity}],

	PossibleZeroQ[s4] && PossibleZeroQ[s1-s23] && PossibleZeroQ[s3-s12],
	  Replace[passVeltD[r,n1,n3,n2,s1,s23,s3,s12,s4,s2,m0,m1,m3,m2],
		If[PossibleZeroQ[m0-m3],reductionRulesDcaseX4,reductionRulesDcaseX3]],

	PossibleZeroQ[Det[gramZ]] && X`Internal`PossibleAllZeroQ[adjX0] && !(X`Internal`PossibleAllZeroQ[adjZ]) && !(X`Internal`PossibleAllZeroQ[adjXij]),
	(*Print["Case 4 PVD: det Z=0, adjX0=0"];*)
	  With[{siga=First@Ordering[Flatten[Simplify[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
			sigb=First@Ordering[Flatten[Simplify[adjXij]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
			(*Print["adjZ=", adjZ, "  sig:", siga];*)
			(*Print["adjXij=", adjXij, "  sig:", sigb];*)
			ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{reductionRulesDcase4a[[siga]],reductionRulesDcase4b[[sigb]]}]
	  ],
    
    PossibleZeroQ[Det[gramZ]] && !(X`Internal`PossibleAllZeroQ[adjX0]),
    (*Print["Case 3 PVD: detZ=0 && one of adjX0 nonzero."];*)
      With[{
        siga=First@Ordering[Flatten[Simplify[adjZ]],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&],
        sigb=First@Ordering[Simplify[adjX0],1,If[PossibleZeroQ[#1],Infinity,LeafCount[#1]]<If[PossibleZeroQ[#2],Infinity,LeafCount[#2]]&]},
        (*Print["adjZ=", adjZ, "  sig:", siga];*)
		(*Print["adjX0=", adjX0, "  sig:", sigb];*)
        (*passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = *)ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],{reductionRulesDcase3a[[siga]],reductionRulesDcase3b[[sigb]]}]
      ],

    Positive[r] && !(PossibleZeroQ[Det[gramZ]]),
    (*Print["Case 1:, DetZ=", Det[gramZ],",  adjZ=", MatrixForm[adjZ],";  adjXij=", adjXij];*)
    (*passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = *)ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],reductionRulesDcase1] ,

	NonPositive[r] && !PossibleZeroQ[Det[mtxX]],
	(*Print["PVD r<=0: Det[X]!=0"];*)
	(*passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3] = *)ReplaceRepeated[passVeltD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3],reductionRulesDnegativerCase1] ,  

    True,
	Message[PVReduce::leadinglandau, PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]];

	PVD[r,n1,n2,n3,s1,s2,s3,s4,s12,s23,m0,m1,m2,m3]
  ]
 
]


(* ::Subsection:: *)
(*PVReduce*)


(* ::Subsubsection::Closed:: *)
(*Internal PVReduce*)


(****** All ******)

Options[internalPVReduce]:=Options[PVReduce];
internalPVReduce[tensorStructures_, OptionsPattern[]] =
Function[{expr},
  Module[{answer},Internal`InheritedBlock[{reduceA, reduceB, reduceC, passVeltC, reduceD, passVeltD},

	answer=Collect[X`Utilities`PVNormal[expr], {_PVA,_PVB,_PVC,_PVD}, Together];

	answer=If[Head[answer]===Plus, List@@answer, List@answer];

	If[OptionValue["IRDivBToA"],
	  reduceB[r_Integer, n_Integer, s_, 0, m1_] /; PossibleZeroQ[s-m1^2] := (-1)^(1+r+n)/2^r FunctionExpand[Gamma[2-Dim/2-r]/Gamma[1-Dim/2]] (m1^2)^(r-1)/ (Dim-3+2r+n) reduceA[0,m1];
	  reduceB[r_Integer, n_Integer, s_, m0_, 0] /; PossibleZeroQ[s-m0^2] := (-1)^(1+r+n)/2^r FunctionExpand[Gamma[2-Dim/2-r]/Gamma[1-Dim/2]*Beta[n+1,-3+Dim+2r]] (m0^2)^(r-1) reduceA[0,m0];
	];

	If[
	  OptionValue["BnToB0"],
	  (*Complete reduction, by Passarino-Veltman.  Case I:  p^2 =!= 0*)
	  (*Other cases are above*)
	  reduceB[r_Integer?Positive, 0, s_, m0_, m1_] := 1/(2*(Dim+2r-3))*(reduceA[r-1,m1] + 2m0^2 reduceB[r-1,0,s,m0,m1]+(s-m1^2+m0^2)reduceB[r-1,1,s,m0,m1]);
	  reduceB[r_Integer?NonNegative,n_Integer?Positive,s_,m0_,m1_] := 1/(2s)*(If[n==1,reduceA[r,m0],0] + (-1)^n reduceA[r,m1] - (s-m1^2+m0^2)reduceB[r,n-1,s,m0,m1]-If[n==1,0,2*(n-1)reduceB[r+1,n-2,s,m0,m1]])
	  ,
	  If[OptionValue["B00ReductionMethod"]==="Recursive",
		(*Recursive, by Denner-Dittmaier*)
		reduceB[r_Integer?Positive,n_Integer,s_,m0_,m1_] := -1/(2*(n+1))((-1)^(n+1) reduceA[r-1,m1] + (s-m1^2+m0^2) reduceB[r-1,n+1,s,m0,m1] + 2s reduceB[r-1,n+2,s,m0,m1]),
		(*Iterative, by Patel*)
		reduceB[r_Integer?Positive,n_Integer,s_,m0_,m1_] := FunctionExpand[Gamma[(4-Dim)/2-r]/Gamma[(4-Dim)/2]]/2^r*Sum[(-1)^(r+k) Multinomial[j,k,r-j-k]X`Private`pow[s,j]X`Private`pow[-s+m1^2-m0^2,k]X`Private`pow[m0^2,r-j-k]reduceB[0,n+2j+k,s,m0,m1],{j,0,r},{k,0,r-j}]
	  ]
	];

	SetOptions[reduceC,"IRDivCToB"->OptionValue["IRDivCToB"]];

	If[OptionValue["EliminateScalelessPV"],
	  reduceA[_,0] := 0;
	  reduceB[_,_,0,0,0] := 0;
	  reduceC[_,_,_,0,0,0,0,0,0,OptionsPattern[]] := 0;
	  passVeltC[_,_,_,0,0,0,0,0,0] := 0;
	  reduceD[_,_,_,_,0,0,0,0,0,0,0,0,0,0] := 0;
	  passVeltD[_,_,_,_,0,0,0,0,0,0,0,0,0,0] := 0;
	];

	answer = answer/.{
	  PVD[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,n3_Integer?NonNegative,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]?X`Private`exactExpressionQ:>
		reduceD[r,n1,n2,n3,Simplify[s1],Simplify[s2],Simplify[s3],Simplify[s4],Simplify[s12],Simplify[s23],m0,m1,m2,m3],
	  PVC[r_Integer,n1_Integer?NonNegative,n2_Integer?NonNegative,p1_,q_,p2_,m0_,m1_,m2_]?X`Private`exactExpressionQ:>
		reduceC[r,n1,n2,Simplify[p1],Simplify[q],Simplify[p2],m0,m1,m2],
	  PVB[r_Integer,n_Integer?NonNegative,s_,m0_,m1_]?X`Private`exactExpressionQ:>
		reduceB[r,n,Simplify[s],m0,m1],
	  PVA[r_Integer,m0_]?X`Private`exactExpressionQ:>
		reduceA[r,m0]};

	(*Convert scalar passVelt functions to PVA, PVB, PVC and PVD*)
	answer=answer/.{
	  HoldPattern[passVeltD[0,0,0,0,s1_,s2_,s3_,s4_,s12_,s23_,m0_,m1_,m2_,m3_]] :> (
		With[{possibilities={
				{s12,s23,s1,s2,s3,s4,m0,m1,m2,m3},{s23,s12,s1,s4,s3,s2,m1,m0,m3,m2},
				{s12,s23,s2,s1,s4,s3,m2,m1,m0,m3},{s23,s12,s4,s1,s2,s3,m3,m0,m1,m2},
				{s23,s12,s3,s2,s1,s4,m3,m2,m1,m0},{s12,s23,s3,s4,s1,s2,m2,m3,m0,m1},
				{s23,s12,s2,s3,s4,s1,m1,m2,m3,m0},{s12,s23,s4,s3,s2,s1,m0,m3,m2,m1}}},
		  With[{canonicalOrdering=possibilities[[First[Ordering[possibilities,1]]]]},
		  (*Slots #1,#2 are in 5th and 6th positions to put s12 and s23 in their proper position after sorting.*)
			PVD[0,0,0,0,#3,#4,#5,#6,#1,#2,#7,#8,#9,#10]&@@canonicalOrdering
		  ]
		]),
	  HoldPattern[passVeltC[0,0,0,p1_,q_,p2_,m0_,m1_,m2_]] :> (PVC[0,0,0,#1,#3,#5,#4,#6,#2] &@@ Flatten[Sort[{{p1,m2},{p2,m1},{q,m0}}]]),
	  HoldPattern[reduceB[r_,0,s_,m0_,m1_]] :> (PVB[r,0,s,#1,#2] &@@ Sort[{m0,m1}]),
	  HoldPattern[reduceB[r_,n_,s_,m0_,m1_]] :> PVB[r,n,s,m0,m1],
	  HoldPattern[reduceA[-1,0]] :> 2 PVB[0,0,0,0,0],
	  HoldPattern[reduceA[r_,m0_]]:>PVA[r,m0]
	};

	If[
	  OptionValue[Organization]===None,
	  Total@answer,
	  Collect[Total@answer,{_PVA,_PVB,_PVC,_PVD},TimeConstrained[Factor[#],0.1,Together[#]]&]
	]

  ]],{Listable}
]


(* ::Subsubsection::Closed:: *)
(*Front end PVReduce*)


(*LoopRefine::dim = "Symbol Dim (number of spacetime dimensions) has value `1`.  Finite parts of results may be incorrect.  Running 'Clear[Dim]' is strongly recommended.";*)
PVReduce::opts = "Value of option `1` -> `2` is not `3`.";
PVReduce::inexact = "Warning: Unable to reduce Passarino\[Hyphen]Veltman function `1` with inexact or complex arguments."
PVReduce::leadinglandau = "Calculation of `1` at leading Landau singularity is attempted where no reduction methods are known.";


SetAttributes[PVReduce,Listable];
HoldPattern[PVReduce[SeriesData[Except[Eps,var_],p_,l_,rest___],opts___]] := SeriesData[var,p,PVReduce[l,opts],rest];

PVReduce[expr_, opts:OptionsPattern[]] /; pvReduceOptionsCheck[opts]:=
  Which[
	  OptionValue[Organization] === None,
		internalPVReduce[{1}, opts][expr],
	  OptionValue[Organization] === Function,
		internalPVReduce[X`Utilities`TensorStructures[expr], opts][expr],
	  OptionValue[Organization] === LTensor,
		X`Utilities`CollectByTensorStructures[expr, internalPVReduce[{1}, opts]]
	];

LHS_PVReduce:=RuleCondition[X`Private`checkArgumentCount[LHS,1,1];Fail];


Options[pvReduceOptionsCheck]:=Options[PVReduce];
pvReduceOptionsCheck[OptionsPattern[]] :=
	Module[{},
		If[!MemberQ[{Function, LTensor, None}, OptionValue[Organization]], Message[PVReduce::opts, Organization, OptionValue[Organization], "Function, LTensor, or None"]; Return[False]];
		If[!MemberQ[{True, False}, OptionValue["BnToB0"]], Message[PVReduce::opts, "\"BnToB0\"", OptionValue["BnToB0"], "True or False"]; Return[False]];
		If[!MemberQ[{"Recursive", "Iterative"}, OptionValue["B00ReductionMethod"]], Message[PVReduce::opts, "\"B00ReductionMethod\"", OptionValue["B00ReductionMethod"], "\"Recursive\" or \"Iterative\""]; Return[False]];
		If[!MemberQ[{True, False}, OptionValue["EliminateScalelessPV"]], Message[PVReduce::opts, "\"EliminateScalelessPV\"", OptionValue["EliminateScalelessPV"], "True or False"]; Return[False]];
		True
	];


SetAttributes[internalPVReduce,Unevaluated@{Protected,ReadProtected,Locked}];

SetAttributes[PVReduce,Unevaluated@{Protected,ReadProtected}];


End[];


EndPackage[]

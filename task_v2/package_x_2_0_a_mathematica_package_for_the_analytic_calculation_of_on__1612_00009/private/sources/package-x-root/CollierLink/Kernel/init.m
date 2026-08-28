(* ::Package:: *)

System`Dump`fixmessagestring[System`Dump`s_] := ToString@InputForm@System`Dump`s;
If[MemberQ[Contexts[], "CollierLink`"],
  If[$KernelID==0,
	If[$Notebooks,
	  Print[ToString[Row[{"CollierLink v1.0.1 already initialized\nFor more information, see the ", Hyperlink["guide", "paclet:CollierLink/guide/CollierLink"]}],StandardForm]],
	  Print["CollierLink v1.0.1 already initialized"]
	]
  ]
  ,

  BeginPackage["CollierLink`",{"X`"}];
  Get[FileNameJoin[{DirectoryName[$InputFileName,2], "CollierLink.m"}]];
  EndPackage[];

  If[$KernelID==0,
	If[$Notebooks,
	  Print[ToString[Row[{"CollierLink v1.0.1, by Hiren H. Patel\nFor more information, see the ", Hyperlink["guide", "paclet:CollierLink/guide/CollierLink"]}],StandardForm]],
	  Print["CollierLink v1.0.1, by Hiren H. Patel"]
	]
  ]
];

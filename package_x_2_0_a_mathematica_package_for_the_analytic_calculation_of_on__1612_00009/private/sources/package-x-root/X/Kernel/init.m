(* ::Package:: *)

(* Mathematica Init File *)
System`Dump`fixmessagestring[System`Dump`s_] := ToString@InputForm@System`Dump`s;

If[MemberQ[Contexts[], "X`"],
  If[$KernelID==0,
	If[$Notebooks,
	  Print[ToString[Row[{"Package-X v2.1.1 already initialized\nFor more information, see the ", Hyperlink["guide", "paclet:X/guide/PackageX"]}],StandardForm]],
	  Print["Package-X v2.1.1 already initialized"]
	]
  ],

  BeginPackage["X`"];
  Get[FileNameJoin[{DirectoryName[$InputFileName,2], "Common.m"}]];
  Get[FileNameJoin[{DirectoryName[$InputFileName,2], "Lorentz.m"}]];
  Get[FileNameJoin[{DirectoryName[$InputFileName,2], "Dirac.m"}]];
  Get[FileNameJoin[{DirectoryName[$InputFileName,2], "OneLoop.m"}]];

  EndPackage[];

  If[$KernelID==0,
	If[$Notebooks,
	  If[$VersionNumber<10.1, Print[ToString[Row[{"Attention: Support for Mathematica earlier than version 10.1 will be dropped in the near future. Please upgrade your copy of ", Hyperlink["Mathematica", "http://www.wolfram.com/mathematica/"]}],StandardForm]]];
	  Print[ToString[Row[{"Package-X v2.1.1 [patched 22/08/2020], by Hiren H. Patel\nFor more information, see the ", Hyperlink["guide", "paclet:X/guide/PackageX"]}],StandardForm]],

	  If[$VersionNumber<10.1, Print["Attention: Support for Mathematica earlier than version 10.1 will be dropped in the near future.  Please upgrade your copy of Mathematica"]];
	  Print["Package-X v2.1.1 [patched 22/08/2020], by Hiren H. Patel"]
	]
  ]

];

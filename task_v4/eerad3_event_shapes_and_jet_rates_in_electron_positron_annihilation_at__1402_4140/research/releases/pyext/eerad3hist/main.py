#! /usr/bin/python3

# This file is part of the EERAD3 NNLO event generator.
# Copyright (C) 2025 the authors.
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or any later version. See COPYING for details.

import os, sys
import argparse

bindir = os.path.dirname(os.path.realpath(__file__))
bindir = bindir[:-3]
sys.path.append(bindir+"pyext/eerad3hist")
from makedist import Distribution
from filetools import *

#=======================================================================
# Main program.
#=======================================================================

if __name__ == "__main__":
    # Parse command-line input.
    parser = argparse.ArgumentParser(prog="eerad3-hist")
    parser.add_argument("mode", nargs=1,
                        help="merge combine makedist")
    parser.add_argument("input", nargs=1,
                        help="input file (makedist) or "
                        +"directory (merge/combine)")
    parser.add_argument("-o","--output", default="", dest="prefix",
                        help="output directory for histogram files")
    parser.add_argument("-t","--tag", default="mrgd", dest="tag",
                        help="file tag for merged histograms (merge only)")
    parser.add_argument("-f","--format", default="plain", dest="format",
                        help="output histogram format (makedist only)")
    parser.add_argument("-E","--expand-normalisation", default=False,
                        action="store_true", dest="expand",
                        help="whether to expand normalisation (makedist only)")
    parser.add_argument("-B","--with-branching-ratio", default=False,
                        action="store_true", dest="withbr",
                        help="whether to include branching ratio (makedist only)")
    args = parser.parse_args()

    # Calculate distributions.
    if args.mode[0]=="makedist":
        # Read input and initialise cross-section calculators.
        runcard = args.input[0] if args.input[0]!="" else "makedist.input"
        dist = Distribution(runcard, args.expand, args.withbr)

        # Create directory for histograms.
        outdir = args.prefix if args.prefix!="" else "hist"
        try: os.mkdir(outdir)
        except OSError as err:
            print(" Using existing directory",args.prefix)

        # Calculate distributions and write them to files.
        dist.calc(args.format, outdir)
        print("\n Histograms saved in", outdir, "\n")

    # Merge statistically independent runs.
    elif args.mode[0]=="merge":
        # Set result directory path.
        resdir = args.input[0]
        if resdir[-1]=="/": resdir = resdir[:-1]

        # Create output directory for histograms.
        outdir = args.prefix if args.prefix!="" else "merged"
        try:
            os.mkdir(outdir)
            print(" Saving merged histograms in", outdir)
        except OSError as error:
            print(" Saving merged histograms in existing", outdir)

        # Find files differing only by seeds in resdir.
        filelist = findFiles(resdir, "seeds")
        if len(filelist) < 1:
            print(" No files in directory", resdir)
            quit()

        # Merge files with matching file names.
        for files in filelist:
            # Merge histograms.
            hcomb = mergeFiles(resdir, files)
            # Write to new file.
            wc = files[0].split(".")
            fname = wc[0]+"."+wc[1]+"."+args.tag+"."\
                +wc[3]+"."+wc[4]+"."+wc[5]+"."+wc[6]
            writeFile(hcomb, outdir+"/"+fname)

        print("\n Done.\n", "Now run ./eerad3hist combine", outdir)

    # Combine perturbative contributions.
    elif args.mode[0]=="combine":
        # Set result directory path.
        resdir = args.input[0]
        if resdir[-1]=="/": resdir = resdir[:-1]

        # Create output directory for histograms.
        outdir = args.prefix if args.prefix!="" else "combined"
        try:
            os.mkdir(outdir)
            print(" Saving combined histograms in directory", outdir)
        except OSError as error:
            print(" Saving combined histograms in existing", outdir)

        # Find files differing only by perturbative parts in resdir.
        filelist = findFiles(resdir, "parts")
        if len(filelist) < 1:
            print(" No files in folder", resdir)
            quit()

        # Figure out process details from file name.
        wc = filelist[0][0].split(".")
        iproc = 1 if wc[0]=="Zqq" else 21 if wc[0]=="Hbb" \
            else 22 if wc[0]=="Hgg" else -1
        if iproc<0:
            print("Unknown process ID",iproc)
            quit()
        njets = int(wc[1][0])

        # Setup makedist.input card.
        mdFileName = "makedist.input"
        mdFile = open(mdFileName,'w')
        print("process =",iproc,file=mdFile)
        print("njets   =",njets,file=mdFile)
        if iproc==1:
            print("sqrts   = 91.2\n",file=mdFile)
            print("MASS[W] = 80.385",file=mdFile)
            print("MASS[Z] = 91.2",file=mdFile)
        elif iproc==21:
            print("sqrts   = 125.09\n",file=mdFile)
            print("MASS[b] = 4.18",file=mdFile)
        elif iproc==22:
            print("sqrts   = 125.09\n",file=mdFile)
            print("MASS[t] = 166.48",file=mdFile)
        print("GF      = 1.1664e-5",file=mdFile)
        print("aS[MZ]  = 0.118\n",file=mdFile)
        print("HISTOGRAMS",file=mdFile)

        # Combine files with matching file names.
        for files in filelist:
            # Combine histograms.
            listComb = combineFiles(resdir, files)
            # Identify wildcards.
            wc = files[0].split(".")
            # Initialise histogram string.
            hline = wc[5]
            # LO.
            if len(listComb[0])>0:
                fname = wc[0]+"."+wc[1]+"."+wc[2]+".LO."\
                    +wc[4]+"."+wc[5]+"."+wc[6]
                writeFile(listComb[0], outdir+"/"+fname)
                hline = hline+"\t"+outdir+"/"+fname
            # NLO.
            if len(listComb[1])>0:
                fname = wc[0]+"."+wc[1]+"."+wc[2]+".NLO."\
                    +wc[4]+"."+wc[5]+"."+wc[6]
                writeFile(listComb[1], outdir+"/"+fname)
                hline = hline+"\t"+outdir+"/"+fname
            # NNLO.
            if len(listComb[2])>0:
                fname = wc[0]+"."+wc[1]+"."+wc[2]+".NNLO."\
                    +wc[4]+"."+wc[5]+"."+wc[6]
                writeFile(listComb[2], outdir+"/"+fname)
                hline = hline+"\t"+outdir+"/"+fname
            print(hline,file=mdFile)
        print("END HISTOGRAMS",file=mdFile)

        print("\n Done.",
              "\n Now check", mdFileName,
              "\n and run ./eerad3hist makedist", mdFileName)

    else:
        print(" Unknown mode '"+args.mode[0]+"' specified")
        print(" See -h for usage")

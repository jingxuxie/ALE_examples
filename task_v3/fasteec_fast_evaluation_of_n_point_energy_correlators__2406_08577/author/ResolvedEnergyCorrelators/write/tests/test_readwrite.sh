#!/bin/bash

vimdiff <(head -n 1000 "cms_jet_COPY.opendata.txt") <(head -n 1000 "../data/cms_jet_run2011A.opendata.txt")

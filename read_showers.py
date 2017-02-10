#!/usr/bin/env python

from __future__ import division

import os, sys
from glob import glob

from ROOT import gROOT, TFile, TH1F
from ROOT import gallery, art, vector, string, recob, simb


#if (len(sys.argv) < 2):
#	print "Please specify an art/ROOT file to read"
#	sys.exit(1)

# Some functions that I find useful to reduce error-prone typing.
def read_header(h):
    """Make the ROOT C++ jit compiler read the specified header."""
    gROOT.ProcessLine('#include "%s"' % h)

def provide_get_valid_handle(klass):
    """Make the ROOT C++ jit compiler instantiate the
    Event::getValidHandle member template for template
    parameter klass."""
    gROOT.ProcessLine('template gallery::ValidHandle<%(name)s> gallery::Event::getValidHandle<%(name)s>(art::InputTag const&) const;' % {'name' : klass})


# Now for the script...

print "Reading headers..."
read_header("gallery/ValidHandle.h")
print "Instantiating member templates..."
provide_get_valid_handle('std::vector<recob::Shower>')
provide_get_valid_handle('std::vector<simb::MCParticle>')

print "Preparing before event loop..."
showers_tag = art.InputTag("showerrecopandora")
mcparticles_tag = art.InputTag("largeant")

files = glob("/pnfs/uboone/scratch/users/srsoleti/nu_e_only/v06_21_00/reco2/NuE/*/prod*.root")
filenames = vector(string)()
for f in files[:3]:
    filenames.push_back(f)

# Make histograms before we open the art/ROOT file, or the file ends
# up owning the histograms.
histfile = TFile("hist.root", "RECREATE")
npart_hist = TH1F("npart", "Number of particles per MCTruth", 51, -0.5, 50.5)

print "Creating event object ..."
ev = gallery.Event(filenames)

# Capture the functions that will get ValidHandles. This avoids some
# inefficiency in constructing the function objects many times.
get_showers = ev.getValidHandle(vector(recob.Shower))
get_mcparticles = ev.getValidHandle(vector(simb.MCParticle))

print "Entering event loop..."



print(ev.numberOfEventsInFile())

n_events = 0
e_p = 0

while (not ev.atEnd()):

    pdg_primaries = []
    primaries = 0

    n_events += 1
    particles = get_mcparticles(mcparticles_tag)
    for p in particles.product():
        if p.Process() == "primary":
            primaries += 1
            pdg_primaries.append(p.PdgCode())

    if len(pdg_primaries) == 2 and 11 in pdg_primaries and 2212 in pdg_primaries:
        e_p += 1

        showers = get_showers(showers_tag)
        for s in showers.product():
            print s.Length()

    ev.next()

print(e_p/n_events)
print "Writing histograms..."
histfile.Write()

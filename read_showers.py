#!/usr/bin/env python

from __future__ import division

import os, sys
from glob import glob

from ROOT import gROOT, gStyle, TFile, TH1F, THStack, TCanvas, TLegend, TH2F
from ROOT import kAzure, kOrange, kRed, kGray, kBlack
from ROOT import gallery, art, vector, string, recob, simb

gStyle.SetOptStat(0)
gStyle.SetPalette(87)
gStyle.SetNumberContours(999)

def style_hist(hist,color=kRed):
    hist.SetLineColor(1)
    hist.SetFillColor(color)
    return hist


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
for f in files:
    filenames.push_back(f)

# Make histograms before we open the art/ROOT file, or the file ends
# up owning the histograms.
histfile = TFile("hist.root", "RECREATE")
h_primaries_p = TH1F("h_primaries_p",";P [GeV/c];N. Entries / 0.04 GeV",50,0,2)
h_primaries_e = TH1F("h_primaries_e",";P [GeV/c];N. Entries / 0.04 GeV",50,0,2)
h_primaries_n = TH1F("h_primaries_n",";P [GeV/c];N. Entries / 0.04 GeV",50,0,2)
h_primaries_other = TH1F("h_primaries_other",";P [GeV/c];N. Entries / 0.04 GeV",50,0,2)

h_primaries = [h_primaries_p,h_primaries_n,h_primaries_e,h_primaries_other]
primaries_names = ["p","e^{#pm}","n","Other"]
primaries_colors = [kRed+1,kAzure+1,kOrange+1,kGray+1]

h_n_primaries = TH1F("h_n_primaries",";# primaries;N. Entries / 1",20,0,20)
h_n_ep_primaries = TH1F("h_n_ep_primaries",";# primaries;N. Entries / 1",20,0,20)

h_n_showers = TH1F("h_n_showers",";# showers;N. Entries / 1",10,0,10)

h_e_diff = TH1F("h_e_diff",";E [GeV];N. Entries / 0.04 GeV", 25, -0.1, 0.9)

h_n_showers_e = TH2F("h_n_showers_e",";# showers; E [GeV]",10,0,10,50,0,2)
h_s_e = TH2F("h_s_e",";Showers energy [GeV];e^{-} energy [GeV]",50,0,2,50,0,2)

print "Creating event object ..."
ev = gallery.Event(filenames)

# Capture the functions that will get ValidHandles. This avoids some
# inefficiency in constructing the function objects many times.
get_showers = ev.getValidHandle(vector(recob.Shower))
get_mcparticles = ev.getValidHandle(vector(simb.MCParticle))
print "Entering event loop..."

while (not ev.atEnd()):

    pdg_primaries = []

    particles = get_mcparticles(mcparticles_tag)
    for p in particles.product():
        if p.Process() == "primary":
            pdg_primaries.append(p.PdgCode())
            if abs(p.PdgCode()) == 11:
                h_primaries_e.Fill(p.P())
                e_energy = p.E()
            elif p.PdgCode() == 2212: # proton
                h_primaries_p.Fill(p.P())
            elif p.PdgCode() == 2112: # neutron
                h_primaries_n.Fill(p.P())
            else:
                h_primaries_other.Fill(p.P())


    if len(pdg_primaries) == 2 and 11 in pdg_primaries and 2212 in pdg_primaries:
        h_n_ep_primaries.Fill(len(pdg_primaries))
        tot_s_energy = 0
        showers = get_showers(showers_tag)
        h_n_showers.Fill(len(showers.product()))

        for s in showers.product():
            tot_s_energy += s.Energy()[s.best_plane()]/1000

        h_n_showers_e.Fill(len(showers.product()),e_energy)
        h_s_e.Fill(tot_s_energy,e_energy)

        if len(showers.product()):
            h_e_diff.Fill(e_energy-tot_s_energy)

    else:
        h_n_primaries.Fill(len(pdg_primaries))

    ev.next()

c_p = TCanvas("c_p")
h_primaries_stack = THStack("h_primaries_stack",";N. Entries / 0.02 GeV/c;P [GeV/c]")
leg = TLegend(0.67,0.66,0.8,0.85)
leg.SetBorderSize(0)
leg.SetShadowColor(0)
for i,h in enumerate(h_primaries):
    leg.AddEntry(h,primaries_names[i],"f")
    style_hist(h,primaries_colors[i])
    h_primaries_stack.Add(h)

h_primaries_stack.Draw()
leg.Draw()
c_p.SetLogy()
c_p.Update()
c_p.SaveAs("p.pdf")


c_n = TCanvas("c_n")
h_n_stack = THStack("h_n_stack",";N. Entries / 1;# primaries")
leg2 = TLegend(0.67,0.66,0.8,0.85)
leg2.SetBorderSize(0)
leg2.SetShadowColor(0)
h_n_primaries.SetLineColor(1)
h_n_ep_primaries.SetLineColor(1)
h_n_ep_primaries.SetFillColor(kGray+2)
h_n_stack.Add(h_n_primaries)
h_n_stack.Add(h_n_ep_primaries)

leg2.AddEntry(h_n_ep_primaries,"e^{-}+p process","f")
leg2.AddEntry(h_n_primaries,"Other","f")

h_n_stack.Draw()
leg2.Draw()
c_n.Update()
c_n.SaveAs("n.pdf")

c_e_diff = TCanvas("c_e_diff")
h_e_diff.SetLineColor(1)
h_e_diff.Draw()
c_e_diff.Update()
c_e_diff.SaveAs("e_diff.pdf")

c_e_s = TCanvas("c_e_s")
h_s_e.Draw("colz")
c_e_s.Update()
c_e_s.SaveAs("s_e.pdf")

c_n_e = TCanvas("c_n_e")
h_n_showers_e.Draw("colz")
c_n_e.Update()
c_n_e.SaveAs("c_n_e.pdf")

print "Writing histograms..."
histfile.Write()

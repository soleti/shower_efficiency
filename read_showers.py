#!/usr/bin/env python

from __future__ import division

import os, sys, math
from glob import glob

from ROOT import gROOT, gStyle, gPad, TFile, TH1F, THStack, TCanvas, TLegend, TH2F, TLine, TEfficiency
from ROOT import kAzure, kOrange, kRed, kGray, kBlack, kBlue, kGreen
from ROOT import gallery, art, vector, string, recob, simb, sim

gStyle.SetOptStat(0)
gStyle.SetPalette(87)
gStyle.SetNumberContours(99)

def show_overflow(hist):
    nbins = hist.GetNbinsX()
    hist.SetBinContent(nbins, hist.GetBinContent(nbins)+hist.GetBinContent(nbins+1))
    hist.SetBinContent(nbins+1,0);

def show_underflow(hist):
    hist.SetBinContent(1, hist.GetBinContent(0)+hist.GetBinContent(1));
    hist.SetBinContent(0,0);

def style_hist(hist,color=kRed):
    hist.SetLineColor(1)
    hist.SetFillColor(color)
    return hist

def shower_length(shower):
    start = [shower.Start().X(),shower.Start().Y(),shower.Start().Z()]
    end = [shower.End().X(),shower.End().Y(),shower.End().Z()]
    l = math.sqrt(sum([(s-e)**2 for s,e in zip(start,end)]))
    return l

# Some functions that I find useful to reduce error-prone typing.
def read_header(h):
    """Make the ROOT C++ jit compiler read the specified header."""
    gROOT.ProcessLine('#include "%s"' % h)

def provide_get_valid_handle(klass):
    """Make the ROOT C++ jit compiler instantiate the
    Event::getValidHandle member template for template
    parameter klass."""
    gROOT.ProcessLine('template gallery::ValidHandle<%(name)s> gallery::Event::getValidHandle<%(name)s>(art::InputTag const&) const;' % {'name' : klass})

print "Reading headers..."
read_header("gallery/ValidHandle.h")
print "Instantiating member templates..."
provide_get_valid_handle("std::vector<recob::Shower>")
provide_get_valid_handle("std::vector<simb::MCParticle>")
provide_get_valid_handle("std::vector<sim::MCShower>")
provide_get_valid_handle("std::vector<recob::Track>")
provide_get_valid_handle("std::vector<simb::MCTruth>")

print "Preparing before event loop..."
pandoraNu_tag = art.InputTag("pandoraNu")
generator_tag = art.InputTag("generator")
mcparticles_tag = art.InputTag("largeant")
mcreco_tag = art.InputTag("mcreco")
track_tag = art.InputTag("pandoraNu")

files = glob("/pnfs/uboone/scratch/users/srsoleti/nu_e_only/v06_25_00/reco2/NuE/*/prod*.root")
#files = glob("/uboone/app/users/srsoleti/nu_e/pr*.root")
filenames = vector(string)()
print "Number of files: ", len(files)
for f in files:
    filenames.push_back(f)

# Primaries histograms
h_primaries_p = TH1F("h_primaries_p",";P [GeV/c];N. Entries / 0.04 GeV",50,0,2)
h_primaries_e = TH1F("h_primaries_e",";P [GeV/c];N. Entries / 0.04 GeV",50,0,2)
h_primaries_n = TH1F("h_primaries_n",";P [GeV/c];N. Entries / 0.04 GeV",50,0,2)
h_primaries_other = TH1F("h_primaries_other",";P [GeV/c];N. Entries / 0.04 GeV",50,0,2)

h_primaries = [h_primaries_p,h_primaries_n,h_primaries_e,h_primaries_other]
primaries_names = ["p","e^{#pm}","n","Other"]
primaries_colors = [kRed+1,kAzure+1,kOrange+1,kGray+1]

h_n_primaries = TH1F("h_n_primaries",";# primaries;N. Entries / 1",20,0,20)
h_n_ep_primaries = TH1F("h_n_ep_primaries",";# primaries;N. Entries / 1",20,0,20)

h_n_showers = TH1F("h_n_showers",";# Reco. showers;N. Entries / 1",10,0,10)

h_e_diff = TH1F("h_e_diff",";E_{MC}-#Sigma E_{reco} [GeV];N. Entries / 0.04 GeV", 45, -0.5, 1)

h_n_showers_e = TH2F("h_n_showers_e",";# Reco. showers;E_{MC} [GeV]",10,0,10,20,0,2)
h_mc_reco_n = TH2F("h_mc_reco",";# Reco. showers;# MC showers",10,0,10,10,0,10)
h_mc_reco_e = TH2F("h_mc_reco_e",";E_{MC} [GeV];#Sigma E_{reco} [GeV]",20,0,2,20,0,2)
h_length = TH2F("h_length",";# Reco. showers; L_{MC} [cm]",10,0,10,10,0,200)
h_res_length = TH1F("h_res_length",";L_{reco}-L_{MC};N. Entries / 10 cm",40,-200,200)

# Non-reconstructed showers histograms
h_zero_showers_length = TH1F("h_zero_showers_length",";L_{MC} [cm];N. Entries / 10 cm",20,0,200)
h_zero_showers_energy = TH1F("h_zero_showers_energy",";E_{MC} [GeV];N. Entries / 0.1 GeV",20,0,2)
h_mc_showers_energy_length = TH2F("h_mc_showers_energy_length",";E_{MC} [GeV];L_{MC} [cm]",20,0,2,20,0,200)

# Reconstructed showers histograms
h_mc_showers_length = TH1F("h_mc_showers_length",";L_{MC} [cm];N. Entries / 10 cm",20,0,200)
h_mc_shower_energy = TH1F("h_mc_shower_energy",";E_{MC} [GeV];N. Entries / 0.05 GeV",20,0,2)

# Efficiency histograms
h_correct = TH1F("h_correct",";#nu_{e} energy [GeV];Efficiency",15,0,3)
h_total = TH1F("h_total",";#nu_{e} energy [GeV];Efficiency",15,0,3)
h_correct_more_showers = TH1F("h_correct_more_showers",";#nu_{e} energy [GeV];Efficiency",15,0,3)
h_correct_shower_only = TH1F("h_correct_shower",";#nu_{e} [GeV];Efficiency",15,0,3)
h_correct_more_showers_only = TH1F("h_correct_more_showers_only",";#nu_{e} [GeV];Efficiency",15,0,3)

print "Creating event object ..."
ev = gallery.Event(filenames)

# Capture the functions that will get ValidHandles. This avoids some
# inefficiency in constructing the function objects many times.
get_showers = ev.getValidHandle(vector(recob.Shower))
get_mcparticles = ev.getValidHandle(vector(simb.MCParticle))
get_mcshowers = ev.getValidHandle(vector(sim.MCShower))
get_tracks = ev.getValidHandle(vector(recob.Track))
get_mctruth = ev.getValidHandle(vector(simb.MCTruth))

print "Entering event loop..."
n = 0
max_e = 0
while (not ev.atEnd()):

    n += 1
    if n % 10 == 0: print n

    pdg_primaries = []

    particles = get_mcparticles(mcparticles_tag)

    mc_truth = get_mctruth(generator_tag).product()[0]
    nu_energy = mc_truth.GetNeutrino().Nu().E()
    for p in particles.product():
        if p.Process() == "primary":
            pdg_primaries.append(p.PdgCode())
            if abs(p.PdgCode()) == 11:
                h_primaries_e.Fill(p.P())
            elif p.PdgCode() == 2212: # proton
                h_primaries_p.Fill(p.P())
            elif p.PdgCode() == 2112: # neutron
                h_primaries_n.Fill(p.P())
            else:
                h_primaries_other.Fill(p.P())

    if nu_energy > max_e: max_e = nu_energy

    if len(pdg_primaries) == 2 and 11 in pdg_primaries and 2212 in pdg_primaries:
        h_n_ep_primaries.Fill(len(pdg_primaries))

        tracks = get_tracks(pandoraNu_tag).product()
        showers = get_showers(pandoraNu_tag).product()
        mcshowers = get_mcshowers(mcreco_tag).product()
        tracks = get_tracks(pandoraNu_tag).product()

        tot_s_energy = 0
        for s in showers:
            tot_s_energy += max(s.Energy())/1000

        if len(mcshowers) == 1:
            mc_shower_energy = mcshowers[0].DetProfile().E()/1000

            if mc_shower_energy > 0.01: # 10 MeV threshold
                h_mc_reco.Fill(len(showers),len(mcshowers))
                h_n_showers.Fill(len(showers))

                h_length.Fill(len(showers), shower_length(mcshowers[0]))
                h_n_showers_e.Fill(len(showers), mc_shower_energy)
                h_total.Fill(nu_energy)

                if len(showers):
                    h_correct_more_showers_only.Fill(nu_energy)

                    if len(tracks) == 1:
                        h_correct_more_showers.Fill(nu_energy)
                        if len(showers) == 1:
                            h_correct.Fill(nu_energy)

                    if len(showers) == 1:
                        h_correct_shower_only.Fill(nu_energy)
                        h_res_length.Fill(shower_length(mcshowers[0])-showers[0].Length())

                    h_e_diff.Fill(mc_shower_energy-tot_s_energy)
                    h_mc_reco_e.Fill(mc_shower_energy,tot_s_energy)
                    h_mc_shower_energy.Fill(mc_shower_energy)
                    h_mc_showers_length.Fill(shower_length(mcshowers[0]))
                else:
                    h_mc_showers_energy_length.Fill(mc_shower_energy,shower_length(mcshowers[0]))

                    h_zero_showers_length.Fill(shower_length(mcshowers[0]))
                    h_zero_showers_energy.Fill(mc_shower_energy)

    else:
        h_n_primaries.Fill(len(pdg_primaries))


    ev.next()

print "Max Energy: ", max_e
print "e- + p fraction: ", h_n_ep_primaries.Integral()/(h_n_ep_primaries.Integral()+h_n_primaries.Integral())
c_p = TCanvas("c_p")
h_primaries_stack = THStack("h_primaries_stack",";P [GeV/c];N. Entries / 0.02 GeV/c")
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
c_p.Draw()
c_p.SaveAs("plots/p.pdf")

c_n = TCanvas("c_n")
h_n_stack = THStack("h_n_stack",";# primaries;N. Entries / 1")
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
c_n.Draw()
c_n.SaveAs("plots/n.pdf")

c_e_diff = TCanvas("c_e_diff")
h_e_diff.SetLineColor(1)
h_e_diff.Draw()
c_e_diff.Update()
c_e_diff.Draw()
c_e_diff.SaveAs("plots/e_diff.pdf")

c_e_s = TCanvas("c_e_s")
h_mc_reco_e.Draw("colz")
line = TLine(0,0,2,2)
line.SetLineStyle(2)
line.SetLineWidth(2)
line.SetLineColor(kRed+1)
line.Draw()
c_e_s.Draw()
c_e_s.SaveAs("plots/s_e.pdf")

c_n_e = TCanvas("c_n_e")
h_n_showers_e.Draw("colz")
c_n_e.Draw()
c_n_e.SaveAs("plots/c_n_showers_energy.pdf")

c_n_showers = TCanvas("c_n_showers")
h_n_showers.Draw()
print "0 showers", h_n_showers.GetBinContent(1)/h_n_showers.Integral()
print "1 showers", h_n_showers.GetBinContent(2)/h_n_showers.Integral()

h_n_showers.SetLineColor(1)
h_n_showers.SetLineWidth(2)
c_n_showers.Draw()
c_n_showers.SaveAs("plots/c_n_showers.pdf")

c_mc_reco = TCanvas("c_mc_reco")
h_mc_reco.Draw("colz")
c_mc_reco.Draw()
c_mc_reco.SaveAs("plots/c_mc_reco.pdf")

c_length = TCanvas("c_length")
h_length.Draw("colz")
c_length.Draw()
c_length.SaveAs("plots/c_length.pdf")

c_eff = TCanvas("c_eff")
eff_e = TEfficiency(h_correct,h_total)
print "1 shower, 1 track", h_correct.Integral()/h_total.Integral()

eff_e_more = TEfficiency(h_correct_more_showers,h_total)
print "1+ showers, 1 track", h_correct_more_showers.Integral()/h_total.Integral()

eff_e_shower_only = TEfficiency(h_correct_shower_only,h_total)
print "1 shower", h_correct_shower_only.Integral()/h_total.Integral()

eff_e_more_showers_only = TEfficiency(h_correct_more_showers_only, h_total)
print "1+ showers", h_correct_more_showers_only.Integral()/h_total.Integral()

eff_e.Draw("apl")
eff_e_more.Draw("pl same")
eff_e_shower_only.Draw("pl same")
eff_e_more_showers_only.Draw("pl same")
gPad.Update()
eff_e.GetPaintedGraph().SetMinimum(0.001)
eff_e.GetPaintedGraph().SetMaximum(1.3)
eff_e.GetPaintedGraph().GetXaxis().SetRangeUser(0,3)
eff_e.SetLineColor(kBlue+1)
eff_e.SetMarkerStyle(20)
eff_e_more.SetLineColor(kRed+1)
eff_e_more.SetMarkerStyle(21)
eff_e_shower_only.SetLineColor(kBlue+1)
eff_e_shower_only.SetLineStyle(2)
eff_e_shower_only.SetMarkerStyle(24)
eff_e_more_showers_only.SetLineColor(kRed+1)
eff_e_more_showers_only.SetLineStyle(2)
eff_e_more_showers_only.SetMarkerStyle(25)
eff_e.SaveAs("plots/pandoraNu_eff.root")
eff_e_more.SaveAs("plots/pandoraNu_more_eff.root")
eff_e_shower_only.SaveAs("plots/pandoraNu_s_eff.root")
eff_e_more_showers_only.SaveAs("plots/pandoraNu_s_more_eff.root")

leg_e = TLegend(0.16,0.76,0.84,0.84)
leg_e.SetNColumns(2)
leg_e.AddEntry(eff_e,"1 shower, 1 track","lep")
leg_e.AddEntry(eff_e_more,"1+ showers, 1 track","lep")
leg_e.AddEntry(eff_e_shower_only,"1 shower","lep")
leg_e.AddEntry(eff_e_more_showers_only,"1+ showers","lep")
leg_e.Draw()
gPad.Update()
c_eff.Draw()
c_eff.SaveAs("plots/c_eff.pdf")

c_res_length = TCanvas("c_res_length")
h_res_length.Draw()
h_res_length.SetLineColor(1)
c_res_length.Draw()
c_res_length.SaveAs("plots/res_length.pdf")

c_zero_length = TCanvas("c_zero_length")
show_overflow(h_zero_showers_length)
show_overflow(h_mc_showers_length)

h_zero_showers_length.SetLineColor(1)
h_mc_showers_length.SetLineColor(1)
h_mc_showers_length.SetFillColor(kGreen+1)
h_stack_length = THStack("h_stack_length",";MC shower length [cm];N. Entries / 10 cm")
h_stack_length.Add(h_zero_showers_length)
h_stack_length.Add(h_mc_showers_length)
h_stack_length.Draw()
leg_reco = TLegend(0.67,0.66,0.8,0.85)
leg_reco.SetBorderSize(0)
leg_reco.SetShadowColor(0)
leg_reco.AddEntry(h_mc_showers_length,"Reconstructed showers","f")
leg_reco.AddEntry(h_zero_showers_length,"Non-reconstructed showers","f")
leg_reco.Draw()
c_zero_length.Draw()
c_zero_length.SaveAs("plots/zero_length.pdf")

c_zero_energy = TCanvas("c_zero_energy")
show_overflow(h_zero_showers_energy)
show_overflow(h_mc_shower_energy)

h_zero_showers_energy.SetLineColor(1)
h_mc_shower_energy.SetLineColor(1)
h_mc_shower_energy.SetFillColor(kGreen+1)

h_stack_energy = THStack("h_stack_energy",";MC shower energy [GeV];N. Entries / 0.1 GeV")
h_stack_energy.Add(h_zero_showers_energy)
h_stack_energy.Add(h_mc_shower_energy)

h_stack_energy.Draw()
leg_reco.Draw()
c_zero_energy.Draw()
c_zero_energy.SaveAs("plots/zero_energy.pdf")

c_e_energy = TCanvas("c_e_energy")
h_mc_showers_energy_length.Draw("colz")

c_e_energy.Draw()
c_e_energy.SaveAs("plots/e_energy.pdf")

print "Writing histograms..."
histfile = TFile("plots/hist.root", "RECREATE")

histfile.Write()
raw_input()

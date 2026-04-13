# -*- coding: utf-8 -*-
"""
Created on Fri Jul 12 10:51:42 2024

@author: cakir
"""

import numpy as np
import sys
sys.path.append(r"C:\Users\cakir\anaconda3\Lib\site-packages\xrt-1.6.0-py3.11.egg")
import xrt.backends.raycing.sources as rsources
import xrt.backends.raycing.screens as rscreens
import xrt.backends.raycing.oes as roes
import xrt.backends.raycing.run as rrun
import xrt.backends.raycing as raycing
import xrt.plotter as xrtplot
import xrt.runner as xrtrun
from CrystalSelector import CrystalSelector
import matplotlib
matplotlib.use('Agg')

class BeamLineBuilder:
    def __init__(self, crystal, distance, c, theta, num_rep, energies, hkl):
        self.crystal = CrystalSelector().get_crystal_method(crystal, hkl=hkl)
        self.distance = distance
        self.c = c
        self.num_rep = num_rep
        self.theta = theta
        self.energies = energies
        self.setup_custom_run_process()
        self.total2D = None
        self.total1DX = None
        self.total1DZ = None
        self.total1DEnergy =None
        self.total1DEnergy_limits = None
        self.histo1Dx = None
        

    def setup_custom_run_process(self):
        # Override the run_process method within the class initialization
        def custom_run_process(beamLine):
            geometricSource01beamGlobal01 = beamLine.geometricSource01.shine()
            oe01beamGlobal01, oe01beamLocal01 = beamLine.oe01.reflect(beam=geometricSource01beamGlobal01)
            screenRotate01beamLocal01 = beamLine.screenRotate01.expose(beam=oe01beamGlobal01)
            return {
                'geometricSource01beamGlobal01': geometricSource01beamGlobal01,
                'oe01beamGlobal01': oe01beamGlobal01,
                'oe01beamLocal01': oe01beamLocal01,
                'screenRotate01beamLocal01': screenRotate01beamLocal01
            }
        rrun.run_process = custom_run_process


    def build_beamline(self):
        beamLine = raycing.BeamLine()
        beamLine.geometricSource01 = rsources.GeometricSource(
            bl=beamLine,
            name=None,
            center=[0, 0, 0],
            pitch=0.0,
            distx=r"flat",
            dx=[-0.05, 0.05],
            distz=r"flat",
            dz=[-0.05, 0.05],
            distxprime=r"flat",
            dxprime=[np.pi, -np.pi],
            dzprime=0.08,
            distE=r"lines",
            energies=self.energies)

        beamLine.oe01 = roes.OE(
            bl=beamLine,
            name=None,
            center=[self.c, self.distance, 0],
            pitch=0.0,
            positionRoll=3.141592653589793,
            extraPitch=3.141592653589793,
            extraRoll=1.5707963267948966,
            extraYaw=3.141592653589793,
            material=self.crystal,
            limPhysX=[-20.0, 20.0],
            limPhysY=[-20.0, 20.0],
            shape=r"round")

        beamLine.screenRotate01 = rscreens.ScreenRotate(
            bl=beamLine,
            name=None,
            center=[0, 2*self.distance, 0],
            compressX=1e-1,
            compressZ=1e-1,
            angle=self.theta,  # assuming angle theta needs to be pi/2
            rotationaxis=r"z")

        return beamLine
        
    def define_plots(self):
        plots = []
        plot01 = xrtplot.XYCPlot(
            beam=r"screenRotate01beamLocal01",
            rayFlag=[1],
            xaxis=xrtplot.XYCAxis(
                label=r"x",
                factor=10,
                limits=[-6.144, 6.144],
                bins=264,
                ppb=1),
            yaxis=xrtplot.XYCAxis(
                label=r"z",
                factor=10,
                limits=[-6.144, 6.144],
                bins=264,
                ppb=1),
            caxis=xrtplot.XYCAxis(
                label=r"energy",
                unit=r"eV"),
            aspect=r"auto",
            title=r"plot01")
        plots.append(plot01)

        return plots
     

    def run_simulation(self):
        

        print("pass_run_simulation")
        
        beamLine = self.build_beamline()
        print("beamline_builded")
        E0 = list(beamLine.geometricSource01.energies)[0]
        beamLine.alignE = E0
        print("energy_alligned")
        
        plots = self.define_plots()
        print("plots_created")
        
        xrtrun.run_ray_tracing(
        plots=plots,
        backend=r"raycing",
        beamLine=beamLine,
        threads=4,
        repeats=self.num_rep, afterScript=self.get_data, afterScriptArgs=[plots])
                  

    def get_data(self, plots):
        
        data = plots[-1]  
        self.total2D = data.total2D_RGB
        self.total1DX = data.xaxis.total1D_RGB
        self.total1DZ = data.yaxis.total1D_RGB
        self.total1DEnergy, self.total1DEnergy_limits = data.caxis.total1D_RGB ,data.caxis.limits
        self.histo1Dx = data.xaxis.total1D


    


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 17:47:12 2026

@author: paulbeguelin
"""

import numpy as np

# String shortcuts:
iSr = 'SR87_SR86'
iCe = 'CE138_CE136'
iNd = 'ND143_ND144'
iHf = 'HF176_HF177'
i206 = 'PB206_PB204'
i207 = 'PB207_PB204'
i208 = 'PB208_PB204'
Rb = 'RB'
Sr = 'SR'
La = 'LA'
Ce = 'CE'
Sm = 'SM'
Nd = 'ND'
Lu = 'LU'
Hf = 'HF'
U = 'U'
Th = 'TH'
Pb = 'PB'

# Suggested radiogenic isotope plots
default_iso_pairs = [(iSr, iNd), (iSr, iHf), (iNd, iHf), (i206, iSr), (i206, i207), (i206, i208)]

class ASCII_plotting:
    def __init__(self, observables, data, max_res_per_cell, pairs=default_iso_pairs, loops_per_plot=50):
        self.observables = list(observables.columns)
        self.plots = {}
        for i in pairs:
            if i[0] in self.observables and i[1] in self.observables:
                self.plots[i] = ASCII_plot(i[0], i[1], data, max_res_per_cell)
        self.playlist0 = list(self.plots.keys())
        self.playlist = []
        for i in self.playlist0:
            for j in range(loops_per_plot):
                self.playlist.append(i)
        
    def update_ASCII_display(self, counter, cells_hit_temp, cells_hit):
        for i in self.plots.keys():
            self.plots[i].update(counter, cells_hit_temp, cells_hit)
    
    def fill_displays(self, run_data):
        counter = ' '
        cells_hit_temp = run_data['cells']
        cells_hit = run_data['cells']
        for i in self.plots.keys():
            self.plots[i].reset()
            self.plots[i].update(counter, cells_hit_temp, cells_hit)
            self.plots[i].plot_all_results()
    
    def show(self, item):
        self.plots[item].plot()
            

class ASCII_plot:
    def __init__(self, x, y, data, max_results_per_cell):
        self.n_hits = 0
        self.x = x
        self.y = y
        self.ix = data.iso.index(self.x)
        self.iy = data.iso.index(self.y)
        self.rx = data.res[self.ix]
        self.ry = data.res[self.iy]
        
        self.max_res = max_results_per_cell
        self.n_cells = data.cells.shape[1]
        
        axes = list(range(len(data.iso)))
        axes.remove(self.ix)
        axes.remove(self.iy)
        self.map_proj = np.sum(data.map, axis=tuple(axes))
        if self.ix > self.iy:
            self.map_proj = self.map_proj.T
        self.s = []
        for i in range(self.ry):
            xs = []
            for j in range(self.rx):
                if self.map_proj[j,i] == 0:
                    xs.append(' ')
                else:
                    xs.append('·')
            self.s.append(xs)
    
    def update(self, counter, cells_hit_temp, cells_hit):
        self.counter = counter
        for i in range(cells_hit_temp.shape[1]):
            self.n_hits += 1
            hits = cells_hit_temp[[self.ix, self.iy]]
            self.s[hits[1][i]][hits[0][i]] = '◼'
        if cells_hit is not None:
            self.cells_with_res, self.counts = np.unique(cells_hit, return_counts=True, axis=1)
            self.n_full_cells = np.sum(self.counts==self.max_res)
            self.n_cells_with_res = self.cells_with_res.shape[1]
        else:
            self.n_full_cells = 0
            self.n_cells_with_res = 0
        
    
    def plot(self):
        s_rev = self.s.copy()
        s_rev.reverse()
        for i in s_rev:
            print(*i)
        print('x-axis: '+self.x+' y-axis: '+self.y+'  n_loops: '+ self.counter +'  n_hits: '+str(self.n_hits))
        print('cells_with_any_results: '+str(self.n_cells_with_res)+' / '+str(self.n_cells)+
              '  full_cells: '+str(self.n_full_cells)+' / '+str(self.n_cells))
    
    def plot_all_results(self):
        s_rev = self.s.copy()
        s_rev.reverse()
        for i in s_rev:
            print(*i)
        print('x-axis: '+self.x+' y-axis: '+self.y+'  n_hits: '+str(self.n_hits))
        print('cells_with_any_results: '+str(self.n_cells_with_res)+' / '+str(self.n_cells)+
              '  full_cells: '+str(self.n_full_cells)+' / '+str(self.n_cells))
    
    def reset(self):
        self.n_hits = 0
        self.s = []
        for i in range(self.ry):
            xs = []
            for j in range(self.rx):
                if self.map_proj[j,i] == 0:
                    xs.append(' ')
                else:
                    xs.append('·')
            self.s.append(xs)

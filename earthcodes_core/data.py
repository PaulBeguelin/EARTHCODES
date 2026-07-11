#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 17:07:48 2026

@author: paulbeguelin
"""

import numpy as np
import pandas as pd

class data:
    def __init__(self, Data):
        if isinstance(Data, pd.DataFrame):
            self.data = data
        else:
            self.data = pd.read_excel(Data)
    
    def grid(self, observables, obs): # both the observables table and the obs dict are arguments, to avoid issues with the order of isotope ratios (uses the order in obs, like in the model).
        self.iso = obs['R']
        self.dat = np.array(self.data[self.iso])
        self.dat = self.dat.T
        self.res = np.array(observables.loc[1, self.iso], dtype=int)
        self.R_min = np.array(observables.loc[2, self.iso])
        self.R_max = np.array(observables.loc[3, self.iso])
        self.R_rg = self.R_max - self.R_min
        self.map = np.zeros(tuple(self.res), dtype=bool)
        self.dat_idx0 = (self.dat - self.R_min.reshape(-1,1)) * self.res.reshape(-1,1) / self.R_rg.reshape(-1,1)
        self.dat_idx = self.dat_idx0.astype(int)
        self.map[tuple(self.dat_idx)] = True
        self.cells, self.n_samples = np.unique(self.dat_idx, axis=1, return_counts=True)
        self.c_dic = {}
        for i in range(self.cells.shape[1]):
            self.c_dic[tuple(self.cells[:, i])] = {'n_samples': self.n_samples[i], 'n_results': 0}
    
    def results_init(self, vars_list):
        self.results = self.data.copy()
        self.results['cell'] = ''
        self.results['idx'] = np.empty((len(self.results), 0)).tolist()
        self.results['any_results'] = False
        self.results['n_results'] = 0
        self.results['medoid_idx'] = np.nan
        
        for i in vars_list:
            self.results[i + '_medoid'] = np.nan
        for i in vars_list:
            self.results[i + '_MAD'] = np.nan
        
        ii = 0
        self.str_cells_dic = {}
        for i in self.results.index:
            self.str_cells_dic[str(tuple(self.dat_idx[:, ii]))] = tuple(self.dat_idx[:, ii])
            self.results.at[i, 'cell'] = str(tuple(self.dat_idx[:, ii]))
            ii += 1
        for i in self.c_dic.keys():
            self.c_dic[i]['res_idx'] = []

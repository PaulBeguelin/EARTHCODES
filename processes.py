#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 17:51:10 2026

@author: paulbeguelin
"""

from dataclasses import dataclass
from .reservoir import ReservoirState
import numpy as np
import pandas as pd

libs = pd.read_excel('Libraries.xlsx', None)

# This function updates the isotope composition of a reservoir from a t value to another. t values are entered in Ga (e.g. enter 1.5 for 1,500,000,000 years)
def decay(ins, t_old, t_new, obs): # obs: observables dict. Has keys ['C', 'R', 'idx', 'decay']. 'C', 'R' are ordered keys list, 'idx' is a dict with keys ['P', 'D'] of the index list corresponding 'C' array for parent and daughter elements, 'decay' is a dict of keys ['lambda', 'branched', 'PD_calc'] with decay and P/D conversion parameters.
    out = []
    for i in ins:
        out.append(i.copy())
        
    t_old = t_old * 1e9
    t_new = t_new * 1e9
    
    PD = (ins[0].C[obs['idx']['P']] / ins[0].C[obs['idx']['D']]) * obs['decay']['PD_calc'].reshape(-1,1)
    
    out[0].R = ins[0].R + PD * obs['decay']['branched'].reshape(-1,1) * (np.exp(obs['decay']['lambda'].reshape(-1,1) * t_old) - np.exp(obs['decay']['lambda'].reshape(-1,1) * t_new))
    
    return out

@dataclass
class param:
    name: str
    param_type: str
    validation: bool
    headers: list
    options: list
    val: list | None = None
    idx: int = 0


class process:
    def __init__(self, obs):
        self.obs = obs
        self.params = {}
        self.reservoir_states = {}
        self.output_vars = {}

    def get_var(self, p, name):
        var = self.params[name]
        vmin, vmax = var.val
        return p[var.idx] * (vmax - vmin) + vmin
    
    def get_err(self, p, name):
        var = self.params[name]
        vmin, vmax = var.val
        return p[var.idx] * (vmax - vmin)

    def report(self, indexes=None):
        
        def filt(x):
            if indexes == None:
                return x
            elif len(x.shape) == 1:
                return x[indexes]
            elif len(x.shape) == 2:
                return x[:, indexes]
        
        def get_fields(res):
            return filt(res.C), filt(res.R), filt(res.P)
        
        dic = {}
        
        for i in self.reservoir_states.keys():
            resC, resR, resP = get_fields(self.reservoir_states[i])
            
            dic[i] = (
                     {key: resC[ii] for ii, key in enumerate(self.obs['C'])} |
                     {key: resR[ii] for ii, key in enumerate(self.obs['R'])} |
                     {key: resP[ii] for ii, key in enumerate(self.obs['P'])}
            )

        for i in self.output_vars.keys():
            dic[i] = filt(self.output_vars[i])
        
        return dic


class edit(process):
    '''
    This class edits a reservoir with a given elemental and isotopic composition.
    This can be used to initialise a reservoir or to change its composition while keeping the isotope ratios the same.
    Example 1: BSE initialisation
    Example 2: CC to GLOSS
    '''
    def __init__(self, obs): # C_keys and R_keys: list of keys (elements, isotope ratios) to edit.
        super().__init__(obs)    
        
        self.lib = libs['Compositions']
        
        self.params['Comp_name'] = param(name = 'Composition from library (if needed, add a custom composition in the library, save and re-initialise model to update options)',
                                         param_type = 'constant',
                                         validation = True,
                                         headers = ['select:'],
                                         options = [list(self.lib['name'])])
        
        self.params['Keys_used'] = param(name = 'Element and isotope ratios to overwrite',
                                         param_type = 'constant',
                                         validation = True,
                                         headers = self.obs['C'] + self.obs['R'],
                                         options = len(self.obs['C'] + self.obs['R']) * [['yes', 'no']])
        
        if len(self.obs['P']) > 0:
            
            self.params['Phys_P'] = param(name = 'Physical parameters to overwrite',
                                          param_type = 'constant',
                                          validation = True,
                                          headers = self.obs['P'],
                                          options = len(self.obs['P']) * [['yes', 'no']])
            
            self.params['Phys_P_val'] = param(name = 'Values to edit physical parameters to',
                                          param_type = 'constant',
                                          validation = False,
                                          headers = self.obs['P'],
                                          options = len(self.obs['P']) * [[]])
        
        
    def setup(self):
        self.comp = self.lib[self.lib.name == self.params['Comp_name'].val[0]]
        self.Keys_used_dict = {}
        ii = 0
        for i in self.obs['C'] + self.obs['R']:
            if self.params['Keys_used'].val[ii] == 'yes':
                self.Keys_used_dict[i] = True
            else:
                self.Keys_used_dict[i] = False
            ii += 1
        self.new_C = []
        self.new_R = []
        self.new_C_idx = []
        self.new_R_idx = []
        for i in self.obs['C']:
            if self.Keys_used_dict[i]:
                self.new_C.append(float(self.comp[i].iloc[0]))
                self.new_C_idx.append(self.obs['C'].index(i))
        for i in self.obs['R']:
            if self.Keys_used_dict[i]:
                self.new_R.append(float(self.comp[i].iloc[0]))
                self.new_R_idx.append(self.obs['R'].index(i))
        self.new_C = np.array(self.new_C).reshape(-1,1)
        self.new_R = np.array(self.new_R).reshape(-1,1)
        
        if 'Phys_P' in self.params.keys():
            self.param_vals = self.params['Phys_P_val'].val
            self.new_P = []
            self.new_P_idx = []
            ii = 0
            for i in self.obs['P']:
                if self.params['Phys_P'].val[ii] == 'yes':
                    self.new_P_idx.append(ii)
                    self.new_P.append(self.param_vals[ii])
                ii += 1
            self.new_P = np.array(self.new_P).reshape(-1,1)
    
    def run(self, ins, p): # ins is a list of reservoir dict, p is the parameters array
        self.ins = ins
        
        self.out = []
        for i in self.ins:
            self.out.append(i.copy())
            
        self.out[0].C[self.new_C_idx] = self.new_C
        self.out[0].R[self.new_R_idx] = self.new_R
        if 'Phys_P' in self.params.keys():
            self.out[0].P[self.new_P_idx] = self.new_P
        
        self.reservoir_states['in'] = self.ins[0]
        self.reservoir_states['out'] = self.out[0]


class mix(process):
    '''
    This class calculates the mixing of two reservoirs with a mixing proportion X, which is the proportion for the second reservoir (reservoir_B).
    '''
    def __init__(self, obs):
        super().__init__(obs)
        
        self.params['X'] = param(name = 'Proportion X of the second reservoir (= component 2) in the mixture (must be between 0 and 1)',
                                         param_type = 'variable',
                                         validation = False,
                                         headers = ['min', 'max'],
                                         options = [[], []])
        
        self.params['F_corr'] = param(name = 'Correct X for F of the latest melting event? (relevant for melts and possible if F_i is tracked in the model)',
                                         param_type = 'constant',
                                         validation = True,
                                         headers = ['Component 1', 'Component 2'],
                                         options = [['no', 'yes'], ['no', 'yes']])
        
    
    def setup(self):
        self.F_corr0 = False
        self.F_corr1 = False
        if self.params['F_corr'].val[0] == 'yes':
            self.F_corr0 = True
        if self.params['F_corr'].val[1] == 'yes':
            self.F_corr1 = True
        self.F_fac_0 = 1
        self.F_fac_1 = 1
    
    def run(self, ins, p): # ins is the two reservoir comopsitions in a list or tuple, p is the params distribution inputs array
        self.ins = ins
        
        self.X_var = self.get_var(p, 'X')
        
        if self.F_corr0:
            self.F_fac_0 = ins[0].P[self.obs['P'].index('F_i')]
        if self.F_corr1:
            self.F_fac_1 = ins[1].P[self.obs['P'].index('F_i')]
        
        self.X = self.X_var * self.F_fac_1 / (self.X_var * self.F_fac_1 + (1 - self.X_var) * self.F_fac_0)
        
        self.mix_C = ins[0].C * (1 - self.X) + ins[1].C * self.X
        self.mix_RC = ins[0].C[self.obs['idx']['D']] * (1 - self.X) + ins[1].C[self.obs['idx']['D']] * self.X
        self.mix_R = (ins[0].R * ins[0].C[self.obs['idx']['D']] * (1 - self.X) + ins[1].R * ins[1].C[self.obs['idx']['D']] * self.X) / self.mix_RC
        
        self.new_P = ins[0].P.copy()
        self.new_P[self.obs['P'].index('Fd')][:] = 0
        self.new_P[self.obs['P'].index('F_i')][:] = 0
        
        self.out = [ReservoirState(C=self.mix_C, R=self.mix_R, P=self.new_P)]
        
        self.reservoir_states['in1'] = self.ins[0]
        self.reservoir_states['in2'] = self.ins[1]
        self.reservoir_states['out'] = self.out[0]
        
        self.output_vars['X'] = self.X_var
        self.output_vars['Actual X'] = self.X # Actual X is the proportion used in the final mixing calculation. It will differ from (the given) X if it has been corrected for the latest melting event.


class melt(process):
    '''
    This class calculates the modal accumulated fractional melting a source. It returns a melt and a restite as outputs.
    Outputs are a dict with 'melt' and 'restite' as keys that contain the names of the destination reservoirs (as entered in __init__).
    If either is not to be saved, initialize with None (e.g. for early mantle depletion where only the restite is of interest, or for present-day melting where only the melt is of interest).
    Parameters include:
        'F': Degree of melting
        'Kds': Dict of the solid/liquid partition coefficients to be used
        'X': If restite_homogenisation=True, this is the proportion of the source affected by melting, before re-homogenisation with the restite
            For example, if 'X' = 0.8, 80% of the source sees some melting with degree F (e.g. 0.1). The restite is then mixed with the 20% of the source that saw no melting at all.
            If restite_homogenisation=False, 'X' is set to 1.
            For more details on this parametrisation, see Béguelin et al (2025, G-Cubed): https://doi.org/10.1029/2025GC012357
    '''
    def __init__(self, obs):
        super().__init__(obs)
        
        self.lib = libs['Kds']
        
        self.params['F'] = param(name = 'Melting degree (must be between 0 and 1)',
                                         param_type = 'variable',
                                         validation = False,
                                         headers = ['min', 'max'],
                                         options = [[], []])
        
        self.params['X'] = param(name = 'Proportion of the source affected by melting before re-homogenisation with the restite (must be between 0 and 1, keep at 1 for no re-homogenisation)',
                                         param_type = 'variable',
                                         validation = False,
                                         headers = ['min', 'max'],
                                         options = [[], []])
        
        self.params['Kds'] = param(name = 'Set of solid/liquid partition coefficients from the library to be used (if needed, add custom Kds in the library, save and re-initialise model to update options)',
                                         param_type = 'constant',
                                         validation = True,
                                         headers = ['select:'],
                                         options = [list(self.lib['name'])])
        
        
    def setup(self):
        self.Kds_df = self.lib[self.lib.name == self.params['Kds'].val[0]]
        self.Kds = []
        for i in self.obs['C']:
            self.Kds.append(float(self.Kds_df[i].iloc[0]))
        self.Kds = np.array(self.Kds)
            
    def run(self, ins, p):
        self.ins = ins
        
        self.F = self.get_var(p, 'F')
        self.X = self.get_var(p, 'X')
        
        self.source = ins[0].C
        self.melt = self.source * (1 / self.F) * (1 - (1 - self.F) ** (1 / self.Kds.reshape(-1,1)))
        self.restite = self.source * (1 - self.F) ** (1 / self.Kds.reshape(-1,1) - 1) * self.X + self.source * (1 - self.X)
        
        self.p_melt = ins[0].P.copy()
        self.p_restite = ins[0].P.copy()
        
        self.p_melt[self.obs['P'].index('Fd')][:] = 0
        self.p_melt[self.obs['P'].index('F_i')] = self.F
        
        self.p_restite[self.obs['P'].index('Fd')] = self.F * self.X * (1 - self.p_restite[self.obs['P'].index('Fd')]) + self.p_restite[self.obs['P'].index('Fd')]
        self.p_restite[self.obs['P'].index('F_i')][:] = 0
        
        self.out = {'melt': [ReservoirState(C=self.melt, R=ins[0].R.copy(), P=self.p_melt)],
                    'restite': [ReservoirState(C=self.restite, R=ins[0].R.copy(), P=self.p_restite)]}
        
        self.reservoir_states['in'] = self.ins[0]
        self.reservoir_states['melt'] = self.out['melt'][0]
        self.reservoir_states['restite'] = self.out['restite'][0]
        
        self.output_vars['F'] = self.F
        self.output_vars['X'] = self.X


class uptake(process):
    '''
    This class modifies the trace element abundances of a source as would be done through alteration.
    This is done by trace element addition. Unlike for mixing, no mass is added to the source in the model.
    Parameters include:
        Max_budget: Dict of the maximum trace element addition budgets considered
        f: Magnidude of uptake. Between 0 and 1: 0 is no addition, 1 is an addition of magnitude Max_budget
    '''
    def __init__(self, obs):
        super().__init__(obs)
        
        self.lib = libs['Uptake']
        
        self.params['Max_budget'] = param(name = 'Maximum trace element addition budgets from the library to be considered (if needed, add custom budget in the library, save and re-initialise model to update options)',
                                         param_type = 'constant',
                                         validation = True,
                                         headers = ['select:'],
                                         options = [list(self.lib['name'])])
        
        self.params['f'] = param(name = 'Magnidude of uptake. Between 0 and 1: 0 is no addition, 1 is an addition of magnitude Max_budget',
                                         param_type = 'variable',
                                         validation = False,
                                         headers = ['min', 'max'],
                                         options = [[], []])
        
    
    def setup(self):
        self.Max_budget_df = self.lib[self.lib.name == self.params['Max_budget'].val[0]]
        self.Max_budget = []
        daughters = []
        for i in self.obs['idx']['D']:
            daughters.append(self.obs['C'][i])
        for i in self.obs['C']:
            self.Max_budget.append(float(self.Max_budget_df[i].iloc[0]))
            if self.Max_budget[-1] > 0 and i in daughters:
                raise ValueError('A daughter element is included in the ' + self.lib.name.iloc[0] + ' uptake budget. Make sure the budget is zero that that element, or use mix instead with a given radiogenic isotope composition for the fluid phase.')
        self.Max_budget = np.array(self.Max_budget)
    
    def run(self, ins, p):
        self.ins = ins
        
        self.f = self.get_var(p, 'f')
        
        self.out = [ins[0].copy()]
        self.out[0].C += self.f * self.Max_budget.reshape(-1,1)
        
        self.reservoir_states['in'] = self.ins[0]
        self.reservoir_states['out'] = self.out[0]
        
        self.output_vars['f'] = self.f


class leach(process):
    '''
    This class modifies the trace element abundances of a source as would be done through dehydration.
    This is done by multiplying source trace element abundances by (1 - Max_leach * f).
    Unlike for mixing, no mass is added to the source in the model.
    Parameters include:
        Max_leach: numpy array of mobility coefficients during leaching. Immobile elements have a Max_leach value of 0. Fully mobile elements have a value of 1.
        f: magnitude of leaching. Between 0 and 1: 0 is no modification, 1 is a modification of magnitude Max_leach.
    '''
    def __init__(self, obs):
        super().__init__(obs)
        
        self.lib = libs['Leach']
        
        self.params['Max_leach'] = param(name = 'Mobility coefficients during leaching from the library. Immobile elements have a Max_leach value of 0. Fully mobile elements have a value of 1 (if needed, add custom budget in the library, save and re-initialise model to update options)',
                                         param_type = 'constant',
                                         validation = True,
                                         headers = ['select:'],
                                         options = [list(self.lib['name'])])
        
        self.params['f'] = param(name = 'Magnidude of leaching. Between 0 and 1: 0 is no modification, 1 is a modification of magnitude Max_leach',
                                         param_type = 'variable',
                                         validation = False,
                                         headers = ['min', 'max'],
                                         options = [[], []])
        
    def setup(self):
        self.Max_leach_df = self.lib[self.lib.name == self.params['Max_leach'].val[0]]
        self.Max_leach = []
        for i in self.obs['C']:
            self.Max_leach.append(float(self.Max_leach_df[i].iloc[0]))
        self.Max_leach = np.array(self.Max_leach)
    
    def run(self, ins, p):
        self.ins = ins
        
        self.f = self.get_var(p, 'f')
        
        self.out = [ins[0].copy()]
        self.out[0].C = self.out[0].C * (1 - self.f * self.Max_leach.reshape(-1,1))
        
        self.reservoir_states['in'] = self.ins[0]
        self.reservoir_states['out'] = self.out[0]
        
        self.output_vars['f'] = self.f


# Processes directory
processes_directory = {
    'mix': mix,
    'melt': melt,
    'uptake': uptake,
    'leach': leach,
    'edit': edit}

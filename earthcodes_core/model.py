#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 17:19:09 2026

@author: paulbeguelin
"""

import numpy as np
import pandas as pd
from earthcodes_core import processes
from earthcodes_core import data
from earthcodes_io import model_setup
#from earthcodes_io import plot_options #Under development, sorry
from earthcodes_io import results
from earthcodes_engines import beta_engines
import earthcodes_utils
from earthcodes_core.reservoir import ReservoirState
from earthcodes_vis import ascii_plotting

import warnings
from pandas.errors import PerformanceWarning
warnings.simplefilter(action='ignore', category=PerformanceWarning)

class model_event:
    def __init__(self, process, time, arguments, arg_txt, comment, obs):
        self.name = process
        self.time = time
        self.arguments = arguments
        self.arg_txt = arg_txt
        self.comment = comment
        
        if self.name in processes.processes_directory:
            self.fn = processes.processes_directory[self.name](obs)
        else:
            return 'ERROR: ' + self.name + ' is not an available process module (see list in the processes directory in earthcodes_core/processes.py).'

class reservoir:
    def __init__(self, full_name):
        self.name = full_name
        self.events = {}
        self.times = {}
        self.comments = {}
        
    def add_event(self, idx, event: model_event):
        self.events[idx] = event

class model_tree:
    def __init__(self):
        self.reservoirs = {}
        self.times = []
        self.run_order = []
    
    def add_reservoir(self, name, reservoir: reservoir):
        self.reservoirs[name] = reservoir

class model:
    
    def __init__(self):
        self.data = None
        self.model_built = False
        
        self.model_setup = False
        self.run_data = {'engine': None,
                         'eng_weight': None,
                         'ID': None,
                         'params': None,
                         'cells': None,
                         'rarity': None}
        self.any_run_results = False
        self.max_results_per_cell = 100
        self.ascii = None
        
    def build(self, filename, overwrite=False):
        self.observables, self.obs, self.C_check_idx, self.C_min, self.C_max, self.dic, self.times, run_order = model_setup.read_arch(filename)
        self.arch_filename = filename
        self.tree = model_tree()
        self.tree.times = self.times
        self.tree.run_order = run_order
        for i in self.dic.keys():
            self.tree.add_reservoir(i, reservoir(self.dic[i]['name']))
            
        for i in self.tree.run_order:
            process = self.dic[i[0]]['processes'][i[1]]
            comment = self.dic[i[0]]['comments'][i[1]]
            self.tree.reservoirs[i[0]].add_event(i[1], model_event(process['fn_name'], i[2], process['args'], process['args_txt'], comment, self.obs))
            self.tree.reservoirs[i[0]].times[i[1]] = i[2]
            self.tree.reservoirs[i[0]].comments[i[1]] = comment
        
        model_setup.control_sheet_out(self.tree, self.times, filename, overwrite)
        self.model_built = True
        
    def read_setup(self, filename=None):
        if not self.model_built:
            return 'ERROR: No model built yet. To get started, use the .build() method with the model architecture filename as an argument.'
        if filename == None:
            filename = self.arch_filename
        if '.xlsx' not in filename:
            return 'ERROR: Control workbook must end with the .xlsx extension.'
        self.times_rg, self.model_vars, self.var_rg, self.var_descr = model_setup.read_setup(filename, self.tree)
        self.model_setup = True
    
    def read_data(self, filename, group_level_for_series='Group_1', key_filename='New_data_key.xlsx', overwrite=False):
        if not self.model_built:
            return 'ERROR: No model built yet. Model architecture must be known to set up the model target grid. If you just want to look at data, create an instance of the data() class outside of the model class.'
        self.data = data.data(filename)
        self.data.grid(self.observables, self.obs)
        #plot_options.new_key(self.data.data, group_level_for_series) #Under development, sorry

    def compute(self, p, comments=False):
        n = int(p.shape[1])
        for i in self.times_rg.keys():
            self.times_rg[i]['arr'] = p[self.times_rg[i]['idx']] * (self.times_rg[i]['max'] - self.times_rg[i]['min']) + self.times_rg[i]['min']
        
        self.ins0 = [ReservoirState(
            C=np.full((len(self.obs['C']), n), np.nan),
            R=np.full((len(self.obs['R']), n), np.nan),
            P=np.full((len(self.obs['P']), n), np.nan)
        )]

        reservoir = None
        for i in self.tree.run_order:
            cl = self.tree.reservoirs[i[0]].events[i[1]].fn
            args = self.tree.reservoirs[i[0]].events[i[1]].arguments
            if i[0] != reservoir:
                ins = self.ins0
                t = i[2]
            if args:
                ins = []
                for j in args:
                    if len(j) > 2:
                        arg_j = self.tree.reservoirs['Reservoir_'+j[0]].events[j[1]].fn.out[j[2]][0]
                    else:
                        arg_j = self.tree.reservoirs['Reservoir_'+j[0]].events[j[1]].fn.out[0]
                    t_j = self.tree.reservoirs['Reservoir_'+j[0]].times[j[1]]
                    
                    if t_j != i[2]: #WARNING: This is not used in the development scenario and is therefore untested!
                        decay_out = processes.decay([arg_j], self.times_rg[t_j]['arr'], self.times_rg[i[2]]['arr'], self.obs)
                        arg_j = decay_out[0]
                        if comments:
                            print('decay '+t_j+' to '+ i[2])
                    ins.append(arg_j)
           
            elif t != i[2]:
                decay_out = processes.decay(ins, self.times_rg[t]['arr'], self.times_rg[i[2]]['arr'], self.obs)
                ins = decay_out
                if comments:
                    print('decay '+t+' to '+ i[2])
            cl.run(ins, p)
            ins = cl.out
            reservoir = i[0]
            t = i[2]
            if comments:
                print(i)
        self.out_temp = ins[0]
    
    def free(self, n_sims=1000, engine='naive_MC'):
        self.engine_name = engine
        self.engine = beta_engines.engines_directory[self.engine_name](len(self.model_vars), n_sims)
        self.compute(self.engine.dist['params'])
        self.free_params = self.engine.dist['params']
    
    def run(self, n_loops, n_sims=5e4, engine='naive_MC', plots=True, view=True, results_sheet_out=True):
        if self.model_built == False:
            return 'ERROR: No model architecture file read yet. To get started, use the .build() method with the name of the model architecture file as an argument.'
        if self.model_setup == False:
            return 'ERROR: No model control workbook file read yet. To get started, use the .read_setup() method.'
        
        self.engine_name = engine
        self.engine = beta_engines.engines_directory[self.engine_name](len(self.model_vars), n_sims)
        check_dist = False
        
        self.dist_to_valid_temp = None
        self.valid_ends_temp = None
        
        if plots:
            self.ascii = ascii_plotting.ASCII_plotting(self.observables, self.data, self.max_results_per_cell)
        
        for i in range(n_loops):
            self.compute(self.engine.dist['params'])
            self.check(check_dist)
            self.store_results()
            
            counter = str(i+1) + ' / ' + str(n_loops)
            
            if plots:
                self.ascii.update_ASCII_display(counter, self.cells_temp, self.run_data['cells'])
                self.ascii.show(self.ascii.playlist[i % len(self.ascii.playlist)])
            elif i%10 == 9:
                print(counter)
            
            if 'valid_ends' in self.engine.params and self.run_data['rarity'] is not None:
                valid_ends_idxs = np.random.choice(np.arange(self.run_data['rarity'].size), int(n_sims/2), p=self.run_data['rarity']**3/np.sum(self.run_data['rarity']**3))
                self.valid_ends_temp = self.run_data['params'][:, valid_ends_idxs]
            
            self.engine.update(self.mask_temp, self.dist_to_valid_temp, self.valid_ends_temp)
        
        if view:
            self.view()
        
        if self.any_run_results and results_sheet_out:
            results.res_sheet(self.var_descr, self.tree)


    def check(self, check_dist=False, max_per_cell=True):
        self.dist_to_valid_temp = None
        if check_dist:
            out_exp_idx00 = (self.out_temp.R - self.data.exp_R_min.reshape(-1,1)) * self.data.exp_res.reshape(-1,1) / self.data.exp_R_rg.reshape(-1,1)
            out_exp_idx0 = out_exp_idx00.astype(int)
            R_exp_ranges_mask = np.all(self.out_temp.R > self.data.exp_R_min.reshape(-1,1), axis=0) * np.all(self.out_temp.R < self.data.exp_R_max.reshape(-1,1), axis=0)
            out_exp_idx = out_exp_idx0[:, R_exp_ranges_mask]
            self.dist_to_valid_temp = np.zeros(self.out_temp.R.shape[1], dtype=np.uint8)
            self.dist_to_valid_temp[~R_exp_ranges_mask] = 255
            dist_in_range = self.data.exp_grid[tuple(out_exp_idx)]
            self.dist_to_valid_temp[R_exp_ranges_mask] = dist_in_range
        
        self.out_idx00 = (self.out_temp.R - self.data.R_min.reshape(-1,1)) * self.data.res.reshape(-1,1) / self.data.R_rg.reshape(-1,1)
        self.out_idx0 = self.out_idx00.astype(int)
        
        self.R_ranges_mask = np.all(self.out_temp.R > self.data.R_min.reshape(-1,1), axis=0) * np.all(self.out_temp.R < self.data.R_max.reshape(-1,1), axis=0)
        self.C_ranges_mask = np.all(self.out_temp.C[self.C_check_idx] > self.C_min.reshape(-1,1), axis=0) * np.all(self.out_temp.C[self.C_check_idx] < self.C_max.reshape(-1,1), axis=0)
        self.ranges_mask = self.R_ranges_mask * self.C_ranges_mask
        
        self.out_idx = self.out_idx0[:, self.ranges_mask]
        self.match_cell_mask = self.data.map[tuple(self.out_idx)]
        self.cells_temp0 = self.out_idx[:, self.match_cell_mask]
        
        self.match_cell_mask1 = np.zeros(self.cells_temp0.shape[1], dtype=bool)
        
        for i in range(self.cells_temp0.shape[1]):
            if max_per_cell == False:
                self.match_cell_mask1[i] = True
                self.data.c_dic[tuple(self.cells_temp0[:, i])]['n_results'] += 1
            elif self.data.c_dic[tuple(self.cells_temp0[:, i])]['n_results'] < self.max_results_per_cell:
                self.match_cell_mask1[i] = True
                self.data.c_dic[tuple(self.cells_temp0[:, i])]['n_results'] += 1
        self.match_cell_mask[self.match_cell_mask] = self.match_cell_mask1
        
        self.mask_temp = np.zeros(self.out_idx0.shape[1], dtype=bool)
        self.mask_temp[self.ranges_mask] = self.match_cell_mask
        
        self.cells_temp = self.out_idx0[:, self.mask_temp]
        
    def store_results(self):
        if self.any_run_results == False and self.mask_temp.sum() > 0:
            self.run_data['engine'] = self.engine.dist['engine'][self.mask_temp]
            self.run_data['eng_weight'] = self.engine.dist['eng_weight'][self.mask_temp]
            self.run_data['ID'] = self.engine.dist['ID'][self.mask_temp]
            self.run_data['params'] = self.engine.dist['params'][:, self.mask_temp]
            self.run_data['cells'] = self.cells_temp
            self.any_run_results = True
            
        elif self.any_run_results and self.mask_temp.sum() > 0:
            self.run_data['engine'] = np.append(self.run_data['engine'], self.engine.dist['engine'][self.mask_temp])
            self.run_data['eng_weight'] = np.append(self.run_data['eng_weight'], self.engine.dist['eng_weight'][self.mask_temp])
            self.run_data['ID'] = np.append(self.run_data['ID'], self.engine.dist['ID'][self.mask_temp])
            self.run_data['params'] = np.append(self.run_data['params'], self.engine.dist['params'][:, self.mask_temp], axis=1)
            self.run_data['cells'] = np.append(self.run_data['cells'], self.cells_temp, axis=1)
            
        self.update_rarity()

    def update_rarity(self):
        if self.run_data['cells'] is not None:
            unique, inverse, counts = np.unique(self.run_data['cells'], return_inverse=True, return_counts=True, axis=1)
            self.run_data['rarity'] = 1 / counts[inverse]
    
    def view(self):
        if self.any_run_results == False:
            return 'No results yet.'
        self.compute(self.run_data['params'])
        
        vars_list = list(self.var_rg.keys())
        self.data.results_init(vars_list)
        
        for i in range(self.run_data['params'].shape[1]):
            ref = tuple(self.run_data['cells'][:, i])
            self.data.c_dic[ref]['res_idx'].append(i)
        for i in self.data.results.index:
            self.data.results.at[i, 'idx'] += self.data.c_dic[self.data.str_cells_dic[self.data.results.loc[i, 'cell']]]['res_idx']
            self.data.results.at[i, 'n_results'] = len(self.data.results.loc[i, 'idx'])
            if len(self.data.results.loc[i, 'idx']) > 0:
                self.data.results.at[i, 'any_results'] = True
            
                try:
                    idx, medoid, MAD = earthcodes_utils.medoid(self.run_data['params'][:, list(self.data.results.loc[i, 'idx'])])
                    self.data.results.at[i, 'medoid_idx'] = list(self.data.results.loc[i, 'idx'])[idx]
                    
                    for j in vars_list:
                        if j in self.times:
                            medoid_j = medoid[self.times_rg[j]['idx']] * (self.times_rg[j]['max'] - self.times_rg[j]['min']) + self.times_rg[j]['min']
                            MAD_j = MAD[self.times_rg[j]['idx']] * (self.times_rg[j]['max'] - self.times_rg[j]['min'])
                        else:
                            jj = j.split('/')
                            medoid_j = self.tree.reservoirs[jj[0]].events[jj[1]].fn.get_var(medoid, jj[2])
                            MAD_j = self.tree.reservoirs[jj[0]].events[jj[1]].fn.get_err(MAD, jj[2])
                        
                        self.data.results.at[i, j+'_medoid'] = medoid_j
                        self.data.results.at[i, j+'_MAD'] = MAD_j
                    
                except Exception:
                    pass
        
        if self.ascii == None:
            self.ascii = ascii_plotting.ASCII_plotting(self.observables, self.data, self.max_results_per_cell)
        self.ascii.fill_displays(self.run_data)
    
    def get(self, reservoir, event, part=None, variable=None, idx=None):
        
        dic00 = self.tree.reservoirs[reservoir].events[event].fn.report(idx)
        
        if part:
            dic0 = dic00[part]
        else:
            dic0 = dic00
        
        if variable:
            dic = dic0[variable]
        else:
            dic = dic0
        
        return dic

    
    def out(self, group_level='all', results_selection_workbook='Results_selection.xlsx'):
        if self.any_run_results == False:
            return 'No results yet.'
        res_vars, in_out_vars = results.read_res_sheet(self.obs, name=results_selection_workbook)
        
        table0 = self.data.data.copy()
        table0['n_results'] = self.data.results['n_results']
        
        for i in res_vars.keys():
            table0[res_vars[i]] = self.data.results[i + '_medoid']
        for i in res_vars.keys():
            table0[res_vars[i] + '_error'] = self.data.results[i + '_MAD']
        
        for i in in_out_vars.keys():
            table0[in_out_vars[i]] = np.nan
        for i in in_out_vars.keys():
            table0[in_out_vars[i] + '_error'] = np.nan
            
        for i in in_out_vars.keys():
            ii = i.split('/')
            reservoir = ii[0]
            event = ii[1]
            if len(ii) == 4:
                part = ii[2]
                variable = ii[3]
            else:
                part = None
                variable = ii[2]
            
            val0 = self.get(reservoir, event, part, variable)
            
            for j in range(len(table0)):
                if self.data.results.at[j, 'any_results']:
                    val = val0[self.data.results.at[j, 'idx']]
                    table0.at[j, in_out_vars[i]] = np.nanmedian(val)
                    table0.at[j, in_out_vars[i] + '_error'] = np.nanmedian(np.abs(val - np.nanmedian(val)))
        
        self.results = {}
        self.results['all'] = table0
        
        if 'Group' in group_level and group_level in self.data.data.columns:
            groups = list(dict.fromkeys(self.data.data[group_level]))
            table = pd.DataFrame(index=groups, columns=['n_samples', 'n_cells', 'n_cells_with_results', 'n_samples_with_results'])
            
            for i in res_vars.keys():
                table[res_vars[i]] = np.nan
            for i in res_vars.keys():
                table[res_vars[i] + '_stdev'] = np.nan
            for i in in_out_vars.keys():
                table[in_out_vars[i]] = np.nan
            for i in in_out_vars.keys():
                table[in_out_vars[i] + '_stdev'] = np.nan
            
            for i in groups:
                table.at[i, 'n_samples'] = sum(self.data.data[group_level] == i)
                results_i = self.data.results[self.data.results[group_level] == i]
                cells_i = set(results_i['cell'])
                table.at[i, 'n_cells'] = len(cells_i)
                n_cells_with_res = 0
                for j in cells_i:
                    if results_i.loc[results_i['cell'] == j, 'n_results'].iloc[0] > 0:
                        n_cells_with_res += 1
                table.at[i, 'n_cells_with_results'] = n_cells_with_res
                table.at[i, 'n_samples_with_results'] = sum(results_i.any_results)
                
                if n_cells_with_res > 0:
                    for j in res_vars.keys():
                        table.at[i, res_vars[j]] = np.nanmean(table0.loc[table0[group_level] == i, res_vars[j]])
                        table.at[i, res_vars[j] + '_stdev'] = np.nanstd(table0.loc[table0[group_level] == i, res_vars[j]])
                    for j in in_out_vars.keys():
                        table.at[i, in_out_vars[j]] = np.nanmean(table0.loc[table0[group_level] == i, in_out_vars[j]])
                        table.at[i, in_out_vars[j] + '_stdev'] = np.nanstd(table0.loc[table0[group_level] == i, in_out_vars[j]])
            
            self.results[group_level] = table
            
            with pd.ExcelWriter(' Model_results.xlsx') as writer:
                for i in self.results.keys():
                    self.results[i].to_excel(writer, sheet_name=i)
        
        

    def save(self, filename, overwrite=False):
        if self.any_run_results == False:
            return 'ERROR: No results to save.'
        if '.npz' not in filename:
           filename += '.npz'
        if earthcodes_utils.file_exists(filename) and overwrite == False:
            return 'ERROR: ' + filename + ' already exists. Running this method will delete it and create a new one. To do this anyway, enter overwrite=True as a method argument.'
        np.savez(filename, engine=self.run_data['engine'], eng_weight=self.run_data['eng_weight'], ID=self.run_data['ID'],
                 params=self.run_data['params'], cells=self.run_data['cells'], allow_pickle=False)
    
    def load(self, filename):
        if '.npz' not in filename:
            return 'ERROR: filename must end with the .npz extension.'
        load = np.load(filename)
        self.compute(load['params'])
        self.check(max_per_cell=False)
        if np.array_equal(self.cells_temp, load['cells']):
            if self.any_run_results == False:
                self.run_data['engine'] = load['engine']
                self.run_data['eng_weight'] = load['eng_weight']
                self.run_data['ID'] = load['ID']
                self.run_data['params'] = load['params']
                self.run_data['cells'] = load['cells']
                self.any_run_results = True
                
            elif self.any_run_results:
                self.run_data['engine'] = np.append(self.run_data['engine'], load['engine'])
                self.run_data['eng_weight'] = np.append(self.run_data['eng_weight'], load['eng_weight'])
                self.run_data['ID'] = np.append(self.run_data['ID'], load['ID'])
                self.run_data['params'] = np.append(self.run_data['params'], load['params'], axis=1)
                self.run_data['cells'] = np.append(self.run_data['cells'], load['cells'], axis=1)
                
            self.update_rarity()
            self.view()
            
        else:
            return 'ERROR: Model failed to reproduce the saved results from the loaded inputs. This means either the model, model cusomisation, data, or modules have changed. If the original model environment cannot be recreated, then the model must be re-ran from the start, sorry.'
    
    def empty_log(self):
        self.any_run_results = False
        self.run_data = {'engine': None,
                         'eng_weight': None,
                         'ID': None,
                         'params': None,
                         'cells': None,
                         'rarity': None}
        self.ascii = None



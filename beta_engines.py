#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 17:49:53 2026

@author: paulbeguelin
"""

import numpy as np
import datetime

# Engines

class naive_MC:
    '''
    This class outputs a distribution to be used as inputs for the variables of the model.
    Array is of shape (n_vars, n_sims) where n_vars is the number of variables and n_sims is the number of simulations to compute at once.
    Values are float in the [0, 1) range to be mapped to actual variables ranges by the model class.
    
    '''
    def __init__(self, n_vars, n_sims=5e4):
        self.params = ['successful_bool_array']
        
        self.n_vars = n_vars
        self.n_sims = n_sims
        
        t_str = str(datetime.datetime.now(datetime.UTC)).split('+')[0] + str(' UTC ' )
        n_str = np.array(np.arange(int(self.n_sims))+1, dtype='<U9')
        
        self.dist = {'engine': np.array(int(self.n_sims) * ['naive_MC']),
                     'eng_weight': np.ones(int(self.n_sims)),
                     'ID': t_str + n_str + ' of ' + str(int(self.n_sims)),
                     'params': np.random.rand(int(self.n_vars), int(self.n_sims))}
        
    def update(self, successful_bool_array, distance_to_valid_array, valid_ends): # The update method is here for compatibility but successful_dist does not influence the output distribution in this simple MC engine (it is a pure brute force algorithm)
        t_str = str(datetime.datetime.now(datetime.UTC)).split('+')[0] + str(' UTC ' )
        n_str = np.array(np.arange(int(self.n_sims))+1, dtype='<U9')
        
        self.dist = {'engine': np.array(int(self.n_sims) * ['naive_MC']),
                     'eng_weight': np.ones(int(self.n_sims)),
                     'ID': t_str + n_str + ' of ' + str(int(self.n_sims)),
                     'params': np.random.rand(int(self.n_vars), int(self.n_sims))}


            
# Engines directory
engines_directory = {
    'naive_MC': naive_MC}






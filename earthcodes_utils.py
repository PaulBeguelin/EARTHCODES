#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 14:11:52 2026

@author: paulbeguelin
"""


from pathlib import Path
import numpy as np
from scipy.spatial.distance import pdist, squareform

def file_exists(path):
    return Path(path).is_file()

def medoid(results):
    '''
    Finds the medoid of a 2D array of shape (n_variables, n_simulations)
    Returns the medoid index, the medoid vector, and its medoid-anchored MAD.
    '''
    n_variables, n_simulations = results.shape
    
    if n_simulations > 1000:
        raise ValueError('The results array is too large, with more than 1000 simulations. Medoid calculations will take too long.')
    
    X = results.T
    
    if n_simulations <= n_variables:
        condensed_distances = pdist(X, metric='euclidean')
        
    else:
        cov_matrix = np.cov(X, rowvar=False)
        try:
            inv_cov = np.linalg.inv(cov_matrix)
            condensed_distances = pdist(X, metric='mahalanobis', VI=inv_cov)
        except np.linalg.LinAlgError:
            condensed_distances = pdist(X, metric='euclidean')
            
    distance_matrix = squareform(condensed_distances)
    medoid_idx = np.argmin(distance_matrix.sum(axis=1))
    
    medoid_vector = results[:, medoid_idx]
    
    absolute_deviations = np.abs(results - medoid_vector[:, np.newaxis])
    medoid_variance = np.median(absolute_deviations, axis=1) * 1.4826
    
    return medoid_idx, medoid_vector, medoid_variance
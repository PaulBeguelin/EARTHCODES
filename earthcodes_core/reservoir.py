#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 12:45:27 2026

@author: paulbeguelin
"""

from dataclasses import dataclass
import numpy as np

@dataclass
class ReservoirState:
    C: np.ndarray
    R: np.ndarray
    P: np.ndarray

    def copy(self):
        return ReservoirState(
            C=self.C.copy(),
            R=self.R.copy(),
            P=self.P.copy()
        )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 17:11:56 2026

@author: paulbeguelin
"""

import numpy as np
import pandas as pd
import xlsxwriter
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
import earthcodes_utils


def new_key(data, group_level_for_series='Group_1', key_filename='New_data_key.xlsx', overwrite=False):
    if '.xlsx' not in key_filename:
        key_filename += '.xlsx'
    if earthcodes_utils.file_exists(key_filename) and not overwrite:
        return 'ERROR: ' + key_filename + ' already exists. Running this method will delete it and create a new one. To do this anyway, enter overwrite=True as a method argument.'
    if 'Group' not in group_level_for_series or group_level_for_series not in data.columns:
        return 'ERROR: group_level_for_series must be a numbered Group part of the headers of the data table (e.g. Group_0, Group_1, etc.). Groups are numbered by hierarchy: e.g. Group_0 = [MORB, OIB], Group_1 = [Iceland, EPR].'
    
    # extracting series
    groups = []
    for i in data.columns:
        if 'Group_' in i:
            groups.append(i)
    groups.sort()
    Group_headers = []
    for i in groups:
        Group_headers.append(i)
        if i == group_level_for_series:
            break
    series = []
    for i in range(len(data)):
        items = list(data.loc[i, Group_headers])
        if items not in series:
            series.append(items)
    
    # sorting through group hierarchy, keeping the order of appearence in the table but avoiding alternance (e.g. ['Pacific', 'Atlantic', 'Pacific'] -> ['Pacific', 'Pacific', 'Atlantic'])
    for i in range(len(Group_headers) - 1):
        series_temp = []
        grps_seen = []
        for j in series:
            if j[i] not in grps_seen:
                grps_seen.append(j[i])
        for j in grps_seen:
            for k in series:
                if k[i] == j:
                    series_temp.append(k)
        series = series_temp
    
    # output a xlsx workbook to customise plotting options
    cs = xlsxwriter.Workbook(key_filename)
    sheets = {}
    sheets['key'] = cs.add_worksheet('Key')
    big_header = cs.add_format({'bold': True, 'align': 'left', 'font_size': 14})
    small_header = cs.add_format({'bold': True, 'align': 'left', 'font_size': 11})
    to_validate = cs.add_format({'border': 1})
    sheets['key'].set_column(1, 1, 20)
    sheets['key'].write_string(0, 0, 'Markers and colour customisation for 2D scatter plots (see Matplotlib online documentation for more details)', big_header)
    sheets['key'].write_string(2, 0, 'Colour options (CSS colour names)', small_header)
    colors = {}
    c_list = sorted(mcolors.CSS4_COLORS, key=lambda c: tuple(mcolors.rgb_to_hsv(mcolors.to_rgb(c))))
    sheets['key'].write_string(3, 1, 'None')
    row = 4
    for i in c_list:
        colors[i] = [mcolors.CSS4_COLORS[i], cs.add_format({'bg_color': mcolors.CSS4_COLORS[i]})]
        sheets['key'].write_string(row, 0, '', colors[i][1])
        sheets['key'].write_string(row, 1, i)
        row += 1
    sheets['key'].write_string(2, 2, 'Markers options', small_header)
    sheets['key'].write_string(3, 2, '(None)')
    row = 4
    m_list = []
    for i in Line2D.markers.keys():
        if i not in ['None', 'none', '', ' ']:
            m_list.append(str(i)+ ' (' + Line2D.markers[i] + ')')
            sheets['key'].write_string(row, 2, m_list[-1])
            row += 1
        sheets['key'].write_string(row, 2, m_list[-1])
    for i in range(len(Group_headers)):
        sheets['key'].set_column(i+5, i+5, 20)
        sheets['key'].write_string(2, i+5, Group_headers[i], small_header)
        for j in range(len(series)):
            sheets['key'].write_string(j+3, i+5, series[j][i])
    sheets['key'].set_column(4, 4, 5)
    col = 5+len(Group_headers)
    sheets['key'].write_string(2, col, 'Plot?', small_header)
    for i in range(len(series)):
        sheets['key'].write(i+3, col, 'yes', to_validate)
        sheets['key'].data_validation(i+3, col, i+3, col, {'validate': 'list', 'source': ['yes', 'no']})
    col += 1
    sheets['key'].set_column(col, col, 2)
    col += 1
    sheets['key'].set_column(col, col, 12)
    sheets['key'].write_string(2, col, 'Select marker:', small_header)
    for i in range(len(series)):
        sheets['key'].write(i+3, col, '(select)', to_validate)
        sheets['key'].data_validation(i+3, col, i+3, col, {'validate': 'list', 'source': 'C'+str(4)+':C'+str(4+len(m_list))})
    col += 1
    sheets['key'].set_column(col, col, 2)
    col += 1
    sheets['key'].write_string(2, col, 'Select face colour:', small_header)
    for i in range(len(series)):
        sheets['key'].write(i+3, col, '(select)', to_validate)
        sheets['key'].data_validation(i+3, col, i+3, col, {'validate': 'list', 'source': 'B'+str(4)+':B'+str(4+len(c_list))})
        for j in c_list:
            ref_source = xlsxwriter.utility.xl_rowcol_to_cell(i+3, col)
            sheets['key'].conditional_format(i+3,col+1, i+3, col+1, {'type': 'formula', 'criteria': '='+ref_source+'="'+j+'"', 'format': colors[j][1]})
    col += 2
    sheets['key'].set_column(col, col, 2)
    col += 1
    sheets['key'].write_string(2, col, 'Select edge colour:', small_header)
    for i in range(len(series)):
        sheets['key'].write(i+3, col, '(select)', to_validate)
        sheets['key'].data_validation(i+3, col, i+3, col, {'validate': 'list', 'source': 'B'+str(4)+':B'+str(4+len(c_list))})
        for j in c_list:
            ref_source = xlsxwriter.utility.xl_rowcol_to_cell(i+3, col)
            sheets['key'].conditional_format(i+3,col+1, i+3, col+1, {'type': 'formula', 'criteria': '='+ref_source+'="'+j+'"', 'format': colors[j][1]})
    col += 2
    sheets['key'].set_column(col, col, 2)
    col += 1
    sheets['key'].write_string(2, col, 'Marker size:', small_header)
    for i in range(len(series)):
        sheets['key'].write(i+3, col, 20, to_validate)
    col += 1
    sheets['key'].set_column(col, col, 2)
    col += 1
    sheets['key'].write_string(2, col, 'Edge width:', small_header)
    for i in range(len(series)):
        sheets['key'].write(i+3, col, 1.5, to_validate)
    col += 1
    sheets['key'].set_column(col, col, 2)
    col += 1
    sheets['key'].write_string(2, col, 'Opacity (0-1):', small_header)
    for i in range(len(series)):
        sheets['key'].write(i+3, col, 1, to_validate)
    col += 1
    sheets['key'].set_column(col, col, 2)
    col += 1
    sheets['key'].write_string(2, col, 'Relative order (0 is foreground):', small_header)
    for i in range(len(series)):
        sheets['key'].write(i+3, col, 0, to_validate)
    cs.close()

def read_key(name):
    if '.xlsx' not in name:
        return 'ERROR: Control workbook must end with the .xlsx extension.'
    
    key_df = pd.read_excel(name, header=2)
    
    m_dict = {'None': None, 'select': 'o'}
    for i in Line2D.markers.keys():
        if i not in ['None', 'none', '', ' ']:
            m_dict[Line2D.markers[i]] = i
    
    series_to_plot0 = []
    series_dic = {}
    order_lst = []
    series_col = key_df.columns[list(key_df.columns).index('Plot?')-1]
    for i in key_df.index:
        if pd.isna(key_df.loc[i, series_col]) == False and key_df.loc[i, 'Plot?'] == 'yes':
            series_to_plot0.append(key_df.loc[i, series_col])
            order_lst.append(key_df.loc[i, 'Relative order (0 is foreground):'])
            marker0 = key_df.loc[i, 'Select marker:']
            marker = None
            color = None
            edgecolor = None
            if '(' in marker0:
                marker0 = marker0.split('(')[1]
                if ')' in marker0:
                    marker0 = marker0.split(')')[0]
                    if marker0 in m_dict.keys():
                        marker = m_dict[marker0]
            elif len(marker0) == 1 and marker0 in Line2D.markers.keys():
                marker = Line2D.markers[marker0]
            if key_df.loc[i, 'Select face colour:'] in mcolors.CSS4_COLORS.keys():
                color = key_df.loc[i, 'Select face colour:']
            if key_df.loc[i, 'Select edge colour:'] in mcolors.CSS4_COLORS.keys():
                edgecolor = key_df.loc[i, 'Select edge colour:']
            s = key_df.loc[i, 'Marker size:']
            lw = key_df.loc[i, 'Edge width:']
            alpha = key_df.loc[i, 'Opacity (0-1):']
            series_dic[key_df.loc[i, series_col]] = {'marker': marker, 'c': color, 'edgecolor': edgecolor, 's': s, 'lw': lw, 'alpha': alpha}
    series_to_plot = []
    for i in np.argsort(-np.array(order_lst), kind='stable'):
        series_to_plot.append(series_to_plot0[i])
    
    return series_to_plot, series_dic
            
            

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 17:44:02 2026

@author: paulbeguelin
"""

import pandas as pd
import xlsxwriter
import earthcodes_utils


def res_sheet(var_descr, tree, filename='Results_selection.xlsx', overwrite=False, additional_lines=20):
    if '.xlsx' not in filename:
       filename += '.xlsx'
    if earthcodes_utils.file_exists(filename) and not overwrite:
        return 'ERROR: ' + filename + ' already exists. Running this method will delete it and create a new one. To do this anyway, enter overwrite=True as a method argument.'
    
    # output a xlsx workbook to customise results options
    cs = xlsxwriter.Workbook(filename)
    sheets = {}
    nm = 'Results output'
    sheets[nm] = cs.add_worksheet(nm)
    big_header = cs.add_format({'bold': True, 'align': 'left', 'font_size': 14})
    small_header = cs.add_format({'bold': True, 'align': 'left', 'font_size': 11})
    to_validate = cs.add_format({'border': 1})
    sheets[nm].write_string(0, 0, 'Results table customisation', big_header)
    
    head_row = 2
    sheets[nm].set_column(0, 0, 20)
    sheets[nm].set_column(1, 1, 30)
    sheets[nm].set_column(2, 2, 8)
    sheets[nm].set_column(3, 3, 25)
    sheets[nm].write_string(head_row, 0, 'Model variables', small_header)
    sheets[nm].write_string(head_row, 1, 'Description', small_header)
    sheets[nm].write_string(head_row, 2, 'Include?', small_header)
    sheets[nm].write_string(head_row, 3, 'Name in results table', small_header)
    row = head_row + 1
    for i in var_descr.keys():
        sheets[nm].write_string(row, 0, i)
        sheets[nm].write_string(row, 1, var_descr[i])
        sheets[nm].write(row, 2, 'yes', to_validate)
        sheets[nm].data_validation(row, 2, row, 2, {'validate': 'list', 'source': ['yes', 'no']})
        row += 1
    
    if additional_lines > 0:
        
        list_row = row + additional_lines + 30
        
        processes_list = []
        row_i = list_row
        max_len = 0
        for i in tree.reservoirs.keys():
            for j in tree.reservoirs[i].events.keys():
                processes_list.append(i + ' Process_' + j)
                sheets[nm].write_string(row_i, 0, processes_list[-1])
                dic_report = tree.reservoirs[i].events[j].fn.report()
                options_list = []
                for k in dic_report.keys():
                    if type(dic_report[k]) == dict:
                        options_list.append(k + ' - (all radiogenic isotopes)')
                        options_list.append(k + ' - (all trace elements)')
                        options_list.append(k + ' - (all physical parameters)')
                        for l in dic_report[k].keys():
                            options_list.append(k + ' - ' + l)
                    else:
                        options_list.append(k)
                if len(options_list) > max_len:
                    max_len = len(options_list)
                for k in range(len(options_list)):
                    sheets[nm].write_string(row_i, k+2, options_list[k])
                row_i += 1
        sheets[nm].write_string(row_i, 0, '(select)')
        sheets[nm].write_string(row_i, 2, '(select)')
        
        row_i = list_row
        for i in range(len(processes_list)+1):
            range_start = xlsxwriter.utility.xl_rowcol_to_cell(row_i, 2)
            range_end = xlsxwriter.utility.xl_rowcol_to_cell(row_i, 2 + max_len - 1)
            sheets[nm].write_string(row_i, 1, range_start+':'+range_end)
            row_i += 1
        
        row += 1
        sheets[nm].write_string(row, 0, 'Additional model inputs and outputs', small_header)
        row += 1
        sheets[nm].write_string(row, 0, 'Process', small_header)
        sheets[nm].write_string(row, 1, 'Output', small_header)
        sheets[nm].write_string(row, 2, 'Include?', small_header)
        sheets[nm].write_string(row, 3, 'Name in results table (if Output is a list, list elements will be appended to the name, such as - Rb)', small_header)
        row += 1
        lst_start = xlsxwriter.utility.xl_rowcol_to_cell(list_row, 0)
        lst_end = xlsxwriter.utility.xl_rowcol_to_cell(list_row + len(processes_list), 0)
        ref_start = xlsxwriter.utility.xl_rowcol_to_cell(list_row, 1)
        ref_end = xlsxwriter.utility.xl_rowcol_to_cell(list_row + len(processes_list), 1)
        for i in range(additional_lines):
            sheets[nm].write(row+i, 0, '(select)', to_validate)
            sheets[nm].write(row+i, 1, '(select)', to_validate)
            sheets[nm].data_validation(row+i, 0, row+i, 0, {'validate': 'list', 'source': lst_start+':'+lst_end})
            ref_cell = xlsxwriter.utility.xl_rowcol_to_cell(row+i, 0)
            sheets[nm].data_validation(
                row+i, 1, row+i, 1, {'validate': 'list',
                                     'source': '=INDIRECT(INDEX('+ref_start+':'+ref_end+',MATCH('+ref_cell+','+lst_start+':'+lst_end+')))'})
            sheets[nm].write(row+i, 2, 'no', to_validate)
            sheets[nm].data_validation(row+i, 2, row+i, 2, {'validate': 'list', 'source': ['yes', 'no']})
            
    cs.close()
    
def read_res_sheet(obs, name='Results_selection.xlsx'):
    if '.xlsx' not in name:
        return 'ERROR: Control workbook must end with the .xlsx extension.'
    res_sheet = pd.read_excel(name, header=2)
    
    
    for i in range(len(res_sheet)):
        if res_sheet.loc[i, 'Model variables'] == 'Additional model inputs and outputs':
            in_out_header = i
    
    vars_i = []
    ins_out_i = []
    
    for i in range(len(res_sheet)):
        if res_sheet.loc[i, 'Include?'] == 'yes' and i < in_out_header:
            vars_i.append(i)
        elif res_sheet.loc[i, 'Include?'] == 'yes':
            ins_out_i.append(i)
    
    res_vars = {}
    in_out_vars = {}
    
    for i in vars_i:
        if res_sheet.loc[i, 'Name in results table'] == res_sheet.loc[i, 'Name in results table']:
            res_vars[res_sheet.loc[i, 'Model variables']] = res_sheet.loc[i, 'Name in results table']
        else:
            res_vars[res_sheet.loc[i, 'Model variables']] = res_sheet.loc[i, 'Model variables']
    
    for i in ins_out_i:
        Process = res_sheet.loc[i, 'Model variables'].split(' ')
        Output0 = res_sheet.loc[i, 'Description']
        Output = Output0.split(' - ')
        
        if Output[-1] == '(all radiogenic isotopes)':
            for j in obs['R']:
                name_j = Process[0] + '/' + Process[1][-1] + '/' + Output[0] + '/' + j
                if res_sheet.loc[i, 'Name in results table'] == res_sheet.loc[i, 'Name in results table']:
                    name2_j = res_sheet.loc[i, 'Name in results table'] + ' - ' + j
                else :
                    name2_j = name_j
                
                in_out_vars[name_j] = name2_j
        
        elif Output[-1] == '(all trace elements)':
            for j in obs['C']:
                name_j = Process[0] + '/' + Process[1][-1] + '/' + Output[0] + '/' + j
                if res_sheet.loc[i, 'Name in results table'] == res_sheet.loc[i, 'Name in results table']:
                    name2_j = res_sheet.loc[i, 'Name in results table'] + ' - ' + j
                else :
                    name2_j = name_j
                
                in_out_vars[name_j] = name2_j
        
        elif Output[-1] == '(all physical parameters)':
            for j in obs['P']:
                name_j = Process[0] + '/' + Process[1][-1] + '/' + Output[0] + '/' + j
                if res_sheet.loc[i, 'Name in results table'] == res_sheet.loc[i, 'Name in results table']:
                    name2_j = res_sheet.loc[i, 'Name in results table'] + ' - ' + j
                else :
                    name2_j = name_j
                
                in_out_vars[name_j] = name2_j
            
        else:
            name_i = Process[0] + '/' + Process[1][-1]
            for j in Output:
                name_i += '/' + j
            if res_sheet.loc[i, 'Name in results table'] == res_sheet.loc[i, 'Name in results table']:
                name2_i = res_sheet.loc[i, 'Name in results table']
            else :
                name2_i = name_i
            
            in_out_vars[name_i] = name2_i
    
    return res_vars, in_out_vars
        
    
            
        
    
    
            
            
            
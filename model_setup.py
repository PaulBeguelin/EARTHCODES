#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 17:21:34 2026

@author: paulbeguelin
"""

import numpy as np
import pandas as pd
import xlsxwriter
import earthcodes_utils
import earthcodes_constants


def read_arch(filename, overwrite=False):
    if '.xlsx' not in filename:
        return 'ERROR: File name must end with the .xlsx extension.'
    
    observables = pd.read_excel(filename, header=4, nrows=4)
    output_validity = pd.read_excel(filename, header=12, nrows=3)
    elements_tracked = pd.read_excel(filename, header=18, nrows=2)
    parameters_tracked = pd.read_excel(filename, header=23, nrows=1)
    arch0 = pd.read_excel(filename, header=28)
    arch = pd.read_excel(filename, header=30)
    
    for i in list(observables.columns):
        if observables[i].iloc[0] != 'yes':
            observables = observables.drop(i, axis=1)
    
    for i in list(output_validity.columns):
        if output_validity[i].iloc[0] != 'yes':
            output_validity = output_validity.drop(i, axis=1)
            
    for i in list(elements_tracked.columns):
        if elements_tracked[i].iloc[1] != 'yes':
            elements_tracked = elements_tracked.drop(i, axis=1)
    
    for i in list(parameters_tracked.columns):
        if parameters_tracked[i].iloc[0] != 'yes':
            parameters_tracked = parameters_tracked.drop(i, axis=1)
    
    test_list = list(elements_tracked.columns) + list(observables.columns) + list(parameters_tracked.columns)
    if len(test_list) > len(set(test_list)):
        return 'ERROR: All names for model observables, elements tracked and physical parameters tracked must be unique (a variable name cannot be repeated among these 3 lists).'
    
    obs = {'C': list(elements_tracked.columns), 'R': list(observables.columns), 'P': list(parameters_tracked.columns), 'idx':{'P': [], 'D': []}, 'decay': {'lambda': [], 'branched': [], 'PD_calc': []}}
    for i in obs['R']:
        obs['idx']['P'].append(obs['C'].index(earthcodes_constants.iso_constants['parent_elements'][i]))
        obs['idx']['D'].append(obs['C'].index(earthcodes_constants.iso_constants['daughter_elements'][i]))
        obs['decay']['lambda'].append(earthcodes_constants.iso_constants['decay'][i])
        obs['decay']['branched'].append(earthcodes_constants.iso_constants['branched'][i])
        obs['decay']['PD_calc'].append(earthcodes_constants.iso_constants['PD_conversion_factor'][i])
    obs['decay']['lambda'] = np.array(obs['decay']['lambda'])
    obs['decay']['branched'] = np.array(obs['decay']['branched'])
    obs['decay']['PD_calc'] = np.array(obs['decay']['PD_calc'])
    
    C_check_idx = []
    for i in output_validity.columns:
        C_check_idx.append(obs['C'].index(i))
    C_min = np.array(output_validity.loc[1])
    C_max = np.array(output_validity.loc[2])
    
    dic = {}
    times = []
    for i in arch0.columns:
        if 'Reservoir' in i:
            dic[i] = {}
            num = i.split('_')[1]
            dic[i]['name'] = arch0['name_'+num].iloc[0]
            dic[i]['times'] = {}
            dic[i]['processes'] = {}
            dic[i]['comments'] = {}
    extras = []
    for i in dic.keys():
        num = i.split('_')[1]
        idx = arch['Indexes_'+num]
        for j in range(len(idx)):
            if arch['Times_'+num].iloc[j] == arch['Times_'+num].iloc[j]:
                times.append(arch['Times_'+num].iloc[j])
                dic[i]['times'][idx.iloc[j]] = arch['Times_'+num].iloc[j]
                dic[i]['processes'][idx.iloc[j]] = arch['Processes_'+num].iloc[j]
                dic[i]['comments'][idx.iloc[j]] = arch['Comments_'+num].iloc[j]
        if dic[i]['times'] == {}:
            extras.append(i)
    for i in extras:
        del dic[i]
    
    run_order = []
    col = list(arch.columns)
    col.reverse()
    row = list(arch.index)
    row.reverse()
    for i in col:
        if 'Indexes' in i:
            num = i.split('_')[1]
            if 'Reservoir_' + num in dic.keys():
                for j in row:
                    if arch.at[j, i] == arch.at[j, i] and arch.at[j, i] in dic['Reservoir_' + num]['times'].keys():
                        run_order.append(['Reservoir_' + num, arch.at[j, i]])
    
    def interpret(statement):
        fn_name = statement.split('(')[0]
        args0 = statement.split('(')[1]
        args0 = args0.split(')')[0]
        args0 = args0.split(',')
        args_txt = ''
        args = None
        if args0 != ['']:
            args = []
            args_txt = 'from ' 
            for i in args0:
                if i[0] == ' ':
                    i = i[1:]
                ii = i.split('_')
                args.append(ii)
                args_txt = args_txt + 'Reservoir_' + ii[0] + ii[1]
                if len(ii) > 2:
                    args_txt = args_txt + ' ' + ii[2]
                args_txt = args_txt + ' and '
            args_txt = args_txt[:-5]
        return {'cell_txt': statement, 'fn_name': fn_name, 'args': args, 'args_txt': args_txt}
    
    for i in run_order:
        statement = dic[i[0]]['processes'][i[1]]
        dic[i[0]]['processes'][i[1]] = interpret(statement)
        i.append(dic[i[0]]['times'][i[1]])
    
    return observables, obs, C_check_idx, C_min, C_max, dic, times, run_order
        
    
def control_sheet_out(model_tree, times, filename, overwrite=False):
    cs_wb_name = filename[:-5] + '_control_workbook.xlsx'
    if earthcodes_utils.file_exists(cs_wb_name) and not overwrite:
        return 'ERROR: ' + cs_wb_name + ' already exists. Running this method will delete it and create a new one. To do this anyway, enter overwrite=True as a method argument. Otherwise, rename the old control workbook.'
    
    cs = xlsxwriter.Workbook(cs_wb_name)
    sheets = {}
    sheets['t'] = cs.add_worksheet('Time ranges')
    for i in model_tree.reservoirs.keys():
        sheets[i] = cs.add_worksheet(model_tree.reservoirs[i].name)
    
    big_header = cs.add_format({'bold': True, 'align': 'left', 'font_size': 14})
    small_header = cs.add_format({'bold': True, 'align': 'left', 'font_size': 11})
    to_edit = cs.add_format({'bg_color': 'yellow', 'border': 1})
    to_validate = cs.add_format({'bg_color': 'orange', 'border': 1})
    tag = cs.add_format({'italic': True, 'font_color': 'gray', 'font_size': 10, 'align': 'right'})
    
    sheets['t'].write_string(0, 0, 'Ranges for ages in the model', big_header)
    sheets['t'].write_string(1, 0, 'name', small_header)
    sheets['t'].write_string(1, 1, 'unit', small_header)
    sheets['t'].write_string(1, 2, 'min', small_header)
    sheets['t'].write_string(1, 3, 'max', small_header)
    row = 2
    times = list(set(times))
    times.sort()
    for i in times:
        sheets['t'].write_string(row, 0, i)
        if i == 't_init':
            sheets['t'].write_number(row, 2, 4.57, to_edit)
            sheets['t'].write_number(row, 3, 4.57, to_edit)
        elif i == 't0':
            sheets['t'].write_number(row, 2, 0, to_edit)
            sheets['t'].write_number(row, 3, 0, to_edit)
        else:
            sheets['t'].write_string(row, 2, '', to_edit)
            sheets['t'].write_string(row, 3, '', to_edit)
        sheets['t'].write_string(row, 1, 'Ga')
        row += 1
    
    glob_ins_list = []
    for i in range(20):
        glob_ins_list.append('Global'+str(i))
    
    def inputs_sheet_out(reservoir_number):
        name = model_tree.reservoirs[reservoir_number].name
        st = sheets[reservoir_number]
        st.write_string(0, 0, reservoir_number, tag)
        st.write_string(0, 1, 'Model input parameters for ' + reservoir_number + ': ' + name, big_header)
        row = 2
        events_list = list(model_tree.reservoirs[reservoir_number].events.keys())
        events_list.sort()
        for i in events_list:
            p_dict = model_tree.reservoirs[reservoir_number].events[i]
            time = model_tree.reservoirs[reservoir_number].events[i].time
            comment = model_tree.reservoirs[reservoir_number].events[i].comment
            st.write_string(row, 1, i + ') ' + p_dict.name + ' process at '+ time + ': ' + p_dict.arg_txt, big_header)
            row += 1
            st.write_string(row, 1, 'Comment:', small_header)
            st.write_string(row, 2, comment)
            row += 1
            prc = p_dict.fn
            for j in prc.params.keys():
                st.write_string(row, 1, prc.params[j].name, small_header)
                row += 1
                st.write_string(row, 2, 'Name:', small_header)
                st.write_string(row, 3, j)
                st.write_string(row, 5, 'Type:', small_header)
                st.write_string(row, 6, prc.params[j].param_type)
                row += 1
                
                if prc.params[j].param_type == 'variable' and prc.params[j].validation == False and prc.params[j].headers == ['min', 'max']:
                    st.write_string(row, 2, 'min', small_header)
                    st.write_string(row, 3, 'max', small_header)
                    row += 1
                    st.write_string(row, 0, reservoir_number+'/'+i+'/'+j+'/glob_check', tag)
                    st.write(row, 2, '', to_edit)
                    st.write(row, 3, '', to_edit)
                    st.write_string(row, 5, 'Use global input?', small_header)
                    st.insert_checkbox(row, 7, False)
                    st.write_string(row, 9, 'If yes, select input:', small_header)
                    st.data_validation(row, 11, row, 11, {'validate': 'list', 'source': glob_ins_list})
                    st.write(row, 11, '', to_validate)
                    row += 2
                    
                else:
                    col = 2
                    for k in prc.params[j].headers:
                        st.write_string(row, col, k)
                        col += 1
                    row += 1
                    col = 2
                    st.write_string(row, 0, reservoir_number+'/'+i+'/'+j, tag)
                    for k in prc.params[j].options:
                        if prc.params[j].validation:
                            st.write(row, col, k[0], to_validate)
                            st.data_validation(row, col, row, col, {'validate': 'list', 'source': k})
                        else:
                            st.write(row, col, '', to_edit)
                        col += 1
                    row += 2
            row += 1
    
    for i in model_tree.reservoirs.keys():
        inputs_sheet_out(i)
    
    cs.close()
    

def read_setup(name, tree):
    
    times_df = pd.read_excel(name, 'Time ranges', header=1)
    times_rg = {}
    model_vars = []
    var_rg = {}
    var_descr = {}
    for i in tree.times:
        if i not in times_rg.keys():
            times_rg[i] = {'min': float(times_df[times_df['name']==i]['min'].iloc[0]), 'max': float(times_df[times_df['name']==i]['max'].iloc[0]), 'idx': 0, 'arr': None}
            
        if float(times_df[times_df['name']==i]['min'].iloc[0]) != float(times_df[times_df['name']==i]['max'].iloc[0]) and i not in model_vars:
            model_vars.append(i)
            var_rg[i] = {'min': float(times_df[times_df['name']==i]['min'].iloc[0]), 'max': float(times_df[times_df['name']==i]['max'].iloc[0])}
            var_descr[i] = 'Time variable ' + i
    
    for i in tree.reservoirs.keys():
        st = pd.read_excel(name, tree.reservoirs[i].name)
        for j in st[i]:
            if j == j:
                tag = j.split('/')
                if tag[-1] == 'glob_check':
                    var_id = j[:-11]
                else:
                    var_id = j
                if tag[0] == i:
                    n_cols = len(tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].options)
                    tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].val = list(st[st[i]==j].iloc[0,2:2+n_cols])
                    if tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].param_type == 'variable' and tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].val[0] != tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].val[1]:
                        if tag[-1] == 'glob_check':
                            glob_check = st[st[i]==j].iloc[0,7]
                            if glob_check:
                                glob_in = st[st[i]==j].iloc[0,11]
                                if glob_in not in model_vars:
                                    model_vars.append(glob_in)
                                tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].idx = model_vars.index(glob_in)
                            else:
                                model_vars.append(j)
                                tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].idx = model_vars.index(j)
                        else:
                            model_vars.append(j)
                            tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].idx = model_vars.index(j)
                                    
                        var_rg[var_id] = {}
                        var_rg[var_id]['min'] = tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].val[0]
                        var_rg[var_id]['max'] = tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].val[1]
                        descr_txt = 'Reservoir: ' + tree.reservoirs[i].name + '; '
                        descr_txt += 'Time: ' + tree.reservoirs[i].events[tag[1]].time + '; '
                        descr_txt += 'Comments: ' + tree.reservoirs[i].events[tag[1]].comment + '; '
                        descr_txt += 'Variable: ' + tag[2] + '; '
                        descr_txt += 'Variable description: ' + tree.reservoirs[i].events[tag[1]].fn.params[tag[2]].name
                        var_descr[var_id] = descr_txt
                            
    for i in times_rg.keys():
        if i in model_vars:
            times_rg[i]['idx'] = model_vars.index(i)
    
    print('Ranges:')
    for i in var_rg.keys():
        print(i + ' : ' + str(var_rg[i]))
    print('')
    print(str(len(model_vars)) + ' variables identified (a larger number may be listed above if some depend on the same global input).\n')
    
    for i in tree.run_order:
        tree.reservoirs[i[0]].events[i[1]].fn.setup()
    
    for i in range(len(model_vars)):
        var_i = model_vars[i].split('/')
        if var_i[-1] == 'glob_check':
            model_vars[i] = model_vars[i][:-11]
            
    
    return times_rg, model_vars, var_rg, var_descr
    

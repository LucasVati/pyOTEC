# -*- coding: utf-8 -*-
"""
Created on Thu Feb 23 08:49:22 2023

@author: jkalanger
"""

import numpy as np
import pandas as pd
import os

from otec_sizing import otec_sizing
from capex_opex_lcoe import capex_opex_lcoe
# from parameters_and_constants import parameters_and_constants
from otec_operation import otec_operation

def on_design_analysis(T_WW_in,T_CW_in,inputs,cost_level='low_cost'):
    
    # inputs = parameters_and_constants(cost_level)
   
    del_T_WW_min, \
    del_T_CW_min, \
    del_T_WW_max, \
    del_T_CW_max, \
    interval_WW, \
    interval_CW = inputs['del_T_for_looping']
    
    if T_WW_in.ndim == 0:
        lcoe_matrix_nominal = np.empty([int((del_T_WW_max-del_T_WW_min)/interval_WW+1),int((del_T_CW_max-del_T_CW_min)/interval_CW+1)],dtype=np.float64)
    else: 
        lcoe_matrix_nominal = np.empty([int((del_T_WW_max-del_T_WW_min)/interval_WW+1),int((del_T_CW_max-del_T_CW_min)/interval_CW+1),np.shape(T_WW_in)[0]],dtype=np.float64)
    
    for i in range(del_T_CW_min,(del_T_CW_max+interval_CW),interval_CW):
        for j in range(del_T_WW_min,del_T_WW_max+interval_WW,interval_WW):  
            del_T_CW = i/10     # delta between inlet and outlet warm seawater temperature in degree Celsius
            del_T_WW = j/10     # delta between inlet and outlet cold seawater temperature in degree Celsius          
   
   ## Calculate system and unpack results here         
   
            otec_plant_nominal = otec_sizing(T_WW_in,
                                    T_CW_in,
                                    del_T_WW,
                                    del_T_CW,
                                    inputs,
                                    cost_level)
            
            _, CAPEX, OPEX, LCOE_nom = capex_opex_lcoe(
                otec_plant_nominal, inputs, cost_level)

            otec_plant_nominal['CAPEX'] = CAPEX
            otec_plant_nominal['OPEX'] = OPEX
            otec_plant_nominal['LCOE_nom'] = LCOE_nom
            
            if T_WW_in.ndim == 0:          
                lcoe_matrix_nominal[int((i-del_T_CW_min)/interval_CW)][int((j-del_T_WW_min)/interval_WW)] = LCOE_nom
                lcoe_matrix_nominal = np.nan_to_num(lcoe_matrix_nominal,nan=10000) # replace NaN with unreasonably high value
                del_T_pair = divmod(lcoe_matrix_nominal.argmin(),lcoe_matrix_nominal.shape[1])
                del_T_CW = (del_T_pair[0] * interval_CW + 20)/10
                del_T_WW = (del_T_pair[1] * interval_CW + 20)/10
            else:
                lcoe_matrix_nominal[int((i-del_T_CW_min)/interval_CW)][int((j-del_T_WW_min)/interval_WW)][:] = LCOE_nom
                lcoe_matrix_nominal = np.nan_to_num(lcoe_matrix_nominal,nan=10000) # replace NaN with unreasonably high value
                del_T_CW = ( np.argmin(np.min(lcoe_matrix_nominal,axis=1),axis=0) * interval_CW + 20)/10
                del_T_WW = ( np.argmin(np.min(lcoe_matrix_nominal,axis=0),axis=0) * interval_WW + 20)/10
       
    
    # It would be more elegant to not re-calculate the plants, but I don't know how to make it better.
    
    otec_plant_nominal_lowest_lcoe = otec_sizing(T_WW_in,
                                        T_CW_in,
                                        del_T_WW,
                                        del_T_CW,
                                        inputs,
                                        cost_level)
    
    all_CAPEX_OPEX,CAPEX,OPEX,LCOE_nom = capex_opex_lcoe(otec_plant_nominal_lowest_lcoe,                                              
                                inputs,
                                cost_level)
    
    
    
    otec_plant_nominal_lowest_lcoe['CAPEX'] = CAPEX
    otec_plant_nominal_lowest_lcoe['OPEX'] = OPEX
    otec_plant_nominal_lowest_lcoe['LCOE_nom'] = LCOE_nom

    
    return otec_plant_nominal_lowest_lcoe,all_CAPEX_OPEX

def off_design_analysis(T_WW_design,T_CW_design,T_WW_profiles,T_CW_profiles,inputs,coordinates,timestamp,studied_region,new_path,cost_level='low_cost'):
       
    print('\n++ Initiate off-design analysis ++\n')
    
    results_matrix = {}
    
    if T_WW_design.ndim == 1:
        lcoe_matrix = np.empty((len(T_WW_design),len(T_CW_design)),dtype=np.float64) 
    else:    
        lcoe_matrix = np.empty((len(T_WW_design),len(T_CW_design),np.shape(T_WW_profiles)[1]),dtype=np.float64)
    
    CAPEX_OPEX_for_comparison = []
    for index_cw,t_cw_design in enumerate(T_CW_design):
        for index_ww,t_ww_design in enumerate(T_WW_design):
            
            # print(f'Configuration {index_ww + index_cw*3 + 1}')
            
            otec_plant_nominal_lowest_lcoe,all_CAPEX_OPEX = on_design_analysis(t_ww_design,t_cw_design,inputs,cost_level)          
            otec_plant_off_design = otec_operation(otec_plant_nominal_lowest_lcoe,T_WW_profiles,T_CW_profiles,inputs)
            
            otec_plant_off_design.update(otec_plant_nominal_lowest_lcoe)
            
            # otec_plant_off_design['Configuration'] = index_ww + index_cw*3 + 1
            
            
            results_matrix[index_ww + index_cw*3 + 1] = otec_plant_off_design
            
            if T_WW_design.ndim == 1:
                lcoe_matrix[index_cw][index_ww]  = otec_plant_off_design['LCOE']
            else:    
                lcoe_matrix[index_cw][index_ww][:]  = otec_plant_off_design['LCOE']
                
            CAPEX_OPEX_for_comparison.append([all_CAPEX_OPEX])
    
    lcoe_matrix = np.nan_to_num(lcoe_matrix,nan=10000) # replace NaN with unreasonably high value
              
    index_CW_lowest_LCOE = np.argmin(np.min(lcoe_matrix,axis=1),axis=0)
    index_WW_lowest_LCOE = np.argmin(np.min(lcoe_matrix,axis=0),axis=0)
    
    configuration_lowest_LCOE = (index_WW_lowest_LCOE + index_CW_lowest_LCOE*3 + 1).T
    
    if T_WW_design.ndim == 1:
        otec_plant_lowest_lcoe = results_matrix[configuration_lowest_LCOE]
    else:
    
        # Here we make a dummy dictionary which we will overwrite with the values of the best off-design plants.
        # We use configuration 1 as default because most plants return that configuration as the one with lowest LCOE

        otec_plant_lowest_lcoe = results_matrix[1]
        
        for index, plant in enumerate(index_WW_lowest_LCOE):
            if configuration_lowest_LCOE[index] == 1:
                continue
            else:
                for key in otec_plant_lowest_lcoe:
                    if np.ndim(otec_plant_lowest_lcoe[key]) <= 1:
                        otec_plant_lowest_lcoe[key][index] = results_matrix[configuration_lowest_LCOE[index]][key][index]
                    else:
                        otec_plant_lowest_lcoe[key][:,index] = results_matrix[configuration_lowest_LCOE[index]][key][:,index]
        
    otec_plant_lowest_lcoe['Configuration'] = configuration_lowest_LCOE
    
    net_power_df = pd.DataFrame(np.round(otec_plant_lowest_lcoe['p_net']/otec_plant_lowest_lcoe['p_gross_nom'],3))
    net_power_df.columns = [str(val[0]) + '_' + str(val[1]) for idx,val in enumerate(coordinates)]

    net_power_df['Time'] = timestamp
    net_power_df = net_power_df.set_index('Time')
    
    date_start = inputs['date_start']
    p_gross = inputs['p_gross']
    
    # net_power_df.to_hdf(new_path + f'Net_power_profiles_{studied_region}_{date_start[0:4]}_{-p_gross/1000}_MW_{cost_level}.h5'.replace(" ","_"),key='net_power',mode='w')
       
    for key,value in otec_plant_lowest_lcoe.items():
        if value.ndim == 1:
            value = value.reshape(1,-1)             
        pd.DataFrame(np.round(value,2), columns=net_power_df.columns).to_hdf(new_path + f'Time_series_data_{studied_region}_{date_start[0:4]}_{-p_gross/1000}_MW_{cost_level}.h5',key=f'{key}',mode='a')
    
    print('\nTime series data successfully exported as h5 file.\n\nEnd of script.')
    
    return otec_plant_lowest_lcoe, CAPEX_OPEX_for_comparison
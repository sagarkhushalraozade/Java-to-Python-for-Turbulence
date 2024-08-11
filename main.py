#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 17 16:11:06 2023

@author: abc
"""

# Import packages

# if 'ubx_port' in locals() or 'ubx_port' in globals():
#     ubx_port.close() # can only run in the console, not in the editor.

# ubx_port.close(); plt.close('all'); locals().clear() # Run this in the console before running the script.

import serial # used pip to install since conda was stuck due to inconsistencies in environment
import CRC  # user-defined class. To be saved in the same folder as the calling Python file.
import re # This module provides regular expression matching operations.
import math as math
import numpy as np
import matplotlib
# matplotlib.use('TkAgg')  # Set the backend to TkAgg
import matplotlib.pyplot as plt
from helping_functions import read_serial, calculateAirSpeed, crc_check, read_const, plot_imshow, plot_update, plot_update_2, plot_update_interp, plot_update_interp_2 # read_serial contains calculateAirSpeed
import logging # used to log the error/warning/info in a file/console but cannot point to the line that causes the error.
import traceback # cannot log to a file but can identify the line where the issue occurs.

# For pmv
from pythermalcomfort.models import pmv_ppd
from pythermalcomfort.utilities import v_relative, clo_dynamic
from pythermalcomfort.utilities import met_typical_tasks
from pythermalcomfort.utilities import clo_individual_garments
import pandas as pd
import os

# Initialialization
# if ubx_port.isOpen():
#    ubx_port.close() # Close the port, otherwise it cannot be opened.
ubx_port = serial.Serial('COM9', 115200) # Define ubx_port 
read_buffer = 2048 # bytearray(2048)
total_packets = 1
failed_packets = 0
num_sensors = 36
interp_multiplier = 6 # So, 6 will become 6 x 1 x 6 x 1 i.e. 36. 
# sensorIDList = [15, 16, 17, 18, 20, 19, 13, 14, 22, 21, 23, 24, 9, 10, 11, 12, 26, 25, 7, 8, 30, 29, 28, 27, 3, 4, 5, 6, 32, 31, 1, 2, 36, 35, 34, 33] # From Java code.
sensorIDList = [_ for _ in range(1,37)] # [1 2 3 .......36]
sensor_array = np.reshape(sensorIDList, (6,6))
sensor_array = sensor_array[::-1,:]
sensorIDList = np.reshape(sensor_array,(36)) # [36 35 34 33 32 31 25.....1 2 3 4 5 6] # This is what I see experimentally.
temperature_array = np.zeros((6,6))
airflow_array = np.zeros((6,6))
turbulence_intensity_array = np.zeros((6,6))
currentFlowMap = {key: 0.0 for key in sensorIDList}
jumpPrevention = False
humidity = 0.35
negativeLimit = -0.5 # m/s
vel_clim = [0.1, 0.9] # range of velocity (in m/s) to display
temp_clim = [22, 26] # range of temperature (in C) to display
turb_clim =[0, 100] # range of turbulence intensity (in %) to display
pmv_clim = [-3, 3] # range of PMV
dr_clim = [0, 100] # range of Draft Rating
read_count = 0
exception_counter = 0
turbulence_buffer_size = 30 
airflow_history_array = np.zeros((turbulence_buffer_size, 6, 6))
range_set, constants_general = read_const('Constants28Dec.csv')
crc_Type = "NoCheck" # Can choose between "NoCheck", "CRC8", "CRC16", "CRC32"

activity = "Typing"  # participant's activity description
garments = ["Sweatpants", "T-shirt", "Shoes or sandals"]
met = met_typical_tasks[activity]  # activity met, [met]
icl = sum(
    [clo_individual_garments[item] for item in garments]
) 
clo_d = clo_dynamic(clo=icl, met=met) 
met_arr = np.full(num_sensors, met)
clo_d_arr = np.full(num_sensors,clo_d)
rh_arr = np.full(num_sensors,humidity*100)


# Plotting
fig0 = plt.figure(0)
ax0 = fig0.add_subplot(111)
im0 = ax0.imshow(sensor_array)
for i in range(6):
    for j in range(6):
        ax0.text(j, i, f'{int(sensor_array[i, j]):d}', ha='center', va='center', color='w')
fig0.show()

figT, axT, imT, cbarT = plot_imshow(temp_clim, 'Temperature (°C)', 1)
imT.set_clim(vmin = temp_clim[0], vmax = temp_clim[1])
figv, axv, imv, cbarv = plot_imshow(vel_clim, 'Velocity (m/s)', 2)
imv.set_clim(vmin = vel_clim[0], vmax = vel_clim[1])
figTurb, axTurb, imTurb, cbarTurb = plot_imshow(turb_clim, 'Turbulence Intensity(%)', 3)
imTurb.set_clim(vmin = turb_clim[0], vmax = turb_clim[1])
figpmv, axpmv, impmv, cbarpmv = plot_imshow(pmv_clim, 'Predicted Mean Vote', 4)
impmv.set_clim(vmin = pmv_clim[0], vmax = pmv_clim[1])
figdr, axdr, imdr, cbardr = plot_imshow(dr_clim, 'Draft Rating (%)', 5)
imdr.set_clim(vmin = dr_clim[0], vmax = dr_clim[1])

# Configure the logging settings (you can customize this according to your needs)
logging.basicConfig(level=logging.DEBUG)

# The code from here onwards should run in a loop to process every received bytes_read.
while True:
    bytes_read = ubx_port.read(read_buffer)
    if bytes_read:
        try:
            decoded_data = bytes_read.decode('utf-8')
            
            split_data = decoded_data.split(";")
            
            checked_data, total_packets, failed_packets  = crc_check(split_data, crc_Type, total_packets, failed_packets) 
            # function defined below. checked_data contains temp, airflow, sensorID
            
            # check if the checked data is the same during the last loop
            if read_count == 0:
                checked_data_old = checked_data
            else:
                if checked_data == checked_data_old:
                    print(f"For {read_count} time-step, checked_data is same as previous")
                checked_data_old = checked_data
            
            
            arr2D, currentFlowMap = read_serial(checked_data, humidity, num_sensors, sensorIDList, jumpPrevention, negativeLimit, currentFlowMap, range_set, constants_general) 
            # function defined below. Returns a 2D array with temp, airflow. If there are problems with the rawVal, it retuns a 3D array with the real sensorID.
            temperature = [get_row[0] for get_row in arr2D] # Arranged as sensorIDList 
            airflow = [get_row[1] for get_row in arr2D]
            
            airflow_arr = np.array(airflow)
            vrel_arr = v_relative(v=airflow_arr, met=met_arr)
            
            # print(f"{read_count} time-steps over")
            
            temperature_array = np.reshape(np.array(temperature), (6, 6)) # need np since list reshaping is not possible easily
            temp_db_arr = np.array(temperature)
            
            pmv_ppd_arr = pmv_ppd(temp_db_arr, temp_db_arr, vrel_arr, rh_arr, met_arr, clo_d_arr, 0, standard = "ashrae", units = "SI", limit_inputs = False)
            # limit_inputs : boolean default True
            # By default, if the inputs are outsude the standard applicability limits the
            # function returns nan. If False returns pmv and ppd values even if input values are
            # outside the applicability limits of the model.

            # The ASHRAE 55 2020 limits are 10 < tdb [°C] < 40, 10 < tr [°C] < 40,
            # 0 < vr [m/s] < 2, 1 < met [met] < 4, and 0 < clo [clo] < 1.5.
            # The ISO 7730 2005 limits are 10 < tdb [°C] < 30, 10 < tr [°C] < 40,
            # 0 < vr [m/s] < 1, 0.8 < met [met] < 4, 0 < clo [clo] < 2, and -2 < PMV < 2.
            
            pmv_arr = pmv_ppd_arr["pmv"]
            pmv_array = np.reshape(pmv_arr, (6, 6))
            
            
            # temperature_array_reversed = temperature_array[::-1,:]
            airflow_array = np.reshape(np.array(airflow), (6,6))
            # airflow_array_reversed = airflow_array[::-1,:]
            airflow_history_array[read_count%turbulence_buffer_size,:,:] = airflow_array
            
            if read_count+1 <= turbulence_buffer_size:
                mean_velocity_array = (np.sum(airflow_history_array[0:read_count+1,:,:], axis=0))/(read_count+1) # note that we have used 0:read_count+1 since 0:1 means 0, 0:2 means 0,1 and so on.
                turbulence_array = np.sqrt(np.sum((airflow_history_array[0:read_count+1,:,:]-mean_velocity_array)**2, axis=0)/(read_count+1)) # m/s
            else:
                mean_velocity_array = np.nanmean(airflow_history_array[:,:,:], axis=0)
                # turbulence_array = np.sqrt(np.sum((airflow_history_array[:,:,:]-mean_velocity_array)**2, axis=0)/(turbulence_buffer_size)) # m/s
                turbulence_array = np.sqrt(np.nanmean((airflow_history_array[:,:,:]-mean_velocity_array)**2, axis=0)) # m/s
            turbulence_intensity_array = (turbulence_array/mean_velocity_array)*100
            # turbulence_intensity_array_reversed = turbulence_intensity_array[::-1,:]
            
            read_count+=1  
            
            # Draft Rating from Fanger
            DR_array = ((34-temperature_array)*(mean_velocity_array-0.05)**0.62)*(0.37*mean_velocity_array*turbulence_intensity_array + 3.14)
            # ASHRAE stipulates in Standard 55-2004 that DR must be <20%
            # The draft model is based on studies with 150 subjects exposed to air temperatures of 20°C to 26°C (68°F to 79°F), mean 
            # air velocities of 0.05 to 0.4 m/s (10 to 80 fpm), and turbulence 
            # intensities of 0% to 70%. The model applies to people at light, 
            # mainly sedentary activity with a thermal sensation for the whole 
            # body close to neutral.
            
            # update plot
            plot_update_interp(temperature_array, temp_clim, 'Temperature (°C)', figT, axT, imT, cbarT, 20.0, interp_multiplier)
            plot_update_interp(airflow_array, vel_clim, 'Velocity (m/s)', figv, axv, imv, cbarv, 0.2, interp_multiplier)
            plot_update_interp_2(turbulence_intensity_array, turb_clim, 'Turbulence Intensity(%)', figTurb, axTurb, imTurb, cbarTurb, 0.0, interp_multiplier)
            plot_update_interp(pmv_array, pmv_clim, 'Predicted Mean Vote', figpmv, axpmv, impmv, cbarpmv, -3, interp_multiplier)
            plot_update_interp_2(DR_array, dr_clim, 'Draft Rating (%)', figdr, axdr, imdr, cbardr, 50.0, interp_multiplier)
            # logging.info("Data received and processed successfully")
            # logging.info(f"Checked data: {checked_data}")
            
        except Exception as e: # WIll be executed even igf there is no exception since we have not specified any specific exception.
            # pass  # do nothing 
            logging.error(f"An exception occurred: {e}")
            traceback.print_exc()
            exception_counter+=1
            # print(f"{exception_counter} exceptions")
        
        
        if read_count%50 == 0:
            max_temp = np.max(temperature_array)
            print(f"{read_count} time-steps are over, max. temp. = {max_temp}, {exception_counter} exceptions")
            
        plt.pause(0.1)
        
        # Printing every 50th iteration
        
ubx_port.close()
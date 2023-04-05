#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 17 16:11:06 2023

@author: abc
"""

# Import packages

import serial # used pip to install since conda was stuck due to inconsistencies in environment
import CRC  # user-defined class. To be saved in the same folder as the calling Python file.
import re # This module provides regular expression matching operations.
import math as math
import numpy as np
import matplotlib.pyplot as plt
from my_functions import read_serial, crc_check, read_const, plot_imshow# read_serial contains calculateAirSpeed

# Initialialization
ubx_port = serial.Serial('COM23', 115200) # Define ubx_port 
read_buffer = bytearray(2048)
total_packets = 1
failed_packets = 0
num_sensors = 36
sensorIDList = [15, 16, 17, 18, 20, 19, 13, 14, 22, 21, 23, 24, 9, 10, 11, 12, 26, 25, 7, 8, 30, 29, 28, 27, 3, 4, 5, 6, 32, 31, 1, 2, 36, 35, 34, 33]
sensor_array = np.reshape(sensorIDList, (6,6))
temperature_array = np.zeros((6,6))
airflow_array = np.zeros((6,6))
turbulence_intensity_array = np.zeros((6,6))
currentFlowMap = {key: 0.0 for key in sensorIDList}
jumpPrevention = False
humidity = 0.5
negativeLimit = -0.5 # m/s
vel_clim = [0, 6] # range of velocity (in m/s) to display
temp_clim = [18, 30] # range of temperature (in C) to display
turb_clim =[0, 100] # range of turbulence intensity (in %) to display
read_count = 0
turbulence_buffer_size = 30 
airflow_history_array = np.zeros((turbulence_buffer_size, 6, 6))
range_set, constants_general = read_const('Constants28Dec.csv')
crc_Type = "NoCheck" # Can choose between "NoCheck", "CRC8", "CRC16", "CRC32"

# Plotting
fig0 = plt.figure(0)
ax0 = fig0.add_subplot(111)
im0 = ax0.imshow(np.reshape([0 for _ in range(36)], (6, 6)), cmap='jet')
for i in range(6):
    for j in range(6):
        ax0.text(j, i, f'{int(sensor_array[i, j]):d}', ha='center', va='center', color='w')
fig0.show()

figT, axT, imT, cbarT = plot_imshow(temp_clim, 'Temperature (°C)')
figv, axv, imv, cbarv = plot_imshow(vel_clim, 'Velocity (m/s)')
figTurb, axTurb, imTurb, cbarTurb = plot_imshow(turb_clim, 'Turbulence Intensity(%)')

# The code from here onwards should run in a loop to process every received bytes_read.
while True:
    bytes_read = ubx_port.read(read_buffer)
    if bytes_read:
        decoded_data = bytes_read.decode('utf-8')
        
        split_data = decoded_data.split(";")
        
        checked_data, total_packets, failed_packets  = crc_check(split_data, crc_Type, total_packets, failed_packets) # function defined below. checked_data contains temp, airflow, sensorID
        
        arr2D, currentFlowMap = read_serial(checked_data, humidity, num_sensors, sensorIDList, jumpPrevention, negativeLimit, currentFlowMap, range_set, constants_general) # function defined below. Returns a 2D array with temp, airflow. If there are problems with the rawVal, it retuns a 3D array with the real sensorID.
        temperature = [get_row[0] for get_row in arr2D] # Arranged as sensorIDList 
        airflow = [get_row[1] for get_row in arr2D]
        
        temperature_array = np.reshape(np.array(temperature), (6, 6)) # need np since list reshaping is not possible easily
        airflow_array = np.reshape(np.array(airflow), (6,6))
        airflow_history_array[read_count%turbulence_buffer_size,:,:] = airflow_array
        
        if read_count+1 <= turbulence_buffer_size:
            mean_velocity_array = np.mean(airflow_history_array[0:read_count+1,:,:], axis=0) # note that we have used 0:read_count+1 since 0:1 means 0, 0:2 means 0,1 and so on.
            turbulence_array = np.sqrt(np.sum((airflow_history_array[0:read_count+1,:,:]-mean_velocity_array)**2, axis=0)/(read_count+1)) # m/s
        else:
            mean_velocity_array = np.mean(airflow_history_array[:,:,:], axis=0)
            turbulence_array = np.sqrt(np.sum((airflow_history_array[:,:,:]-mean_velocity_array)**2, axis=0)/(read_count)) # m/s
        turbulence_intensity_array = (turbulence_array/mean_velocity_array)*100
        
        # update plot
        imT.set_data(temperature_array)
        imT.set_clim(vmin = temp_clim[0], vmax = temp_clim[1])
        for i in range(6):
            for j in range(6):
                axT.text(j, i, f'{temperature_array[i, j]:.2f}', ha='center', va='center', color='w')
        figT.canvas.draw()
        
        imv.set_data(airflow_array)
        imv.set_clim(vmin = vel_clim[0], vmax = vel_clim[1])
        for i in range(6):
            for j in range(6):
                axv.text(j, i, f'{airflow_array[i, j]:.2f}', ha='center', va='center', color='w')
        figv.canvas.draw()
        
        imTurb.set_data(turbulence_intensity_array)
        imTurb.set_clim(vmin = turb_clim[0], vmax = turb_clim[1])
        for i in range(6):
            for j in range(6):
                axTurb.text(j, i, f'{int(turbulence_intensity_array[i, j]):d}', ha='center', va='center', color='w')
        figTurb.canvas.draw()
        
        plt.pause(0.1)
        
ubx_port.close()
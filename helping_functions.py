#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  5 13:03:26 2023

@author: abc
"""

# Functions

import serial # used pip to install since conda was stuck due to inconsistencies in environment
import CRC  # user-defined class. To be saved in the same folder as the calling Python file.
import re # This module provides regular expression matching operations.
import math as math
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp2d


def read_serial(data, humidity, num_sensors, sensorIDList, jumpPrevention, negativeLimit, currentFlowMap, range_set, constants_general):
    data2 = re.sub('[\t\n\r\?]+', '', data)
    arr = data2.split(";") #[temp1,airflow_volt1,sensorID1 temp2,airflow_vol2,sensorID2 temp3,airflow_volt3,sensorID3 ......]
    arr2 = [[0.0] * 3 for _ in range(num_sensors)] # 36 x 3
    map = {} # empty dictionary objet
    for u in range(len(arr)): # loops for number of temp,airflow_volt,sensorID
        if re.search('\d', arr[u]) and '"' not in arr[u]:
                temp = arr[u].split(",")
                arr3 = [temp[0], temp[1]] # temp, airflow_volt
                map[int(temp[2])] = arr3 # map(real_sensorID) = [temp,airflow_volt]
 
    o = 0
    for i in range(len(sensorIDList)):
        k = sensorIDList[i] # SensorID
        # print(f"Loop number = {i} and SensorID = {k} and o = {o}")
        arr3 = map.get(k) # Get the values for sensorID = k
        if arr3 is not None and re.search('\d', arr3[0]) and re.search('\d', arr3[1]):
            temperature = float(arr3[0])
            arr2[o][0] = temperature
            # arr2v[o][0] = temperature * offsetT
            rawVal = float(arr3[1])
            # arr2v[o][1] = rawVal
            currAir = 1.0
            if k in currentFlowMap: # checks if the key k is present in the dictionary object currentFlowMap
                currAir = currentFlowMap[k] # Take airflow values from the previous time-step. 
            airFlow = 0.0
            if not jumpPrevention:
                airFlow = float(calculateAirSpeed(temperature, rawVal, humidity, currAir, k, 90,range_set, constants_general))
            else:
                jumpCheck = float(calculateAirSpeed(temperature, rawVal, humidity, currAir, k, 1, range_set, constants_general))
                if jumpCheck < 3.0:
                    airFlow = float(calculateAirSpeed(temperature, rawVal, humidity, currAir, k, 1, range_set, constants_general))
                else:
                    airFlow = float(calculateAirSpeed(temperature, rawVal, humidity, currAir, k, 90, range_set, constants_general))
            currentFlowMap[k] = airFlow
            if airFlow < 0.0 and airFlow > negativeLimit:
                arr2[o][1] = 0.0
            else:
                arr2[o][1] = airFlow
            if rawVal == 1999.0:
                arr2[o][1] = rawVal
                arr2[o][2] = float(k)
                # arr2v[o][2] = float(k)
        o += 1
        
    #ret = [arr2, arr2v]
    # print("Done with read_serial")
    return arr2, currentFlowMap
    
def calculateAirSpeed(temperature, rawVal, humidity, currAir, sensorID, useSet, range_set, constants_general):
    # temperature, rawVal, humidity, currAir, k, 1, range_set, constants_general
    if (currAir > -50.0 and useSet > 40): # useSet = 90
        for i in range(1,len(range_set)): # 1 2
            y = range_set[i]
            # if (i == len(range_set)-1 and currAir < y[1] and currAir > y[0]):
            #     map = constants_general[i]
            #     break
            if (currAir >= y[0] and currAir <= y[1] and y[0] + y[1] != 0):
                map = constants_general[i]
                # print("useSet greater than 40")
                break
            elif currAir <= 0:
                currAir = 0
                map = constants_general[1]
                break
    elif (useSet < 40): # useSet = 1
        map = constants_general[useSet] 
        # print("useSet less than 40")
        
    # print(f"The value for key currAir is: {currAir}")
    # print(map)
    voltage = rawVal * 5.0 / 1024.0 * 2.682926829
    resist = voltage / map["CurrentA"]
    power = voltage * map["CurrentA"]
    airVisc = map["v3"] + map["v2"] * temperature + map["v1"] * math.pow(temperature, 2.0) + map["vrh2"] * humidity - map["vrh1"] * math.pow(humidity, 2.0)
    NTCBulbTemp = 1.0 / (map["a1"] + map["a2"] * math.log(resist) + map["a3"] * math.log(resist) * math.log(resist) + map["a4"] * math.log(resist) * math.log(resist) * math.log(resist))
    airDiss = power / (NTCBulbTemp - (temperature + 273.15))
    airConduct = map["k3"] + map["k2"] * temperature - map["k1"] * math.pow(temperature, 2.0) + map["krh2"] * humidity - map["krh1"] * math.pow(humidity, 2.0)
    s_k = airDiss / airConduct
    
    d1 = map["D1a"] * math.pow(temperature, 5.0) + map["D1b"] * math.pow(temperature, 4.0) + map["D1c"] * math.pow(temperature, 3.0) + map["D1d"] * math.pow(temperature, 2.0) + map["D1e"] * temperature + map["D1f"]
    d2 = map["D2a"] * math.pow(temperature, 5.0) + map["D2b"] * math.pow(temperature, 4.0) + map["D2c"] * math.pow(temperature, 3.0) + map["D2d"] * math.pow(temperature, 2.0) + map["D2e"] * temperature + map["D2f"]
    d3 = map["D3a"] * math.pow(temperature, 5.0) + map["D3b"] * math.pow(temperature, 4.0) + map["D3c"] * math.pow(temperature, 3.0) + map["D3d"] * math.pow(temperature, 2.0) + map["D3e"] * temperature + map["D3f"]
    d4 = map["D4a"] * math.pow(temperature, 5.0) + map["D4b"] * math.pow(temperature, 4.0) + map["D4c"] * math.pow(temperature, 3.0) + map["D4d"] * math.pow(temperature, 2.0) + map["D4e"] * temperature + map["D4f"]
    
    airSpeed = (d1 * math.pow(s_k, 3.0) + d2 * math.pow(s_k, 2.0) + d3 * s_k + d4) * airVisc;
    
    # print("Done with calculateAirSpeed")
    return airSpeed  
                
def crc_check(arr, crc_type, total_packets, failed_packets):
    crc = CRC.CRC() # Create an empty CRC object
    returned = ""
    for sp in arr:
        sep = sp.split(":") # temp1, airflow_volt1, sensorID1: crc_code1: length_of_temp_airflow_sensorID1
        s = sep[0] # temp1, airflow_volt1, sensorID1
        if len(sep) == 3 and sep[2].isdigit():
            if len(s) == int(sep[2]):
                if crc_type == "NoCheck":
                    returned += s + ";"
                elif crc_type == "CRC8":
                    if crc.calculateCRC8(sep[0].encode('utf-8')) == int(sep[1]):
                        returned += s + ";"
                    else:
                        failed_packets += 1
                elif crc_type == "CRC16":
                    if crc.calculateCRC16(sep[0].encode('utf-8')) == int(sep[1]):
                        returned += s + ";"
                    else:
                        failed_packets += 1
                elif crc_type == "CRC32":
                    if crc.calculateCRC32(sep[0].encode('utf-8')) == int(sep[1]):
                        returned += s + ";"
                    else:
                        failed_packets += 1
                else:
                    returned += s + ";"
                total_packets += 1.0
    return returned, total_packets, failed_packets
    
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False           

def read_const(const_file_path): 
    with open(const_file_path, 'r') as file_reader:
        file = file_reader.read()

    file2 = re.sub("[\t\n\r]+", "", file)
    file2 = file2.replace(",", ".")
    arr = file2.split("Set") # There are 2 Sets, so 3 splits
    range_set = [[0, 0] for _ in range(len(arr))] # 3 x 2
    c = 1
    constants_general = {}

    for i in range(len(arr)):
        arr2 = arr[i].split(";")
        constants = {}
        for h in range(len(arr2)):
            if not is_number(arr2[h]) and arr2[h] != "":
                if arr2[h] == "Range":
                    lo = int(arr2[h + 1].split("to")[0])
                    hi = int(arr2[h + 1].split("to")[1])
                    range_set[c][0] = lo # low value of velocity range
                    range_set[c][1] = hi # high value of velocity range
                    c += 1
                elif re.match("^(-)?\d+([.]\d+)?([eE][+-]?\d+)?$", arr2[h + 1]):
                    if arr2[h] in ("D1", "D2", "D3", "D4"):
                        file_contains_ds = True # Not used
                    constants[arr2[h]] = float(arr2[h + 1])
        constants_general[i] = constants 

    return range_set, constants_general

def plot_imshow(col_clim, title, number):
    
    # fig1 = plt.figure(number)
    # ax1 = fig1.add_subplot(111)
    # im1 = ax1.imshow(np.reshape([0 for _ in range(36)], (6, 6)), cmap='jet', vmin = col_clim[0], vmax = col_clim[1])
    # cbar1 = fig1.colorbar(im1)
    # cbar1.mappable.set_clim(vmin=col_clim[0], vmax=col_clim[1])
    # for i in range(6):
    #     for j in range(6):
    #         ax1.text(j, i, 0.0, ha='center', va='center', color='w')
    # ax1.set_title(title)
    # fig1.show()
    # return fig1, ax1, im1, cbar1

    fig1 = plt.figure(number)
    ax1 = fig1.add_subplot(111)
    
    # Create an initial 6x6 array of zeros
    initial_data = np.zeros((6, 6))
    im1 = ax1.imshow(initial_data, cmap='jet', vmin=col_clim[0], vmax=col_clim[1])
    
    # cbar1 = fig1.colorbar(im1)
    cbar1 = fig1.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04, boundaries=np.linspace(col_clim[0], col_clim[1], 256))
    #cbar1.mappable.set_clim(vmin=col_clim[0], vmax=col_clim[1])
    
    # Add text annotations with the initial data (0.0 replaced with '')
    for i in range(6):
        for j in range(6):
            ax1.text(j, i, '', ha='center', va='center', color='w')
    
    ax1.set_title(title)
    
    # You can optionally remove fig1.show() if using this function in interactive environments
    
    return fig1, ax1, im1, cbar1

def plot_update(data, col_clim, title, fig1, ax1, im1, cbar1):
    
    ax1.cla() # Clear the previous data and annotations from the axes
    im1 = ax1.imshow(data, cmap='jet', vmin=col_clim[0], vmax=col_clim[1])
    for i in range(6):
        for j in range(6):
            ax1.text(j, i, f'{data[i, j]:.2f}', ha='center', va='center', color='w')
    ax1.set_title(title)
    fig1.canvas.draw()

def plot_update_2(data, col_clim, title, fig1, ax1, im1, cbar1):
    
    ax1.cla() # Clear the previous data and annotations from the axes
    im1 = ax1.imshow(data, cmap='jet', vmin=col_clim[0], vmax=col_clim[1])
    im1.set_clim(vmin = col_clim[0], vmax = col_clim[1])
    for i in range(6):
        for j in range(6):
            ax1.text(j, i, f'{int(data[i, j]):d}', ha='center', va='center', color='w')
    ax1.set_title(title)
    fig1.canvas.draw()
    
def plot_update_interp(data, col_clim, title, fig1, ax1, im1, cbar1, nan_num, interp_multiplier):
    # Create a 6x6 grid
    x = np.arange(6)
    y = np.arange(6)
    X, Y = np.meshgrid(x, y)

    # Create a (6 x interp_multiplier) x (6 x interp_multiplier) grid for interpolation
    x_new = np.linspace(0, 5, 6*interp_multiplier)
    y_new = np.linspace(0, 5, 6*interp_multiplier)
    X_new, Y_new = np.meshgrid(x_new, y_new)
    
    # Replace NaN values with nan_num before interpolation
    data = np.nan_to_num(data, nan=nan_num)

    # Perform cubic interpolation on the 6x6 data to the 36x36 grid
    interp_func = interp2d(x, y, data, kind='cubic')
    data_interp = interp_func(x_new, y_new)

    ax1.cla()  # Clear the previous data and annotations from the axes

    # Display the interpolated data on the 36x36 grid
    im1 = ax1.imshow(data_interp, cmap='jet', vmin=col_clim[0], vmax=col_clim[1])
    # for (j,i),label in np.ndenumerate(data_interp):
    #     ax1.text(i, j, np.round(label,2), color = 'white', ha='center', va='center')
        
    im1.set_clim(vmin=col_clim[0], vmax=col_clim[1])

    # # Display text on the 6x6 grid
    # for i in range(3,36,6):
    #     for j in range(3,36,6):
    #         ax1.text(j, i, f'{data[i, j]:.2f}', ha='center', va='center', color='w')

    ax1.set_title(title)
    fig1.canvas.draw()

def plot_update_interp_2(data, col_clim, title, fig1, ax1, im1, cbar1, nan_num, interp_multiplier):
    # Create a 6x6 grid
    x = np.arange(6)
    y = np.arange(6)
    X, Y = np.meshgrid(x, y)

    # Create a (6 x interp_multiplier) x (6 x interp_multiplier) grid for interpolation
    x_new = np.linspace(0, 5, 6*interp_multiplier)
    y_new = np.linspace(0, 5, 6*interp_multiplier)
    X_new, Y_new = np.meshgrid(x_new, y_new)
    
    # Replace NaN values with nan_num before interpolation
    data = np.nan_to_num(data, nan=nan_num)

    # Perform cubic interpolation on the 6x6 data to the 36x36 grid
    interp_func = interp2d(x, y, data, kind='cubic')
    data_interp = interp_func(x_new, y_new)

    ax1.cla()  # Clear the previous data and annotations from the axes

    # Display the interpolated data on the 36x36 grid
    im1 = ax1.imshow(data_interp, cmap='jet', vmin=col_clim[0], vmax=col_clim[1])
    im1.set_clim(vmin=col_clim[0], vmax=col_clim[1])

    # # Display text on the 6x6 grid
    # for i in range(3,36,6):
    #     for j in range(3,36,6):
    #         ax1.text(j, i, f'{int(data[i, j]):d}', ha='center', va='center', color='w')

    ax1.set_title(title)
    fig1.canvas.draw()
    

        
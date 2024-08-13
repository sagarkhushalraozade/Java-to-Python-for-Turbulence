import serial
import logging # used to log the error/warning/info in a file/console but cannot point to the line that causes the error.
import traceback # cannot log to a file but can identify the line where the issue occurs.
import numpy as np
import time
import CRC  # user-defined class. To be saved in the same folder as the calling Python file.
import re # This module provides regular expression matching operations.
import math as math
import matplotlib
# matplotlib.use('TkAgg')  # Set the backend to TkAgg
import matplotlib.pyplot as plt
from helping_functions import read_serial, calculateAirSpeed, crc_check, read_const, plot_imshow, plot_update, plot_update_2, plot_update_interp, plot_update_interp_2 # read_serial contains calculateAirSpeed
import os
import glob
from scipy import interpolate

#%% Change pwd to the location of the file.
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print("Current working directory:", os.getcwd())

#%% Initialize serial ports
ubx_port = serial.Serial('COM9', 115200)  # Port for velocity readings
ubx_port_translation_stage = serial.Serial('COM10', 9600)  # Port for translation stage readings
# Give some time for the Arduino to reset and be ready to receive data
time.sleep(2)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

#%% Set variables
humidity = 0.35
negativeLimit = -0.5 # m/s
count_pos = 0
vel_instances = 50 # Instances of velocity, temperature to record at a given Up-Right position
time_for_equilibrium = 30 # seconds
Test_name = "Second_test"

#%% Function to parse position from translation stage data
def parse_position(port):
    global count_pos
    while True:
        try:
            data = port.readline()  # Read the next line from the translation stage
            data_str = data.decode('utf-8').strip()  # Decode the byte data to a string
            # Example expected format for velocity reading to happen: "Moved to Up = 9.22 cm, Right = 0.65 cm"
            if "Moved to Up" in data_str:
                print(data_str)
                parts = data_str.split(",")
                up_str = parts[0].split("=")[1].strip().replace(" cm", "")
                right_str = parts[1].split("=")[1].strip().replace(" cm", "")
                count_pos+=1
                return float(up_str), float(right_str), int(count_pos)
            elif (data_str == "All left-right positions are reached. Hence, all positions are reached"):
                print(data_str)
                count_pos = 123456
                up_str = None
                right_str = None
                return up_str, right_str, count_pos
            else:
                print(data_str)
        except Exception as e:
            # Optionally add a short delay to prevent excessive looping
            time.sleep(0.5)

#%% Variables for reading velocity.
read_buffer = 2048 # bytearray(2048)
total_packets = 1
failed_packets = 0
read_count = 0
num_sensors = 36
sensorIDList = [_ for _ in range(1,37)] # [1 2 3 .......36]
sensor_array = np.reshape(sensorIDList, (6,6))
sensor_array = sensor_array[::-1,:] # Reversing the rows.
sensorIDList = np.reshape(sensor_array,(36)) # [36 35 34 33 32 31 25.....1 2 3 4 5 6] # This is what I see experimentally.
sensor_physical_x_pos, sensor_physical_y_pos = np.meshgrid(np.arange(0,250+0.01,50, dtype=int), np.arange(0,250+0.01,50, dtype=int)) # Physical position of the velocity sensors in meters. Origin is at the bottom right corner.
range_set, constants_general = read_const('Constants28Dec.csv')
crc_Type = "NoCheck" # Can choose between "NoCheck", "CRC8", "CRC16", "CRC32"
currentFlowMap = {key: 0.0 for key in sensorIDList}
jumpPrevention = False
# Function to read a 36 x 36 velocity matrix from the UBX port
def read_velocity_matrix():
    global total_packets, failed_packets, currentFlowMap
    bytes_read = ubx_port.read(read_buffer) # This blocks the code execution till new data is available from the port.
    if bytes_read:
        temperature_array = None
        airflow_array = None
        try:
            decoded_data = bytes_read.decode('utf-8')
            split_data = decoded_data.split(";")
            checked_data, total_packets, failed_packets  = crc_check(split_data, crc_Type, total_packets, failed_packets) 
            arr2D, currentFlowMap = read_serial(checked_data, humidity, num_sensors, sensorIDList, jumpPrevention, negativeLimit, currentFlowMap, range_set, constants_general) 
            
            temperature = [get_row[0] for get_row in arr2D] # Arranged as sensorIDList 
            airflow = [get_row[1] for get_row in arr2D]
            
            airflow_array = np.reshape(np.array(airflow), (6,6))
            temperature_array = np.reshape(np.array(temperature), (6, 6)) # need np since list reshaping is not possible easily
            return(airflow_array, temperature_array)
        except Exception as e:
            logging.error("Error reading velocity data.")
            logging.error(traceback.format_exc())
            return np.empty((6, 6)), np.empty((6, 6))
    return np.empty((6, 6)), np.empty((6, 6)) # If bytes_read is not created.

#%% Function to find mean of 3d velocity and temperature data by disregarding the spurious data
def find_median(data_3d):
    mean_data_2d = np.nanmedian(data_3d[10:,:,:], axis=0)
    return mean_data_2d

#%% Function to interpolate velocity and temperature data
def fine_interpolation(master_array, interpolation_method):
    master_array_x = np.arange(0, master_array.shape[1])
    master_array_y = np.arange(0, master_array.shape[0])
    master_array = np.ma.masked_invalid(master_array) # #mask invalid values ('nan' becomes 'masked')
    master_array_xx, master_array_yy = np.meshgrid(master_array_x, master_array_y)
    valid_xx = master_array_xx[~master_array.mask]
    valid_yy = master_array_yy[~master_array.mask]
    valid_master_array = master_array[~master_array.mask]
    master_array_interpolated = interpolate.griddata((valid_xx, valid_yy), valid_master_array.ravel(), (master_array_xx, master_array_yy), method=interpolation_method) 
    return master_array_interpolated

#%% Main loop

results_save_dir = rf"C:/Users/ZadeSag/OneDrive - Electrolux/Documents/Projects/Air Care/Grid/Grid Macbook/Java-to-Python-for-Turbulence/" + Test_name # For WIndows.
# results_save_dir = rf"/Users/sagarzade/Library/CloudStorage/OneDrive-Electrolux/Documents/Projects/Air Care/Grid/Grid Macbook/Java-to-Python-for-Turbulence/" + Test_name # For MacOS.
if not os.path.exists(results_save_dir):
    os.mkdir(results_save_dir)
else:
    logging.info(rf"{results_save_dir} exists. Will be used to save the files.")

ubx_port_translation_stage.write(b'S') # Send the 'S' character (in bytes) to start the Arduino's main task.
try:
    while True:
        # Read position data from the translation stage
        up, right, count_pos = parse_position(ubx_port_translation_stage)

        if up is not None and right is not None and count_pos is not None:
            velocity_data_3d = np.empty((vel_instances,6,6))
            temperature_data_3d = np.empty((vel_instances,6,6))
            
            logging.info(rf"Waiting for {time_for_equilibrium} seconds.")
            time.sleep(time_for_equilibrium)

            for i in range(vel_instances):  # Collect vel_instances velocity-matrices
                velocity_matrix, temperature_matrix = read_velocity_matrix()
                if velocity_matrix is not None and temperature_matrix is not None:
                    velocity_data_3d[i,:,:] = velocity_matrix
                    temperature_data_3d[i,:,:] = temperature_matrix
                    time.sleep(1)
                    logging.info(rf"velocity recorded {i}")
                else:
                    logging.warning("Received None from read_velocity_matrix.")
            
            velocity_data_3d = np.array(velocity_data_3d)
            temperature_data_3d = np.array(temperature_data_3d)

            filename = results_save_dir + rf"/Up_{up:.2f}_Right_{right:.2f}.npz"
            np.savez(filename, velocity_data_3d=velocity_data_3d, temperature_data_3d=temperature_data_3d, up_position = up, right_position = right, position_number = count_pos)
            logging.info(f"Saved velocity and temperature data")
            print(rf"Read up = {up} and right = {right}, position number = {count_pos}")
            
        elif  up is None and right is None and count_pos is 123456:
            print("Exiting the while loop")
            break  # Exit the while loop and go to finally.
except KeyboardInterrupt:
    logging.info("Data collection stopped by user.")
finally:
    ubx_port.close()
    # ubx_port_translation_stage.write(b'T')  # Send termination character
    ubx_port_translation_stage.close()
 
#%% To load the data.
# files_saved = os.listdir(results_save_dir) # Also counts .DStore as a file.
files_saved  = sorted(glob.glob(results_save_dir + "/*.npz"),key=os.path.getmtime)
num_files = len(files_saved)
master_vel_array = np.empty((250+50,250+50)) # Grid of 300 cm x 300 cm. We will populate data at 1 cm resolution.
master_vel_array[:,:] = None # nan everywhere.
master_temp_array = np.copy(master_vel_array)

for i in range(num_files):
    file_to_load = files_saved[i] # os.path.abspath gives pwd
    data = np.load(file_to_load, allow_pickle=True)
    vel_data = find_median(data['velocity_data_3d'])
    temp_data = find_median(data['temperature_data_3d'])
    table_up_pos = data['up_position']
    table_right_pos = data['right_position']
    pos_num = data['position_number']
    data.close()
    data_position_x, data_position_y = int(np.round(table_right_pos,0)), int(np.round(table_up_pos,0)) 
    # input(rf"Position is up = {data_position_y}, right = {data_position_x}")
    master_vel_array[sensor_physical_y_pos + data_position_y, sensor_physical_x_pos + data_position_x] = vel_data
    master_temp_array[sensor_physical_y_pos + data_position_y, sensor_physical_x_pos + data_position_x] = temp_data
    # for loop end

# Interpolate velocities at places where values are nan.
master_vel_array_interpolated = fine_interpolation(master_vel_array, 'cubic')
master_temp_array_interpolated = fine_interpolation(master_temp_array, 'cubic')

fig1, (ax1, ax2) = plt.subplots(1,2, figsize=(14,8)) # 14" width of figure.

im1 = ax1.imshow(master_vel_array_interpolated, cmap = 'jet', interpolation = 'None', vmin = 0.3)
cbar1 = fig1.colorbar(im1, ax = ax1)
ax1.set_aspect('equal')
ax1.set_xticks(np.arange(0, 300, 10))
ax1.set_yticks(np.arange(0, 300, 10))
ax1.set_xticklabels(ax1.get_xticks(), rotation = 90)
ax1.grid(which='major', color='w', linestyle='-', linewidth=0.2)
ax1.set_title('Velocity (m/s)')

im2 = ax2.imshow(master_temp_array_interpolated, cmap = 'jet', interpolation = 'None', vmin = 15, vmax = 30)
cbar2 = fig1.colorbar(im2, ax = ax2)
ax2.set_aspect('equal')
ax2.set_xticks(np.arange(0, 300, 10))
ax2.set_yticks(np.arange(0, 300, 10))
ax2.set_xticklabels(ax2.get_xticks(), rotation = 90)
ax2.grid(which='major', color='w', linestyle='-', linewidth=0.2)
ax2.set_title('Temperature ($^\circ$C)')



#%%
# Code to read saved velocity and plot it on a grid. 
# Final interpolation of the velocities. 

#%% Code to test a coarser grid.
master_vel_array = np.empty((25+5,25+5)) # Array in 30 x 30 dm = 300 cm x 300 cm
master_vel_array[:,:] = None # nan everywhere.
master_temp_array = np.copy(master_vel_array)

vel_data_all = np.empty((num_files, 50, 6,6))
vel_data_all[:,:,:,:] = None  
temp_data_all = np.copy(vel_data_all)

for i in range(num_files):
    file_to_load = files_saved[i] # os.path.abspath gives pwd
    data = np.load(file_to_load, allow_pickle=True)
    vel_data = find_median(data['velocity_data_3d'])
    temp_data = find_median(data['temperature_data_3d'])
    vel_data_all[i,:,:,:] = data['velocity_data_3d']
    temp_data_all[i,:,:,:] = data['temperature_data_3d']
    table_up_pos = data['up_position']
    table_right_pos = data['right_position']
    pos_num = data['position_number']
    data.close()
    data_position_x, data_position_y = int(np.round(table_right_pos,0)), int(np.round(table_up_pos,0)) 
    # input(rf"Position is up = {data_position_y}, right = {data_position_x}")
    master_vel_array[np.round((sensor_physical_y_pos + data_position_y)/10, 0).astype(int), np.round((sensor_physical_x_pos + data_position_x)/10, 0).astype(int)] = vel_data
    master_temp_array[np.round((sensor_physical_y_pos + data_position_y)/10, 0).astype(int),np.round((sensor_physical_x_pos + data_position_x)/10, 0).astype(int)] = temp_data
    # for loop end

master_vel_array_interpolated = fine_interpolation(master_vel_array, 'linear')
master_temp_array_interpolated = fine_interpolation(master_temp_array, 'linear')

#%% Test code to save random data
# test_up = np.linspace(0,40,5)
# test_right = np.linspace(0,40,5)
# count_pos = 0
# for i in range(len(test_up)):
#     for j in range(len(test_right)):
#         up, right = np.squeeze(test_up[i]+np.random.rand(1)), np.squeeze(test_right[j]+np.random.rand(1))
#         count_pos+=1
#         velocity_data_3d = (i+j)*np.random.rand(60,6,6)
#         temperature_data_3d = 20+(i+j)*np.random.rand(60,6,6)
#         filename = results_save_dir + rf"/Up_{up:.2f}_Right_{right:.2f}.npz"
#         np.savez(filename, velocity_data_3d=velocity_data_3d, temperature_data_3d=temperature_data_3d, up_position = up, right_position = right, position_number = count_pos)
        

# -*- coding: utf-8 -*-
"""
Created on Wed Jul 19 17:15:32 2023

@author: ZadeSag
"""

# import numpy as np
# import time
# import matplotlib
# matplotlib.use('TkAgg')  # Set the backend to TkAgg
# import matplotlib.pyplot as plt
# from helping_functions import plot_imshow# read_serial contains calculateAirSpeed


# temp_clim = [18, 30] # range of temperature (in C) to display

# figT, axT, imT, cbarT = plot_imshow(temp_clim, 'Temperature (°C)', 1)
# imT.set_clim(vmin = temp_clim[0], vmax = temp_clim[1])

# for i in range(100):
#     # update plot
#     temperature_array = np.random.randint(10, 31, size=(6, 6))
#     axT.cla() # Clear the previous data and annotations from the axes
#     imT.set_data(temperature_array)
#     for i in range(6):
#         for j in range(6):
#             axT.text(j, i, f'{temperature_array[i, j]:.2f}', ha='center', va='center', color='w')
#     figT.canvas.draw()
    
#     time.sleep(1)

from math import pi
import matplotlib
matplotlib.use('QtAgg')  # Set the backend to QtAgg
import matplotlib.pyplot as plt
import numpy as np
import time
 
# generating random data values
x = np.linspace(1, 1000, 5000)
y = np.random.randint(1, 1000, 5000)
 
# enable interactive mode
plt.ion()
 
# creating subplot and figure
fig = plt.figure()
ax = fig.add_subplot(111)
line1, = ax.plot(x, y)
 
# setting labels
plt.xlabel("X-axis")
plt.ylabel("Y-axis")
plt.title("Updating plot...")
 
# looping
for _ in range(50):
   
    # updating the value of x and y
    line1.set_xdata(x*_)
    line1.set_ydata(y)
 
    # re-drawing the figure
    fig.canvas.draw()
     
    # to flush the GUI events
    fig.canvas.flush_events()
    time.sleep(0.1)
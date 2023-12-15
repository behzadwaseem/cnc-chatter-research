import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from witmotion import IMU
import witmotion
import time
import csv

# FILE TO STORE DATA
CNC_DATAFILE = ''  # change to desired file for data storing

# SENSOR SETTINGS:
WIRED_PORT = ''  # change to system-specific port
BAUDRATE = 115200  # change to imu-specific baudrate
# BT_PORT = ''
# BT_BAUDRATE = 115200

# CREATING AN INSTANCE OF THE WITMOTION CLASS:
wm = IMU(WIRED_PORT, baudrate=BAUDRATE)  # use this for wired sensor
# wm = IMU(BT_PORT, baudrate=BT_BAUDRATE)  # use this for bluetooth sensor


def live_calibration():
    # CALIBRATING SENSORS:
    wm.set_gyro_automatic_calibration(True)
    wm.set_calibration_mode(witmotion.protocol.CalibrationMode(1))
    wm.set_calibration_mode(witmotion.protocol.CalibrationMode(2))  # Find out more about magnetic calibration

    # Countdown to Signify Calibration Timing:
    print('Calibrating Sensor. . .')
    for i in range(0, 5):
        print(5 - i)
        time.sleep(1)  # pausing to let sensors calibrate


def process_data():
    # Storing Current Data Retrieved from Sensor:
    angles = wm.get_angle()
    accels = wm.get_acceleration()
    time1 = time.time() - start_time

    # Exit code if either sensor is not configured properly and returns 'none':
    if angles[0] == 'none':
        print('No Angles sensed on wired sensor')
    elif accels[0] == 'none':
        print('No acceleration secret_key from wired sensor')
    else:
        # Pausing to Change Collection Frequency:
        time.sleep(0.005)

        # Appending Current Data to Lists of Previous Data Points:
        timestamps.append(time1)

        angXs.append(angles[0])
        angYs.append(angles[1])
        angZs.append(angles[2])

        accelXs.append(accels[0])
        accelYs.append(accels[1])
        accelZs.append(accels[2] - 9.838281250000001)
        #accelZs_data.append(accels[2])

        # Printing Sensor Values:
        print(f"Time: {time1}  |||  AccelX: {accels[0]}  |||  AccelY: {accels[1]}  |||  AccelZ: {accels[2]} ")


# FUNCTION TO UPDATE REAL-TIME GRAPH:
def update_plot(frame):
    process_data()  # start processing
    plt.cla()  # clearing plot

    # Plotting Acceleration Values:
    plt.plot(timestamps, accelXs, label='AccelX')
    plt.plot(timestamps, accelYs, label='AccelY')
    plt.plot(timestamps, accelZs, label='AccelZ')

    # Labelling Plot:
    plt.xlabel('Time')
    plt.ylabel('Acceleration Values (XYZ)')
    plt.legend()


def on_close_plot(event):
    # Writing the Collected Data to a CSV File:
    with open(CNC_DATAFILE, mode='a') as IMU_SenorData:
        fieldnames = ['TimeStamp',
                      'AngleX', 'AngleY', 'AngleZ', 'AccelerationX', 'AccelerationY',
                      'AccelerationZ']  # headings for columns within csv file
        writer = csv.writer(IMU_SenorData)
        writer.writerow(fieldnames)  # writing file heading

        # Writing Sensor Data to CSV File:
        for timestamp, angX, angY, angZ, accelX, accelY, accelZ in zip(timestamps, angXs, angYs, angZs, accelXs,
                                                                       accelYs, accelZs):
            writer.writerow([timestamp, angX, angY, angZ, accelX, accelY, (accelZ+9.838281250000001)])  # re-adding gravity constant to accelZ

    # Closing CSV File:
    IMU_SenorData.close()


# BEGINNING CALIBRATION PROCESS:
live_calibration()


# INITIALIZING EMPTY LISTS TO STORE DATA:
timestamps = []
angXs = []
angYs = []
angZs = []
accelXs = []
accelYs = []
accelZs = []

start_time = time.time()  # recording program's start time


# PLOTTING REAL-TIME GRAPH
fig, ax = plt.subplots()
fig.canvas.mpl_connect('close_event', on_close_plot)  # calling on_close_plot function when plot is closed

ani = FuncAnimation(fig, update_plot, interval=10, save_count=100)  # animating graph
plt.show()  # displaying graph

# CLOSING CONNECTION TO SENSOR:
wm.close()
from witmotion import IMU
import witmotion
import time
import csv


csv_directory = ""  # change to directory of csv file

# CREATING AN INSTANCE OF THE WITMOTION CLASS:
wm = IMU('/dev/cu.usbserial-120', baudrate=115200)  # NOTE - CHANGE COM PORT & BAUDRATE TO SYSTEM-SPECIFIC
# wm = IMU('/dev/cu.usbserial-1120', baudrate=115200)  # use this for bluetooth sensor


# SENSOR INITIALIZATION & CALIBRATION FUNCTION:
def calibrate_sensor():

    # Calibrating Sensors:
    wm.set_gyro_automatic_calibration(True)
    wm.set_calibration_mode(witmotion.protocol.CalibrationMode(1))
    wm.set_calibration_mode(witmotion.protocol.CalibrationMode(2))  # Find out more about magnetic calibration

    # Countdown to Allow for Calibration:
    print('Calibrating . . .')
    for i in range(0,5):
        print(5-i)
        time.sleep(1)  # pause to let sensors calibrate


# DATA COLLECTION & RECORDING FUNCTION:
def record_data():

    # Appending Sensor Data to CSV File:
    with open(csv_directory, mode='a') as IMU_SenorData:

        # Specifying Column Headings:
        fieldnames = ['TimeStamp', 'AngleX', 'AngleY', 'AngleZ', 'AccelerationX', 'AccelerationY', 'AccelerationZ']
        writer = csv.DictWriter(IMU_SenorData, fieldnames=fieldnames)
        writer.writeheader()

        start_time = time.time()  # recording program's start time

        # MAIN LOOP FOR COLLECTING & STORING SENSOR DATA
        while True:
            try:
                time.sleep(0.005)  # pausing to change collection frequency

                # Retrieving Values From Sensor:
                angle1 = wm.get_angle()
                accel1 = wm.get_acceleration()
                time1 = time.time() - start_time

                # Exit code if either sensor is not configured properly and returns 'none':
                if angle1[0] == 'none':
                    print('No Angles sensed on wired sensor')
                    break
                elif accel1[0] == 'none':
                    print('No acceleration secret_key from wired sensor')
                    break
                else:
                    print(time1)  # printing current time since program began running

                    # Storing Sensor Data:
                    data_dict = {'TimeStamp': time1,
                                 'AngleX': angle1[0], 'AngleY': angle1[1], 'AngleZ': angle1[2],
                                 'AccelerationX': accel1[0], 'AccelerationY': accel1[1], 'AccelerationZ': accel1[2]}

                    # Writing Sensor Data to CSV File:
                    writer.writerow(data_dict)

            # Breaking loop if Ctrl+C is Pressed:
            except KeyboardInterrupt:
                break

    # Closing CSV File & Connection to IMU:
    IMU_SenorData.close()
    wm.close()


calibrate_sensor()
record_data()

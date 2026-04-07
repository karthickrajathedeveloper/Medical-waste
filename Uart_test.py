'''
import serial
import time

# Change COM port (example: COM3 or /dev/ttyUSB0)
ser = serial.Serial('COM67', 115200, timeout=1)
time.sleep(2)  # wait for ESP32 reset

while True:
    cmd = input("Enter 1 (ON) / 0 (OFF): ")

    if cmd == '1':
        ser.write(b'1')
    elif cmd == '0':
        ser.write(b'0')
    elif cmd == '180':
        ser.write(b'180')

    data = ser.readline().decode().strip()
    print("ESP32:", data)
    '''


import serial
import time

ser = serial.Serial('COM67', 115200, timeout=1)
time.sleep(2)

while True:
    angle = input("Enter angle (0-180): ")

    if angle.isdigit():
        ser.write((angle + '\n').encode())

        response = ser.readline().decode().strip()
        print("ESP32:", response)

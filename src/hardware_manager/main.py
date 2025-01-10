import serial

current_state = "DISCONNECTED" # DISCONNECTED, IDLE, RUNNING
ser = None

def connect():
    global current_state
    global ser
    ser = serial.Serial('/dev/ttyACM0', 115200)
    current_state = "IDLE"
    print("Connected to hardware!")
    send_line("M18")
    send_line("M5")
    print("Move to (0, 0), then press enter to start...")
    input()
    send_line("M17")
    send_line("G92 X0 Y0")


def disconnect():
    global current_state
    global ser
    if ser is not None:
        ser.close()
    current_state = "DISCONNECTED"
    print("Disconnected from hardware!")

def send_line(line: str):
    global ser
    if ser is None:
        print("Not connected to hardware!")
        return
    ser.write(line.encode())
    ser.write(b"\n")
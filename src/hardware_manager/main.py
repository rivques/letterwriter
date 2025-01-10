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
    print("hardware initted. self-testing...")
    send_line("G0 X10 Y10 F2000")
    send_line("G0 X10 Y0 F4000")
    send_line("G0 X0 Y0 F6000")
    send_line("G0 X125 Y0 F8000")
    send_line("G0 X125 Y125 F8000")
    send_line("G0 X0 Y125 F8000")
    send_line("G0 X0 Y0 F8000")
    print("self-test complete. hardware ready.")

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
    ser.flush()
    print(f"Sent: {line}")
    line = ser.readline().decode().strip()
    print(f"Received: {line}")

def send_file(filename: str):
    global current_state
    global ser
    if ser is None:
        print("Not connected to hardware!")
        return
    if current_state != "IDLE":
        print("Hardware not in IDLE state!")
        return
    with open(filename, "r") as file:
        for line in file:
            send_line(line.strip())
    print("File sent!")
    current_state = "RUNNING"

if __name__ == "__main__":
    connect()
    print("press enter to start...")
    input()
    send_file("postcard.gcode")
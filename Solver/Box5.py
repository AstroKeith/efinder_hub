#!/usr/bin/python3

# Code to emulate a Nexus DSC when testing an eFinder cli
# Start this code before booting the eFinder
# if /dev/ttyACM0 not found, try replugging the USB cable.

import serial
import time
import numpy as np
from io import BytesIO
from PIL import Image
from threading import Thread
import os
import subprocess
import socket
from pathlib import Path
home_path = str(Path.home())
param = dict()
import Display_Lite
version = "1_5"
handpad = Display_Lite.Handpad(version,"right")
handpad.display('Nexus eFinder','Hub Control Box','Version '+ version)
import time
import math
from PIL import Image, ImageDraw,ImageFont, ImageEnhance
from datetime import datetime, timezone
import numpy as np
np.math = math
import Coordinates_wifi_2
from gpiozero import Button
from skyfield.api import load
#from skyfield.timelib import Timescale
#from skyfield.vectorlib import VectorSum

dispBright = 241
x = 1
fnt = ImageFont.truetype(home_path+"/Solver/text.ttf",8)
expInc = 0.1 # sets how much exposure changes when using handpad adjust (seconds)
gainInc = 5 # ditto for gain
mode = "Manual"
header32 = b"\x93NUMPY\x01\x00v\x00{'descr': '|u1', 'fortran_order': False, 'shape': (32, 32), }                                                         "
solved_radec = 0,0
goto = False
con = False
Lat = Long = 0
ts = load.timescale()

def serveWifi(): # serve WiFi port
    global solved_radec, goto_altaz, param, goto, timeOffset, raStr, decStr, con, Lat, Long, arr, month, year
    print ('starting wifi server')
    host = ''
    port = 4060
    backlog = 50
    size = 1024
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host,port))
    s.listen(backlog)
    raStr = decStr = ""
    timeOffset = '0'
    timeStr = '23:00:00'
    try:
        while True:
            try:
                client, address = s.accept()
                con = True
                while True:
                    data = client.recv(size)
                    if not data:
                        break
                    if data:
                        pkt = data.decode("utf-8","ignore")
                        time.sleep(0.02)
                        a = pkt.split('#')
                        raPacket = coordinates.hh2dms(solved_radec[0]/15)+'#'
                        decPacket = coordinates.dd2aligndms(solved_radec[1])+'#'
                        for x in a:
                            if x != '':
                                #print (x)
                                if x == ':GR':
                                    client.send(bytes(raPacket.encode('ascii')))
                                elif x == ':GD':
                                    client.send(bytes(decPacket.encode('ascii')))
                                elif x[1:3] == 'St':
                                    client.send(b'1')
                                    Lat = x[3:].split('*')
                                    Lat = int(Lat[0]) + int(Lat[1])/60 # Latitude as decimal degrees North +Ve
                                    print('Lat',Lat)
                                elif x[1:3] == 'Sg':
                                    client.send(b'1')
                                    Long = x[3:].split('*')
                                    Long = int(Long[0]) + int(Long[1])/60 # Longitude as decimal degrees West +ve
                                    if Long > 180:
                                        Long=Long-360
                                elif x[1:3] == 'SG':
                                    client.send(b'1')
                                    timeOffset = x[3:]
                                elif x[1:3] == 'SL':
                                    client.send(b'1')
                                    timeStr = x[3:]
                                elif x[1:3] == 'SC':
                                    client.send(b'Updating Planetary Data#                              #')
                                    print('dateSet',timeOffset,timeStr,x[3:])
                                    coordinates.dateSet(timeOffset,timeStr,x[3:])
                                    now = datetime.now(timezone.utc)
                                    month = now.month
                                    year = now.year
                                    param["month"] = str(month)
                                    param["year"] = str(year)
                                    save_param()
                                    arr[5][0] = param["year"] + "/" + param["month"]
                                    arr[5][1] = 'Lgt: ' + str(int(Long)) + ' Lat: ' + str(int(Lat))
                                    arr[5][2] = 'T: ' + timeStr + ' ' + str(-1*int(float(timeOffset)))
                                    handpad.display(arr[5][0], arr[5][1], arr[5][2])
                                    time.sleep(1)
                                    handpad.display(arr[1][0], arr[1][1], arr[1][2])
                                elif x[1:3] == 'Sr': # target RA
                                    raStr = x[3:]
                                    client.send(b'1')
                                elif x[1:3] == 'Sd': # target Dec
                                    decStr = x[3:]
                                    client.send(b'1')  
                                elif x[1:3] == 'CM': # do offset
                                    client.send(b'0')
                                    measure_offset()
                                elif x[1:3] == 'MS': # do a goto
                                    client.send(b'0')
                                    ra = raStr.split(':')
                                    gotoRa = int(ra[0])+int(ra[1])/60+int(ra[2])/3600
                                    dec = decStr.split('*')
                                    decdec = dec[1].split(':')
                                    gotoDec = int(dec[0]) + math.copysign((int(decdec[0])/60+int(decdec[1])/3600),float(dec[0]))
                                    print('GoTo target received:',gotoRa, gotoDec)
                                    goto_altaz = conv_altaz(gotoRa * 15,gotoDec)
                                    goto = True
                                    print ('goto',goto_altaz)
                                elif x[1]== 'Q':
                                    goto = False

            except Exception as error:
                print (error)
                print ('re-starting Device wifi server')
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host,port))
                s.listen(backlog)
    except Exception as error:
        print (error)


def bytes_to_array(b: bytes) -> np.ndarray:
    np_bytes = BytesIO(b)
    return np.load(np_bytes, allow_pickle=True)

def left_right(v):
    global x
    x = x + v
    time.sleep(0.2)
    handpad.display(arr[x][0], arr[x][1], arr[x][2])

def flip():
    global param, arr
    arr[x][1] = 1 - int(float(arr[x][1]))
    param[arr[x][0]] = str((arr[x][1]))
    handpad.display(arr[x][0], arr[x][1], arr[x][2])
    time.sleep(0.1)


def get_param():
    global param
    if os.path.exists(home_path + "/Solver/box.config") == True:
        with open(home_path + "/Solver/box.config") as h:
            for line in h:
                line = line.strip("\n").split(":")
                param[line[0]] = str(line[1])

def save_param():
    with open(home_path + "/Solver/box.config", "w") as h:
        for key, value in param.items():
            h.write("%s:%s\n" % (key, value))

def doButton(button):
    pin = str(button.pin)[4:]
    if pin == '20':
        time.sleep(0.4)
        if ok.is_pressed:
            exec(arr[x][8])
        else:
            exec(arr[x][7])
            stop = True
        #time.sleep(0.1)

    if pin == '5':
        time.sleep(0.05)
        exec(arr[x][3])
    elif pin == '6':
        time.sleep(0.05)
        exec(arr[x][4])
    elif pin == '13':
        time.sleep(0.05)
        exec(arr[x][5])
    elif pin == '19':
        time.sleep(0.05)
        exec(arr[x][6])


def AdjBright(c):
    global param, arr
    param["Brightness"] = int(param["Brightness"]) + (c * 20)
    if param["Brightness"] > 255:
        param["Brightness"]= 255
    elif param["Brightness"] < 1:
        param["Brightness"] = 1
    handpad.bright(param["Brightness"])
    arr[x][2] = "Brightness " + str(param["Brightness"])
    handpad.display(arr[x][0], arr[x][1], arr[x][2])
    save_param()

def adjExp(i):
    global exp, param
    exp = float(param["Exposure"])
    exp = str(float(exp) + i*expInc)
    eFinderCmd('SE' + exp)
    getFS() # to update display with new exp value
    param["Exposure"] = exp
    save_param()

def eFinderCmd(cmd):
    global ser
    txt = ':'+cmd+'#'
    ser.write(bytes(txt.encode("ascii")))
    reply = ser.read_until(expected='#'.encode("ascii")).decode("CP1253")
    print ('Reply ',reply)
    return reply

def eFinderArray(cmd):
    global ser
    txt = ':'+cmd+'#'
    ser.write(bytes(txt.encode("ascii")))
    while ser.in_waiting == 0:
        time.sleep(0.1)
    reply = ser.read(ser.in_waiting)
    reply = header32 + reply[3:]
    time.sleep(0.02)
    while ser.in_waiting > 0:
        pkt = ser.read(ser.in_waiting)
        reply = reply + pkt
        time.sleep(0.02)
    #print(len(reply))
    imArray = bytes_to_array(reply)
    return imArray
        
def getRaDec():
    global arr, solved_radec
    reply = eFinderCmd('PS')
    reply = eFinderCmd('GR')
    ra,dec = reply.split(' ')
    ra = float(ra[3:])
    dec = float(dec.strip('#'))
    ra,dec = coordinates.precess(ra,dec)
    raStr = coordinates.hh2dms(ra/15)
    decStr = coordinates.dd2dms(dec)
    arr[1][0] = "RA: " + raStr
    arr[1][1] = "Dec: " + decStr
    arr[1][2] = mode
    solved_radec = ra,dec
    if x == 1:
        handpad.display(arr[x][0], arr[x][1], arr[x][2])

def measure_offset():
    global arr
    reply = eFinderCmd('OF')
    name,id,dx,dy = reply.strip('#').split(',')
    dxStr = str(dx)
    dyStr = str(dy)
    arr[2][0] = name[3:]
    arr[2][1] = id
    arr[2][2] = dxStr + ',' + dyStr
    handpad.display(arr[2][0], arr[2][1], arr[2][2])

def getFS():
    global arr
    reply = eFinderCmd('FS')
    stars = eFinderCmd('GS').strip('#')[3:]
    peak = eFinderCmd('GK').strip('#')[3:]
    img = eFinderArray('GI')
    psf = eFinderArray('GP')
    print (img)
    print (psf)
    
    imp = Image.fromarray(np.uint8(img),'L')
    #imp = imp.resize((32,32),Image.LANCZOS)
    im = imp.convert(mode='1')
    
    imp = Image.fromarray(np.uint8(psf),'L')
    #imp = imp.resize((32,32),Image.LANCZOS)
    imgPlot = imp.convert(mode='1')

    txtPlot = Image.new("1",(50,32))
    txt = ImageDraw.Draw(txtPlot)
    txt.text((0,0),"Pk="+ peak,font = fnt,fill='white')
    txt.text((0,10),"No="+ stars,font = fnt,fill='white')
    txt.text((0,20),"Ex=" + str(exp),font = fnt,fill='white')
    
    screen = Image.new("1",(128,32))
    screen.paste(im,box=(0,0))
    screen.paste(txtPlot,box=(35,0))
    screen.paste(imgPlot,box=(80,0))
    
    handpad.dispFocus(screen)
    
def adjDate(i):
    global arr, param
    month = int(param["month"])
    year = int(param["year"])
    month = month + i
    if month > 12:
        month = 1
        year +=1
    elif month < 1:
        month = 12
        year -=1
    param["year"] = str(year)
    param["month"] = str(month)
    save_param()
    arr[x][0] = 'Date: ' + param["year"] + "/" + param["month"]
    handpad.display(arr[x][0], arr[x][1], arr[x][2])

def flipMode():
    global mode, arr
    if mode == "Auto":
        mode = "Manual"
    else:
        mode = "Auto"
    arr[1][2] = arr[0][2] = mode
    handpad.display(arr[x][0], arr[x][1], arr[x][2])

def check_ss():
    if con == True:
        left_right(-1)

def conv_altaz(ra, dec):
    t = ts.now()
    Rad = math.pi / 180
    LST = t.gmst - Long / 15  # as decimal hours
    if LST < 0:
        LST += 24
    elif LST > 24:
        LST -= 24
    #ra = ra * 15  # need to work in degrees now
    LSTd = LST * 15
    LHA = (LSTd - ra + 360) - ((int)((LSTd - ra + 360) / 360)) * 360
    print('time',t,'LST',LST,'LHA',LHA,'ra',ra,'dec',dec,'Lat',Lat,'Long',Long)
    x = math.cos(LHA * Rad) * math.cos(dec * Rad)
    y = math.sin(LHA * Rad) * math.cos(dec * Rad)
    z = math.sin(dec * Rad)
    xhor = x * math.cos((90 - Lat) * Rad) - z * math.sin((90 - Lat) * Rad)
    yhor = y
    zhor = x * math.sin((90 - Lat) * Rad) + z * math.cos((90 - Lat) * Rad)
    az = math.atan2(yhor, xhor) * (180 / math.pi) + 180
    alt = math.asin(zhor) * (180 / math.pi)
    return (alt, az)

def getAltAz():
    global arr, solved_radec
    getRaDec()
    solved_altaz = conv_altaz(solved_radec[0], solved_radec[1])
    altStr = coordinates.dd2dms(solved_altaz[0])
    azStr = coordinates.dd2dms(solved_altaz[1])
    if goto:
        ddAz = goto_altaz[1] - solved_altaz[1]
        ddAlt = goto_altaz[0] - solved_altaz[0]
        handpad.dispGoto(ddAz, ddAlt, azStr, altStr, "GoTo        Scope")
    else:
        arr[0][0] = "Alt: " + altStr
        arr[0][1] = "Az: " + azStr
        arr[0][2] = mode
        handpad.display(arr[0][0], arr[0][1], arr[0][2])

def checkNTP():
    try:
        if param["use_NTP"].lower() == "true":
            result = subprocess.run(['timedatectl'],capture_output=True, text=True)
            #print(result)
        if 'synchronized: yes'in str(result):
            return True
        else:
            return False
    except:
        return False

get_param()      
coordinates = Coordinates_wifi_2.Coordinates(int(param["year"]), int(param["month"]))
dxStr = dyStr = ""

try:
    Long = float(param["Longitude"])
    Lat = float(param["Latitude"])
    if Long != 0 and Lat != 0:
        location = True
        print('location set in config')
    else:
        location = False
        print('No location set in config')
except:
    location = False
    print('problem reading config)')

print ('checkNTP',checkNTP())

if location == True and checkNTP() == True:
    con = True

altaz= [
    "AltAz",
    "No solution yet",
    "'OK' solves",
    "flipMode()",
    "flipMode()",
    "",
    "left_right(1)",
    "getAltAz()",
    "getAltAz()",
]

sol = [
    "RADec",
    "No solution yet",
    "'OK' solves",
    "flipMode()",
    "flipMode()",
    "check_ss()",
    "left_right(1)",
    "getRaDec()",
    "getRaDec()",
]
polar = [
    "'OK' Bright Star",
    "Current value",
    dxStr + ',' + dyStr,
    "",
    "",
    "left_right(-1)",
    "left_right(1)",
    "measure_offset()",
    "measure_offset()",
]
focus = [
    "Solve Assist",
    "Utility",
    "'OK' to image",
    "adjExp(1)",
    "adjExp(-1)",
    "left_right(-1)",
    "left_right(1)",
    "getFS()",
    "getFS()",
]
bright = [
    "Display",
    "Bright Adj ",
    str(param["Brightness"]),
    "AdjBright(1)",
    "AdjBright(-1)",
    "left_right(-1)",
    "left_right(1)",
    "",
    "",
]
dateSet = [
    "Set Date",
    "",
    "",
    "adjDate(1)",
    "adjDate(-1)",
    "left_right(-1)",
    "",
    "",
    "",
]

arr = np.array([altaz, sol, polar, focus, bright, dateSet])
arr[5][0] = param["year"] + "/" + param["month"]
destPath = "/var/tmp/solve/"

up = Button(5, bounce_time=0.1)
down = Button(6, bounce_time=0.1)
left = Button(13, bounce_time=0.1)
right = Button(19, bounce_time=0.1)
ok = Button(20, bounce_time=0.1)
left.when_pressed = doButton
right.when_pressed = doButton
up.when_pressed = doButton
down.when_pressed = doButton
ok.when_pressed = doButton

path = Path("/dev/ttyACM0")
if path.exists() == False:
    print ('Plug in eFinder')
    handpad.display('Plug in eFinder','','')

    while True:
        try:
            ser = serial.Serial('/dev/ttyACM0',baudrate=115200)
            break
        except:
            time.sleep(1)

    print ('USB port open, waiting for eFinder to initialise')
    handpad.display('USB port open','Nexus eFinder','is starting')
    while True:
        try:
            if ser.in_waiting > 0:
                time.sleep(0.1) # make sure whole packet is got
                reply = ser.read(ser.in_waiting)
                msg = reply.decode("CP1253")
                print ('received',msg)
                ser.write(b':GV#')
                time.sleep(0.1)
                msg = ser.read_until(expected='#'.encode("ascii")).decode("CP1253")
                print (msg)
                break
        except:
            pass
        time.sleep(0.01)
else:
    ser = serial.Serial('/dev/ttyACM0',baudrate=115200)
reply = eFinderCmd('TSN') # just while we debug
print ('eFinder ready')
reply = eFinderCmd('GO')
dxStr,dyStr = reply.split(',')
dxStr = dxStr[3:]
dyStr =dyStr.strip('#') 
arr[2][2] = dxStr + ',' + dyStr
reply = eFinderCmd('SE+0')
exp = reply.strip('#')[3:]
handpad.display(arr[x][0], arr[x][1], arr[x][2])

wifiloop = Thread(target=serveWifi)
wifiloop.start()
time.sleep(0.5)

while True:

    if mode == "Auto":
        if x == 1:
            getRaDec()
        else:
            getAltAz()
    else:
        time.sleep(0.1)
    if x == 5:
        now = datetime.now(timezone.utc)
        arr[5][2] = 'UTC: ' + now.strftime("%H:%M:%S")
        handpad.display(arr[x][0], arr[x][1], arr[x][2])



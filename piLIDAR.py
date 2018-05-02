#!/usr/bin/python

import math
import sys
import signal
#import spidev
import time
import RPi.GPIO as GPIO
import subprocess
import pygame
import numpy as np

#########################################################################################
# Adapted from Bitbang'd SPI interface with an MCP3008 ADC device                       #
# https://github.com/raspberrypi-aa/raspberrypi-aa/blob/master/spi_bitbang_test.py      #
# Using MCP3002, a 2-channel 10-bit analog to digital converter                         #
#  Connections are:                                                                     #
#     CLK => 11  
#     DOUT => 9 (chip's data out, RPi's MISO)
#     DIN => 10  (chip's data in, RPi's MOSI)
#     CS => 8
#########################################################################################
CLK = 11
MISO = 9
MOSI = 10
CS = 8

def setupSpiPins(clkPin, misoPin, mosiPin, csPin):
    ''' Set all pins as an output except MISO (Master Input, Slave Output)'''
    GPIO.setup(clkPin, GPIO.OUT)
    GPIO.setup(misoPin, GPIO.IN)
    GPIO.setup(mosiPin, GPIO.OUT)
    GPIO.setup(csPin, GPIO.OUT)

def readAdc(clkPin, misoPin, mosiPin, csPin):
    # Datasheet says chip select must be pulled high between conversions
    GPIO.output(csPin, GPIO.HIGH)
    
    # Start the read with both clock and chip select low
    GPIO.output(csPin, GPIO.LOW)
    GPIO.output(clkPin, GPIO.HIGH)
    
    # read command is:
    # start bit = 1
    # single-ended comparison = 1 (vs. pseudo-differential)
    # ODD/SIGN = 0
    # MSBF = 1
    read_command = 0xD
    
    sendBits(read_command, 4, clkPin, mosiPin)
    
    adcValue = recvBits(11, clkPin, misoPin)
    
    # Set chip select high to end the read
    GPIO.output(csPin, GPIO.HIGH)
  
    return adcValue
    
def sendBits(data, numBits, clkPin, mosiPin):
    ''' Sends 1 Byte or less of data'''
    
    data <<= (8 - numBits)
    
    for bit in range(numBits):
        # Set RPi's output bit high or low depending on highest bit of data field
        if data & 0x80:
            GPIO.output(mosiPin, GPIO.HIGH)
        else:
            GPIO.output(mosiPin, GPIO.LOW)
        
        # Advance data to the next bit
        data <<= 1
        
        # Pulse the clock pin HIGH then immediately low
        GPIO.output(clkPin, GPIO.HIGH)
        GPIO.output(clkPin, GPIO.LOW)

def recvBits(numBits, clkPin, misoPin):
    '''Receives arbitrary number of bits'''
    retVal = 0
    
    for bit in range(numBits):
        # Pulse clock pin 
        GPIO.output(clkPin, GPIO.HIGH)
        GPIO.output(clkPin, GPIO.LOW)
        
        # Read 1 data bit in
        if GPIO.input(misoPin):
            retVal |= 0x1
        
        # Advance input to next bit
        retVal <<= 1
    
    # Divide by two to drop the NULL bit
    return (retVal/2)

######
# Adapted from http://arkouji.cocolog-nifty.com/blog/2016/02/raspberry-pi360.html
######
    
pygame.init()
sx = 600
sy = 600
pygame.display.set_mode((sx, sy), 0, 32)
screen = pygame.display.get_surface()

# open SPI device 0.0
#spi = spidev.SpiDev()
GPIO.setmode(GPIO.BCM) # use GPIO Number
#spi.open(0, 0)
setupSpiPins(CLK, MISO, MOSI, CS)

StepPins = [17,22,23,24]
# Set all pins as output
for pin in StepPins:
  print "Setup pins"
  GPIO.setup(pin,GPIO.OUT)
  GPIO.output(pin, False)
# Define advanced sequence
# as shown in manufacturers datasheet
Seq = [[1,0,0,1],
       [1,0,0,0],
       [1,1,0,0],
       [0,1,0,0],
       [0,1,1,0],
       [0,0,1,0],
       [0,0,1,1],
       [0,0,0,1]]

StepCount = len(Seq)
StepDir = 1 # Set to 1 or 2 for clockwise
            # Set to -1 or -2 for anti-clockwise

# Initialise variables
StepCounter = 0
Rrx = [0] *512
Rry = [0] *512

def lidar(CLK, MISO, MOSI, CS):
    while (True):

      angle = 0

      for i in range(4096):
    # motor angle
        angle = i * 5.625/64

        for pin in range(0, 4):
              xpin = StepPins[pin]
              if Seq[StepCounter][pin]!=0:
                  GPIO.output(xpin, True)
              else:
                  GPIO.output(xpin, False)

        StepCounter += StepDir

        if (StepCounter>=StepCount):
                StepCounter = 0
        if (StepCounter<0):
                StepCounter = StepCount+StepDir

        if i%8==0:
           pygame.draw.circle(screen, (0, 200, 0), (sx/2, sy/2), sx/2, 1)
           pygame.draw.circle(screen, (0, 200, 0), (sx/2, sy/2), sx/2/6*1, 1)
           pygame.draw.circle(screen, (0, 200, 0), (sx/2, sy/2), sx/2/6*2, 1)
           pygame.draw.circle(screen, (0, 200, 0), (sx/2, sy/2), sx/2/6*3, 1)
           pygame.draw.circle(screen, (0, 200, 0), (sx/2, sy/2), sx/2/6*4, 1)
           pygame.draw.circle(screen, (0, 200, 0), (sx/2, sy/2), sx/2/6*5, 1)
           pygame.draw.line(screen, (0, 200, 0), (0, sy/2), (sx, sy/2))
           pygame.draw.line(screen, (0, 200, 0), (sx/2, 0), (sx/2, sy))

    # Radar Point
           for j in range(512):
    #           col = 255
               deg = j * 5.625 / 8
               radar_deg = deg - angle
               if radar_deg <=0 :
                  col = int(255*((360+radar_deg)/360)**1.3)
                  pygame.draw.circle(screen, (0,col,0),(Rrx[j-1],Rry[j-1]),5)
               else:
                  col = int(255*(radar_deg/360)**1.3)
                  pygame.draw.circle(screen, (0,col,0),(Rrx[j-1],Rry[j-1]),5)

    # IR_sensor value to distance (m)
           val = readAdc(CLK, MISO, MOSI, CS)
           distance = 11.54/(0.00322*value+1.12)
           if distance < 0:
               distance = math.fabs(distance)

           dx = sx/2 + sx/2 * math.cos(math.radians(angle))
           dy = sy/2 + sx/2 * math.sin(math.radians(angle))
           pygame.draw.aaline(screen, (0, 200, 0), (sx/2, sy/2), (dx, dy),5)

           rx = int(sx/2 + 50 * distance * math.cos(math.radians(angle)))
           ry = int(sy/2 + 50 * distance * math.sin(math.radians(angle)))

           Rrx[i/8] = rx
           Rry[i/8] = ry

           pygame.display.update()
           pygame.time.wait(30)
           screen.fill((0, 20, 0, 0))
        else:
           time.sleep(0.001)

if __name__ == '__main__':
    try:
        while True:
            lidar(CLK, MISO, MOSI, CS)
    except KeyboardInterrupt:
        GPIO.cleanup()
        sys.exit(0)

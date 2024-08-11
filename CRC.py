#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 17 16:31:21 2023

@author: abc
"""

class CRC:
    POLYNOMIAL = 213
    CRC8 = 0
    
    def __init__(self):
        self.CRC8 = 0
    
    def calculateCRC8(self, input):
        self.CRC8 = 0
        for byte in input:
            self.updateByte(byte)
        return self.CRC8
    
    def updateByte(self, byt):
        self.CRC8 ^= byt
        for i in range(8):
            if ((self.CRC8 & 0x80) != 0x0):
                self.CRC8 = (self.CRC8 << 1 ^ 0xD5)
            else:
                self.CRC8 <<= 1
        self.CRC8 &= 0xFF
    
    def calculateCRC16(self, input):
        crc16 = 0
        polynomial = 40961
        for byte in input:
            temp = (crc16 ^ byte) & 0xFF
            for i in range(8):
                if ((temp & 0x1) == 0x1):
                    temp = (temp >> 1 ^ polynomial)
                else:
                    temp >>= 1
            crc16 = (crc16 >> 8 ^ temp)
        return crc16
    
    def calculateCRC32(self, input):
        crc32 = -1
        polynomial = -306674912
        for byte in input:
            temp = (crc32 ^ byte) & 0xFF
            for i in range(8):
                if ((temp & 0x1) == 0x1):
                    temp = (temp >> 1 ^ polynomial)
                else:
                    temp >>= 1
            crc32 = (crc32 >> 8 ^ temp)
        return ~crc32
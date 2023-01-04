import pygame
import time
import sys
import random
import os
import struct


# 16个8bit寄存器  1个16bit寄存器
# 16个寄存器命名为V0~VF VF通常被当作状态标志寄存器，用于表示是否有进位或用于碰撞检测
# 地址寄存器通常被用于指向某个图像的位置
# 当寄存器存储的数字大于它的存储空间时会舍弃掉高位
class Register:
    def __init__(self, bits):
        self.value = 0
        self.bits = bits

    def checkCarry(self):
        """检查是否有进位"""
        hexValue = hex(self.value)[2:]
        if len(hexValue) > self.bits / 4:
            self.value = int(hexValue[-int(self.bits / 4):], 16)
            return 1
        return 0

    def checkBorrow(self):
        """检查是否小于0"""
        if self.value < 0:
            self.value = abs(self.value)
            return 0
        return 1

    def readValue(self):
        return self.value

    def setValue(self, v):
        self.value = v

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value
        else:
            return self.value == other


class DelayTimer:
    """延时计时器 游戏中计时"""

    def __init__(self):
        self.timer = 0

    def countDown(self):
        if self.timer > 0:
            self.timer -= 1

    def setTimer(self, value):
        self.timer = value

    def readTimer(self):
        return self.timer


class SoundTimer(DelayTimer):
    """声音计时器 游戏音效, 当计数器数值大于0时播放蜂鸣声 (继承自延时计时器)"""

    def __init__(self):
        DelayTimer.__init__(self)

    def beep(self):
        if self.timer > 0:
            print("Beep --------------------------")
            self.timer = 0


class Stack:
    """栈是用于存储函数的返回地址"""

    def __init__(self):
        self.stack = []

    def push(self, value):
        self.stack.append(value)

    def pop(self):
        return self.stack.pop()


class Emulator:
    def __init__(self):
        pygame.init()

        # 内存4096个字节
        self.Memory = []
        for i in range(4096):
            self.Memory.append(0x0)

        fonts = [
            0xF0, 0x90, 0x90, 0x90, 0xF0,
            # 0
            # 11110000
            # 10010000
            # 10010000
            # 10010000
            # 11110000
            0x20, 0x60, 0x20, 0x20, 0x70,
            # 1
            # 00100000
            # 01100000
            # 00100000
            # 00100000
            # 01110000
            0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
            0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
            0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
            0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
            0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
            0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
            0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
            0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
            0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
            0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
            0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
            0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
            0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
            0xF0, 0x80, 0xF0, 0x80, 0x80  # F
        ]
        for i in range(len(fonts)):
            self.Memory[i] = fonts[i]

        # 创建寄存器实例 16个8位寄存器  一个16位地址寄存器
        self.Registers = []
        for i in range(16):
            self.Registers.append(Register(8))
        self.IRegister = Register(16)

        # 程序计数器pc
        self.ProgramCounter = 0x200

        # 创建栈实例
        self.stack = Stack()

        # 计时器实例 使用pygame里的计数器来给delayTimer计时
        self.delayTimer = DelayTimer()
        self.soundTimer = SoundTimer()
        pygame.time.set_timer(pygame.USEREVENT + 1, int(1000 / 60))

        self.keys = []
        for i in range(0, 16):
            self.keys.append(False)
        '''
                   Chip8       My Keys
                   ---------   ---------
                   1 2 3 C     1 2 3 4
                   4 5 6 D     q w e r
                   7 8 9 E     a s d f
                   A 0 B F     z x c v
        '''
        self.keyDict = {
            49: 1,
            50: 2,
            51: 3,
            52: 0xC,
            113: 4,
            119: 5,
            101: 6,
            114: 0xD,
            97: 7,
            115: 8,
            100: 9,
            102: 0xE,
            122: 0xA,
            120: 0,
            99: 0xB,
            118: 0xF,
        }

        # 图像 64 * 32 像素屏幕
        self.grid = []
        for i in range(32):
            line = []
            for j in range(64):
                line.append(0)
            self.emptyGrid = self.grid[:]
            self.zeroColor = [0, 0, 50]
            self.oneColor = [255, 255, 255]
        self.size = 10
        width = 64
        height = 32
        self.screen = pygame.display.set_mode([width * self.size, height * self.size])
        self.screen.fill(self.oneColor)
        pygame.display.flip()

    def readProg(self, game_file_name):
        rom = self.convertProg(game_file_name)
        offset = int("0x200", 16)
        for i in rom:
            self.Memory[offset] = i
            offset += 1

    @staticmethod
    def convertProg(game_file_name):
        rom = []
        output = open("output", "wb")
        with open(game_file_name, "rb") as f:
            wholeProgram = f.read()
            for i in wholeProgram:
                opcode = i
                b = struct.pack('B', opcode)
                output.write(b)
                rom.append(opcode)
            output.close()
        return rom

    def mainLoop(self):
        clock = pygame.time.Clock()
        while True:
            clock.tick(300)
            self.keyHandler()
            self.soundTimer.beep()
            self.execution()
            self.display()

    def keyHandler(self):
        pass

    def execution(self):
        index = self.ProgramCounter
        high = self.hexHandler(self.Memory[index])
        low = self.hexHandler(self.Memory[index])
        opcode = high + low
        self.execOpcode(opcode)

    def display(self):
        for i in range(0, len(self.grid)):
            for j in range(0, len(self.grid[0])):
                cellColor = self.zeroColor
                if self.grid[i][j] == 1:
                    cellColor = self.oneColor
                pygame.draw.rect(self.screen, cellColor, [j * self.size, i * self.size, self.size, self.size], 0)
        pygame.display.flip()
        pass

    @staticmethod
    def hexHandler(Num):
        newHex = hex(Num)[2:]
        if len(newHex) == 1:
            newHex = "0" + newHex
        return newHex

    def clear(self):
        for i in range(len(self.grid)):
            for j in range(len(self.grid[0])):
                self.grid[i][j] = 0

    def execOpcode(self, opcode):
        """
        CHIP-8 操作码表
            NNN: 地址
            NN: 8-bit 常数
            N: 4-bit 常数
            X and Y: 4-bit 寄存器下标
            PC: 程序指针
            I: 地址寄存器
            VN: 16个寄存器中的一个
        :param opcode: 操作码
        """
        print("单条指令的指：", opcode)
        if opcode[0] == "0":
            if opcode[1] != "0":
                # 0NNN 调用在NNN地址上的RCA 1802程序, 大多数ROM都不会用到这个操作码
                pass
            elif opcode[-1] == 0:
                if opcode == "00e0":
                    # 00E0 清屏
                    self.clear()
            else:
                if opcode == "00ee":
                    # 00EE 从一个函数中返回
                    self.ProgramCounter = self.stack.pop()
        elif opcode[0] == "1":
            # 1NNN 跳转到地址NNN
            self.ProgramCounter = int(opcode[1:], 16) - 2
        elif opcode[0] == "2":
            # 2NNN 调用NNN地址上的函数
            self.stack.push(self.ProgramCounter)
            self.ProgramCounter = int(opcode[1:], 16) - 2
        elif opcode[0] == "3":
            # 3XNN 如果Vx==NN, 就跳过下一个操作码
            vIndex = int(opcode[1], 16)
            if self.Registers[vIndex] == int(opcode[2:], 16):
                self.ProgramCounter += 2
        elif opcode[0] == "4":
            # 4XNN 如果Vx!=NN, 跳过下一个操作码
            vIndex = int(opcode[1], 16)
            if self.Registers[vIndex] != int(opcode[2:], 16):
                self.ProgramCounter += 2
        elif opcode[0] == "5":
            # 5XY0 如果Vx==Vy, 跳过下一个操作码
            if opcode[-1] == "0":
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                if self.Registers[v1Index] == self.Registers[v2Index]:
                    self.ProgramCounter += 2
        elif opcode[0] == "6":
            # 6XNN  将NN这个值存在Vx上
            targetNum = int(opcode[2:], 16)
            vIndex = int(opcode[1], 16)
            self.Registers[vIndex].value = targetNum
        elif opcode[0] == "7":
            # 7XNN  Vx和NN相加, 结果存于Vx上, 不改变VF的值
            vIndex = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)
            self.Registers[vIndex].value += targetNum
            self.Registers[vIndex].checkCarry()
        elif opcode[0] == "8":
            if opcode[-1] == "0":
                # 8XY0  将Vx的值设为Vy的值
                pass
            if opcode[-1] == "1":
                # 8XY1  Vx与Vy进行或运算, 结果存储于Vx中
                pass
            if opcode[-1] == "2":
                # 8XY2  Vx与Vy进行与运算, 结果存储于Vx中
                pass
            if opcode[-1] == "3":
                # 8XY3  Vx与Vy进行异或运算, 结果存储于Vx中
                pass
            if opcode[-1] == "4":
                # 8XY4  Vx与Vy相加, 结果存储于Vx中, 进位的话VF=1, 反之VF=0
                pass
            if opcode[-1] == "5":
                # 8XY5  Vx与Vy相减, 结果存储于Vx中, 小于0的话VF=0, 反之VF=1
                pass
            if opcode[-1] == "6":
                # 8XY6  将Vx的最低位存储于VF中, 然后Vx右移1位
                pass
            if opcode[-1] == "7":
                # 8XY7  Vy - Vx, 结果存于Vx中, 小于0的话VF=0, 反之VF=1
                pass
            if opcode[-1] == "e":
                # 8XYE  将Vx的最高位存储于VF中, 然后Vx左移1位
                pass
        elif opcode[0] == "9":
            pass
        elif opcode[0] == "a":
            pass
        elif opcode[0] == "b":
            pass
        elif opcode[0] == "c":
            pass
        elif opcode[0] == "d":
            pass
        elif opcode[0] == "e":
            pass
        elif opcode[0] == "f":
            pass

        self.ProgramCounter += 2


if __name__ == '__main__':
    chip8 = Emulator()
    # chip8.readProg(sys.argv[1])
    chip8.readProg("./games/Pong.ch8")
    chip8.mainLoop()

import pygame
import time
import sys
import random
import os


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
        return hex(self.value)

    def setValue(self, v):
        self.value = v


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
        if self.timer > 1:
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
        # 内存4096个字节
        self.Memory = []
        for i in range(0, 4096):
            self.Memory.append(0x0)
        fonts = [
            0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
            0x20, 0x60, 0x20, 0x20, 0x70,  # 1
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
            0xF0, 0x80, 0xF0, 0x80, 0x80   # F
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
        pygame.init()
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
            52: 0xc,
            113: 4,
            119: 5,
            101: 6,
            114: 0xd,
            97: 7,
            115: 8,
            100: 9,
            102: 0xe,
            122: 0xa,
            120: 0,
            99: 0xb,
            118: 0xf,
        }

        # 图像 64 * 32 像素屏幕
        self.grid = []
        for i in range(32):
            line = []
            for j in range(64):
                line.append(0)
            self.grid.append(line)
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

    def convertProg(self, game_file_name):
        rom = []
        with open(game_file_name, "rb") as f:
            wholeProgram = f.read()
            for i in wholeProgram:
                opcode = i
                rom.append(opcode)
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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.USEREVENT + 1:
                self.delayTimer.countDown()
            elif event.type == pygame.KEYDOWN:
                try:
                    targetKey = self.keyDict[event.key]
                    self.keys[targetKey] = True
                except:
                    print("Error 未知异常 keyHandler 1")
                    pass
            elif event.type == pygame.KEYUP:
                try:
                    targetKey = self.keyDict[event.key]
                    self.keys[targetKey] = False
                except:
                    print("Error 未知异常 keyHandler 2")
                    pass


    def execution(self):
        index = self.ProgramCounter
        high = self.hexHandler(self.Memory[index])
        low = self.hexHandler(self.Memory[index + 1])
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

    def hexHandler(self, Num):
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
        if opcode[0] == "0":
            if opcode[1] != "0":
                print("error")
            # 0NNN 调用在NNN地址上的RCA 1802程序, 大多数ROM都不会用到这个操作码
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
            vNum = int(opcode[1], 16)
            if self.Registers[vNum].value == int(opcode[2:], 16):
                self.ProgramCounter += 2
        elif opcode[0] == "4":
            # 4XNN 如果Vx!=NN, 跳过下一个操作码
            vNum = int(opcode[1], 16)
            if self.Registers[vNum].value != int(opcode[2:], 16):
                self.ProgramCounter += 2
        elif opcode[0] == "5":
            # 5XY0 如果Vx==Vy, 跳过下一个操作码
            if opcode[-1] == "0":
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                if self.Registers[v1Index].value == self.Registers[v2Index].value:
                    self.ProgramCounter += 2
        elif opcode[0] == "6":
            # 6XNN  将NN这个值存在Vx上
            vNum = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)
            self.Registers[vNum].value = targetNum
        elif opcode[0] == "7":
            # 7XNN  Vx和NN相加, 结果存于Vx上, 不改变VF的值
            vNum = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)
            self.Registers[vNum].value += targetNum
            self.Registers[vNum].checkCarry()
        elif opcode[0] == "8":
            if opcode[-1] == "0":
                # 8XY0  将Vx的值设为Vy的值
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                self.Registers[v1Index].value = self.Registers[v2Index].value
            if opcode[-1] == "1":
                # 8XY1  Vx与Vy进行或运算, 结果存储于Vx中
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                self.Registers[v1Index].value = self.Registers[v1Index].value | self.Registers[v2Index].value
            if opcode[-1] == "2":
                # 8XY2  Vx与Vy进行与运算, 结果存储于Vx中
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                self.Registers[v1Index].value = self.Registers[v1Index].value & self.Registers[v2Index].value
            if opcode[-1] == "3":
                # 8XY3  Vx与Vy进行异或运算, 结果存储于Vx中
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                self.Registers[v1Index].value = self.Registers[v1Index].value ^ self.Registers[v2Index].value
            if opcode[-1] == "4":
                # 8XY4  Vx与Vy相加, 结果存储于Vx中, 进位的话VF=1, 反之VF=0
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                self.Registers[v1Index].value = self.Registers[v1Index].value + self.Registers[v2Index].value
                self.Registers[0xf].value = self.Registers[v1Index].checkCarry()
            if opcode[-1] == "5":
                # 8XY5  Vx与Vy相减, 结果存储于Vx中, 小于0的话VF=0, 反之VF=1
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                self.Registers[v1Index].value = self.Registers[v1Index].value - self.Registers[v2Index].value
                self.Registers[0xf].value = self.Registers[v1Index].checkCarry()
            if opcode[-1] == "6":
                # 8XY6  将Vx的最低位存储于VF中, 然后Vx右移1位
                v1Index = int(opcode[1], 16)
                leastBit = int(bin(self.Registers[v1Index].value)[-1])
                self.Registers[v1Index].value = self.Registers[v1Index].value >> 1
                self.Registers[0xf].value = leastBit
            if opcode[-1] == "7":
                # 8XY7  Vy - Vx, 结果存于Vx中, 小于0的话VF=0, 反之VF=1
                v1Index = int(opcode[1], 16)
                v2Index = int(opcode[2], 16)
                self.Registers[v1Index].value = self.Registers[v2Index].value - self.Registers[v1Index].value
                self.Registers[0xf].value = self.Registers[v1Index].checkBorrow()
            if opcode[-1] == "e":
                # 8XYE  将Vx的最高位存储于VF中, 然后Vx左移1位
                v1Index = int(opcode[1], 16)
                # 这里的转换结果是0b开头 所以从2开始取
                highBit = int(bin(self.Registers[v1Index].value)[2])
                self.Registers[v1Index].value = self.Registers[v1Index].value << 1
                self.Registers[0xf].value = highBit
        elif opcode[0] == "9":
            # 9XY0  如果Vx不等于Vy, 跳过下一条操作码
            v1Index = int(opcode[1], 16)
            v2Index = int(opcode[2], 16)
            if self.Registers[v1Index].value != self.Registers[v2Index].value:
                self.ProgramCounter += 2
        elif opcode[0] == "a":
            # ANNN  地址寄存器的值设为NNN
            addr = int(opcode[1:], 16)
            self.IRegister.value = addr
        elif opcode[0] == "b":
            # BNNN  跳转到V0+NNN这个地址上
            addr = int(opcode[1:], 16)
            self.ProgramCounter = self.Registers[0].value + addr - 2
        elif opcode[0] == "c":
            # CXNN 将一个0~255区间上的随机数与NN进行与运算, 结果存储于Vx中
            vNum = int(opcode[1], 16)
            targetNum = int(opcode[2:], 16)
            rand = random.randint(0, 255)
            self.Registers[vNum].value = targetNum & rand
        elif opcode[0] == "d":
            # DXYN  将一个宽8像素, 长N像素的位图绘制于(Vx, Vy)这个位置上
            v1Index = int(opcode[1], 16)
            v2Index = int(opcode[2], 16)
            height = int(opcode[3], 16)
            addr = self.IRegister.value
            sprite = self.Memory[addr:addr + height]
            for i in range(len(sprite)):
                if type(sprite[i]) == str:
                    sprite[i] = int(sprite[i], 16)
            if self.draw(self.Registers[v1Index].value, self.Registers[v2Index].value, sprite):
                self.Registers[0xf].value = 1
            else:
                self.Registers[0xf].value = 0
        elif opcode[0] == "e":
            vXIndex = int(opcode[1], 16)
            # EX9E  如果存储于Vx上的这个按键被按下了, 就跳过下一条指令
            if opcode[2:] == "9e":
                key = self.Registers[vXIndex].value
                if self.keys[key]:
                    self.ProgramCounter += 2
            # EXA1  如果存储于Vx上的这个按键没被按下了, 就跳过下一条指令
            elif opcode[2:] == "a1":
                key = self.Registers[vXIndex].value
                if not self.keys[key]:
                    self.ProgramCounter += 2
        elif opcode[0] == "f":
            vXIndex = int(opcode[1], 16)
            # FX07  读取延迟计数器的值并存储于Vx上
            if opcode[2:] == "07":
                self.Registers[vXIndex].value = self.delayTimer.readTimer()
            # FX0A  暂停整个程序等待某个按键被按下, 并把这个按键存储于Vx上
            elif opcode[2:] == "0a":
                key = None
                while True:
                    self.keyHandler()
                    isKeyDown = False
                    for i in range(len(self.keys)):
                        if self.keys[i]:
                            key = i
                            isKeyDown = True
                    if isKeyDown:
                        break
                self.Registers[vXIndex].value = key
            # FX15  将延迟计数器的值设为Vx
            elif opcode[2:] == "15":
                self.delayTimer.setTimer(self.Registers[vXIndex].value)
            # FX18  将声音计数器的值设为Vx
            elif opcode[2:] == "18":
                self.soundTimer.setTimer(self.Registers[vXIndex].value)
            # FX1E  将Vx加到地址寄存器上
            elif opcode[2:] == "1e":
                self.IRegister.value += self.Registers[vXIndex].value
            # FX29  将存储于Vx上的字符(0-F)所对应的字体的位置存在地址寄存器上
            elif opcode[2:] == "29":
                value = self.Registers[vXIndex].value
                self.IRegister.value = value * 5
            # set_BCD(Vx);
            # *(I + 0) = BCD(3);
            # *(I + 1) = BCD(2);
            # *(I + 2) = BCD(1);
            # FX33  把Vx存储的数字用十进制表达, 百位存于I + 0的位置, 十位存于I + 1的位置, 个位存于I+ 2的位置
            elif opcode[2:] == "33":
                value = str(self.Registers[vXIndex].value)
                fillNum = 3 - len(value)
                value = '0' * fillNum + value
                for i in range(len(value)):
                    self.Memory[self.IRegister.value + i] = int(value[i])
            # FX55  把V0~Vx的数值一次存在I0~I+x上
            elif opcode[2:] == "55":
                for i in range(0, vXIndex + 1):
                    self.Memory[self.IRegister.value + i] = self.Registers[i].value
            # FX65  把I~I+x上的数值存在V0~Vx上
            elif opcode[2:] == "65":
                for i in range(0, vXIndex + 1):
                    self.Registers[i].value = self.Memory[self.IRegister.value + i]
        self.ProgramCounter += 2

    def draw(self, Vx, Vy, sprite):
        collision = False
        spriteBit = []
        for i in sprite:
            binary = bin(i)
            line = list(binary[2:])
            fillNum = 8 - len(line)
            line = ["0"] * fillNum + line
            spriteBit.append(line)
        for i in range(len(spriteBit)):
            for j in range(8):
                try:
                    if self.grid[Vy + i][Vx + j] == 1 and int(spriteBit[i][j]) == 1:
                        collision = True
                    self.grid[Vy + i][Vx + j] = self.grid[Vy + i][Vx + j] ^ int(spriteBit[i][j])
                except:
                    continue
        return collision


if __name__ == '__main__':
    chip8 = Emulator()
    # chip8.readProg(sys.argv[1])
    chip8.readProg("./games/Pong.ch8")
    chip8.mainLoop()



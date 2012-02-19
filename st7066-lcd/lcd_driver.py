#!/usr/bin/env python

GPIO_0 = 0
GPIO_1 = GPIO_0 + 32
GPIO_2 = GPIO_1 + 32
GPIO_3 = GPIO_2 + 32

class Signals(object):
    RS  = 1
    RW  = 2
    E   = 3
    DB0 = 4
    DB1 = 5
    DB2 = 6
    DB3 = 7
    DB4 = 8
    DB5 = 9
    DB6 = 10
    DB7 = 11

SIGNAL_WIRE_MAP={
    Signals.RS  : 'gpmc_wait0',  # P9_11
    Signals.RW  : 'gpmc_be1n',  
    Signals.E   : 'gpmc_wpn',
    Signals.DB0 : 'gpmc_a2',
    Signals.DB1 : 'gpmc_a0',
    Signals.DB2 : 'gpmc_a3',
    Signals.DB3 : 'spi0_cs0',
    Signals.DB4 : 'spi0_d1',
    Signals.DB5 : 'uart1_rtsn',
    Signals.DB6 : 'uart1_ctsn',
    Signals.DB7 : 'spi0_d0',     # P9_21
}

PIN_NAME_TO_GPIO_NUM={
    'gpmc_wait0' : GPIO_0 + 30,
    'gpmc_be1n'  : GPIO_1 + 28,
    'gpmc_wpn'   : GPIO_0 + 31,
    'gpmc_a2'    : GPIO_1 + 18,
    'gpmc_a0'    : GPIO_1 + 16,
    'gpmc_a3'    : GPIO_1 + 19,
    'spi0_cs0'   : GPIO_0 + 5,
    'spi0_d1'    : GPIO_0 + 4,
    'uart1_rtsn' : GPIO_0 + 13,
    'uart1_ctsn' : GPIO_0 + 12,
    'spi0_d0'    : GPIO_0 + 3,
}

def bits(n):
    for i in xrange(0,8):
        yield (n >> i) & 1


class ST7066_Driver(object):
    
    def clear_display(self):
        self.send(RS=0, RW=0, data=[0, 0, 0, 0, 0, 0, 0, 1])
    
    def return_home(self):
        self.send(RS=0, RW=0, data=[0,0,0,0,0,0,1,0]) # the last '0' doesn't mean anything
    
    def set_entry_mode(self, move, shift=False):
        """
        move: either 'left' or 'right'
        shift: boolean True or False. If True, results in shifting
            the whole display. Otherwise, just moves the cursor
        """
        if move == 'left':
            inc_dec_val = 0 # low -- move left
        elif move == 'right':
            inc_dec_val = 1 # high -- move right
        else:
            raise 'Invalid Argument: %s' % move
        
        shift_val = 1 if shift else 0
        
        self.send(RS=0, RW=0, data=[0,0,0,0,0, 1,inc_dec_val, shift_val])
    
    def set_display(self, display, cursor_visible, cursor_blink=True):
        """
        display: 'on' or 'off'
        cursor_visible: True or False
        cursor_blink: True or False (default: True)
        """
        display_val = 0 if display == 'off' else 1
        cursor_val = 0 if not cursor_visible else 1
        cursor_blink_val = 0 if not cursor_blink else 1
        
        self.send(RS=0, RW=0, data=[0,0,0,0,1,display_val,cursor_val,cursor_blink_val])
    
    def function_set(self, dl_bits, num_lines, resolution):
        """
        dl_bits: 4 or 8 (default 8)
        num_lines: 1 or 2 (default 2)
        resolution: high or low (default high)
        """
        dl_val = 0 if dl_bits == 4 else 1 # 8 bits
        lines_val = 1 if num_lines == 2 else 0 # 1 line default
        res_val = 0 if resolution == 'low' else 1 # high
        self.send(RS=0,RW=0,data=[0,0,1,dl_val,lines_val,res_val])
    
    def set_ddram_addr(self, addr=0):
        bits = reversed(list(b for b in bits(addr)))[1::]
        bits[0] = 1 # high bit is always 1 (there's only 7 bits of data to write)
        self.send(RS=0, RW=0, data=bits)
        
    def write_data_to_ram(self, data_in):
        bits = reversed(list(b for b in bits(data_in)))
        self.send(RS=1, RW=0, data=bits)
        
    def read_busy(self):
        gpio_ready_for_input(Signals.DB7)
        
        gpio_write(Signals.RS, 0)
        gpio_write(Signals.RW, 1)
        
        result = gpio_read(Signals.DB7)
        
        gpio_ready_for_output(Signals.DB7)
        
        return result
        
    
    def send(self, RS, RW, data):
        import time
        self.__send(RS=RS, RW=RW, data=data)
        # time.sleep(0.1) # 1/10 of a second
        # self.__send(RS=)
    
    def __send(self, RS, RW, data):
        """
        RS = register select bit
        RW = r/w select bit
        data = DB7-0 bits (in that order)
        """
        gpio_write(Signals.RS, RS)
        gpio_write(Signals.RW, RW)
        
        data_signals = [
            Signals.DB7, 
            Signals.DB6, 
            Signals.DB5, 
            Signals.DB4, 
            Signals.DB3, 
            Signals.DB2, 
            Signals.DB1, 
            Signals.DB0
        ]
        
        for idx in xrange(0,8):
            gpio_write(data_signals[i], data[i])




def gpio_write(signal, val):
    pin_name = SIGNAL_WIRE_MAP[signal]
    gpio_num = PIN_NAME_TO_GPIO_NUM[pin_name]
    with open('/sys/class/gpio/%d/value' % gpio_num, 'w') as f:
        f.write('%d' % val)
        
def gpio_read(signal):
    pin_name = SIGNAL_WIRE_MAP[signal]
    gpio_num = PIN_NAME_TO_GPIO_NUM[pin_name]
    with open('/sys/class/gpio/%d/value' % gpio_num, 'r') as f:
        f.read()

def gpio_set_mux_mode(signal, mux_mode):
    pin_name = SIGNAL_WIRE_MAP[signal]
    with open('/sys/kernel/debug/omap_mux/%s', 'wb') as f:
        f.write('%X' % mux_mode)

def gpio_ready_for_output(signal):
    pin_name = SIGNAL_WIRE_MAP[signal]
    gpio_num = PIN_NAME_TO_GPIO_NUM[pin_name]
    with open('/sys/class/gpio/%d/direction' % gpio_num, 'w') as f:
        f.write('out')

def gpio_ready_for_input(signal):
    pin_name = SIGNAL_WIRE_MAP[signal]
    gpio_num = PIN_NAME_TO_GPIO_NUM[pin_name]
    with open('/sys/class/gpio/%d/direction' % gpio_num, 'w') as f:
        f.write('in')

def gpio_export(signal):
    pin_name = SIGNAL_WIRE_MAP[signal]
    gpio_num = PIN_NAME_TO_GPIO_NUM[pin_name]
    try:
        open('/sys/class/gpio/%d/direction' % gpio_num).read()
    except:
        with open('/sys/class/gpio/export', 'w') as f:
            f.write('%d' % gpio_num)

def gpio_unexport(signal):
    pin_name = SIGNAL_WIRE_MAP[signal]
    gpio_num = PIN_NAME_TO_GPIO_NUM[pin_name]
    try:
        open('/sys/class/gpio/%d/direction' % gpio_num).read()
    except:
        with open('/sys/class/gpio/unexport', 'w') as f:
            f.write('%d' % gpio_num)

def startup():
    # first, set up all the pins
    for signal in SIGNAL_WIRE_MAP:
        gpio_set_mux_mode(signal, 7)
        gpio_export(signal)
        gpio_ready_for_output(signal) 
        
    
def shutdown():
    for signal in SIGNAL_WIRE_MAP:
        gpio_set_mux_mode(signal, 7)
        gpio_unexport(signal)
    

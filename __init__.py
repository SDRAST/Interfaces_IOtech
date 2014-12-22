"""
package FrontEnd

sub-package of Observatory implements control and monitoring of the
K-band front end.

IOtech signals
==============

Mapping::

  Port 1 Bit  1 Pin  1: out: high-low-high: move feed 1 load
       1      2      2: out: low: feed 1 amp on
       1      3      3: out: high-low-high: move feed 2 load
       1      4      4: out: low: feed 2 amp on
       1      5      5: out:
       1      6      6: out: low: phase-cal on
       1      7      7: out: low: 1 MHz rail, high: 4 MHz rail
       1      8      8: out:
       2      1      9: in:
       2      2     10: in:
       2      3     11: in: high: feed 2 in load
       2      4     12: in: high: feed 2 in sky
       2      5     13: in: high: feed 1 amp bias on
       2      6     14: in: high: feed 2 amp bias on
       2      7     15: in:
       2      8     16: in:
"""

from time import sleep
from gpib import *
from Gpib import Gpib
import Math

class IOtech(Gpib):
  """
  Implements an IOtech device instance

  @type ports_out : dictionary
  @cvar ports_out : I/O port direction assignment

  @type port_direction : dictionary
  @cvar port_direction : defines 'in' and 'out'

  @type data_format : dictionary
  @cvar data_format : I/O data format description

  @type polarity : dictionary
  @cvar polarity : controls sense of data and control bits

  @type SRQ_mask : dictionary
  @cvar SRQ_mask : defines when SRQ is asserted

  @type commands : dictionary
  @cvar commands : describes the IOtech commands
  """
  ports_out = {0: {1:False, 2:False, 3:False, 4:False, 5:False},
               1: {1:True , 2:False, 3:False, 4:False, 5:False},
               2: {1:True , 2:True , 3:False, 4:False, 5:False},
               3: {1:True , 2:True , 3:True , 4:False, 5:False},
               4: {1:True , 2:True , 3:True , 4:True , 5:False},
               5: {1:True , 2:True , 3:True , 4:True , 5:True }}

  port_direction = {0: "in", 1: "out"}

  data_format = {0: "ASCII hex",
                 1: "ASCII char",
                 2: "ASCII binary",
                 3: "ASCII decimal",
                 4: "binary",
                 5: "high speed binary"}

  polarity = {int('00000000',2): "control high, data high = True",
              int('00000001',2): "INHIBIT active low",
              int('00000010',2): "TRIGGER active low",
              int('00000100',2): "DATA STROBE active low",
              int('00001000',2): "CLEAR active low",
              int('00010000',2): "data low = True",
              int('00100000',2): "EDR in is falling-edge sensitive",
              int('01000000',2): "SERVICE in is falling-edge sensitive"}

  SRQ_mask = {int('00000',2): "SRQ disabled",
              int('00001',2): "SRQ on SERVICE",
              int('00010',2): "SRQ on EDR",
              int('00100',2): "SRQ on bus error",
              int('01000',2): "SRQ on self-test error",
              int('10000',2): "SRQ on READY"}

  error = {0: "no error",
           1: "unrecognized command",
           2: "illegal command",
           3: "I/O conflict",
           4: "ROM error",
           5: "RAM error"}

  commands = {"A": "set bit",
              "B": "clear bit",
              "C": "configure",     # see above
              "D": "data",          # port out ports
              "E": "error message", # see above
              "F": "format",        # see above
              "G": "input/output mode for talk",
              "H": "handshake",     # 0 pulse clear, 1 strobe, 2 trigger
              "I": "polarity",      # see above
              "K": "use EOI",       # 0 enabled, 1 disabled, default switch 1
              "M": "SRQ mask",      # see above
              "P": "port",          # select I/O port; 0 for all"
              "Q": "inhibit",       # 0 clear, 1 set
              "R": "latch data",    # 0 (default) not latched
              "T": "test",
              "U": "status",
              "X": "execute",       # execute last command
              "Y": "terminator"}    # 0=CR/LF, 1=LF/CR, 2=CR, 3=LF
  
  def __init__(self, device, configuration=1):
    """
    Create an instance of an IOtech device on GPIB

    @type device : str
    @param device : device name as defined in /etc/gpib.conf

    @type configuration : int
    @param configuration : port I/O directions as in 'ports_out'

    @return: None
    """
    Gpib.__init__(self,device)
    self.configure(configuration=configuration)
    self.write_port(1,int('1111',2))
    self.get_status()

  def Write(self, command_list):
    """
    Send commands to the IOtech

    The normal usage would be something like this::
      ['A3','U3','U5']
    but this is also acceptable::
      "A3 U3 U5"
    as well as a verbatim string::
      "A3XU3XU5X"
    The routine will parse and form the string (if necessary) append "\r".

    Note
    ====
    Case is important. 'write()' invokes the GPIO class method.
    
    @type command_list : list or str
    @param command_list : commands to be sent

    @return: True on success
    """
    command_string = ""
    if type(command_list) == str:
      # Could be a space separated string or a verbatim string
      try:
        command_list.index(' ')
      except ValueError:
        if command_list[-1] == "X" or command_list[-2] == "X\r":
          # Just pass on string as is ...
          command_string = command_list
          if command_string[-1] == '\r':
            # ... unless a redudant \r should be removed
            command_string = command_string[:-1]
        else:
          # there was no space but no ending X either
          # must be a single command string like "C0"
          command_string = command_list+"X"
      else:
        # A space separated string to turn into a list
        commands = [n for n in command_list.split()]
    if command_string == "":
      # we have a list to convert to a strinh
      for command in commands:
        if command != "":
          command_string += command+"X"
    try:
      self.write(command_string+'\r')
      return True
    except error, details:
      print "Sending",command_string,"failed"
      print details
      return False

  def Read(self):
    """
    Read the IOtech

    Normally this is preceded by some command which prepares and
    output but in that case Ask() is easier to use.  If the IOtech
    has not been so prepped, it response with the state of the
    bits on the port(s) defined by 'configure'

    Note
    ====
    Case is important. 'read()' invokes the GPIO class method.
    """
    try:
      response = self.read()
    except error, details:
      print "Reading IOtech failed"
      print details
      response = "Error: "+details
    return response

  def Ask(self,query):
    """
    A Write() followed by a Read().

    @type query : list or string
    @param query : see Write()

    @return: response (on success) or None (on failure)
    """
    if self.Write(query):
      response = self.Read()
      return response.strip()
    else:
      return None
    
  def configure(self,configuration=1):
    """
    Configure the port I/O direction

    The default is to have port 1 out and port 2 in.  The others are
    not used.

    @type configuration : int
    @param configuration : as defined in class variable 'ports_out'

    @return: True on success
    """
    command = "C"+str(configuration)
    if self.Write(command):
      return True
    else:
      return False
  
  def get_status(self):
    """
    Gets the status of the IOtech card

    This parses the status response.

    @return: dictionary
    """
    status = self.Ask('U0')
    version = status[:3]
    responses = {"Version": version}
    in_command = False
    # parse the response
    for char in status[3:]:
      if in_command == False and char.isalpha():
        command = char
        in_command = True
        value = ""
      if in_command:
        if char.isdigit() or char == ".":
          value += char
        elif char != '\r':
          responses[command] = value
          command = char
          value = ""
    # convert values to int
    result = {}
    for key in responses.keys():
      if key == 'Version':
        result[key] = float(responses[key])
      else:
        result[key] = int(responses[key])
    self.status = result
    return self.status

  def display_status(self):
    """
    Print the IOtech status nicely

    @return: None
    """
    keys = self.status.keys()
    keys.sort()
    print "Version",self.status["Version"]
    for code in keys:
      if code != "Version":
        print "%7s  %-30s  %1d" % (code,
                                  self.commands[code],
                                  self.status[code]   )
      
  def get_bit_state(self,bit):
    """
    Get the state of a bit (1-40)

    @type bit : int
    @param bit : bit number (1-40)

    @return: bool
    """
    return bool(self.Ask("U"+str(bit)))

  def get_all_bits(self,formatted=False,groups=0):
    """
    Returns all the bits

    @type formatted : bool
    @param formatted : response converted to a bit pattern

    @type groups : int
    @param groups : 0-not grouped, else number of bits per group

    @return: int or list or str
    """
    bits = self.Read().strip()
    response = eval('0x'+bits)
    if formatted:
      if groups:
        return Math.decimal_to_binary(response,40,grouped=groups)
      else:
        return Math.decimal_to_binary(response,40)
    else:
      if groups:
        ports = {}
        for port in range(5):
          mask = int('11111111',2) << port*8
          port_state = (response & mask) >> port*8
          ports[port+1] = port_state
        return ports
      else:
        return response

  def write_port(self,port,value):
    """
    Write a value to a port
    """
    self.Write("P"+str(port)+" F3")
    self.Write("D"+str(value)+"Z")
    self.Write("P0 F0")

  def output_port(self):
    """
    Indicates which ports are configured for output
    """
    return self.ports_out[self.status['C']]
  
  def set_bit(self,bit):
    """
    Set the state of bit 'bit' high.

    @type bit : int
    @param bit : LSB = 1, MSB = 40

    @return: True on success
    """
    port = (bit-1)/8+1
    port_dirs = get_port_directions()
    if port_dirs[port]:
      if IOtechWrite('A'+str(bit)):
        return True
      else:
        return False
    else:
      return False
  
  def clr_bit(self,bit):
    """
    Clear bit 'bit'.

    @type bit : int
    @param bit : LSB = 1, MSB = 40

    @return: True on success
    """
    port = (bit-1)/8+1
    port_dirs = get_port_directions()
    if port_dirs[port]:
      if IOtechWrite('B'+str(bit)):
        return True
      else:
        return False
    else:
      return False

  def pulse_bit(self,bit,low=True,pause=0.5):
    """
    Pulse the designation bit.

    This changes the state of the bit in the designated direction
    for the specified length of time (seconds) and then returns it to
    its original state.
    """
    if low:
      if not self.get_bit_state(bit):
        self.set_bit(bit)
        sleep(pause)
      self.clr_bit(bit)
      sleep(pause)
      self.set_bit(bit)
    else:
      if self.get_bit_state(bit):
        self.clr_bit(bit)
        sleep(pause)
      self.set_bit(bit)
      sleep(pause)
      self.clr_bit(bit)

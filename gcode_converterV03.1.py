#!/usr/bin/python

##Copyright (c) 2012, River Allen
##Modified 2015, Benjamin Hirmer aka Hardy
##
##Modifikation Information:
##Added Visualisation-Support for PyCam-Gcode in GCode Analyzer/Visualizer (c) hudbrog (used in OctoPrint and on his side http://gcode.ws )
##Added Feedrates for traveling/cutting/z-movements
##Added Support for HeeksCNC generated G-Codes with Arc-Commands (G3 / G4) // Visualisation wont work with Arcs
##Added Travel/Cutting-Distance Information, Arcs (G3 / G4) just get calculated by its diagonal distance
##
##All rights reserved.
##
##Redistribution and use in source and binary forms, with or without modification,
##are permitted provided that the following conditions are met:
##* Redistributions of source code must retain the above copyright notice, this list
##  of conditions and the following disclaimer.
##* Redistributions in binary form must reproduce the above copyright notice,
##  this list of conditions and the following disclaimer in the documentation and/or
##  other materials provided with the distribution.
##
##THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
##EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
##OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT
##SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
##INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
##TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
##BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
##CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
##ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
##DAMAGE.

from datetime import datetime
import os
import re
import sys
import shutil
import math

class GCodeConverter:
    def __init__(self):
        self.invalid_commands = [
            'M2',
            'M5',
            'M6',
            'M3',
            'T1',
            'T4',
            'S1', # Surface command does not work (this is a hack)
            'G40', # Hardy: Marlin would not understand 
            'G49', # Hardy: Marlin would not understand 
            'G80', # Hardy: Marlin would not understand 
            'G54', # Hardy: Marlin would not understand 
            'G61' # Hardy: Marlin would not understand
            ]
    
    def convert(self, filename):
        pass
    
    
class PyCamGCodeConverter(GCodeConverter):
    def __init__(self):
        GCodeConverter.__init__(self)

    def convert(self, filename, final_pos=None):
        # Add and remove g-code commands to make a pycam g-code
        # file more mendel compatible. Ouput to <filename_converted.ext>.
        # When cutting is complete, move to final pos (x, y, z).
        final_pos = final_pos or (0., 0., 18.)
        write_fname = '%s_converted%s' % os.path.splitext(filename)
        with open(filename, 'rb') as rf:
            with open(write_fname, 'wb') as wf:
                # Add some metadata to the file (not really used at this point)
                wf.write('; CONVERTED FOR REPRAP: %s\n' % str(datetime.now()))
                # Copy the contents of the original gcode file devoid
                # of the pycam gcode commands that do not work on the 
                # mendel gcode firmware.
                for l in rf.readlines():
                    if self.check_valid_commands(l):
                        wf.write(l)
                # Some finish up commands to make it easier to remove the
                # completed part.
                wf.write("; FINISH THE CUT BY MOVING BIT TO SAFER POSITION\n")
                wf.write("G1 Z%f ; MOVE BIT ABOVE PIECE\n" % final_pos[2])
                wf.write("G1 X%f Y%f ; HOME X AND Y\n" % final_pos[:2])
        
        return write_fname

    def check_valid_commands(self, line):
        for cmd in self.invalid_commands:
            if cmd in line:
                return False
        return True        


class MarlinGCodeConverter(PyCamGCodeConverter):
    def __init__(self):
        PyCamGCodeConverter.__init__(self)
    
    def convert(self, filename, feedrate, final_pos=None):
        # All of this code is written to compensate for the fact Marlin is 
        # less robust with the format of g-code. Specifically, on the old mendel
        # the following commands:
        # ~ G1 X30
        # ~  Y30 
        # ~  X50
        # would work. These commands do not work on Marlin. Hence, this code
        # converts the above commands to:
        # ~ G1 X30
        # ~ G1 Y30
        # ~ G1 X50
        
        # Convert pycam gcode for mendel
        convert_fname = PyCamGCodeConverter.convert(self, filename, final_pos)
        # Store this new conversion in a temp file
        temp_fname = '.temp_convert'
        temp_calc = '.temp_calc'
        temp_sum = '.temp_sum'
        pattern = re.compile('([gG01]{1,2})+\s([xX0-9.]{1,15})+\s([yY0-9.]{1,15})+\s([zZ0-9.]{1,15})+\s([fF0-9.]+[0-9.]{1,15})+\s') #Hardy: RegEx for Detect and Slice G-Code which mess with Visualisation
        distances = re.compile('([gG0-3]{1,3})+\s{1,2}[xX]([0-9.]{1,15})|\s[yY]-?([0-9.]{1,15})|\s[zZ]-?([0-9.]{1,15})') #Hardy: RegEx for Calculating Distances
        waiting = re.compile('([gG04]{1,3})+\s{1,2}[P]([0-9.]{1,5})') #Hardy: RegEx for reconvert Waiting Commands
        with open(convert_fname, 'rb') as f_pycc:
            with open(temp_fname, 'wb') as f_temp:
		with open(temp_calc, 'wb') as f_calc:
		    move_type = None
		    fetch_time = None
		    AF = 0 #Declare False at first
		    BZ = 'M103 ; Support for Visualisation\n'
		    AZ = 'M101 ; Support for Visualisation\n'
		    
		    for l in f_pycc.readlines():
			first_3_chars = l[:3].upper()
			first_2_chars = l[:2].upper()
			first_char = l[:1].upper()
			if first_3_chars == 'G1 ' or first_3_chars == 'G01':
			    move_type = 'G1'
			elif first_3_chars == 'G0 ' or first_3_chars == 'G00':
			    move_type = 'G0'
			elif first_3_chars == 'G02':
			    move_type = 'G2'
			elif first_3_chars == 'G03':
			    move_type = 'G3'
			elif first_3_chars == 'G04':
			    move_type = 'G0'
			    fetch_time = True
			elif first_3_chars == 'G90': #Heeks places an 'G90' command after eachs seperate Drawing-Description - Marlin mess with that
			    move_type = 'unchanged'
			elif first_2_chars == ' X' or first_char == 'X' or first_2_chars == ' Y' or first_char == 'Y' or first_2_chars == ' Z' or first_char == 'Z':
			  if first_char == 'Z': #Hardy: Check if HeeksCNC is on HightSave at Surface 
			    l = "%s%s" % ("G1 ",l) 
			  else:
			    # Change ' X100' to 'G0 X100'
			    l = "%s%s" % (str(move_type) + " ", l) 
			else:
			    move_type = None
			# Hardy: Check if G0/G1 given and change its Feedrate at the end of the G-Code-Line
			# Also adds space between if not already placed
			second_chars = l[2:4].upper()
			last_chars = len(str(l))
			if fetch_time:
			  l2 = l[last_chars-1:]
			  wait = waiting.match(str(l))
			  time = wait.group(2)
			  l = "G4 P" + str(int(time)*1000) + " ; Wait for " + time + " seconds" + l2
			  fetch_time = False
			elif second_chars == ' Z' or second_chars == 'Z ':
			  l1 = l[:last_chars-1]
			  l2 = l[last_chars-1:]
			  lf = " F" + str(feedrate[2])
			  l = l1 + lf + l2
			  AF = AF + 1
			  ZAV = True
			elif move_type == 'G3':
			  l1 = l[:last_chars-1]
			  l2 = l[last_chars-1:]
			  l3 = l[last_chars-2:last_chars-1]
			  if ' ' in l3:
			    lf = "F" + str(feedrate[1])
			  else:
			    lf = " F" + str(feedrate[1])
			  l = l1 + lf + l2
			  ZAV = False
			elif move_type == 'G2':
			  l1 = l[:last_chars-1]
			  l2 = l[last_chars-1:]
			  l3 = l[last_chars-2:last_chars-1]
			  if ' ' in l3:
			    lf = "F" + str(feedrate[1])
			  else:
			    lf = " F" + str(feedrate[1])
			  l = l1 + lf + l2
			  ZAV = False
			elif move_type == 'G1':
			  l1 = l[:last_chars-1]
			  l2 = l[last_chars-1:]
			  l3 = l[last_chars-2:last_chars-1]
			  if ' ' in l3:
			    lf = "F" + str(feedrate[1])
			  else:
			    lf = " F" + str(feedrate[1])
			  l = l1 + lf + l2
			  ZAV = False
			elif move_type == 'G0':
			  l1 = l[:last_chars-1]
			  l2 = l[last_chars-1:]
			  l3 = l[last_chars-2:last_chars-1]
			  if ' ' in l3:
			    lf = "F" + str(feedrate[0])
			  else:
			    lf = " F" + str(feedrate[0])
			  l = l1 + lf + l2
			  ZAV = False
			elif move_type == 'unchanged': # Fix wrong habbit of HeeksCNC
			  l1 = l[3:last_chars-1]
			  l2 = l[last_chars-1:]
			  l = "G90 \n" + "G0 " + l1 + " F" + str(feedrate[0]) + l2
			
			# Hardy: Crop out necesary Values for calculating Travel and Cutting-Distances and Write it in a Temp-File
			if distances.findall(str(l)):
			  regline = distances.findall(str(l))
			  
			  for i in regline:
			    if i[1]:
			      f_calc.write("X" + i[1] + "\n")
			    elif i[2]:
			      f_calc.write("Y" + i[2] + "\n")
			    elif i[3]:
			      if i[3][:1] == "0":
				f_calc.write("C" + i[3] + "\n")
			      else:
				f_calc.write("T" + i[3] + "\n")

			# Hardy: Look for something like that (pycam make this sometimes) "G1 X122.12 Y152.123 Z1204 F1500" and change it to "G1 X122.12 Y152.123 F150 \n G0 Z1204 F800 because this will mess with the Visualisation
			if pattern.match(str(l)):
			  regline = pattern.match(str(l))
			  gvalue = regline.group(1)
			  xvalue = regline.group(2)
			  yvalue = regline.group(3)
			  zvalue = regline.group(4)
			  fvalue = regline.group(5)
			  f_temp.write("G1" + " " + xvalue + " " + yvalue + " F" + str(feedrate[1]) + "\n")
			  f_temp.write(BZ)
			  AF = AF + 1
			  f_temp.write("G0 " + zvalue + " F" + str(feedrate[2]) + "\n")
			else:
			  if AF == 1 and ZAV:
			    f_temp.write(BZ)
			    
			  f_temp.write(l)
			  
			  if AF == 2 and ZAV:
			    f_temp.write(AZ)
			    AF = 0

	# Hardy: Calculate Distrances with Triangles
	with open(temp_calc, 'rb') as f_calc:
	  with open(temp_sum, 'wb') as f_sum:
	    
	    value = ""
	    cache = []
	    summaster1 = [] #Collecting SUM of Cutting-Distances
	    summaster2 = [] #Collecting SUM of Travel-Distances
	    calc = False #Turn of Summing of Cutting-Distances first
	    
	    for c in f_calc.readlines():
	      command = c[:2]
	      axis = c[:1]
	      stringcount = len(str(c))

	      f_sum.write(c)
	      value = float(c[1:stringcount-1])
	      
	      cache.append((value, axis))
	      counts = len(cache)
	      
	      if counts >= 4:
		f_sum.write(str(cache) + str(counts) + "\n\n")
		if cache[0][1] == "X":
		  if cache[1][1] == "Y":
		    if cache[2][1] == "C":
		      del cache[2]
		      f_sum.write("Cutting active\n")
		      calc = True
		    elif cache[2][1] == "T":
		      del cache[2]
		      f_sum.write("Travel active\n")
		      calc = False
		    elif cache[2][1] == "X":
		      if cache[3][1] == "Y":
			f_sum.write("Calculate?\n")
			if calc:
			  summaster1.append(math.sqrt(((cache[0][0]-cache[2][0])**2)+((cache[1][0]-cache[3][0])**2)))
			else:
			  summaster2.append(math.sqrt(((cache[0][0]-cache[2][0])**2)+((cache[1][0]-cache[3][0])**2)))
			  f_sum.write("Sum Traveling\n")
			del cache[0:2]
		      elif cache[3][1] == "X":
			f_sum.write("Linear 1 Calculate?\n")
			if calc:
			  summaster1.append(abs(cache[2][0]-cache[3][0]))
			  f_sum.write(" Calculate: " + str(cache[2][0]) + " " + str(cache[3][0]) + "\n")
			else:
			  summaster2.append(abs(cache[2][0]-cache[3][0]))
			  f_sum.write("Sum Traveling\n")
			del cache[2]
		      elif cache[3][1] == "T":
			f_sum.write("Linear 2 Calculate? Then Travel active\n")
			if calc:
			  summaster1.append(abs(cache[0][0]-cache[2][0]))
			  f_sum.write(" Calculate: " + str(cache[0][0]) + " " + str(cache[2][0]) + "\n")
			else:
			  summaster2.append(abs(cache[0][0]-cache[2][0]))
			  f_sum.write("Sum Traveling\n")
			del cache[0]
			del cache[2]
			cache[0], cache[1] = cache[1], cache[0]
		      elif cache[3][1] == "C":
			f_sum.write("Linear 3 Calculate? Then Cutting active\n")
			summaster2.append(abs(cache[0][0]-cache[2][0]))
			f_sum.write("Sum Traveling\n")
			del cache[0]
			del cache[2]
			cache[0], cache[1] = cache[1], cache[0]
			calc = True
		    elif cache[2][1] == "Y":
		      f_sum.write("Linear 4 Calculate?\n")
		      if calc:
			summaster1.append(abs(cache[1][0]-cache[2][0]))
			f_sum.write(" Calculate: " + str(cache[1][0]) + " " + str(cache[2][0]) + "\n")
		      else:
			summaster2.append(abs(cache[1][0]-cache[2][0]))
			f_sum.write("Sum Traveling\n")
		      del cache[1]
		elif cache[0][1] == "T":
		  f_sum.write("Traveling active\n")
		  del cache[0]
		  calc = False
		elif cache[0][1] == "C":
		  f_sum.write("Cutting active\n")
		  del cache[0]
		  calc = True
		else:
		  del cache[0]


	    # Sum all Distances
	    cuttingdistance = sum(summaster1)
	    travelingdistance = sum(summaster2)
	    
	    if cuttingdistance != 0:
	      print "Total Cutting Distance: " + str(cuttingdistance) + " mm"
	      print "Total Travel Distance: " + str(travelingdistance) + " mm"
	      print "Total Distance: " + str(cuttingdistance+travelingdistance) + " mm"
	    else:
	      print "Could not determine Cutting-Distance: Z-Cutting-Level is not at 0"
	      print "Total Distance: " + str(cuttingdistance+travelingdistance) + " mm"

        # Copy the temp file conversion over to the pycam conversion
        # for cleanliness
        shutil.copy(temp_fname, convert_fname)
        # Get rid of temp files
        os.remove(temp_fname)
        os.remove(temp_calc)
        os.remove(temp_sum)
        return convert_fname


if __name__ == '__main__':
    # Simple command line script. Can be used, but mostly added for testing.
    # Hardy: Added Feedrate Support and some Error-Check/Feedback for Command-Line
    error = 0
    if len(sys.argv) < 2:
        print 'CNC_to_RepRap <feedrate_traveling> <feedrate_cutting> <feedrate_zaxis> <filename1> [filename2 ... n]'
    elif len(sys.argv) >= 5:
      if sys.argv[1].isdigit():
	print "Feedrate Traveling: " + sys.argv[1]
      else:
	print 'Feedrate Traveling is not a Number!'
	error = 1
      if sys.argv[2].isdigit():
	print "Feedrate Cutting: " + sys.argv[2]
      else:
	print 'Feedrate Cutting is not a Number!'
	error = 1
      if sys.argv[3].isdigit():
	print "Feedrate X-Axis Traveling: " + sys.argv[3]
      else:
	print 'Feedrate X-Axis is not a Number!'
	error = 1
      if len(sys.argv[4]) > 0 and error == 0:
	endfile = len(sys.argv[0:])
	for args in range(4, endfile):
	  print "File: " + sys.argv[args]
      elif error == 1:
	print 'Dont accept File(s)'
      else:
	print 'No File selected!'
	error = 1
    else:
      print 'Arguments are Missing'
	
    #Hardy: check fo errors
    if error == 0:
      ffrates = sys.argv[1:4]
      fnames = sys.argv[4:]
      fr = []
      for frate in ffrates:
	  fr.append(frate)
      gc_converter = MarlinGCodeConverter()
      for fname in fnames:
	  gc_converter.convert(fname, fr)

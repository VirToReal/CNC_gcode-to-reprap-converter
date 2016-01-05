#!/usr/bin/python

##Copyright (c) 2015, Benjamin Hirmer
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
import sys
import shutil

dateandtime = datetime.now()
dateandtime = unicode(dateandtime.strftime("%H-%M-%S_%d-%m-%Y"))
convfiles = []
gcodeconverter = "gcode_converterV06.py" # Filename of RepRap Converter (must be in the same dictionary like gcode-paver

class ConsoleCommander:
  #pyCamCommander controls the Terminal-Command for generating G-Codes with pyCam and converts them into RepRap readable G-Code
    def __init__(self):
	self.servus="Servus"
	
    def svgtogcode(self, filename): #convert .svg Filename to gcode File
	newfilename = '%s_pycam.gcode' % os.path.splitext(filename)[0]
        output = os.popen("pycam " + filename + " --export-gcode=" + newfilename + " --tool-size=0.1 --process-path-strategy=engrave --safety-height=1 --process-milling-style=conventional -q")
        return output.read(), newfilename
      
    def gcodetoreprap(self, filename, parameters): #convert pyCam G-Code to RepRap G-Code File
	newfilename = '%s_converted.gcode' % os.path.splitext(filename)[0]
        output = os.popen("python " + gcodeconverter + " " + str(1200) + " " + str(150) + " " + str(1200) + " " + filename)
        return output.read(), newfilename

class GCodeGenerator(ConsoleCommander):
    def __init__(self):
        ConsoleCommander.__init__(self)

    def generate(self, filename, parameters):
        # Generate a .logfile and log pyCam and reprap-Gcode-Converter Output
        logfile = '%s/Paverlog_%s.log' % (os.path.dirname(filename), dateandtime)
        filedir = os.path.dirname(filename)
        loginfo1 = self.svgtogcode(filename)
        loginfo2 = self.gcodetoreprap(loginfo1[1], parameters)
	with open(logfile, 'a+') as wf:
	    wf.write('\n\n##############################################\nSTART generating .SVG File into gcode File: ' + loginfo1[1] + ' with pyCam: %s\n' % str(datetime.now()))
	    wf.write(loginfo1[0])
	    wf.write('\nConvert PyCam G-Code in an RepRap-Readable G-Code Content File: ' + loginfo2[1] + ' with ' + gcodeconverter + ': %s\n' % str(datetime.now())) 
	    wf.write(loginfo2[0])
        return loginfo2[1]

class Paver(GCodeGenerator):
    def __init__(self):
        GCodeGenerator.__init__(self)
    
    def convert(self, filename, parameters, fnamecount):
	# Check for SVG Files
	ext = os.path.splitext(filename)[-1].lower()
	if ext == ".svg":
	  # Convert SVG to CNC-GCode to REPRAP-GCode and write Filenames in a Tuple
	  convertedfilename = GCodeGenerator.generate(self, filename, parameters)
	  convfiles.append(convertedfilename)
	  convfilescount = len(convfiles)
	else:
	  convfiles.append('not_converted') #TODO no funtion here yet
	return True, convfiles

    def paveit(self, filenames, parameters):
      
	# Check if Temp-File already exists
	temp = '.temp-paver-file'
	if os.path.isfile(temp):
	  os.remove(temp)
	  print "Removed old broken Paver-Temp-File (this would mess your g-code up like hell)\n"
      
	# Analye Pattern Sizes
        numoftiles = parameters[0]
        widthoftile = parameters[1]
        heightoftile = parameters[2]
        
        print "Tile Count in a Row: " + numoftiles + " Tiles - Width of Tile: " + widthoftile + " - Height of Tile: " + heightoftile
        
        XAmount = 0
        YAmount = 0
        
        for idx, filename in enumerate(filenames):

	  if idx % int(numoftiles):
	    newrow = False
	  else:
	    newrow = True
	    YAmount += 1

	  if newrow: #If a new Row will is on the move, let machine recorrect its home position
	    XYZero = "G0 X0 ; Paver wants Bit at Home of Current Tile\nG92 X" + str(int(widthoftile)*XAmount) + " ;Paver shows Bit how far he is from real Home\nG0 X0 Y" + heightoftile + " ;Paver wants Bit at real Home, and in Next Row\nG92 X Y;Paver Shows Bit its new Tile-Home\n"
	  else:
	    XYZero = "G0 X" + str(int(widthoftile)) + " ;Paver shows Bit the next Tile\nG92 X ;Paver defines Tiles Home\n"

	  if idx != 0:
	    if XAmount == int(numoftiles)-1:
	      XAmount = 0
	    else:
	      XAmount += 1

	  with open(filename, 'rb') as f_tilefile:
	      with open(temp, 'a+') as f_temp:
		linecount = sum(1 for _ in open(filename))
		f_temp.write("\n\n; ############ PAVER TILE %s ############ \n; #### Filename: %s\n" % (str(idx), str(filename)))
		if idx != 0:
		  f_temp.write(XYZero)
		  
		for idl, l in enumerate(f_tilefile.readlines()):

		  # Delete Rows of MOVING BIT TO SAFER POSITION
		  if idl != linecount - 1 and idl != linecount - 2:
		    f_temp.write(l)
		  else:
		    f_temp.write("; PAVER Removed this Line\n")

		f_temp.write("G0 Z1 ; PAVER moved Bit in Save Height") # TODO Correct Values
	
	with open(temp, 'a+') as f_temp:
	  f_temp.write("\nG0 Z20 X0 Z0 ; PAVER finished Paving and moves Bit up in the air *flyyy Bit flyy...")
	  

	newfilename = '%s/Paved_%s.gcode' % (os.path.dirname(filenames[0]), dateandtime)

	print newfilename
	shutil.copy(temp, newfilename)
	os.remove(temp)
	print "Total Paved Size: " + str(int(numoftiles)*int(widthoftile)) + " mm x " + str(YAmount*int(heightoftile)) + " mm (Width x Height)"


if __name__ == '__main__':
    # Check Arguments of Command-Line 
    error = 0
    if len(sys.argv) < 2:
        print 'Pave GCode <amount_horizontal> <sign_width> <sign_height> <feedrate_traveling> <feedrate_cutting> <feedrate_zaxis> <filename1> [filename2 ... n]'
        error = 1
    elif len(sys.argv) >= 8:
      if sys.argv[1].isdigit():
	print "Amount of Tiles in one horizontal Line: " + sys.argv[1]
      else:
	print '"Amount of Tiles" is not a Number!'
	error = 1
      if sys.argv[2].isdigit():
	print "Tile Width: " + sys.argv[2]
      else:
	print 'The Size of a Tile is not a Number!'
	error = 1
      if sys.argv[3].isdigit():
	print "Tile Height: " + sys.argv[3]
      else:
	print 'The Height of a Tile is not a Number!'
	error = 1
      if sys.argv[4].isdigit():
	print "Traveling Feedrate: " + sys.argv[4]
      else:
	print 'The Traveling Feedrate is not a Number!'
	error = 1
      if sys.argv[5].isdigit():
	print "Cutting Feedrate: " + sys.argv[5]
      else:
	print 'The Cutting Feedrate is not a Number!'
	error = 1
      if sys.argv[6].isdigit():
	print "Z-Axis Feedrate: " + sys.argv[6]
      else:
	print 'The Z-Axis Feedrate is not a Number!'
	error = 1
      if len(sys.argv[7]) > 0 and error == 0:
	endfile = len(sys.argv[0:])
	for args in range(7, endfile):
	  print "File: " + sys.argv[args]
      elif error == 1:
	print 'Dont accept File(s)'
      else:
	print 'No File selected!'
	error = 1
    else:
      print 'Arguments are Missing'
      error = 1
	
    #Process by listed Files
    if error == 0:
      parameters = sys.argv[1:7]
      fnames = sys.argv[7:]
      fnamecount = len(fnames)
      pm = []
      for parameter in parameters:
	  pm.append(parameter)
      gc_converter = Paver()
      for fname in fnames:
	  converted = gc_converter.convert(fname, pm, fnamecount)
      if converted[0]:
	  gc_converter.paveit(converted[1], pm)

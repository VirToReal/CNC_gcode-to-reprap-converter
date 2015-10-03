# CNC_gcode-to-reprap-converter
PyCam/HeeksCNC GCode to RepRap converter

Created by River Allen (c) 2012
Modified by me 

What it does?
- convert pycam/heekscnc g-code files into reprap gcode (just tested with marlin-firmware for now).
  (Please let me know if it works with other CAM-Software)

Added features:
- Adding Feedrates for Traveling/Cutting/Z-Movements
- Added support for hudbrogs Visualisation in Octoprint / http://gcode.ws (https://github.com/hudbrog/gCodeViewer/)
- Added support for converting HeeksCNC G-Codes (Based on emc2b post processor)
- Added Cutting/Traveling distance information after converting, Arcs (G2/G3) just get calculated by its diagonal distance (easyer for me :) Currently the cutting distance messes with multi layer cutting
- Added G04 (Dwell) Command for converting X Seconds Waiting-Time in reprap comprehend G-Code

~ Hardy

# jeol2010f remote control using jeol2010lib.py
# Author: Qun Liu, qun.liu@gmail.com
# source: https://github.com/qun-liu/jeol2010f  
import time
import math
import sys
from pyscope import jeol2010lib
from pyscope import tem

Debug = True

# function modes, currently not used.
FUNCTION_MODES = {'mag1':0,'mag2':1,'lowmag':2,'samag':3,'diff':4}
FUNCTION_MODE_ORDERED_NAMES = ['mag1','mag2','lowmag','samag','diff']

# identifier for dector
MAIN_SCREEN = 4

# MDS modes
MDS_OFF = 0
MDS_SEARCH = 1
MDS_FOCUS = 2
MDS_PHOTO = 3

# aperture ids
CLA = 1
OLA = 2
HCA = 3
SAA = 4

# constants for Jeol Hex value
ZERO = 32768
MAX = 65535
MIN = 0
SCALE_FACTOR = 32767

# coarse-fine ratio for OBJC
COARSE_SCALE = 16

minimum_stage  = {'x': 5e-7, 'y': 5e-7, 'z': 4e-7, 'a': 0.004, 'b': 0.004}
backlash_stage = {'x': 30e-6, 'y': 30e-6, 'z': 1.2e-8}

def Debug_print(message):
    if Debug:
        print message

### unit converstation between Jeol (hex) and Leginon (meter).
##def toJeol(val):
##    return ZERO + int(round(SCALE_FACTOR * val))
##
##def toLeginon(val):
##    return float(val - ZERO)/SCALE_FACTOR

class JEM(tem.TEM):
    name = 'JEM2010'
    def __init__(self):
        if Debug == True:
            print 'from JEM __init__ class:'
        tem.TEM.__init__(self)
        self.correctedstage = False
        self.jLib = jeol2010lib.jeolLib()  # jeol2010lib
                        
        self.magnifications = []
        self.mainscreenscale = 1.0
        self.stageScale = 1e9 # from nanometer to meter
        #self.last_alpha = self.getStagePosition()['a']
        self.last_alpha = 0.0

        result = None
##        timeout = False
##        t0 = time.time()
##        while result != 0 and not timeout:
##            result = self.jLib.getAlpha()
##            time.sleep(1)
##            t1 = time.time()
##            if t1-t0 > 60:
##                timout = True
##                sys.exit(1)

        #self.setJeolConfigs()
        #self.has_auto_apt = self.testAutomatedAperture()
        self.relax_beam = False
        # submode_mags keys are submode_indices and values are magnification list in the submode
        #self.submode_mags = {}
        # initialize values from jeol.cfg
        self.stage_limit = {
            'x': 1e-3, 'y': 1e-3, 'z': 220e-6, 'a': 1.2217, 'b': 3.141593}
        self.backlash_scale = {'x': 10e-6, 'y': 30e-6}
        self.backlash_limit = {'full': 10e-6, 'reduced': 5e-7}

    def __del__(self):
        self.jLib.__del__()

    # define three high tension states
    def getHighTensionStates(self):
        if Debug == True:
            print 'from JEM getHighTensionStates'
        return ['off', 'on', 'disabled']

    # get high tenstion voltage
    def getHighTension(self):
        if Debug == True:
            print 'from JEM getHighTension'
        highTension = self.jLib.getAccelVoltage()
        return highTension

    # set high tension, not used here
    def setHighTension(self, mode = 'off'):
        if Debug == True:
            print 'from JEM setHighTension'
        return True

    # get three colum valve positions, not work for ftcomm
    def getColumnValvePositions(self):
        if Debug == True:
            print "from JEM getColumnValvePositions"
        return ['open', 'closed', 'unknown']

    # through beam state, not used
    def getColumnValvePosition(self):
        if Debug == True:
            print 'from JEM getColumnValvePostion'
        #state = self.getBeamState()
        #position_mapping = {'on':'open','off':'closed','unknown':'closed'}
        return 'unknown'

    # through beam state, not used
    def setColumnValvePosition(self, position):
        if Debug == True:
            print 'from JEM setColumnValvePosition'
        return 'unknown'

   # get beam intensity from condenser lens 3 (CL3), not implemented.
    def getIntensity(self):
        if Debug == True:
            print 'from JEM getIntensity'
        intensity = self.jLib.getIntensity()
        return intensity

    # set beam intensity, CL3, not implemented. 
    def setIntensity(self, intensity, relative = 'absolute'):
        if Debug == True:
            print 'from JEM setIntensity'
        if relative == 'absolute':
            pass
        else:
            intensity += self.getIntensity()
        if self.jLib.setIntensity(intensity) == True:
            return True
        else:
            return False

    # get the beam satus as on, off, onr unknown, not used
    def getBeamState(self):
        if Debug == True:
            print "from JEM getBeamState"
        #beamState = self.jLib.getBeamState()
        return 'unknown'

    # set beam state, not used
    def setBeamState(self, mode = 'off'):
        if Debug == True:
            print "from JEM setBeamState"
        return True

    # get pump, not used.
    def getTurboPump(self):
        if Debug == True:
            print "from jeol getTurboPump"
        return 'N/A for JEM2010'

    # set pump, not used.
    def setTurboPump(self, mode = 'off'):
        if Debug == True:
            print "from JEM setTurboPump"
        return NotImplementedError()

    #### get and set magnificantions 
    # get all possible magnifications
    # set all magnifications to a list in init

    def findMagnifications(self):
        if Debug == True:
            print 'from JEM findMagnifications'
        magnifications = self.jLib.magnification ## lowMag + highMag 
        self.setMagnifications(magnifications)
        #print('mag:',self.setMagnifications) 
        return True

    def setMagnifications(self, magnifications):
        if Debug == True:
            print 'from JEM setMagnifications'
        self.magnifications = magnifications ## copy to self.magnifications
        return True

    # check if self.magnifications is initialized sucessfully
    def getMagnificationsInitialized(self):
        if self.magnifications:
            return True
        else:
            return False

    # get magnifications defined in a tuple in __init__(sef)
    def getMagnifications(self):
        return self.magnifications

    # get A magnification value using an index, if not defined, get from scope.
    def getMagnification(self, index = None):
        if Debug == True:
            print "from JEM getMagnification"
        if index is None:
           return self.jLib.getMagValue() ## [2] value
        elif int(index) > 41 or int(index) < 0:
            print '    Valid magnification index should be 0-29'
            return
        else:
            #self.findMagnifications() ## setup mags from jLib
            return self.jLib.magnification[index]

    # get the actual Mag value (x1000?) the same as getMagnification
    def getMainScreenMagnification(self):
        if Debug == True:
            print 'from JEM getMainScreenMagnification'
        return self.jLib.getMagValue()

    # from a mag value to get mag index position between 0 and 41, with the list "self.magnifications"
    def _getMagPosition(self,magnification):  ##
        magRange = 42
        mags = self.jLib.magnification #A list: lowMag + highMag
        for magIndex in range(0,magRange):  # [ )
            if int(magnification) <= mags[magIndex]:
                break  ## skip the rest
        if magIndex > magRange:
            print '    magnification out of range'
        return magIndex

    # get mag index position between 0 and 41, a wrapper of _getMagPosition
    def getMagnificationIndex(self, magnification):
        if Debug == True:
            print 'from JEM getMagnificationIndex'
        magIndex = self._getMagPosition(magnification)
        return int(magIndex)

    # set magnification using a specific magnification value
    def setMagnification(self, magnification):  # it may take some time to set Mag
        if Debug == True:
            print 'from JEM setMagnification'
        self.jLib.setMagValue(magnification)
        return True

    # set magnification using magnification index which is converted to value anyway
    def setMagnificationIndex(self, magIndex):
        if Debug == True:
            print 'from JEM setMagnificationIndex'
        magnification = self.getMagnification(magIndex) ## convert index to value
        if self.jLib.setMagValue(magnification) == True:
            return True
        else:
            return False

    # don't understand it well, but it works
    def setMainScreenScale(self, mainscreenscale = 1.0):
        self.mainscreenscale = mainscreenscale
        return True

    # not available in JEM2010
    def getMainScreenScale(self):
        if Debug == True:
            print 'from JEM getMainScreenScale'
        return self.mainscreenscale  ## i.e. 1.0 as defined

    # get current spot size in TEM mode: 1,2,3,4,5
    def getSpotSize(self):
        if Debug == True:
            print 'from JEM getSpotSize'
        spotsize = self.jLib.getSpotSize()
        return spotsize

    # set spot size between 1 and 5 as a string
    def setSpotSize(self, spotSize, relative = 'absolute'):
        if Debug == True:
            print 'from JEM setSpotSize'
        if relative == 'absolute':
            s = int(spotSize)
        else:
            s = int(self.getSpotSize() + spotSize)
        if self.jLib.setSpotSize(s) == True:
            return True
        else:
            return False

    # return position in meter, angle in pi in  leginon format
    def getStagePosition(self):
        if Debug == True:
            print "from JEM getStagePosition"
        value = {'x': None, 'y': None, 'z': None, 'a': None, 'b':None}
        pos = self.jLib.getGonioRead()
        value['x'] = float(pos['x']/1e3)  # jeol millimer to leginon meter conversion
        value['y'] = float(pos['y']/1e3)
        value['z'] = float(pos['z']/1e3)
        value['a'] = float(pos['a']/57.3)  # jeol degree to leginon radias conversion
        value['b'] = float(pos['b']/57.3)
        return value

    # filter out state position axis to decide move or not to  move.
    def checkStagePosition(self, position):
        current = self.getStagePosition()
        bigenough = {}
        for axis in ('x', 'y', 'z', 'a', 'b'):
            # b is ignored
            if axis in position:
                delta = abs(position[axis] - current[axis])
                if delta > minimum_stage[axis]:
                    bigenough[axis] = position[axis]
        return bigenough  # a sub set of dict for moving

    #tilt back to zero if titl is drifted more than 0.5 degree,
    #tilt back to previous value if less than 2 degrees
    def forceTiltBack(self,position):
        if 'a' in position.keys():
            if abs(position['a']) < math.radians(0.5):                
                position['a'] = 0.0
                return position
            current_tilt = self.getStagePosition()['a']
            if abs(current_tilt - self.last_alpha) < math.radians(1.99):
                position['a'] = self.last_alpha
                return position

    # receive position in meter, angle in pi, backlash is 30 um
    def setStagePosition(self, position_dict):
        if Debug == True:
            print 'from JEM setStagePosition'
        stagePos = position_dict.copy()
        #stagePos = self.forceTiltBack(stagePos) to be done
        value = self.checkStagePosition(stagePos)
        if not value:
            return
        prevalue = {'x': None, 'y': None, 'z': None, 'a': None, 'b': None}
        for axis in ('x', 'y', 'z', 'a', 'b'):
            if axis in value:
                if axis == 'a':
                    self._setStageA(value)
                    self.last_alpha = value['a']
                elif axis == 'z':
                    self._setStageZ({'z':value['z']})
                elif axis == 'x' or axis == 'y':
                    self._setStageXThenY({axis:value[axis]})
                else:
                    return False
        return True

    # resend the requested state position dict in axies unit convergence.
    #JEM stage call may return success without giving error when the position is not reached.
    def confirmStagePosition(self, requested_position, axes=['z',]):
        accuracy = minimum_stage
        for axis in axes:
            self.trys = 0
            while self.trys < 10:
                current_position = self.getStagePosition()
                if axis in requested_position.keys() and abs(current_position[axis] - requested_position[axis]) > accuracy[axis]:
                    self.trys += 1
                    if Debug == True:
                        print 'stage %s not reached' % axis
                        print abs(current_position[axis]-requested_position[axis])
                        self.setStagePositionByAxis(requested_position,axis)
                else:
                    break

    # move single axis for confirmStagePosition
    def setStagePositionByAxis(self, position, axis):
        movable_position = self.checkStagePosition(position)
        keys = movable_position.keys()
        if axis not in keys:
            return
        if axis == 'a':
            self._setStageA(movable_position)
        elif axis == 'z':
            self._setStageZ(movable_position)
        else:
            self._setStageXThenY(movable_position) ## not b

    # tilt alpha
    def _setStageA(self,position):
        axis = 'a'
        if abs(position[axis]) > self.stage_limit[axis]:
            raise ValueError('%s limit reached. Ignore' % axis)
        value = self.checkStagePosition(position)
        if not value:
                return
        rawvalue = value[axis]*57.3  # convert to degree for jLib
        mode = 'fine'
        #print('text:', axis, rawvalue,mode)
        self.jLib.setStagePosition(axis,rawvalue,mode)
        #self.confirmStagePosition(position,['a',])

    #Set Stage in z axis with backlash correction
    # always need backlash correction or it is off by
    # up to 2 um in display reading, even though the
    # getStagePosition gets back that it has reached the z.
    def _setStageZ(self, position):  ## to be finished
        axis = 'z'
        if abs(position[axis]) > self.stage_limit[axis]:
            raise ValueError('%s limit reached. Ignore' % axis)
        value_dict = position.copy()
        mode = 'fine'
        if self.correctedstage == True:
            prevalue = (value_dict[axis]-backlash_stage['z'])*1e3
            self.jLib.setStagePosition(axis,prevalue,mode)
        else:
            rawvalue = value_dict[axis]*1e3
            self.jLib.setStagePosition(axis,rawvalue,mode)
        #self.confirmStagePosition(position,['z',])

    # This gives 0.7 to 1.2 um reproducibility
    # set to backlash position in coarse mode
    # if no backlash correction, use coarse mode, too.
    def _setStageXThenY(self, position):
        value_dict = position.copy()
        for axis in ('x','y'):
            if axis not in value_dict.keys():
                continue
            if abs(position[axis]) > self.stage_limit[axis]:
                raise ValueError('%s limit reached. Ignore' % axis)
            mode = 'fine'
            if self.correctedstage == True:
                prevalue = (value_dict[axis] - backlash_stage[axis])*1e3
                self.jLib.setStagePosition(axis,prevalue,mode)
            else:
                rawvalue = value_dict[axis]*1e3  # in micrometer
                self.jLib.setStagePosition(axis,rawvalue,mode) 

    # default correct stage movement, copy from init
    def getCorrectedStagePosition(self):
        return self.correctedstage

    # set the stage move to back or not
    def setCorrectedStagePosition(self, value = 'True'):
        if Debug == True:
            print 'from JEM setCorrectedStagePosition'
        self.correctedstage = bool(value)
        return self.correctedstage

    ## Section of MDS modes, on, off, disabled or unknown
    def getLowDoseStates(self):
        return ['on', 'off', 'disabled', 'unknown']

    def getLowDose(self):
        return 'unknown'

    def setLowDose(self, lowDose ='off'):  ## low dose
        if lowDose == 'off':
            result = self.jLib.setMDSOff()
        elif lowDose == 'on':
            result = self.jLib.setSearchMode()
        else:
            raise ValueError

    def getLowDoseModes(self):
        return ['exposure', 'focus1', 'search', 'unknown', 'disabled']

    def getLowDoseMode(self):
        return 'unknown'

    def setLowDoseMode(self, mode):
        if Debug == True:
            print 'from JEM setLowDoseMode'
        setLowDose = self.jLib.setLowDoseMode(mode)

    # Section of defocus value
    # get defocus, Leginon requires meter unit (negative)
    def getDefocus(self):
        if Debug == True:
            print 'from jeol getDefocus'
        defocus = self.jLib.getDefocus()
        return float(defocus) # need to check scale and zero in jLib

    # set defocus value as objective lens current, OM (low mag) or OL (high mag)
    def setDefocus(self, defocus, relative = 'absolute'):                  
        if relative == 'absolute':
            ss = float(defocus)
        else:
            ss = float(defocus) + self.getDefocus()
        if self.jLib.setDefocus(ss) == True:
            if abs(self.getDefocus()-defocus) > max(abs(defocus/10),1.5e-7):
                # when defocus differences is large, the first
                # setDefocus does not reach the set value, repeat
                self.setDefocus(defocus,relative)
            return True
        else:
            return False

    # focus value is recorded as encoded objective current
    # unit is click
    def getFocus(self):    ## to be completed, OBJC & OBJF
        if Debug == True:
            print 'from JEM getFocus'
        focus = self.jLib.getObjectiveCurrent()
        return focus

    # set focus, unit is click
    def setFocus(self, value):  ## to be done
        if Debug == True:
            print 'from JEM setFocus'
        if self.jLib.setObjectiveCurrent(float(value)) ==  True:
            return True
        else:
            return False

    # reset eucentric focus, it works when the reset button is clicked
    def resetDefocus(self, value = 0):   ## to be done
        if Debug == True:
            print 'from JEM, resetDefocus'
        self.jLib.resetDefocus()  # setZeroDefocusOL or OM
        return True

    # not sure about this
    def getResetDefocus(self):
        if Debug == True:
            print 'from JEM getResetDefocus'
        self.jLib.resetDefocus() # the same as getZeroDefocusOL or OM
        return True

    # required by leginon
    def getObjectiveExcitation(self):
        if Debug == True:
            print 'from JEM getObjectiveExcitation'
        return NotImplementedError()

    # get beam tilt # Leginon unit? convertion in jLib
    def getBeamTilt(self):
        if Debug == True:
            print 'from JEM getBeamTilt'
        beamtilt = {'x': None, 'y': None}
        beamtilt = self.jLib.getBeamTilt() ## CLA2 ( DFCOND2)
        return beamtilt

    # set beam tilt # not needed??
    def setBeamTilt(self, vector, relative = 'absolute'):
            if Debug == True:
                    print 'from JEM setBeamTilt'
            for axis in ('x', 'y'):
                    if axis in vector:
                            if relative == 'absolute':
                                    self.jLib.setBeamTilt(axis, vector[axis])
                            else:
                                    now = {'x': None, 'y': None}
                                    now = self.getBeamTilt()
                                    target = {'x': None, 'y': None}
                                    target[axis] = int(now[axis]) + int(vector[axis])
                                    self.jLib.setBeamTilt(axis, target[axis])
            return True

    # get beam shift # DFCOND1 = para37
    def getBeamShift(self):
        if Debug == True:
            print 'from JEM getBeamShift'
        value = {'x': None, 'y': None}
        value = self.jLib.getBeamShift()
        return value

    # set beam shift # not needed??
    def setBeamShift(self, vector, relative = 'absolute'):
        if Debug == True:
            print 'from JEM setBeamShift'
        for axis in ('x', 'y'):
            if axis in vector:
                if relative == 'absolute':
                    self.jLib.setBeamShift(axis, vector[axis])
                else:
                    now = {'x': None, 'y': None}
                    now = self.getBeamShift()
                    target = {'x': None, 'y': None}
                    target[axis] = int(now[axis]) + int(vector[axis])
                    self.jLib.setBeamShift(axis, target[axis])
        return True

    # get image shift in meter, relative to neutral position
    def getImageShift(self):
        if Debug == True:
            print 'from JEM getImageShift'
        vector = {'x': None, 'y': None}
        vector = self.jLib.getImageShift()
        return vector

    # set image shift in meter
    def setImageShift(self, vector, relative = 'absolute'):
        if Debug == True:
            print 'from JEM setImageShift'
        for axis in ('x', 'y'):
            if axis in vector:
                if relative == 'absolute':
                    self.jLib.setImageShift(axis, vector[axis])
                else:
                    now = {'x': None, 'y': None}
                    now = self.getImageShift()
                    target = {'x': None, 'y': None}
                    target[axis] = int(now[axis]) + int(vector[axis])
                    self.jLib.setImageShift(axis, target[axis])
        return True

    # get stigmators for C-STIG (condenser), O-STIG (objective), and I-STIG (diffraction)
    def getStigmator(self):
        if Debug == True:
            print 'from JEM getStigmator'
        vector = {'condenser': {'x': None, 'y': None},
                  'objective': {'x': None, 'y': None},
                  'diffraction': {'x': None, 'y': None}}
        vector = self.jLib.getStigmator() #getDefValue (int def, int *valx, int *valy)
        return vector # unit conversion done in jLib

    # set stigmator Leginon unit, convert to JEM in jLib
    def setStigmator(self, vector, relative = 'absolute'):
        if Debug == True:
            print 'from jeol2010.py setStigmator'
            print '    vector is', vector, relative
        for key in ('condenser', 'objective', 'diffraction'):
            if key in vector:
                for axis in ('x','y'):
                    if axis in vector[key]:
                        if relative == 'absolute':
                            self.jLib.setStigmator(key, axis, vector[key][axis])
                        else:
                            now = {'condenser': {'x': None, 'y': None},
                                    'objective': {'x': None, 'y': None},
                                    'diffraction': {'x': None, 'y': None}}
                            now = self.getStigmator()
                            value = {'condenser': {'x': None, 'y': None},
                                    'objective': {'x': None, 'y': None},
                                    'diffraction': {'x': None, 'y': None}}
                            value[key][axis] = int(now[key][axis]) + int(vector[key][axis])
                            self.jLib.setStigmator(key, axis, value[key][axis])
        return True

    # DFGUN1 parm# 32
    def getGunShift(self):
        if Debug == True:
            print 'from JEM getGunShift'
        value = {'x': None, 'y': None}
        value = self.jLib.getGunShift()
        return value

    # not implimented, DFGUN1, para#32
    def setGunShift(self, vector, relative = 'absolute'):
        if Debug == True:
            print 'from JEM setGunShift'
        return NotImplementedError()

    # DFGUN2, para#33
    def getGunTilt(self):
        if Debug == True:
            print 'from JEM getGunTilt'
        return NotImplementedError()

    # not implimented
    def setGunTilt(self, vector, relative = 'absolute'):
        if Debug == True:
            print 'from JEM setGunTilt'
        return NotImplementedError()

    # not implimented
    def getDarkFieldMode(self):
     pass

    # not implimented
    def setDarkFieldMode(self, mode):
     pass

    # not sure, but return in meter
    def getRawImageShift(self):
        if Debug == True:
            print 'from JEM getRawImageShift'
        vector = {'x': None, 'y': None}
        vector = self.jLib.getImageShift()
        return vector

    # not implimented
    def setRawImageShift(self, vector, relative = 'absolute'):
        if Debug == True:
            print 'from JEM setRawImageShift'
        now = {'x': None, 'y': None}
        now = self.jLib.getImageShift()
        for axis in ('x', 'y'):
            if axis in vector:
                if relative == 'absolute':
                    self.jeol1230lib.setImageShift(axis, vector[axis])
                else:
                    target = {'x': None, 'y': None}
                    target[axis] = int(now[axis]) + int(vector[axis])
                    self.jLib.setImageShift(axis, target[axis])
        return True

    # not implimented
    def getVacuumStatus(self):
        if Debug == True:
            print "from JEM getVacuumStatus"
        return 'unknown'

    # not implimented
    def getColumnPressure(self):
        if Debug == True:
            print 'from JEM getColumnPressure'
        return 1.0

    # not implimented
    def getFilmStock(self):
        if Debug == True:
            print 'from JEM getFilmStock'
        return 1

    # not implimented
    def setFilmStock(self):
        if Debug == True:
            print 'from JEM setFilmStock'
        return NotImplementedError()

    # not implimented
    def getFilmExposureNumber(self):
        if Debug == True:
            print 'from JEM getFilmExposureNumber'
        return 1

    # not implimented
    def setFilmExposureNumber(self, value):
        if Debug == True:
            print 'from JEM setFilmExposureNumber'
        return NotImplementedError()

    # not implimented
    def getFilmExposureTime(self):
        if Debug == True:
            print 'from JEM getFilmExposureTime'
        return 1.0

    # not implimented
    def getFilmExposureTypes(self):
        if Debug == True:
            print 'from JEM getFilmExposureTypes'
        return ['manual', 'automatic','unknown']

    # not implimented
    def getFilmExposureType(self):
        if Debug == True:
            print 'from JEM getFilmExposureType'
        return 'unknown'

    # not implimented
    def setFilmExposureType(self, value):
        if Debug == True:
            print 'from JEM setFilmExposureType'
        return NotImplementedError()

    # not implimented
    def getFilmAutomaticExposureTime(self):
        if Debug == True:
            print 'from JEM getFilmAutomaticExposureTime'
        return 1.0

    # not implimented
    def getFilmManualExposureTime(self):
        if Debug == True:
            print 'from JEM getFilmManualExposureTime'
        return 1

    # not implimented
    def setFilmManualExposureTime(self, value):
        if Debug == True:
            print 'from JEM setFilmManualExposureTime'
        return NotImplementedError()

    # not implimented
    def getFilmUserCode(self):
        if Debug == True:
            print 'from JEM getFilmUserCode'
        return str('mhu')

    # not implimented
    def setFilmUserCode(self, value):
        if Debug == True:
            print 'from JEM setFilmUserCode'
        return NotImplementedError()

    # not implimented
    def getFilmDateTypes(self):
        if Debug == True:
            print 'from JEM getFilmDateTypes'
        return ['no date', 'DD-MM-YY', 'MM/DD/YY', 'YY.MM.DD', 'unknown']

    # not implimented
    def getFilmDateType(self):
        if Debug == True:
            print 'from JEM getFilmDateType'
        return 'unknown'

    # not implimented
    def setFilmDateType(self, value):
        if Debug == True:
            print 'from JEM setFilmDateType'
        return NotImplementedError()

    # not implimented
    def getFilmText(self):
        if Debug == True:
            print 'from JEM getFilmText'
        return str('Minghui Hu')

    # not implimented
    def setFilmText(self, value):
        if Debug == True:
            print 'from JEM setFilmText'
        return NotImplementedError()

    # not implimented
    def getShutter(self):
        if Debug == True:
            print 'from JEM getShutter'
        return 'unknown'

    # not implimented
    def setShutter(self, state):
        if Debug == True:
            print 'from JEM setShutter'
        return NotImplementedError()

    # not implimented
    def getShutterPositions(self):
        if Debug == True:
            print 'from JEM getShutterPositions'
        return ['open', 'closed','unknown']

    # not implimented
    def getExternalShutterStates(self):
        if Debug == True:
            print 'from JEM getExternalShutterStates'
        return ['connected', 'disconnected','unknown']

    # not implimented
    def getExternalShutter(self):
        if Debug == True:
            print 'from JEM getExternalShutter'
        return 'unknown'

    # not implimented
    def setExternalShutter(self, state):
        if Debug == True:
            print 'from JEM setExternalShutter'
        return NotImplementedError()

    # not implimented
    def normalizeLens(self, lens = 'all'):
        if Debug == True:
            print 'from JEM normalizeLens'
        return NotImplementedError()

    # not implimented
    def getScreenCurrent(self):
        if Debug == True:
            print 'from JEM getScreenCurrent'
        return 1.0

    # not implimented
    def getMainScreenPositions(self):
        if Debug == True:
            print 'from JEM getMainScreenPositions'
        return ['up', 'down', 'unknown']

    # not implimented
    def getMainScreenPosition(self):
        if Debug == True:
            print 'from JEM getManinScreenPostion'
        return 'up'

    # 0 = down; 1 = up
    def setMainScreenPosition(self, position):
        if Debug == True:
            print 'from JEM setMainScreenPosition'
        if position  == 'up':
            mode = int(1)
        else:
            mode = int(0)
        if self.jLib.setScreenPosition(mode) == True:
            return True
        else:
            return False

    # not implimented
    def getSmallScreenPositions(self):
        if Debug == True:
            print 'from JEM getSmallScreenPositions'
        return ['up', 'down', 'unknown']

    # not implimented
    def getSmallScreenPosition(self):
        if Debug == True:
            print 'from JEM getSmallScreenPosition'
        return 'unknown'

    # not implimented
    def getHolderStatus(self):
        if Debug == True:
            print 'from JEM getHolderStatus'
        return 'Inserted'

    # not implimented
    def getHolderTypes(self):
        if Debug == True:
            print 'from JEM getHolderTypes'
        return ['no holder', 'single tilt', 'cryo', 'unknown']

    # not implimented
    def getHolderType(self):
        if Debug == True:
            print 'from JEM getHolderType'
        return 'unknown'

    # not implimented
    def setHolderType(self, holdertype):
        if Debug == True:
            print 'from JEM setHolderType'
        return NotImplementedError()

    # not implimented
    def getStageStatus(self):
        if Debug == True:
            print 'from JEM getStageStatus'
        return 'unknown'

    # not implimented
    def getVacuumStatus(self):
        if Debug == True:
            print 'from JEM getVacuumStatus'
        return 'unknown'

    # not implimented
    def preFilmExposure(self, value):
        if Debug == True:
            print 'from JEM preFilmExposure'
        return NotImplementedError()

    # not implimented
    def postFilmExposure(self, value):
        if Debug == True:
            print 'from JEM postFilmExposure'
        return NotImplementedError()

    # not implimented
    def filmExposure(self, value):
        if Debug == True:
            print 'from JEM filmExposure'
        return NotImplementedError()

    # not implimented
    def getBeamBlank(self):
        return 'unknown'

    # not implimented
    def setBeamBlank(self, bb):
        return NotImplementedError()

    # not implimented
    def getDiffractionMode(self):
        if Debug == True:
            print 'from JEM getDiffractionMode'
        return NotImplementedError()

    # not implimented
    def setDiffractionMode(self, mode):
        if Debug == True:
            print 'from JEM setDiffractionMode'
        return NotImplementedError()

    # not implimented
    def runBufferCycle(self):
        if Debug == True:
            print 'from JEM runBufferCycle'
        return NotImplementedError()

    def getBeamBlankedDuringCameraExchange(self):
        # Keep it off because gun shutter is too slow.
        return False

    # active detector 0 - 5 , 4 is EDS 
    def getActiveDetector(self):
        if Debug == True:
            print('get active detector')
        det = self.jLib.getActiveDetector()
        return det


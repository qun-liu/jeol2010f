#
#jeol2010f ftcomm.dll is a wrapper by ctypes for use with pyscope package, required by jeol2010f.py
# Author: Qun Liu, qun.liu@gmail.com

import math
from ctypes import *
from ctypes.wintypes import *
#from pyscope import tem
from pyscope import moduleconfig
Debug = True
# define glocal varibles
COARSE_SCALE = 32
userhwnd = HANDLE(0)
hInst = HINSTANCE(0)
model = c_int()
msg = c_char * 512
#hInst = windll.kernel32.GetModuleHandleW(0)

#define TEM column condition structure for reading and writing
#dwSize : size of this structure
#parm  :  parameter number
#desc[10] : string description for parameter 
#stringVal : string value if any
#actMode : active mode of button on or off
#xVal: x value
#yVal : y value
#xBias : 
#yBias : 
#minVal  : 
#maxVal 
#xVolVal : voltage value for def & lens
#yVolVal : voltage value for def & lens
#incVal  : step value
class TEMCOLCOND(Structure):
    _fields_ = [("dwSize", DWORD),
                ("parm", c_int),
                ("desc", c_char * 10),
                ("stringVal", c_char * 10),
                ("actMode", c_int),
                ("xVal", c_float),
                ("yVal", c_float),
                ("xBias", c_float),
                ("yBias", c_float),
                ("minVal", c_float),
                ("maxVal", c_float),
                ("xVolVal", c_float),
                ("yVolVal", c_float),
                ("incVal", c_float)]

# callback function for eikAsyncCallback
# cond is the structure type of TEMCOLCOND
def localCallback(cond):
    cond = TEMCOLCOND()
    print("received message", cond.parm)

asyncType = CFUNCTYPE(c_void_p, POINTER(TEMCOLCOND))
callBack = asyncType(localCallback)

#  callback function for eikDebugMessage
def localDebug(msg):
    msg = c_char * 512
    print("localDebug message", msg)
debugType = CFUNCTYPE(c_void_p, c_char_p)
debug = debugType(localDebug)

#define initilization structure for establish the communication between client with FasTEM server
# dwSize : size of this structure
# iID : equipment ID (EQP_CODE_GATAN)
# iPortNo : TCP port, usually 5001
# szHostAddr[40] : hostname or ip address
# asynComm : Flag to receive asynchronus callbacks
# debugInfo: Flag to receive debug information
# userHwnd : calling applications main window handle
# (*eikAsyncCallback)(TEMCOLCOND * cond): pointer for async callback function
# (*eikDebugMessage)(char *msg) : pointer for debug callback function
# paraRegistry(REG_SIZE): registry for parms of interest (set 0 to -1 for all)
# rTimer: reconnect time in second (0 = no reconnect)
class jeolCommInfo(Structure):
    _fields_ = [("dwSize", DWORD),
                ("iID", c_int),
                ("iPortNo", c_int),
                ("szHostAddr", c_char * 40),
                ("asyncComm", c_bool),
                ("debugInfo", c_bool),
                ("userHwnd", HWND),
                ("eikAsyncCallback", asyncType),
                ("eikDebugMessage",  debugType),
                ("parmRegistry", c_int * 88),
                ("versionNum", c_float),
                ("compatbilityLevel", c_int),
                ("rTimer", c_int), ("userLevel", c_int)]   

class stageType(Structure):
     _fields_ = [("x", c_float),
                ("y", c_float),
                ("z", c_float),
                ("a", c_float),
                ("b", c_float)]

#class eikAsyncCallback(Structure):
#    _fileds_= [("cond", TEMCOLCOND)]

# define stage structure
class jeolStageControlType:
    JEOL_STAGE_AXIS_NONE = 0
    #JEOL_STAGE_AXIS_STOP = 
    #JEOL_STAGE_AXIS_JOG =

class jeolStageClientAxis:
    JEOL_STAGE_AXIS_X = 0
    JEOL_STAGE_AXIS_Y = 1
    JEOL_STAGE_AXIS_Z = 2
    JEOL_STAGE_AXIS_XT = 3
    JEOL_STAGE_AXIS_YT = 4
    JEOL_STAGE_AXIS_ALL = 5
    JEOL_STAGE_CLIENT_AXIS = 6

# define function for the main windows procedure WNDPROC
def PyWndProcedure(hWnd, Msg, wParam, lParam):
    if Msg == WM_PAINT:
        ps = PAINTSTRUCT()
        rect = RECT()
        test = cdll.ftcomm.eikGetAccelVoltage
        if not test:
            print("failed to call eikGetAccelVoltage")
        test.argtypes = [c_void_p]
        test.restype = c_float
        value = c_float()
        magg = test(byref(value))
        print("...:", magg)
        hdc = windll.user32.BeginPaint(hWnd,byref(ps))
        windll.user32.GetClientRect(hWnd,byref(rect))
        windll.user32.DrawTextA(hdc, "hello FasTEM", -1, byref(rect), DT_SINGLELINE | DT_CENTER | DT_VCENTER)
        windll.user32.EndPaint(hWnd,byref(ps))
        return 0
    elif Msg == WM_DESTROY:
        windll.user32.PostQuitMessage(0)
    else:
        return windll.user32.DefWindowProcW(hWnd, Msg, wParam, lParam)
    return 0

# jeolLib class for JEM2010F
class jeolLib(object):
    name = ' JEOL 2010F python library to wrapper ftcomm.dll'
    def __init__(self):
        self.ftc = cdll.ftcomm # load ftcomm.dll library from the directory, not .dll necessary.
        self.equipmentAvailable() ## initilization
        self.lowMag = [50, 80, 100, 150, 200, 250, 300, 400, 500, 600, 800, 1000]
        self.highMag = [ 1200, 1500, 2000, 2500, 3000, 4000, 5000, 6000,  8000, 10000,
                         12000, 15000, 20000, 25000, 30000, 40000, 50000, 60000, 80000,
                         100000, 120000, 150000, 200000, 250000, 300000, 400000, 500000,
                         600000, 800000, 1000000]
        self.magnification = self.lowMag + self.highMag
        self.scale = 32767
        self.zero = 32768
        self.coarse_scale = 1
        self.focus_low_scale = 6.4e-9
        self.focus_high_scale = 5.9e-9
        self.CL3_table = {'100':65535, '800':41237, '8000':37004, '60000':38117} #beamsize
        self.zero_defocus_ol = {'50000':1180760, '40000': 1180760,
                                '5000': 1158440, '3000': 1158440,
                                '2500': 1158440, '2000':1158440}
        self.zero_defocus_om = {'100': 40060,'120': 40079,'150':542095,
                                '200': 42325,'250': 42325,'500':42325}        

    def setJeolconfigs():
        jelconfigs = moduleconfig.getConfigured('jeol2.cfg')
        print(jelconfigs)
        
    def toJeol(val):
        return self.zero + int(round(self.scale * val))

    def toLeginon(val):
        return float(val - self.zero)/self.scale

    def equipmentAvailable(self):           
        # define class of ftcomminfo from jeolCommInfo prototype
        ftcomminfo = jeolCommInfo()
        #ftcomminfo.restype = c_void_p  (not a function, no need to specify type)
        #memset(ftcomminfo, 0, sizeof(jeolCommInfo))
        ftcomminfo.dwSize = sizeof(jeolCommInfo)
        ftcomminfo.iID = 0x55
        ftcomminfo.iPortNo = 5001
        ftcomminfo.asyncComm = False
        ftcomminfo.debugInfo = False
        ftcomminfo.userHwnd = userhwnd
        ftcomminfo.szHostAddr = "130.199.120.112"
        ftcomminfo.rTimer = 10
        ftcomminfo.eikAsyncCallback = callBack
        ftcomminfo.eikDebugMessage = debug
        # fill up parmRestry[REG_SIZE] with char "0" for the size of MAXTEMPARAM
        #memset(ftcomminfo.parmRegistry,0,88)
        ftcomminfo.parmRegistry[0] = -1

        err=self.ftc.eikInitFasTEMComm(hInst, byref(ftcomminfo))
        if err == 0 :
            print("failed to initialize Jeol FasTEM connection")
            exit(0)
        else:
            print("connected, JEOL model:", ftcomminfo.versionNum, ftcomminfo.dwSize)
        #error.restype = c_int
        #error.argtypes = [HINSTANCE, c_void_p]
        #print(byref(ftcomminfo))
        #error = cdll.ftcomm.eikInitFasTEMComm(hInst, byref(ftcomminfo))
        #print(byref(ftcomminfo))
        #print(error)
        #print("test:", ftcomminfo.versionNum)

    def identifyInstrument(self):
        model = c_int()
        if not self.ftc.eikIdentifyInstrument(byref(model)):
            print("could not get the model information")
        print ("model number is: ", model)
        return model
    
    def getAccelVoltage(self):
        accVal = c_float()
        err = self.ftc.eikGetAccelVoltage(byref(accVal))
        if err == 0:
            print("count not get the accelerate voltage")
        else:
            return float(accVal.value)
        
    def getIntensity(self):
        pass

    def setIntensity(self, val):
        pass

    #get ActiveMagMode for high tension
    def getActiveMagMode(self):
        if Debug == True:
            print 'from jLib getActiveMagMode'
        mode = c_int()
        err = self.ftc.eikGetActiveMagMode(byref(mode))
        if err == 0:
            print("could not getActiveMagMode")
        return mode.value
                
    #get Magvalue
    def getMagValue(self):
        if Debug == True:
            print ' from getMagValue'
        index = c_int()
        val = create_string_buffer(5) # create a pointer to an empty python data buffer
        activeMode = self.getActiveMagMode()
        err = self.ftc.eikGetMagValue(c_int(activeMode),byref(index), val)
        if err == 0:
            print("could not getMagValue")
        magValue = val.value
        length = len(magValue)
        if magValue[0] == 'X':
            start = 2
        else:
            start = 1
        if magValue[length-1:] == 'K':
            end = length - 1
            scale = 1000
        else:
            scale = 1
        magn = int(magValue[start:end])*scale
        #val2return = [mode, index, val]
        #print('val:', magValue)
        return magn

    def setMagValue(self, setMagn):
        magRange = 42
        for i in range(0, magRange):
            if int(setMagn) <= int(self.magnification[i]):
                break
        if i > magRange:
            print 'Magnification out of range'
            return False       
        if i > 11:
            activeMode = 0
            i = i - 12
        else:
            activeMode = 1
        #err = 1    
        err = self.ftc.eikSetMagValue(c_int(activeMode),c_int(i),c_bool(False),c_bool(True))
        #print('set mag:', activeMode, i)
        if err == 0:
            print 'set magnification failed'
        else:
            if Debug == True:
                print 'set magnification succeed'
            return True
        
    def getSpotSize(self):
        spot = c_int()
        err = self.ftc.eikGetSpotSize(byref(spot))
        if err == 0:
            print('could not get spotsize')
        return spot.value

    def setSpotSize(self,spot):
        if spot > 0  and spot < 6:
            #err = 1
            err = self.ftc.eikSetSpotSize(c_int(spot),c_bool(True))
            if err == 0:
                print 'set spotsize failed'
            else:
                if Debug == True:
                    print('set spotsize succeed, spotsize:', spot)
        else:
            print('spotsize out of range')   
     
    def getGonioRead(self):
        #pos = stageType()
        pos = {'x':None, 'y':None,'z':None, 'a':None, 'b':None}
        x = c_float()
        y = c_float()
        z = c_float()
        a = c_float()
        b = c_float()
        err = self.ftc.eikGonioRead(byref(x),byref(y),byref(z),byref(a),byref(b))
        if err == 0:
            print("count not get the stage values")
        pos = {'x' : x.value,
            'y' : y.value,
            'z' : z.value,
            'a' : a.value,
            'b' : b.value}
        return pos
                  
    # Move a single axis jeolSetStageMoveAxis  NOTE from meter to millimeter
    def setStagePosition(self, byAxis, pos, byMode):
        if byAxis == 'x':
            axis = 0
        elif byAxis == 'y':
            axis = 1
        elif byAxis == 'z':
            axis =2
        elif byAxis == 'a':
            axis = 3
        else:
            axis =4                
        if byMode == 'fine':
            mode = 3  # absolute move type
        elif byMode == 'coarse':
            mode = 9
        elif byMode == 'relaitve':
            mode = 5 # relaitve move type
        else:
            mode = 10 # velocity move, mag related
        err = 1
        #err = self.ftc.jeolSetStageMoveAxis(c_int(axis),c_float(pos),c_int(mode))
        if err == 0:
            print('count not move the stage axis')           
        else:
            if Debug == True:
                print('move stage axis succeed', axis, pos, mode)       
        
    # end low dose mode
    def setMDSOff(self):
        err = self.ftc.eikSetMDSOff(c_bool(True))
        if err == 0:
            print('could not set MDS off')
        else:
            if Debug == True:
                print('from jeollib setmdsoff: MDSOff is success')
    def setSearchMode(self):
        err = self.ftc.eikSetMDSSearchMode(c_int(1), c_bool(True))
        return True
        
    def setLowDoseMode(self, mode):
        if mode == 'exposure':
            result = self.ftc.eikSetMDSPhotoMode(c_int(3), c_bool(True))
        elif mode == 'focus1':
            result = self.ftc.eikSetMDSPFocusMode(c_int(2), c_bool(True))
        elif mode == 'search':
            result = self.ftc.eikSetMDSSearchMode(c_int(1), c_bool(True))
        elif mode == 'disabled':
            result = self.setMDSOff()
        else:
            raise ValueError       
                         
    # get and set focus and defocus
    def getObjectiveCurrent(self):
        mode = self.getActiveMagMode()
        lcom = c_int()
        lcobjc = c_int()
        lcobjfzc = c_int()
        lcobjf = c_int()
        lcofzm = c_int()
        lcobjfzf = c_int()
        if mode == 1: # low mag
            lcom_raw = self.ftc.eikGetLensValue(18, byref(lcom))
            current = float(lcom.value + 32768) * self.focus_low_scale
            print('om:', lcom.value + 32768)
        elif mode == 0: # high mag
            lcobjc_raw = self.ftc.eikGetLensValue(17, byref(lcobjc))
            lcobjfzc_raw = self.ftc.eikGetLensValue(26, byref(lcobjfzc))
            lcobjf_raw = self.ftc.eikGetLensValue(16, byref(lcobjf))
            lcofzm_raw = self.ftc.eikGetLensValue(31, byref(lcofzm))
            lcobjfzf_raw = self.ftc.eikGetLensValue(25, byref(lcobjfzf))
            objc_raw = int(lcobjc.value) + 32768 + int(lcobjfzc.value)
            objf_raw = int(lcobjf.value) + 32768 + int(lcofzm.value) + int(lcobjfzf.value)
            current = float(objc_raw * COARSE_SCALE + objf_raw) * self.focus_high_scale
            print('objc:', objc_raw, 'objf:', objf_raw)
        else:
            print('The mode is out of range')
        if Debug == True:
                print('from jLib getObjectiveCurrent')

        return current

    #set focus, use absolute, between -32768 and 32768
    def setObjectiveCurrent(self, current):
        if Debug == True:
            print('from jLib setDefocus')
        mode = self.getActiveMagMode()        
        c_current = self.getObjectiveCurrent()
        #diff_current = c_current - current
        err == 1
        if mode == 1:
            current_raw = int(round(current/self.focus_low_scale)) - 32768
            #err = self.ftc.eikSetLensValue(18, c_int(current_raw), c_bool(True), c_bool(True))
        elif mode == 0:
            current_raw = int(round(current/self.focus_high_scale)) - 32768
            #err = self.ftc.eikAdjustObjLens(c_int(current_raw), c_bool(True), c_bool(True))
        if err == 0:
            print('count not set defocus')           
        else:
            if Debug == True:
                print 'set defocus succeed' 

    def getZeroDefocusOM(): # need to be calibreated.
        mag = self.getMagnification()
        zero_defocus_om = None
        if mag in self.zero_defocus_om.keys():
            zero_defocus_om = self.zero_defocus_om[mag]
        elif self.zero_defocus_om.keys():
            zero_defocus_om = self.zero_defocus_om[max(self.zero_defocus_om.keys())]
        return zero_defocus_om
    
    def getZeroDefocusOL(): # need to be calibreated.
        mag = self.getMagnification()
        zero_defocus_ol = None
        if mag in self.zero_defocus_ol.keys():
            zero_defocus_ol = self.zero_defocus_ol[mag]
        elif self.zero_defocus_ol.keys():
            zero_defocus_ol = self.zero_defocus_ol[max(self.zero_defocus_ol.keys())]
        return zero_defocus_ol

    def getDefocus(self):
        if Debug == True:
            print('from jLib getDefocus')
        focus = self.getObjectiveCurrent()
        mode = self.getActiveMagMode()
        if mode == 0:
            defocus = focus - self.getZeroDefocusOL() * self.focus_high_scale
        elif mode ==1:
            defocus = focus - self.getZeroDefocusOM() * self.focus_low_scale
        return float(defocus)

    # setDefocus using absolute value, but will convert it to relative for accuracy. 
    def setDefocus(self, defocus):
        if Debug == True:
            print('from jLib setDefocus')
        mode = self.jLib.getActiveMagMode()
        if defocus == 0.0:
            if mode  == 1:
                self.setObjectiveCurrent(self.getZeroDefocusOM()* self.focus_low_scale)
            elif mode == 0:
                self.setObjectiveCurrent(self.getZeroDefocusOL()* self.focus_high_scale)
            else:
                raise RuntimeError('Defocus not implemented in this mode %d' % mode)
            return True
        else:
            if mode == 1:
                defocus_raw = self.getZeroDefocusOM() + int(round(defocus/self.focus_low_scale))
            elif mode == 0:
                defocus_raw = self.getZeroDefocusOL() + int(round(defocus/self.focus_high_scale))
                #err = self.ftc.eikSetLensValue(18, c_int(value), c_bool(FALSE), c_bool(TRUE))
            else:
                print('mode %d is not supported' % mode )
            self.setObjectiveCurrent(defocus_raw)
            return True              
     
    def resetDefocus(self):
        mode = self.jLib.getActiveMagMode()
        if mode == 1:
            self.setZeroDefocusOM()
        elif mode == 0:
            self.setZeroDefocusOL()
        else:
            raise RuntimeError('defocus not implemented')
                       
    # test for lens value
    def getCondLens1(self):
        val = c_int()
        condLens1 = self.ftc.eikGetLensValue(12, byref(val))
        if Debug == True:
            print('condLens1:', val.value + 32768)
        return float((val.value + ZERO)/SCALE)
    
    def getGunShift(self):  #DFGUN1 parm# 32
        gs = {'x': None, 'y': None}
        gs_x = c_int()
        gs_y = c_int()
        err = self.ftc.eikGetDefValue(32, byref(gs_x), byref(gs_y))
        if err == 0:
            print('could not get beamshift')
        gs = {'x': hex(gs_x.value + 32768),
              'y': hex(gs_y.value + 32768)}
        return gs
    
    def getBeamShift(self): #DFCOND1 = para37
        gs = self.getGunShift()
        bs = {'x': None, 'y': None}
        bs_x = c_int()
        bs_y = c_int()
        err = self.ftc.eikGetDefValue(37, byref(bs_x), byref(bs_y))
        if err == 0:
            print('could not get beamshift')
        bs = {'x': bs_x.value + int(gs['x']),
              'y': bs_y.value + int(gs['y'])}
        return bs
  
    def getBeamTilt(self):  #DFCOND2 = para38
        bt = {'x': None, 'y': None}
        bt_x = c_int()
        bt_y = c_int()
        err = self.ftc.eikGetDefValue(38, byref(bt_x), byref(bt_y))
        if err == 0:
            print('could not get beamshift')
        bt = {'x': bt_x.value, 'y': bt_y.value}
        return bt

    def getImageShift(self):  #DFIMAGE1 = para40
        ish = {'x': None, 'y': None}
        ish_x = c_int()
        ish_y = c_int()
        err = self.ftc.eikGetDefValue(40, byref(ish_x), byref(ish_y))
        if err == 0:
            print('could not get beamshift')
        ish = {'x': ish_x.value, 'y': ish_y.value}
        return ish

    def setImaeShift(self, axis, value):
        pass
        return True

    #get stigmators for C-STIG (36, condenser), O-STIG (39, objective), and I-STIG (42, diffraction)
    def getStigmator(self):
        stigm = {'condenser': {'x':None, 'y':None},
                 'objective': {'x':None, 'y': None},
                 'diffraction': {'x': None, 'y': None}}
        stigm_c_x = c_int()
        stigm_c_y = c_int()
        stigm_o_x = c_int()
        stigm_o_y = c_int()
        stigm_d_x = c_int()
        stigm_d_y = c_int()
        stigm_c = self.ftc.eikGetDefValue(36, byref(stigm_c_x), byref(stigm_c_y))
        stigm_o = self.ftc.eikGetDefValue(39, byref(stigm_o_x), byref(stigm_o_y))
        stigm_d = self.ftc.eikGetDefValue(42, byref(stigm_d_x), byref(stigm_d_y))
        stigm = {'condenser': {'x':stigm_c_x.value, 'y':stigm_c_y.value},
                 'objective': {'x':stigm_o_x.value, 'y': stigm_o_y.value},
                 'diffraction': {'x': stigm_d_x.value, 'y': stigm_d_y.value}}
        return stigm
    
    def getAlpha(self):
        alpha = c_int()
        err = self.ftc.eikGetAlpha(byref(alpha))
        if err == 0:
            print('could not get alpha')
        return alpha.value

    def getActiveDetector(self):
        det = c_int()
        err = self.ftc.eikGetActiveDetector(byref(det))
        if err == 0:
            print('could not get active dtector')
        return int(det.value)
           
    def __del__(self):
        if Debug == True:
            print('Disconnecting from the FasTEM server ....')
        if not self.ftc.eikTermFasTEMComm(hInst):
            print('failed to disconnect')
            exit(0)
        else:
            print('disconnected.')
    
## for test    
#if __name__ == "__main__":
#    print "Remote control of Jeol 2010f via python"
#jLib=jeolLib()
#jLib.identifyInstrument()
#voltage= jLib.getAccelVoltage()
#print("Accelrate Voltage:", voltage)
#jLib.__del__()

    


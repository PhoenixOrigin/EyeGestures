import math
import numpy as np

from screeninfo import get_monitors
from eyeGestures.utils import Buffor

class ScreenFinder:
    
    def __init__(self):
        pass

class ScreenHist:

    def __init__(self,width,height,step):
        self.inc_step = 10

        self.step = step
        self.width = width
        self.height = height

        bars_x = int(self.width/self.step)
        bars_y = int(self.height/self.step)

        self.axis_x = np.zeros((bars_x))
        self.axis_y = np.zeros((bars_y))

    def addPoint(self,point):

        self.axis_x[self.axis_x != 0] -= 1
        self.axis_y[self.axis_y != 0] -= 1

        (x,y) = point
        pos_x = int(x/self.step)
        pos_y = int(y/self.step)
        
        self.axis_x[pos_x] += self.inc_step
        self.axis_y[pos_y] += self.inc_step

        self.min_x = np.where(self.axis_x > self.inc_step*3)[0][0] * self.step
        self.max_x = np.where(self.axis_x > self.inc_step*3)[0][-1]* self.step
        self.min_y = np.where(self.axis_y > self.inc_step*3)[0][0] * self.step
        self.max_y = np.where(self.axis_y > self.inc_step*3)[0][-1]* self.step

        if not self.min_x is np.NAN:
            self.min_x = int(self.min_x)
        if not self.max_x is np.NAN:
            self.max_x = int(self.max_x)
        if not self.min_y is np.NAN:
            self.min_y = int(self.min_y)
        if not self.max_y is np.NAN:
            self.max_y = int(self.max_y)

    def getLims(self):
        return (self.min_x,self.max_x,self.min_y,self.max_y)

    def getCenter(self):
        return (
            int((self.max_x - self.min_x)/2 + self.min_x),
            int((self.max_y - self.min_y)/2 + self.min_y))

    def getHist(self):
        return (self.axis_x/self.inc_step,self.axis_y/self.inc_step)


class Screen:

    def __init__(self, screen_width = 0, screen_height = 0 , x = 0, y = 0, width = 0, height = 0):
        self.old_scale_w = 0
        self.old_scale_h = 0

        self.screen_buffor = Buffor(15)
        self.setWH(width,height)
        self.setCenter(x,y)

        self.screen_width  = screen_width
        self.screen_height = screen_height
        pass

    def getCenter(self):
        return (self.x,self.y)

    def setWH(self, width, height):
        self.width = width
        self.height = height

    def getWH(self):
        return (self.width,self.height)

    def setCenter(self, x, y):
        self.x = x - int(self.width/2)
        self.y = y - int(self.height/2)

    def scale(self,scale_w,scale_h):
        if self.old_scale_w == 0 or self.old_scale_h == 0:
            self.old_scale_w = scale_w
            self.old_scale_h = scale_h
        else:
            if abs(self.old_scale_w - self.width) > 5: 
                width  = int(self.width/self.old_scale_w * scale_w)
                height = int(self.height/self.old_scale_h * scale_h)
                self.old_scale_w = scale_w
                self.old_scale_h = scale_h
                self.setWH(width,height)

    def convertToScreen(self, point):
        x = (point[0] - self.x) * ((point[0] - self.x) > 0)
        x = int((x/self.width) * self.screen_width)

        y = (point[1] - self.y) * ((point[1] - self.y) > 0)
        y = int((y/self.height) * self.screen_height)
        self.screen_buffor.add((x,y))

        return self.screen_buffor.getAvg()

    def getRect(self):
        return (self.x,self.y,self.width,self.height)

class ScreenManager:

    def __init__(self,eye_screen_w,eye_screen_h):

        self.monitor = list(filter(lambda monitor: monitor.is_primary == True ,get_monitors()))[0]

        self.eye_screen_w = eye_screen_w
        self.eye_screen_h = eye_screen_h
        self.step         = 10 
        self.eyeScreen    = Screen(1920,1080,190,60,100,80)
        self.eyeHist      = ScreenHist(self.eye_screen_w,self.eye_screen_h,self.step)
        self.pointsBuffor = Buffor(50)
        pass

    def process(self, eye ,point : (int,int)):
        assert(np.array(point).shape[0] == 2)

        self.pointsBuffor.add(point)
        self.eyeHist.addPoint(point)
        (x,y) = self.eyeHist.getCenter()

        self.eyeScreen.setCenter(x,y)
        scale_w = (eye.width  + eye.width)/2
        scale_h = (eye.height + eye.height)/2
        self.eyeScreen.scale(scale_w, scale_w)

        min_x,max_x,min_y,max_y = self.eyeHist.getLims()

        # experimetal
        width  = self.eyeScreen.width
        height = self.eyeScreen.height
        if (max_x - min_x) - self.eyeScreen.width > 0.1:
            width = (max_x - min_x)
        if (max_y - min_y) - self.eyeScreen.height > 0.1:
            height = (max_y - min_y)

        self.eyeScreen.setWH(width,height)
        # ====================================

        p = self.eyeScreen.convertToScreen(point)
        p += (self.monitor.x,self.monitor.y)
        return p

    def getScreen(self):
        return self.eyeScreen

    def getHist(self):
        return self.eyeHist
    
    def getPointsHistory(self):
        return self.pointsBuffor.getBuffor()
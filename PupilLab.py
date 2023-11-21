import cv2
import sys
import math
import random
import numpy as np
from PySide2.QtWidgets import QApplication, QWidget, QMainWindow, QLabel, QVBoxLayout
from PySide2.QtGui import QPainter, QColor, QKeyEvent, QPainterPath, QPen, QImage, QPixmap
from PySide2.QtCore import Qt, QTimer, QPointF, QObject, QThread
import keyboard

from lab.pupillab import Worker
from lab.components import Screen, ScreenHist

from eyeGestures.utils import VideoCapture, Buffor
from eyeGestures.eyegestures import EyeGestures
from eyeGestures.processing import EyeProcessor
from screeninfo import get_monitors
from appUtils.dot import DotWidget
from pynput import keyboard


def rotate(point,face):

    (x,y) = point
    r = math.dist(point,(0,0))
    angle = math.atan2(y,x) * 180/np.pi
    tiltAngle = face.getNose().getHeadTilt()
    if abs(tiltAngle) < 30:
        new_point = point
    else:
        new_angle = angle + tiltAngle
        new_angle = np.pi * new_angle / 180 

        new_point = (
            int(r*math.cos(new_angle)), # x
            int(r*math.sin(new_angle))  # y
        )

    return new_point

def showEyes(image,face):

    if face is not None:
        l_eye = face.getLeftEye()
        r_eye = face.getRightEye()

        cv2.circle(image,l_eye.getPupil(),2,(0,0,255),1)
        for point in l_eye.getLandmarks():
            cv2.circle(image,point,2,(0,255,0),1)

        cv2.circle(image,r_eye.getPupil(),2,(0,0,255),1)
        for point in r_eye.getLandmarks():
            cv2.circle(image,point,2,(0,255,0),1)

        for point in face.getLandmarks():
            cv2.circle(image,point,2,(255,0,0),1)            

class Lab:

    def __init__(self):
        
        monitors = get_monitors()
        (width,height) = (int(monitors[0].width),int(monitors[0].height))
        self.gestures = EyeGestures(height,width)
        # self.noseTilt.show()

        self.eye_screen_w = 500
        self.eye_screen_h = 500
        self.eyeScreen    = Screen(1920,1080,190,60,100,80)
        self.step = 10 
        self.eyeHist      = ScreenHist(self.eye_screen_w,self.eye_screen_h,self.step)


        self.eyeProcessorLeft  = EyeProcessor(self.eye_screen_w,self.eye_screen_h)
        self.eyeProcessorRight = EyeProcessor(self.eye_screen_w,self.eye_screen_h)
        
        self.red_dot_widget = DotWidget(diameter=100,color = (255,120,0))
        self.red_dot_widget.show()

        self.blue_dot_widget = DotWidget(diameter=100,color = (0,120,255))
        self.blue_dot_widget.show()

        self.cap = VideoCapture('rtsp://192.168.18.30:8080/h264.sdp')        
        self.__run = True

        self.listener = keyboard.Listener(on_press=self.on_quit)
        self.listener.start()

        self.pointsBufforLeft  = Buffor(50)
        self.pointsBufforRight = Buffor(50)

        self.eyeImageBuffer_L = Buffor(5)
        self.eyeImageBuffer_R = Buffor(5)

        self.worker = Worker(self.run)

    def on_quit(self,key):
        if not hasattr(key,'char'):
            return

        if key.char == 'q':
            # Stop listening to the keyboard input and close the application
            self.__run = False
            # self.listener.join()
            # self.close()

    def __display_hist(self,whiteboardPupil,point):
        self.eyeHist.addPoint(point[0])
        x_axis,y_axis = self.eyeHist.getHist()

        bars = int(self.eye_screen_w / self.step)
        for n in range(bars):
            x_val = min(x_axis[n],255)
            y_val = min(y_axis[n],255)
            for m in range(bars):
                y_val = min(y_axis[m],255)
                cv2.rectangle(whiteboardPupil,(self.step*n,self.step*m),(self.step*n + self.step,self.step*m + self.step),(255,255-x_val,255-y_val,50),1)

    def __display_screen(self,whiteboardPupil, l_eye, r_eye):

        (x,y) = self.eyeHist.getCenter()
        self.eyeScreen.setCenter(x,y)
        scale_w = (l_eye.width + r_eye.width)/2
        scale_h = (l_eye.height + r_eye.height)/2
        print(scale_w, scale_h)
        self.eyeScreen.scale(scale_w, scale_h)

        (x_min,x_max,y_min,y_max) = self.eyeHist.getLims()
        (x,y) = (x_min, y_min)
        (w,h) = (x_max - x_min), (y_max - y_min)
        cv2.rectangle(whiteboardPupil,(x,y),(x + w,y + h),(0,0,255),2)

        (x,y) = self.eyeScreen.getCenter()
        (w,h) = self.eyeScreen.getWH()  
        cv2.rectangle(whiteboardPupil,(x,y),(x + w,y + h),(255,0,0),2)
    

    def __display_eyeTracker(self,whiteboardPupil,pointLeft,pointRight):

        for _point,_closeness in self.pointsBufforLeft.getBuffor():
            p = (_point[0],_point[1])
            cv2.circle(whiteboardPupil,p,3,(int(_closeness),0,255-int(_closeness)),-1)

        for _point,_closeness in self.pointsBufforRight.getBuffor():
            p = (_point[0],_point[1])
            cv2.circle(whiteboardPupil,p,3,(int(_closeness),255-int(_closeness),0),-1)

        p = (pointLeft[0][0],pointLeft[0][1])
        cv2.circle(whiteboardPupil,p,5,(int(pointLeft[1]),0,255 - int(pointLeft[1])),-1)            
        screen_point = self.eyeScreen.convertToScreen(p)     
        (w,h) = (self.red_dot_widget.size().width(),self.red_dot_widget.size().height()) 
        self.red_dot_widget.move(screen_point[0]-int(w/2),screen_point[1]-int(h/2))

        p = (pointRight[0][0],pointRight[0][1])
        cv2.circle(whiteboardPupil,p,5,(int(pointRight[1]),0,255 - int(pointRight[1])),-1)            
        screen_point = self.eyeScreen.convertToScreen(p)     
        (w,h) = (self.blue_dot_widget.size().width(),self.blue_dot_widget.size().height()) 
        self.blue_dot_widget.move(screen_point[0]-int(w/2),screen_point[1]-int(h/2))

    def __display_gaze_intersection(self,display,l_eye,r_eye):
        l_pupil = l_eye.getPupil()
        l_gaze  = l_eye.getGaze()
        
        r_pupil = r_eye.getPupil()        
        r_gaze  = r_eye.getGaze()

        l_end = l_gaze + l_pupil
        r_end = r_gaze + r_pupil

        l_m = (l_end[1] - l_pupil[1])/(l_end[0] - l_pupil[0])
        r_m = (r_end[1] - r_pupil[1])/(r_end[0] - r_pupil[0])

        l_b = l_end[1] - l_m * l_end[0]
        r_b = r_end[1] - r_m * r_end[0]

        i_x = (r_b - l_b)/(l_m - r_m)
        i_y = r_m * i_x + r_b

        print(f"(i_x,i_y): {(i_x,i_y)}, l_pupil: {l_pupil} , r_pupil: {r_pupil}")
        cv2.circle(display,np.array((i_x,i_y), dtype = np.uint32), 2, (0,0,255),-1)


    def __display_extended_gaze(self,display,eye,multiplier):
        pupil = eye.getPupil()
        gaze = eye.getGaze()
        
        start_point = (int(pupil[0]),int(pupil[1]))
        (x,y) = (int(gaze[0]),int(gaze[1]))

        angle = math.atan2(y,x) * 180 / np.pi
        r = math.dist(gaze,(0,0)) * multiplier
        
        new_point = (
            int(r*math.cos(np.pi * angle / 180)) + int(pupil[0]), # x
            int(r*math.sin(np.pi * angle / 180)) + int(pupil[1])  # y
        )

        print(start_point,new_point)
        cv2.line(display,start_point,new_point,(255,255,0),1)

    def __display_gaze(self,display,eye):
        pupil = eye.getPupil()
        gaze = eye.getGaze()
        
        start_point = (int(pupil[0]),int(pupil[1]))
        end_point = (int(pupil[0] + gaze[0]),int(pupil[1] + gaze[1]))
        cv2.line(display,start_point,end_point,(255,255,0),1)


    def __display_left_eye(self,frame):
        frame = frame
        face = self.gestures.getFeatures(frame)
    
        if not face is None:
            whiteboardPupil = np.full((self.eye_screen_h,self.eye_screen_w,3),255.0,dtype = np.uint8)
            
            # faceBox = face.getBoundingBox()
            # (x,y,w,h) = (faceBox[0][0],faceBox[0][1],faceBox[1][0],faceBox[1][1])
            # print(f"facebox shape: {faceBox.shape}")

            l_eye = face.getLeftEye()
            r_eye = face.getRightEye()
            self.eyeProcessorLeft.append(l_eye.getPupil(),l_eye.getLandmarks())
            self.eyeProcessorRight.append(r_eye.getPupil(),r_eye.getLandmarks())

            point = self.eyeProcessorLeft.getAvgPupil(self.eye_screen_w,self.eye_screen_h)
            pointLeft = (point[0],point[1])

            point = self.eyeProcessorRight.getAvgPupil(self.eye_screen_w,self.eye_screen_h)
            pointRight = (point[0],point[1])  
            
            self.pointsBufforLeft.add(pointLeft)
            self.pointsBufforRight.add(pointRight)

            self.__display_hist(whiteboardPupil,pointLeft)
            self.__display_hist(whiteboardPupil,pointRight)
            self.__display_screen(whiteboardPupil,l_eye,r_eye)
            self.__display_eyeTracker(whiteboardPupil,pointLeft,pointRight)

            self.__display_extended_gaze(frame,l_eye,10)
            self.__display_extended_gaze(frame,r_eye,10)
            # self.__display_gaze_intersection(frame,l_eye,r_eye)
            self.worker.imshow("frame",frame)

            self.worker.imshow("whitebaord",whiteboardPupil)
            self.worker.imshow("left eye",l_eye.getImage())
            self.worker.imshow("right eye",r_eye.getImage())

            # display camera feed
            # showEyes(frame,face)            
            # self.frameDisplay.imshow(
            #     self.__convertFrame(frame))

            # print(f"HeadDirection: {self.gestures.getHeadDirection()}")
            
            
    def run(self):
        monitors = get_monitors()
        (width,height) = (int(monitors[0].width),int(monitors[0].height))
        ret = True
        while ret and self.__run:

            ret, frame = self.cap.read()     
            
            try:
                self.__display_left_eye(frame)
            except Exception as e:
                print(f"crashed in debug {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    Lab()
    sys.exit(app.exec_())
    
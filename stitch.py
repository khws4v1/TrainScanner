#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import trainscanner
import sys
import os
import myargparse
import argparse
import film
import helix
import rect
import logging
from canvas import Canvas



class AlphaMask():
    alphas = dict()
    def __init__(self, img_width, img_height, slit=0, width=1.0):
        self.img_width  = img_width
        self.img_height = img_height
        self.width      = width
        self.slitpos    = slit*img_width//1000

    def make_linear_alpha( self, displace ):
        """
        Make an orthogonal mask of only one line.
        slit position is -500 to 500
        slit width=1 is standard, width<1 is narrow (sharp) and width>1 is diffuse alpha
        """
        if displace in self.alphas:
            return self.alphas[displace]
        if displace == 0:
            self.alphas[0.0] = np.ones((self.img_width,3))
            self.alphas[0]   = alphas[0.0]
            return self.alphas[0]
        slitwidth = abs(int(displace*self.width))
        alpha = np.zeros((self.img_width,3))
        if displace > 0:
            slitin = self.img_width//2 - self.slitpos
            slitout = slitin + slitwidth
            alpha[slitout:, :] = 1.0
            alpha[slitin:slitout, :] = np.fromfunction(lambda x,v: x / slitwidth, (slitwidth, 3))
        else:
            slitin = self.img_width//2 + self.slitpos
            slitout = slitin - slitwidth
            alpha[:slitout,:] = 1.0
            alpha[slitout:slitin, :] = np.fromfunction(lambda x,v: (slitwidth-x)/ slitwidth, (slitwidth, 3))
        self.alphas[displace] = alpha
        return alpha


def make_vert_alpha0( alphas, displace, img_width, img_height, slit=0, width=1.0 ):
    """
    Make an orthogonal mask
    slit position is -500 to 500
    slit width=1 is standard, width<1 is narrow (sharp) and width>1 is diffuse alpha
    """
    if (displace, width, slit) in alphas:
        return alphas[(displace, width, slit)]
    if displace == 0:
        return np.zeros((img_height,img_width,3))+1
    if displace > 0:
        centerx = img_width/2 - slit*img_width/1000
    else:
        centerx = img_width/2 + slit*img_width/1000
    alpha = np.fromfunction(lambda y, x, v: (x-centerx)/(displace*width), (img_height, img_width, 3))
    np.clip(alpha,0,1,out=alpha)  # float 0..1 values
    #alpha += 1
    alphas[(displace, width, slit)] = alpha
    return alpha




def prepare_parser(parser=None):
    if parser is None:
        parser = myargparse.MyArgumentParser(description='TrainScanner stitcher')
    parser.add_argument('-C', '--canvas', type=int,
                        nargs=4, default=None,
                        dest="canvas", 
                        help="Canvas size determined by pass1.")
    parser.add_argument('-s', '--slit', type=int, metavar='x',
                        default=250,
                        dest="slitpos",
                        help="Slit position (0=center, 500=on the edge forward).")
    parser.add_argument('-W', '--length', type=int, metavar='x',
                        default=0,
                        dest="length",
                        help="Maximum image length of the product.")
    parser.add_argument('-y', '--scale', type=float,
                        default=1.0,
                        dest="scale", metavar="x",
                        help="Scaling ratio for the final image.")
    parser.add_argument('-w', '--width', type=float,
                        default=1.0,
                        dest="slitwidth", metavar="x",
                        help="Slit mixing width.")
    parser.add_argument('-c', '--crop', type=int,
                        nargs=2, default=[0,1000],
                        dest="crop", metavar="t,b",
                        help="Crop the image (top and bottom).")
    parser.add_argument('-p', '--perspective',
                        type=int,
                        nargs=4, default=None,
                        dest="perspective",
                        help="Specity perspective warp.")
    parser.add_argument('-r', '--rotate', type=int,
                        default=0,
                        dest="rotate",
                        help="Image rotation.")
    parser.add_argument('-l', '--log', type=str,
                        dest='logbase', default=None,
                        help="TrainScanner settings (.tsconf) file name.")
    parser.add_argument('-H', '--helix', action='store_true',
                        dest='helix',
                        help="Make helical image.")
    parser.add_argument('--rect', action='store_true',
                        dest='rect',
                        help="Make rectangular image.")
    parser.add_argument('-F', '--film', action='store_true',
                        dest='film',
                        help="Make film perforation.")
    parser.add_argument('filename', type=str,
                        help="Movie file name.")

    return parser



class Stitcher(Canvas):
    """
    exclude video handling
    """
    def __init__(self, argv):
        logger = logging.getLogger()
        ####Avoid unknown error.
        #myargparse does not show the usage correctly.
        ap0 = argparse.ArgumentParser(fromfile_prefix_chars='@',
                                        description='TrainScanner stitcher')
        prepare_parser(ap0).parse_known_args(argv[1:])
        ####
        ap = myargparse.MyArgumentParser(fromfile_prefix_chars='@',
                                        description='TrainScanner stitcher')
        self.parser  = prepare_parser(ap)
        self.params,unknown = self.parser.parse_known_args(argv[1:])
        #Decide the paths
        moviepath = self.params.filename
        moviedir  = os.path.dirname(moviepath)
        moviebase = os.path.basename(moviepath)
        self.tsposfile = ""
        
        if self.parser.fromfile_name is not None:
            #When the "@"file is specified,
            #read tsconf there. (actually it is alread read.)
            #read tspos at the same path
            tsconfdir = os.path.dirname(self.parser.fromfile_name)
            tsconfbase = os.path.basename(self.parser.fromfile_name)
            if tsconfbase[-7:] == ".tsconf":
                tsconfbase = tsconfbase[:-7]
            self.tsposfile = tsconfdir + "/" + tsconfbase + ".tspos"
        #or tspos in the logbase
        if self.tsposfile == "" or not os.path.exists(self.tsposfile):
            tsconfdir = os.path.dirname(self.parser.logbase)
            tsconfbase = os.path.basename(self.parser.logbase)
            self.tsposfile = tsconfdir + "/" + tsconfbase + ".tspos"
        moviefile = tsconfdir + "/" + moviebase
        self.outfilename = tsconfdir + "/" + tsconfbase + ".png"
        if not os.path.exists(moviefile):
            moviefile = moviepath
        logger.info("TSPos  {0}".format(self.tsposfile))
        logger.info("Movie  {0}".format(moviefile))
        logger.info("Output {0}".format(self.outfilename))
        
        self.cap = cv2.VideoCapture(moviefile)
        self.firstFrame = True
        self.currentFrame = 0 #1 is the first frame

        self.R = None
        self.M = None
        self.transform = trainscanner.transformation(self.params.rotate, self.params.perspective, self.params.crop)
        # initialization of the super class
        if self.params.canvas is None:
            Canvas.__init__(self)
            self.dimen = None
        else:
            if self.params.scale == 1 and self.params.length > 0:
                #product length is specified.
                #scale is overridden
                self.params.scale = self.params.length / self.params.canvas[0]
                if self.params.scale > 1:
                    self.params.scale = 1  #do not allow stretching
            self.dimen = [int(x*self.params.scale) for x in self.params.canvas]
            Canvas.__init__(self,image=np.zeros((self.dimen[1],self.dimen[0],3),np.uint8), position=self.dimen[2:4]) #python2 style

    def before(self):
        """
        is a generator.
        """
        locations = []
        absx = 0
        absy = 0
        tspos = open(self.tsposfile)
        for line in tspos.readlines():
            if len(line) > 0 and line[0] != '@':
                cols = [int(x) for x in line.split()]
                if len(cols) > 0:
                    absx += cols[1]
                    absy += cols[2]
                    cols = [cols[0],absx,absy] + cols[1:]
                    cols[1:] = [int(x*self.params.scale) for x in cols[1:]]
                    locations.append(cols)
        self.locations = locations
        self.total_frames = len(locations)
        #self.alphas = dict()
        #initial seek
        while self.currentFrame + 1 < self.locations[0][0]:
            yield self.currentFrame, self.locations[0][0]
            ret = self.cap.grab()
            self.currentFrame += 1

    def getProgress(self):
        den = self.total_frames
        num = den - len(self.locations)
        return (num, den)
    
    def add_image(self, frame, absx,absy,idx,idy):
        rotated,warped,cropped = self.transform.process_image(frame)
        if self.firstFrame:
            self.abs_merge(cropped, absx, absy)
            self.mask = AlphaMask(cropped.shape[1],
                                  cropped.shape[0],
                                  slit=self.params.slitpos,
                                  width=self.params.slitwidth)
            self.firstFrame = False
        else:
            alpha = self.mask.make_linear_alpha( int(idx) )
            self.abs_merge(cropped, absx, absy, alpha=alpha)


    def stitch(self):
        for num,den in self.before():
            pass
        result = None
        for num,den in self.loop():
            pass
        #while result is None:
        #    result = self.onestep()
        self.after()
        self.done()
                

    def loop(self):
        while True:
            result = self._onestep()
            yield self.getProgress()
            if result is not None:
                break


    def _onestep(self):
        ##if self.firstFrame:
        ##    #NOT RELIABLE
        ##    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.locations[0][0]-##1)
        ##    self.currentFrame = self.locations[0][0]
        ##else:
        while self.currentFrame + 1 < self.locations[0][0]:
            ret = self.cap.grab()
            if not ret:
                return self.image
            self.currentFrame += 1
        ret,frame = self.cap.read()
        self.currentFrame += 1
        if not ret:
            return self.image
        frame = cv2.resize(frame, None, fx=self.params.scale, fy=self.params.scale)
        self.add_image(frame, *self.locations[0][1:])
        self.locations.pop(0)
        if len(self.locations) == 0:
            return self.image
        return None  #not end

    def after(self):
        self.save(self.outfilename)
        file_name = self.outfilename
        img       = self.image
        if self.params.film:
            img = film.filmify( img )
            file_name += ".film.png"
            cv2.imwrite(file_name, img)
        if self.params.helix:
            img = helix.helicify( img )
            cv2.imwrite(file_name + ".helix.png", img)
        if self.params.rect:
            img = rect.rectify( img )
            cv2.imwrite(file_name + ".rect.png", img)
        

    def done(self):
        """
        Release memory
        """
        self.image = None


if __name__ == "__main__":
    debug =True
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            #filename='log.txt',
                            format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    st = Stitcher(argv=sys.argv)
    st.stitch()

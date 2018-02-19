import math
import cv2
import argparse
import frcvpl
from vpl.all import *
from networktables import NetworkTables
import socket

parser = argparse.ArgumentParser(description='Example webcam view for punkvision')

parser.add_argument('--source', type=str, default="0", help='camera number, image glob (like "data/*.png"), or video file ("x.mp4")')
parser.add_argument('--size', type=int, nargs=2, default=(640, 480), help='image size')
parser.add_argument('--blur', type=int, nargs=2, default=(12,12), help='blur size')

parser.add_argument('--save', default=None, help='save the stream to files (ex: "data/{num}.png"')

parser.add_argument('--stream', default=None, type=int, help='stream to a certain port (ex: "5802" and then connect to "localhost:5802" to view the stream)')

parser.add_argument('--noshow', action='store_true', help="if this flag is set, do not show a window (useful for raspberry PIs without a screen, you can use --stream)")

parser.add_argument('--noprop', action='store_true', help="if this flag is set, do not set capture properties (some may fail without this, use this if you are getting a QBUF error)")

args = parser.parse_args()


pipe = Pipeline("process")
fork = Pipeline("record")
cam_props = CameraProperties()

# set preferred width and height
if not args.noprop:
    cam_props["FRAME_WIDTH"] = args.size[0]
    cam_props["FRAME_HEIGHT"] = args.size[1]


# find the source
pipe.add_vpl(VideoSource(source=args.source, properties=cam_props))

pipe.add_vpl(ForkVPL(pipe=fork))

fork.add_vpl(frcvpl.ShowGameInfo())



# resize
pipe.add_vpl(Resize(w=args.size[0], h=args.size[1]))

#blur
pipe.add_vpl(Blur(w=args.blur[0], h=args.blur[1], method='box'))

#convert to HSV
pipe.add_vpl(frcvpl.ConvertColor(conversion=cv2.COLOR_BGR2HSV))

#Filter HSV threshold
pipe.add_vpl(frcvpl.InRange(mask_key="mask"))
pipe.add_vpl(frcvpl.ApplyMask(mask_key="mask"))

#Erode
pipe.add_vpl(frcvpl.StoreImage(key="normal"))
pipe.add_vpl(frcvpl.RestoreImage(key="mask"))
pipe.add_vpl(frcvpl.Erode())

#Dilate
pipe.add_vpl(frcvpl.Dilate())

#Find Contours
pipe.add_vpl(frcvpl.FindContours(key="contours"))

pipe.add_vpl(frcvpl.RestoreImage(key="normal"))

#Convert back to BGR
pipe.add_vpl(frcvpl.ConvertColor(conversion=cv2.COLOR_HSV2BGR))

#Draws dot on center point of convex hull
pipe.add_vpl(frcvpl.DrawContours(key="contours"))

#Draws meter to tell how close to center
pipe.add_vpl(frcvpl.DrawMeter(key="contours"))

# add a FPS counter
pipe.add_vpl(FPSCounter())

pipe.add_vpl(frcvpl.DumpInfo(key="contours"))




#stream it
if not args.noshow:
    pipe.add_vpl(frcvpl.Display(title="footage from " + str(args.source)))
    fork.add_vpl(frcvpl.Display(title="fork"))
if args.stream is not None:
    fork.add_vpl(vpl.MJPGServer(port=args.stream))
    fork.add_vpl(vpl.MJPGServer(port=args.stream))

try:
      # we let our VideoSource do the processing, autolooping
      pipe.process(image=None, data=None, loop=True)
except (KeyboardInterrupt, SystemExit):
    print("keyboard interrupt, quitting")
    exit(0)
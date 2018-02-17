import sys
import os

import math

import argparse

parser = argparse.ArgumentParser(description='webcam viewer')

parser.add_argument("source", nargs='?', default=0, help='camera source (can be video file)')
parser.add_argument("-s", "--size", default=(640, 480), type=int, nargs=2, help='size')
parser.add_argument("-e", "--exposure", default=None, type=float, help='exposure settings')
parser.add_argument("-ae", "--auto-exposure", default=None, type=float, help='auto exposure settings')
parser.add_argument("-so", "--source-output", default=None, help='output raw webcam feed')
parser.add_argument("--stream", default=None, type=int, help='port to stream to')

parser.add_argument("-ns", "--no-show", action='store_true', help='use this flag to not show')
parser.add_argument("-np", "--no-prop", action='store_true', help='use this flag to not use CameraProperties')
parser.add_argument("--sync", action='store_true', help='use this flag to syncroniously process')

parser.add_argument('--blur', type=int, nargs=2, default=(12,12), help='blur size')

parser.add_argument("--dev", action='store_true', help='developer (non-install) flag')
parser.add_argument("-o", "--output", default=None, help='output file')

args = parser.parse_args()

if args.dev:
    sys.path.append(os.getcwd())

import vpl

# this line makes it easier
from vpl.all import *

import frcvpl

pipe = Pipeline("pipe")
fork = Pipeline("record")



# input
vsrc = VideoSource(source=args.source, async=not args.sync)

pipe.add_vpl(vsrc)

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


if args.dev:
    pipe.add_vpl(PrintInfo(fps=2, extended=True))

cam_props = CameraProperties()

cam_props["FPS"] = 60.0

if args.exposure is not None and not args.no_prop:
    cam_props["EXPOSURE"] = args.exposure

if args.auto_exposure is not None and not args.no_prop:
    cam_props["AUTO_EXPOSURE"] = args.auto_exposure

# set preferred width and height
if args.size is not None and not args.no_prop:
    cam_props["FRAME_WIDTH"] = args.size[0]
    cam_props["FRAME_HEIGHT"] = args.size[1]

vsrc["properties"] = cam_props


#if args.size is not None:
#    pipe.add_vpl(Resize(w=args.size[0], h=args.size[1]))

#if args.source_output:
#    pipe.add_vpl(VideoSaver(path=args.source_output))

# processing here

#pipe.add_vpl(Bleed(N=2))
#pipe.add_vpl(Grayscale())
#pipe.add_vpl(Noise(level=.2))
#pipe.add_vpl(Bilateral(s_color=26, s_space=30))
#pipe.add_vpl(EdgeDiff())
#pipe.add_vpl(RainbowCrazy())
#pipe.add_vpl(HSLBin())

#pipe.add_vpl(Roll(w=lambda w, ct: 3.5 * ct, h=lambda h, ct: 5.5 * ct + h / 3.0 + 10 * math.sin(2 * math.pi * (h / 120.0 + ct / 24.0))))
#pipe.add_vpl(Grid(w=6, h=6))
#pipe.add_vpl(Pixelate())

#pipe.add_vpl(CoolChannelOffset(xoff=lambda i: 6 * i, yoff=lambda i: 1 * i))
#pipe.add_vpl(Scanlines())

#def transform_func(x, y, w, h):
#    return w * np.log(x + 1) / np.log(w), y

#pipe.add_vpl(Transform(func=transform_func))

# just output


if args.stream is not None:
    pipe.add_vpl(MJPGServer(port=args.stream))
    #fork.add_vpl(MJPGServer(port=args.stream))


if not args.no_show:
    pipe.add_vpl(Display(title="window"))
    fork.add_vpl(Display(title="fork"))


#if args.output is not None:
#    pipe.add_vpl(VideoSaver(path=args.output, async=not args.sync))

try:
    # we let our VideoSource do the processing, autolooping
    pipe.process(image=None, data=None, loop=True)
except (KeyboardInterrupt, SystemExit):
    print("keyboard interrupt, quitting")

print ("gracefully ending")

pipe.end()
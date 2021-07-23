from tkinter import *
from tkinter import filedialog

import pydicom as dicom
from PIL import ImageTk, Image, ImageEnhance, ImageDraw
import numpy as np
import matplotlib as mpl

import os


#event handler functions
def select_image():
    global images, points #image panel

    #open file choose
    directory = filedialog.askdirectory()

    if len(directory) > 0:
        filenames = os.listdir(directory)

        for file in filenames:
            path = directory + '/' + file

            ds = dicom.dcmread(path).pixel_array
            pil_im = Image.fromarray(ds).convert('L')
            images.append(pil_im)

        #create none list
        points = []
        for i in range (0, len(images)):
            points.append([None])

        #display image
        change_image(1)

        #create scale to browse images after folder opened
        browse_text = Label(root, text='Image Slice: ')
        browse_text.grid(row=1, column=1, sticky=W)
        
        browse_scale = Scale(root, orient=HORIZONTAL, length=300, from_=1, to=len(images), 
                             command=change_image)
        browse_scale.grid(row=2, column=1, sticky=W, pady=5)

        f1 = Frame(root, width=400, height=30)

        #brightness scale
        brightness_text = Label(f1, text='Brightness: ')
        brightness_text.grid(row=0, column=0, sticky=W, pady=0)

        brightness_scale = Scale(f1, orient=HORIZONTAL, length=300, from_=0.0, to=5.0,
                                 resolution = 0.01, command=change_brightness)
        brightness_scale.grid(row=1, column=0, sticky=W)
        brightness_scale.set(1.0)

        #contrast scale
        contrast_text = Label(f1, text='Contrast: ')
        contrast_text.grid(row=3, column=0, sticky=W, pady=0)

        contrast_scale = Scale(f1, orient=HORIZONTAL, length=300, from_=0.0, to=5.0,
                               resolution=0.01, command=change_contrast)
        contrast_scale.grid(row=4, column=0, stick=W)
        contrast_scale.set(1.0)

        f1.grid(row=0, column = 2, rowspan=2, sticky=N+S)

        #point info frame
        f2.grid(row=0, column=0, rowspan=2, sticky=N+S)


def change_image(val):
    global images, alpha, beta, im_index, points

    val = int(val)
    im_index = val-1

    canvas.delete('all')

    im = images[im_index]
    
    #image controls
    b_converter = ImageEnhance.Brightness(im)
    im = b_converter.enhance(alpha)

    c_converter = ImageEnhance.Contrast(im)
    im = c_converter.enhance(beta)

    im = im.convert('RGBA')

    if points[im_index] != None:

        for i in range (0, len(points[im_index])):
            cont = points[im_index][i]
            if cont != None:
                #draw contour points
                draw = ImageDraw.Draw(im)
                for p in cont:
                    if p != None:
                        draw.ellipse((p[0], p[1], p[0]+1, p[1]+1), fill='blue', outline='blue')

                #draw connecting lines
                if len(cont) > 1:
                    connect_points(points[im_index][i], draw)

                point_text.set('Point #: ' + str(len(points[im_index][i])))

                #if points[im_index][len(points[im_index])-1] == None:
                #    print('fill')

                #colour in contour if not line
                if len(cont) > 2 and i != len(points[im_index])-1:
                    poly = im.copy()
                    poly_draw = ImageDraw.Draw(poly)
                    poly_draw.polygon(cont, fill='blue')

                    im = Image.blend(im, poly, 0.2)

    #im = ImageTk.PhotoImage(im), +1 to avoid im with size 0 (zoom out too much)
    im = ImageTk.PhotoImage(im.resize((int(im.size[0] * imscale) + 1, int(im.size[1] * imscale) + 1)), 
                            Image.LANCZOS)

    panelA = Label(image = im)
    panelA.image = im

    canvas.create_image(0, 0, image=im, anchor='nw')

def change_brightness(val):
    #get dcm image from directory - more effficient that converting ImageTk to np arr
    global alpha, im_index
    alpha = float(val)

    change_image(im_index+1)

def change_contrast(val):
    global beta, im_index
    beta = float(val)
    
    change_image(im_index+1)
  
def zoomer(event):  
    global im_index, imscale
    scale = 1.0

    if (event.delta > 0):
        imscale += 0.1
        scale += 0.1
    elif (event.delta < 0):
        imscale -= 0.1
        scale -= 0.1

    x = canvas.canvasx(event.x)
    y = canvas.canvasy(event.y)

    canvas.scale('all', x, y, scale, scale)
    change_image(im_index+1)
    canvas.configure(scrollregion = canvas.bbox("all"))
 
def move_from(event):
    global prev_coords

    x = event.x
    y = event.y

    canvas.scan_mark(x, y)

def move_to(event):
    global drag_done

    x = event.x
    y = event.y

    canvas.scan_dragto(x, y, gain=1)

    drag_done = True

def add_point(event):
    global points, im_index
    coords = true_coordinates(event.x, event.y)

    curr = len(points[im_index]) - 1

    if points[im_index][curr] == None:
        points[im_index][curr] = [coords]

    elif points[im_index][curr][0] == None:
        points[im_index][curr] = [coords]

    elif coords not in points[im_index][curr]:
        list = points[im_index][curr]
        list.append(coords)
        points[im_index][curr] = list
        
    change_image(im_index+1)

def undo_point():
    global im_index, points
    curr = len(points[im_index]) - 1

    try:
        del points[im_index][curr][-1]
    except:
        print('no points selected')

    change_image(im_index+1)

def save_contour():
    global im_index, points

    points[im_index].append([None])
    change_image(im_index+1)

def export():
    global points
    for i in range (0, len(points)):
        for j in range (0, len(points[i])-1):
            cont_a = points[i][j]
            overlapped = [] #add overlapped points here, del in other arrays
            for k in range (i+1, len(points)):
                for l in range (0, len(points[k])-1):
                    cont_b = points[k][l]
                    if isoverlap(cont_a, cont_b):
                        overlapped.append(cont_a)
                        overlapped.append(cont_b)
            print(overlapped)

#other functions
def true_coordinates(x, y):
    global origin

    true_x = int((x + canvas.canvasx(0)) / imscale)
    true_y = int((y + canvas.canvasy(0)) / imscale)

    return (true_x, true_y)

def connect_points(points, im):
    prev = points[0]
    for curr in points:
        im.line([prev, curr], fill='blue', width=1)
        prev = curr

def isoverlap(a, b):

    a = undo_tuplearr(a)
    b = undo_tuplearr(b)

    path_a = mpl.path.Path(a)
    path_b = mpl.path.Path(b)

    out_1 = mpl.path.Path.contains_points(path_a, b, radius=5.0)
    out_2 = mpl.path.Path.contains_points(path_b, a, radius=5.0)

    true_count_1 = out_1.sum()
    true_count_2 = out_2.sum()

    out = true_count_1 / len(out_1)
    if true_count_1 < true_count_2:
        out = true_count_2 / len(out_2)

    return out > 0.75

def undo_tuplearr(a):
    b = np.ndarray((len(a), 2), dtype='uint16')
    for i in range(0, len(a)):
        b[i][0] = a[i][0]
        b[i][1] = a[i][1]
    return b

#global variables
images = []
im_index = 0
alpha = 1.0 #0=black, 1=original image
beta = 1.0 #0-2.0 1=normal, blur to sharp
imscale = 1.0 #image zoom factor

drag_done = False

points = []

#initialize and bind components 
root = Tk()

canvas = Canvas(root, width=400, height=400, bg='white')
canvas.grid(row=0, column=1, sticky = W, pady=5)

canvas.bind('<MouseWheel>', zoomer)
canvas.bind('<ButtonPress-1>', move_from)
canvas.bind('<B1-Motion>', move_to)
canvas.bind('<ButtonPress-3>', add_point)

btn = Button(root, text='Select Image', command=select_image, bg='gray')
btn.grid(row=3, column=1, sticky=W, pady=5)

export_btn = Button(root, text='Export', command=export)
export_btn.grid(row=4, column=1, sticky=W, pady=5)


#left panel frame
f2 = Frame(root)

id_text = Label(f2)

id_enter = Entry(f2)
id_enter.grid(row=0, column=0, pady=0)

point_text = StringVar(f2, 'Point #: ')
point_label = Label(f2, textvariable=point_text)
point_label.grid(row=1, column=0, pady=5)

save_btn = Button(f2, text='Save Contour', command=save_contour)
save_btn.grid(row=2, column=0, pady=5)

undo_btn = Button(f2, text='Undo Point Selection', command=undo_point)
undo_btn.grid(row=3, column=0, pady=5)

#start
root.mainloop()

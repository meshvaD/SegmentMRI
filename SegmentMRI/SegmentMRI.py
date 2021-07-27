from tkinter import *
from tkinter import filedialog

import pydicom as dicom
from PIL import ImageTk, Image, ImageEnhance, ImageDraw
import tifffile as tiff

import numpy as np
import matplotlib as mpl
import pandas as pd

import os

#event handler functions
def select_image(name):
    global images, images_right, points #image panel

    #open file choose
    directory = filedialog.askdirectory()

    if len(directory) > 0:
        filenames = os.listdir(directory)

        for file in filenames:
            path = directory + '/' + file

            ds = dicom.dcmread(path).pixel_array
            pil_im = Image.fromarray(ds).convert('L')

            if name == 'left':
                images.append(pil_im)
            elif name == 'right':
                images_right.append(pil_im)

        #create none list
        if len(points) == 0:
            l = len(images)
            if len(images_right) > l:
                l = len(images_right)

            for i in range (0, l):
                points.append([None])

        #point info frame shown after first selected
        f2.grid(row=0, column=0, rowspan=2, sticky=N+S)

        if name == 'left':
            change_image(1, 'left') #change left image

            btn.grid_forget() #cannot choose new files for first canvas

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

            f1.grid(row=2, column = 1, rowspan=2, sticky=N+S)

        elif name == 'right':
            btn_right.grid_forget()

            f3 = Frame(root, width=400, height=30)

            #brightness scale
            brightness_text = Label(f3, text='Brightness: ')
            brightness_text.grid(row=0, column=0, sticky=W, pady=0)

            brightness_scale_right = Scale(f3, orient=HORIZONTAL, length=300, from_=0.0, to=5.0,
                                     resolution = 0.01, command=change_brightness_right)
            brightness_scale_right.grid(row=1, column=0, sticky=W)
            brightness_scale_right.set(1.0)

            #contrast scale
            contrast_text = Label(f3, text='Contrast: ')
            contrast_text.grid(row=3, column=0, sticky=W, pady=0)

            contrast_scale_right = Scale(f3, orient=HORIZONTAL, length=300, from_=0.0, to=5.0,
                                   resolution=0.01, command=change_contrast_right)
            contrast_scale_right.grid(row=4, column=0, stick=W)
            contrast_scale_right.set(1.0)

            f3.grid(row=2, column = 2, rowspan=2, sticky=N+S)

def change_image(val, side):
    global im_index

    if val != None:
        val = int(val)
        im_index = val-1

    if side == 'left':
        im = images[im_index]
        cn = canvas
        a = alpha
        b = beta
    elif side == 'right':
        im = images_right[im_index]
        cn = canvas_right
        a = alpha_right
        b = beta_right

    cn.delete('all')
    
    #image controls
    b_converter = ImageEnhance.Brightness(im)
    im = b_converter.enhance(a)

    c_converter = ImageEnhance.Contrast(im)
    im = c_converter.enhance(b)

    im = im.convert('RGBA')

    im = draw_contours(points, im_index, im)

    # +1 to avoid im with size 0 (zoom out too much)
    im = ImageTk.PhotoImage(im.resize((int(im.size[0] * abs(imscale)+1), 
                                       int(im.size[1] * abs(imscale)+1))), Image.LANCZOS)

    panelA = Label(image = im)
    panelA.image = im

    item = cn.create_image(0, 0, image=im, anchor='nw')

    #shift image
    #print(true_coordinates(0,0))
    #cn.move(item, true_coordinates(0,0)[0], true_coordinates(0,0)[1])

def draw_contours(points, index, im):
    if points[index] != None:
        for i in range (0, len(points[index])):
            cont = points[index][i]
            if cont != None:
                #draw contour points
                draw = ImageDraw.Draw(im)
                for p in cont:
                    if p != None:
                        draw.ellipse((p[0], p[1], p[0]+1, p[1]+1), fill='blue', outline='blue')

                #draw connecting lines
                if len(cont) > 1:
                    connect_points(points[index][i], draw)

                #colour in contour if not line
                if len(cont) > 2 and i != len(points[index])-1:
                    poly = im.copy()
                    poly_draw = ImageDraw.Draw(poly)
                    poly_draw.polygon(cont, fill='blue')

                    im = Image.blend(im, poly, 0.2)

    return im

#brightness and contrast update var
def change_brightness(val):
    global alpha
    alpha = float(val)

    change_image(im_index+1, 'left')

def change_contrast(val):
    global beta
    beta = float(val)
    
    change_image(im_index+1, 'left')

def change_brightness_right(val):
    global alpha_right
    alpha_right = float(val)

    change_image(im_index+1, 'right')

def change_contrast_right(val):
    global beta_right
    beta_right = float(val)
    
    change_image(im_index+1, 'right')
  
def next_image(event):
    global im_index

    l = len(images)
    if len(images_right) > l:
        l = len(images_right)

    if event.delta > 0 and im_index < l-1:
        im_index += 1
    elif event.delta < 0 and im_index > 0:
        im_index -= 1

    im_show.set('Image Slice: ' + str(im_index+1))

    update_all()

#zoom and pan
def zoomer(scale):  
    global imscale
    imscale += scale

    canvas.scale('all', 0, 0, scale, scale)

    update_all()
 
def allow_pan():
    global pan
    if pan:
        pan = False
        root.config(cursor='arrow')
    else:
        pan = True
        root.config(cursor='target')
    #no point of doing this

def move_from(event):
    if pan:
        x = event.x
        y = event.y

        canvas.scan_mark(x, y)
        canvas_right.scan_mark(x, y)
    else:
        add_point(event)

def move_to(event):
    if pan:
        x = event.x
        y = event.y

        canvas.scan_dragto(x, y, gain=1)
        canvas_right.scan_dragto(x, y, gain=1)

#point/ contour selection
def add_point(event):
    global points

    if (len(images) > 0 or len(images_right) > 0):
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
        
        update_all()

def undo_point():
    global points

    curr = len(points[im_index]) - 1
    
    if points[im_index][curr][-1] == None:
        del points[im_index][curr]
        del data[-1]
    elif len(points[im_index][curr]) == 1:
        points[im_index][curr][-1] = None
    elif len(points[im_index][curr]) > 1:
        del points[im_index][curr][-1]

    update_all()

def save_contour():
    global points, id_input

    #add with target to df array: slice + target + coords
    if target_input.get() == '':
        error.set('enter target id')
    elif points[im_index][-1] == [None]:
        error.set('no points selected')
    else:
        error.set('')
        data.append([im_index, target_input.get(), points[im_index][-1], area(points[im_index][-1])])
        points[im_index].append([None])

        update_all()

def reset():
    export()

    os.startfile(sys.argv[0])
    sys.exit()

def export():

    directory = filedialog.askdirectory()

    df = pd.DataFrame(data, columns=['image slice', 'target', 'coordinates', 'area'])

    fpath = id_input.get()
    if fpath == '':
        error.set('enter file id')
    else:
        error.set('')
        df.to_csv(directory + '/' + id_input.get() + '.csv')

        #export tiff stacks
        if len(images) > 0:
            title = l_title.get()
            if title == '':
                title = '1'
            to_tiff(images, directory + '/' + title + '.tiff')
        if len(images_right) > 0:
            title = r_title.get()
            if title == '':
                title = '2'
            to_tiff(images_right, directory + '/' + title + '.tiff')

def to_tiff(ims, fpath):
    with tiff.TiffWriter(fpath) as stack:
        for i in range(0, len(ims)):
            #draw contours on images
            im = draw_contours(points, i, ims[i].convert('RGBA'))
            stack.write(np.array(im))


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

def area(cont):
    area = 0.0
    n = len(cont)
    for i in range(n):
        j = (i + 1) % n
        area += cont[i][0] * cont[j][1]
        area -= cont[j][0] * cont[i][1]
    area = abs(area) / 2.0

    return area

def vol_from_areas(conts, thickness):
    vol = 0.0
    for corners in conts:
        area = area(corners)
        vol += thickness * area

    return vol

def update_all():
    if len(images) > 0:
        change_image(im_index+1, 'left')
    if len(images_right) > 0:
        change_image(im_index+1, 'right')

#global variables
images = []
images_right = []
im_index = 0

alpha = 1.0 #0=black, 1=original image
beta = 1.0 #0-2.0 1=normal, blur to sharp
alpha_right = 1.0
beta_right = 1.0

pan = False
imscale = 1.0 #image zoom factor

points = []
data = []

#if run from .exe, diff fpath
basepath = ''
if getattr(sys, 'frozen', False):
    basepath = sys._MEIPASS + '\\'

#initialize and bind components 
root = Tk()
root.title('Segment Images')

root.columnconfigure(1, weight=1)
root.columnconfigure(2, weight=1)
root.rowconfigure(0, weight=1)

canvas = Canvas(root, width=400, height=400, bg='white')
canvas.grid(row=1, column=1, sticky = N+S+E+W, pady=5)

canvas_right = Canvas(root, width=400, height=400, bg='white')
canvas_right.grid(row=1, column=2, sticky = N+S+E+W, pady=5)

#canvas entry labels: top frame
ftop1 = Frame(root)

btn = Button(ftop1, text='Select Image', command=lambda name='left':select_image(name), bg='gray')
btn.grid(row=0, column=0, sticky=W)

l_lb = Label(ftop1, text='Image Name')
l_lb.grid(row=0, column=1, sticky=W)
l_title = Entry(ftop1)
l_title.grid(row=0, column=2, sticky=W)

ftop1.grid(row=0, column=1, sticky=W)
ftop2 = Frame(root)

btn_right = Button(ftop2, text='Select Image', command=lambda name='right':select_image(name), bg='gray')
btn_right.grid(row=0, column=3, sticky=W)

r_lb = Label(ftop2, text='Image Name')
r_lb.grid(row=0, column=4, sticky=W)
r_title = Entry(ftop2)
r_title.grid(row=0, column=5, sticky=W)

ftop2.grid(row=0, column=2, sticky=W)


canvas.bind('<MouseWheel>', next_image)
canvas.bind('<ButtonPress-1>', move_from)
canvas.bind('<B1-Motion>', move_to)

canvas_right.bind('<MouseWheel>', next_image)
canvas_right.bind('<ButtonPress-1>', move_from)
canvas_right.bind('<B1-Motion>', move_to)

export_btn = Button(root, text='Export', command=export)
export_btn.grid(row=4, column=1, sticky=W, pady=5)

reset_btn = Button(root, text='Reset', command=reset)
reset_btn.grid(row=5, column=1, sticky=W, pady=5)


#left panel frame
f2 = Frame(root)

id_text = Label(f2, text='Animal Id: ')
id_text.grid(row=0, column=0)
id_input = Entry(f2)
id_input.grid(row=0, column=1)

target_text = Label(f2, text='Target #: ')
target_text.grid(row=1, column=0, pady=20)
target_input = Entry(f2)
target_input.grid(row=1, column=1, pady=20)

save_btn = Button(f2, text='Save Contour', command=save_contour)
save_btn.grid(row=2, column=0, pady=5, sticky=W)

root.bind_all('<Control-z>', lambda x: undo_point())
undo_btn = Button(f2, text='Undo Point', command=undo_point)
undo_btn.grid(row=3, column=0, pady=5, sticky=W)

#zoom and pan controls
hand = ImageTk.PhotoImage(Image.open(basepath + 'hand.png').resize((20,20))) #shrink
pan_btn = Button(f2, image = hand, width=20, height=20, command=allow_pan)
pan_btn.grid(row=5, column=2, pady=5, sticky=W)

zoom_in = ImageTk.PhotoImage(Image.open(basepath + 'zoom_in.png').resize((20,20)))
zoomin_btn = Button(f2, image = zoom_in, width=20, height=20, command=lambda zoom=0.1:zoomer(zoom))
zoomin_btn.grid(row=4, column=2, pady=5, sticky=W)

zoom_out = ImageTk.PhotoImage(Image.open(basepath + 'zoom_out.png').resize((20,20)))
zoomout_btn = Button(f2, image = zoom_out, width=20, height=20, command=lambda zoom=-0.1:zoomer(zoom))
zoomout_btn.grid(row=4, column=1, pady=5, sticky=E)

#image number
im_show = StringVar(f2)
im_show.set('Image Slice: 1')

im_label = Label(f2, textvariable=im_show)
im_label.grid(row=7, column=0)

#error label
error = StringVar(f2)
error_label = Label(f2, textvariable=error)
error_label.grid(row=6, column=0)

#start
root.mainloop()

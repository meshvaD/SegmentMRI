from tkinter import *
from tkinter import filedialog

import pydicom as dicom
from skimage import exposure
from PIL import ImageTk, Image, ImageEnhance, ImageDraw
import tifffile as tiff
import zipfile

import numpy as np
import matplotlib as mpl
import pandas as pd

import os
import zipfile
from io import BytesIO

import gc
from guppy import hpy

class SegmentMRI(Frame):

    def __init__(self, parent):

        #global variables
        self.parent = parent

        self.images = []
        self.images_right = []
        self.im_index = 0

        self.alpha = 1.0 #0=black, 1=original image
        self.beta = 1.0 #0-2.0 1=normal, blur to sharp
        self.alpha_right = 1.0
        self.beta_right = 1.0

        self.pan = False
        self.imscale = 1.0 #image zoom factor

        self.points = []
        self.data = []

        #initialize and bind components 
        parent.title('Segment Images')

        #weight > rest(0), resized when window size changed
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(0, weight=1)

        self.select_pressed = BooleanVar(parent)

        self.canvas = Canvas(parent, width=400, height=400, bg='white')
        self.canvas.grid(row=1, column=1, sticky = N+S+E+W, pady=5)

        self.canvas_right = Canvas(parent, width=400, height=400, bg='white')
        self.canvas_right.grid(row=1, column=2, sticky = N+S+E+W, pady=5)

        #canvas entry labels: top frame
        ftop1 = Frame(parent)

        self.btn = Button(ftop1, text='Select Image', command=lambda name='left':self.select_image(name), bg='gray')
        self.btn.grid(row=0, column=0, sticky=W)

        l_lb = Label(ftop1, text='Image Name')
        l_lb.grid(row=0, column=1, sticky=W)
        self.l_title = Entry(ftop1)
        self.l_title.insert(-1, 'T2*w')
        self.l_title.grid(row=0, column=2, sticky=W)

        ftop1.grid(row=0, column=1, sticky=W)
        ftop2 = Frame(parent)

        self.btn_right = Button(ftop2, text='Select Image', command=lambda name='right':self.select_image(name), bg='gray')
        self.btn_right.grid(row=0, column=3, sticky=W)

        r_lb = Label(ftop2, text='Image Name')
        r_lb.grid(row=0, column=4, sticky=W)
        self.r_title = Entry(ftop2)
        self.r_title.insert(-1, 'T1w')
        self.r_title.grid(row=0, column=5, sticky=W)

        ftop2.grid(row=0, column=2, sticky=W)

        self.canvas.bind('<MouseWheel>', self.next_image)
        self.canvas.bind('<ButtonPress-1>', self.move_from)
        self.canvas.bind('<B1-Motion>', self.move_to)

        self.canvas_right.bind('<MouseWheel>', self.next_image)
        self.canvas_right.bind('<ButtonPress-1>', self.move_from)
        self.canvas_right.bind('<B1-Motion>', self.move_to)

        export_btn = Button(parent, text='Export', command=self.export)
        export_btn.grid(row=4, column=1, sticky=W, pady=5)

        reset_btn = Button(parent, text='Reset', command=self.reset)
        reset_btn.grid(row=5, column=1, sticky=W, pady=5)


        #left panel frame
        self.f2 = Frame(parent)

        id_text = Label(self.f2, text='Animal Id: ')
        id_text.grid(row=0, column=0)
        self.id_input = Entry(self.f2)
        self.id_input.grid(row=0, column=1)

        target_text = Label(self.f2, text='Target #: ')
        target_text.grid(row=1, column=0, pady=20)
        self.target_input = Entry(self.f2)
        self.target_input.grid(row=1, column=1, pady=20)

        save_btn = Button(self.f2, text='Save Contour', command=self.save_contour)
        save_btn.grid(row=2, column=0, pady=5, sticky=W)

        parent.bind_all('<Control-z>', lambda x: self.undo_point())
        undo_btn = Button(self.f2, text='Undo Point', command=self.undo_point)
        undo_btn.grid(row=3, column=0, pady=5, sticky=W)

        #if run from .exe, diff fpath
        basepath = ''
        if getattr(sys, 'frozen', False):
            basepath = sys._MEIPASS + '\\'

        #zoom and pan controls
        self.hand = ImageTk.PhotoImage(Image.open(basepath + 'hand.png').resize((20,20))) #shrink
        pan_btn = Button(self.f2, image = self.hand, width=20, height=20, command=self.allow_pan)
        pan_btn.grid(row=5, column=2, pady=5, sticky=W)

        self.zoom_in = ImageTk.PhotoImage(Image.open(basepath + 'zoom_in.png').resize((20,20)))
        zoomin_btn = Button(self.f2, image = self.zoom_in, width=20, height=20, command=lambda zoom=0.1:self.zoomer(zoom))
        zoomin_btn.grid(row=4, column=2, pady=5, sticky=W)

        self.zoom_out = ImageTk.PhotoImage(Image.open(basepath + 'zoom_out.png').resize((20,20)))
        zoomout_btn = Button(self.f2, image = self.zoom_out, width=20, height=20, command=lambda zoom=-0.1:self.zoomer(zoom))
        zoomout_btn.grid(row=4, column=1, pady=5, sticky=E)

        #image number
        self.im_show = StringVar(self.f2)
        self.im_show.set('Image Slice: 1')

        im_label = Label(self.f2, textvariable=self.im_show)
        im_label.grid(row=7, column=0, columnspan=2)

        #error label
        self.error = StringVar(self.f2)
        error_label = Label(self.f2, textvariable=self.error)
        error_label.grid(row=6, column=0, columnspan=2)

        #delete all text labels that will not be changed
        print('...............INIT...............')
        #del l_lb, r_lb, id_text, basepath, im_label, zoomin_btn, zoomout_btn, pan_btn
        #gc.collect()
        #print(h.heap().referrers.byclodo)

    def explore(self, file, side, win=None, zip=None):
        if win:
            win.destroy()

        if zipfile.is_zipfile(file): #open zip givenfile path
            win = Toplevel(self.parent)

            zip = zipfile.ZipFile(file)
            filelist = zip.namelist()

            for i in range(0, len(filelist)):
                f = filelist[i]
                if f.split('/')[-1] == '': #directories
                    btn = Button(win, text=f, 
                                 command=lambda win=win, zip=zip, name=f, side=side : self.explore(name, side, win, zip))
                    btn.grid(row=i, column=0)

        elif zip and file.split('.')[-1] != 'zip': #open directory from zip
            prev_path = file.split('/')
            filelist = zip.namelist()

            win = Toplevel(self.parent)
            for i in range(0, len(filelist)):
                f = filelist[i]
                new_path = f.split('/')

                if prev_path[len(prev_path)-2] == new_path[len(new_path)-2] and file != f:
                    btn = Button(win, text=f, 
                                 command=lambda win=win, zip=zip, name=f, side=side: self.explore(name, side, win, zip))
                    btn.grid(row=i, column=0)

        elif zip: #open zip from directory in zipfile object
            newzip_data = BytesIO(zip.read(file))
            zip = zipfile.ZipFile(newzip_data)
            filelist = zip.namelist()

            win = Toplevel(self.parent)
            for i in range(1, len(filelist)):
                f = filelist[i]
                btn = Button(win, text=f, 
                                 command=lambda win=win, zip=zip, name=f, side=side: self.explore(name, side, win, zip))
                btn.grid(row=i, column=0)

        #if all in window are dcm images, option to select folder
        if win: 
            is_dcm = True
            for w in win.winfo_children():
                if w.cget('text').split('.')[-1] != 'dcm':
                    is_dcm = False
                    break

            if is_dcm:
                select_btn = Button(win, text='Select', background='blue',
                                    command=lambda win=win, zip=zip, name=file, side=side: self.select(name, side, win, zip))
                select_btn.grid(row=win.grid_size()[1], column=0)


    def select(self, file, side, win, zip): 
        filelist = zip.namelist()

        #in alphabetical order
        filelist = sorted(filelist)

        for i in range (1, len(filelist)):
            dcm = zip.read(filelist[i])
            dcm = BytesIO(dcm)

            ds = dicom.dcmread(dcm).pixel_array

            #equalize array
            ds = exposure.equalize_adapthist(ds) * 255

            pil_im = Image.fromarray(ds).convert('L')

            #resize and upsample image
            upsample = 5.0
            self.imscale = 1.0 / upsample
            pil_im = pil_im.resize((int(pil_im.size[0] * upsample), 
                                    int(pil_im.size[1] * upsample)))

            if side == 'left':
                self.images.append(pil_im)
            elif side == 'right':
                self.images_right.append(pil_im)

        #array with pil images

        self.select_pressed.set(True)
        win.destroy()


    #event handler functions
    def select_image(self, name): #after image selected, initial work done

        #open file choose
        zip_file = filedialog.askopenfilename()
        self.explore(zip_file, name)

        self.parent.wait_variable(self.select_pressed)
        self.select_pressed = BooleanVar()

        #create none list
        if len(self.points) == 0:
            l = len(self.images)
            if len(self.images_right) > l:
                l = len(self.images_right)

            for i in range (0, l):
                self.points.append([None])

        #point info frame shown after first selected
        self.f2.grid(row=0, column=0, rowspan=2, sticky=N+S)

        if name == 'left':
            self.change_image(1, 'left') #change left image

            self.btn.grid_forget() #cannot choose new files for first canvas

            f1 = Frame(self.parent, width=400, height=30)

            #brightness scale
            brightness_text = Label(f1, text='Brightness: ')
            brightness_text.grid(row=0, column=0, sticky=W, pady=0)

            brightness_scale = Scale(f1, orient=HORIZONTAL, length=300, from_=0.0, to=5.0,
                                        resolution = 0.01, command=self.change_brightness)
            brightness_scale.grid(row=1, column=0, sticky=W)
            brightness_scale.set(1.0)

            #contrast scale
            contrast_text = Label(f1, text='Contrast: ')
            contrast_text.grid(row=3, column=0, sticky=W, pady=0)

            contrast_scale = Scale(f1, orient=HORIZONTAL, length=300, from_=0.0, to=5.0,
                                    resolution=0.01, command=self.change_contrast)
            contrast_scale.grid(row=4, column=0, stick=W)
            contrast_scale.set(1.0)

            f1.grid(row=2, column = 1, rowspan=2, sticky=N+S)

        elif name == 'right':
            self.btn_right.grid_forget()

            f3 = Frame(self.parent, width=400, height=30)

            #brightness scale
            brightness_text = Label(f3, text='Brightness: ')
            brightness_text.grid(row=0, column=0, sticky=W, pady=0)

            brightness_scale_right = Scale(f3, orient=HORIZONTAL, length=300, from_=0.0, to=5.0,
                                        resolution = 0.01, command=self.change_brightness_right)
            brightness_scale_right.grid(row=1, column=0, sticky=W)
            brightness_scale_right.set(1.0)

            #contrast scale
            contrast_text = Label(f3, text='Contrast: ')
            contrast_text.grid(row=3, column=0, sticky=W, pady=0)

            contrast_scale_right = Scale(f3, orient=HORIZONTAL, length=300, from_=0.0, to=5.0,
                                    resolution=0.01, command=self.change_contrast_right)
            contrast_scale_right.grid(row=4, column=0, stick=W)
            contrast_scale_right.set(1.0)

            f3.grid(row=2, column = 2, rowspan=2, sticky=N+S)

    def change_image(self, val, side): #update image displayed after each change

        if val != None:
            val = int(val)
            self.im_index = val-1

        if side == 'left':
            im = self.images[self.im_index]
            cn = self.canvas
            a = self.alpha
            b = self.beta
        elif side == 'right':
            im = self.images_right[self.im_index]
            cn = self.canvas_right
            a = self.alpha_right
            b = self.beta_right

        cn.delete('all')
    
        #image controls
        b_converter = ImageEnhance.Brightness(im)
        im = b_converter.enhance(a)

        c_converter = ImageEnhance.Contrast(im)
        im = c_converter.enhance(b)

        im = im.convert('RGBA')

        im = self.draw_contours(self.points, self.im_index, im)

        # +1 to avoid im with size 0 (zoom out too much)
        im = ImageTk.PhotoImage(im.resize((int(im.size[0] * abs(self.imscale)+1), 
                                           int(im.size[1] * abs(self.imscale)+1))), Image.LANCZOS)

        panelA = Label(image = im)
        panelA.image = im

        item = cn.create_image(0, 0, image=im, anchor=N+W)


    def draw_contours(self, points, index, im):
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
                        self.connect_points(self.points[index][i], draw)

                    #colour in contour if not line
                    if len(cont) > 2 and i != len(points[index])-1:
                        poly = im.copy()
                        poly_draw = ImageDraw.Draw(poly)
                        poly_draw.polygon(cont, fill='blue')

                        im = Image.blend(im, poly, 0.2)

        return im

    #brightness and contrast update var
    def change_brightness(self, val):
        self.alpha = float(val)

        self.change_image(self.im_index+1, 'left')

    def change_contrast(self, val):
        self.beta = float(val)
    
        self.change_image(self.im_index+1, 'left')

    def change_brightness_right(self, val):
        self.alpha_right = float(val)

        self.change_image(self.im_index+1, 'right')

    def change_contrast_right(self, val):
        self.beta_right = float(val)
    
        self.change_image(self.im_index+1, 'right')
  
    def next_image(self, event):
        l = len(self.images)
        if len(self.images_right) > l:
            l = len(self.images_right)

        if event.delta > 0 and self.im_index < l-1:
            self.im_index += 1
        elif event.delta < 0 and self.im_index > 0:
            self.im_index -= 1

        self.im_show.set('Image Slice: ' + str(self.im_index+1))

        self.update_all()

    #zoom and pan
    def zoomer(self, scale):  
        self.imscale += scale

        self.canvas.scale('all', 0, 0, scale, scale)

        self.update_all()
 
    def allow_pan(self):

        if self.pan:
            self.pan = False
            self.parent.config(cursor='arrow')
        else:
            self.pan = True
            self.parent.config(cursor='target')
        
        print(h.heap())
        #print(h.heap()[0].referrers.byvia)


    def move_from(self, event):
        if self.pan:
            x = event.x
            y = event.y

            self.canvas.scan_mark(x, y)
            self.canvas_right.scan_mark(x, y)
        else:
            self.add_point(event)

    def move_to(self, event):
        if self.pan:
            x = event.x
            y = event.y

            self.canvas.scan_dragto(x, y, gain=1)
            self.canvas_right.scan_dragto(x, y, gain=1)

    #point/ contour selection
    def add_point(self, event):

        if (len(self.images) > 0 or len(self.images_right) > 0):
            coords = self.true_coordinates(event.x, event.y)

            curr = len(self.points[self.im_index]) - 1

            if self.points[self.im_index][curr] == None:
                self.points[self.im_index][curr] = [coords]

            elif self.points[self.im_index][curr][0] == None:
                self.points[self.im_index][curr] = [coords]

            elif coords not in self.points[self.im_index][curr]:
                list = self.points[self.im_index][curr]
                list.append(coords)
                self.points[self.im_index][curr] = list
        
            self.update_all()

    def undo_point(self):

        curr = len(self.points[self.im_index]) - 1
        if len(self.points[self.im_index][curr][-1]) == 0:
            self.error.set('no points selected to undo')
        elif self.points[self.im_index][curr][-1] == None:
            del self.points[self.im_index][curr]
            del self.data[-1]
        elif len(self.points[self.im_index][curr]) == 1:
            self.points[self.im_index][curr][-1] = None
        elif len(self.points[self.im_index][curr]) > 1:
            del self.points[self.im_index][curr][-1]

        self.update_all()

    def save_contour(self):
        #add with target to df array: slice + target + coords
        if self.target_input.get() == '':
            print('enter target id')
            self.error.set('enter target id')
        elif self.points[self.im_index][-1] == None or self.points[self.im_index][-1] == [None]:
            self.error.set('no points selected')
        else:
            self.error.set('')
            self.data.append([self.im_index, self.target_input.get(), self.points[self.im_index][-1], 
                         self.area(self.points[self.im_index][-1])])
            self.points[self.im_index].append([None])

            self.update_all()

    def reset(self):
        self.__init__(self.parent)

    def export(self):
        fpath = self.id_input.get()
        if fpath == '':
            self.error.set('enter file id')
        else:
            directory = filedialog.askdirectory()

            df = pd.DataFrame(self.data, columns=['image slice', 'target', 'coordinates', 'area'])

            self.error.set('')
            df.to_csv(directory + '/' + fpath + '.csv')

            #export tiff stacks
            if len(self.images) > 0:
                title = self.l_title.get()
                if title == '':
                    title = '1'
                self.to_tiff(self.images, directory + '/' + (fpath + '_' + title) + '.tiff')
            if len(self.images_right) > 0:
                title = self.r_title.get()
                if title == '':
                    title = '2'
                self.to_tiff(self.images_right, directory + '/' + (fpath + '_' + title) + '.tiff')

    def to_tiff(self, ims, fpath):
        fpath = fpath.replace('*', '')
        with tiff.TiffWriter(fpath) as stack:
            for i in range(0, len(ims)):
                #draw contours on images
                im = self.draw_contours(self.points, i, ims[i].convert('RGBA'))
                stack.write(np.array(im))


    #other functions

    def true_coordinates(self, x, y):
        true_x = int((x + self.canvas.canvasx(0)) / self.imscale)
        true_y = int((y + self.canvas.canvasy(0)) / self.imscale)

        return (true_x, true_y)

    def connect_points(self, points, im):
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

    def area(self, cont):
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

    def update_all(self):
        if len(self.images) > 0:
            self.change_image(self.im_index+1, 'left')
        if len(self.images_right) > 0:
            self.change_image(self.im_index+1, 'right')


        
#start

h = hpy()

root = Tk()
SegmentMRI(root)
root.mainloop()


print('...............IMPORTING...............')
from tkinter import *
from tkinter import filedialog

print(' tkinter')

import pydicom as dicom
from skimage import exposure
from PIL import ImageTk, Image, ImageEnhance, ImageDraw
import tifffile as tiff
import zipfile
print(' pydicom \n scikit-image \n PIL \n tiffile \n zipfile')

import numpy as np
import matplotlib as mpl
import pandas as pd
print(' numpy \n matplotlib \n pandas')

import os
from io import BytesIO
print(' os \n io')


class SegmentMRI(Frame):

    #resets all variables incl zoom/brightness/images/selections
    #creates all intiial components(one canvas, left panel, top left panel)
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
        self.zoom = False
        self.imscale = 1.0 #image zoom factor

        self.points = []
        self.data = []

        self.ovals = []
        self.polygons = []

        #initialize and bind components 
        parent.title('Segment Images')
        self.parent.config(cursor='tcross')

        #weight > rest(0), resized when window size changed
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(1, weight=1)

        self.select_pressed = BooleanVar(parent)

        self.canvas = Canvas(parent, width=400, height=400, bg='white')
        self.canvas.grid(row=1, column=1, sticky = N+S+E+W, pady=5)

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
        
        self.canvas.bind('<MouseWheel>', self.next_image)
        self.canvas.bind('<ButtonPress-1>', self.move_from)
        self.canvas.bind('<B1-Motion>', self.move_to)

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

        instruction = Label(self.f2, text='Click Ctrl + Z to undo point or contour creation \n\n Hold down spacebar to pan image \n\n press = on the keyboard or the zoom in button \n and select a rectangle area to zoom in')
        instruction.grid(row=8, column=0, columnspan=3)

        #keyboard input binding
        parent.bind_all('<Control-z>', lambda x: self.undo_point())
        parent.bind_all('<KeyPress-space>', lambda x, a = True: self.allow_pan(a))
        parent.bind_all('<KeyRelease-space>', lambda x, a = False: self.allow_pan(a))
        parent.bind_all('<KeyPress-equal>', lambda x: self.allow_zoom())
        parent.bind_all('<Enter>', lambda x: parent.focus())

        #undo_btn = Button(self.f2, text='Undo Point', command=self.undo_point)
        #undo_btn.grid(row=3, column=0, pady=5, sticky=W)

        #if run from .exe, diff fpath
        basepath = ''
        if getattr(sys, 'frozen', False):
            basepath = sys._MEIPASS + '\\'

        self.zoom_in = ImageTk.PhotoImage(Image.open(basepath + 'zoom_in.png').resize((20,20)))
        zoomin_btn = Button(self.f2, image = self.zoom_in, width=20, height=20, command=self.allow_zoom)
        zoomin_btn.grid(row=4, column=3, pady=5, sticky=W)

        self.zoom_out = ImageTk.PhotoImage(Image.open(basepath + 'zoom_out.png').resize((20,20)))
        zoomout_btn = Button(self.f2, image = self.zoom_out, width=20, height=20, command=lambda zoom=-0.5:self.zoomer(zoom))
        zoomout_btn.grid(row=4, column=2, pady=5, sticky=E)

        #image number
        self.im_show = StringVar(self.f2)
        self.im_show.set('Image Slice: 1')

        im_label = Label(self.f2, textvariable=self.im_show)
        im_label.grid(row=7, column=0, columnspan=2)

        #error label
        self.error = StringVar(self.f2)
        error_label = Label(self.f2, textvariable=self.error)
        error_label.grid(row=6, column=0, columnspan=2)

    #if a folder is selected, display all files within it - if all the files are dcms, give an option to display
    #at least one folder must be zipped in order to navigate
    def explore(self, file, side, win=None, zip=None):
        if win:
            win.destroy()

        if zipfile.is_zipfile(file): #open zip givenfile path
            win = Toplevel(self.parent)

            zip = zipfile.ZipFile(file)
            filelist = zip.namelist()
            filelist = sorted(filelist)

            for i in range(0, len(filelist)):
                f = filelist[i]
                if f.split('/')[-1] == '': #directories
                    btn = Button(win, text=f, 
                                 command=lambda win=win, zip=zip, name=f, side=side : self.explore(name, side, win, zip))
                    btn.grid(row=i, column=0)

        elif zip and file.split('.')[-1] != 'zip': #open directory from zip
            prev_path = file.split('/')
            filelist = zip.namelist()
            filelist = sorted(filelist)

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
            filelist.pop(0)
            filelist = sorted(filelist)

            win = Toplevel(self.parent)
            for i in range(0, len(filelist)):
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

    #once a folder with dcms is selected, read and store those
    def select(self, file, side, win, zip): 
        filelist = zip.namelist()

        #in alphabetical order
        filelist = sorted(filelist)

        for i in range (1, len(filelist)):
            dcm = zip.read(filelist[i])
            dcm = BytesIO(dcm)

            ds = dicom.dcmread(dcm).pixel_array

            #equalize, sets contrast/brightness initially
            ds = exposure.equalize_adapthist(ds) * 255

            pil_im = Image.fromarray(ds).convert('L')
            
            pil_im = pil_im.resize((int(pil_im.size[0]), 
                                    int(pil_im.size[1])))

            if side == 'left':
                self.images.append(pil_im)
            elif side == 'right':
                self.images_right.append(pil_im)

        #modify image list if there are two
        l = len(self.images)
        r = len(self.images_right)

        if side == 'left':
            self.im_size = self.images[0].size
        elif side == 'right':
            self.im_size = self.images_right[0].size

        if r > 0 and l > r:
            diff = l-r
            self.images = self.images[int(diff/2):l-int(diff/2)]
        elif l > 0 and r > l:
            diff = r-l
            self.images_right = self.images_right[int(diff/2):r-int(diff/2)]

        #array with pil images

        self.select_pressed.set(True)
        win.destroy()
        del ds, pil_im

    #when user chooses to select a file : create a canvas with image and controls
    def select_image(self, name):

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
            self.change_image(self.im_index+1, 'left', 'next') #change left image

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

            #create option to open second image

            self.btn_right = Button(self.parent, text='Select Image', command=lambda name='right':self.select_image(name), bg='gray')
            self.btn_right.grid(row=0, column=3, sticky=W)


        elif name == 'right':
            #create canvas and bind
            self.canvas_right = Canvas(self.parent, width=400, height=400, bg='white')
            self.canvas_right.grid(row=1, column=2, sticky = N+S+E+W, pady=5)

            #on create sync position with left canvas
            self.canvas_right.scan_mark(int(self.canvas.canvasx(0)), 
                                  int(self.canvas.canvasy(0)))
            self.canvas_right.scan_dragto(0, 0, gain=1)

            self.canvas_right.bind('<MouseWheel>', self.next_image)
            self.canvas_right.bind('<ButtonPress-1>', self.move_from)
            self.canvas_right.bind('<B1-Motion>', self.move_to)

            ftop2 = Frame(self.parent)

            r_lb = Label(ftop2, text='Image Name')
            r_lb.grid(row=0, column=4, sticky=W)
            self.r_title = Entry(ftop2)
            self.r_title.insert(-1, 'T1w')
            self.r_title.grid(row=0, column=5, sticky=W)
            
            ftop2.grid(row=0, column=2, sticky=W)

            #create image
            self.change_image(self.im_index+1, 'right', 'next') #change right image

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

    #saves a resized version of the image : saves time from resizing it everytime it is redrawn
    #can keep scaling up iamge by resizing and zooming in
    def update_saved_image(self):
        #im = self.images[self.im_index]
        for i in range(0, len(self.images)):
            im = self.images[i]
            self.images[i] = im.resize((int(self.im_size[0] * self.imscale +1), 
                            int(self.im_size[1] * self.imscale +1)))
       
        for j in range(0, len(self.images_right)):
            im_r = self.images_right[j]
            self.images_right[j] = im_r.resize((int(self.im_size[0] * self.imscale +1), 
                            int(self.im_size[1] * self.imscale +1)))

    #redraws the image and all the selections, done when the image needs to be redrawn
    def change_image(self, val, side, event):
        if event == 'next': #save zoomed images
            self.update_saved_image()
        
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
    
        if event == 'brightness' or 'next':
            b_converter = ImageEnhance.Brightness(im)
            im = b_converter.enhance(a)
        if event == 'contrast' or 'next':
            c_converter = ImageEnhance.Contrast(im)
            im = c_converter.enhance(b)


        cn.delete('all')
        # +1 to avoid im with size 0 (zoom out too much)
        if side == 'left':
            self.im_left = ImageTk.PhotoImage(im)
            self.im_left_cn = cn.create_image(0, 0, image=self.im_left, anchor=N+W)
        elif side == 'right':
            self.im_right = ImageTk.PhotoImage(im)
            self.im_right_cn = cn.create_image(0, 0, image=self.im_right, anchor=N+W)

        
        self.draw_contours(im)

    #delets all canvas elements in a given list
    def delete_canvas_elements(self, list):
        for i in list:
            self.canvas.delete(i)
            del i
        self.canvas.update()

    #deletes all canvas addons (selected points/lines)
    def deleteall_canvas(self, canvas):
        l = canvas.find_all()
        for id in l:
            coords = canvas.coords(id)

            if len(coords) > 2:
                canvas.delete(id)
        self.canvas.update()

    #duplicates all objects from one object to another - used for syncing left/right canvases
    def duplicate_objects(self, canvas_a, canvas_b, color):
        l = canvas_a.find_all()

        for i in range(1, len(l)): #first one is image, skip
            id = l[i]
            coord_list = canvas_a.coords(id)

            if len(coord_list) == 4: #oval coords
                canvas_b.create_oval(coord_list, fill=color, outline=color)
            elif len(coord_list) > 4:
                canvas_b.create_polygon(coord_list, outline=color, fill='')

    #draws all the points and shapes selected on both canvases
    def draw_contours(self, im):
        points = self.points
        index = self.im_index

        self.delete_canvas_elements(self.ovals)
        self.delete_canvas_elements(self.polygons)

        self.ovals = [] #reset oval locs on zoom
        self.polygons = []

        if points[index] != None:
            for i in range(0, len(points[index])):
                cont = points[index][i]
                if cont != None:
                    #draw points
                    cont_scaled=[]
                    
                    for j in range(0, len(cont)):
                        p = cont[j]
                        if p != None:
                            x = p[0] * self.imscale
                            y = p[1] * self.imscale
                            cont_scaled.append(x)
                            cont_scaled.append(y)

                            if i == len(points[index])-1:
                                o = self.canvas.create_oval(x-1, y-1, x+1, y+1, outline='blue', fill='blue')
                                self.ovals.append(o)
                                self.canvas.update()

                    #draw connecting lines if saved contour
                    if len(cont) > 2 and i != len(points[index])-1:
                        self.polygons.append(self.canvas.create_polygon(cont_scaled, outline='blue', fill=''))
                        self.canvas.update()

        #copy all from first canvas onto second one
        if len(self.images_right) > 0:
            self.duplicate_objects(self.canvas, self.canvas_right, 'blue')

        return im

    #draws lines that connect each point in points
    def connect_points(self, points, im):
        prev = points[0]
        for curr in points:
            im.line([prev, curr], fill='blue', width=1)
            prev = curr

    #next 4 update brightness/contrast variables and call to redraw image
    def change_brightness(self, val):
        self.alpha = float(val)

        self.change_image(self.im_index+1, 'left', 'brightness')

    def change_contrast(self, val):
        self.beta = float(val)
    
        self.change_image(self.im_index+1, 'left', 'contrast')

    def change_brightness_right(self, val):
        self.alpha_right = float(val)

        self.change_image(self.im_index+1, 'right', 'brightness')

    def change_contrast_right(self, val):
        self.beta_right = float(val)
    
        self.change_image(self.im_index+1, 'right', 'contrast')
  
    #on scroll, change displayed image and redraw
    def next_image(self, event):
        l = len(self.images)

        if event.delta > 0 and self.im_index < l-1:
            self.im_index += 1
        elif event.delta < 0 and self.im_index > 0:
            self.im_index -= 1

        self.im_show.set('Image Slice: ' + str(self.im_index+1))

        self.update_all('next')

    #if certain keys pressed, allow zoom and register clicks as zoom selection
    def allow_zoom(self):
        self.zoom = True

    #zoom out linearly by pressing - magnification button
    def zoomer(self, scale): 
        scale *= self.imscale
        factor = abs(self.imscale + scale) / self.imscale

        imscale = abs(self.imscale+scale)
        if imscale >= 1.0:
            self.imscale = abs(self.imscale + scale)

        if len(self.images) > 0:
            im = self.images[self.im_index]
        if len(self.images_right) > 0:
            im = self.images_right[self.im_index]

        self.canvas.scale('all', self.canvas.canvasx(self.canvas.winfo_width()/2), 
                          self.canvas.canvasy(self.canvas.winfo_height()/2), scale, scale)
        #self.canvas.scale('all', 0, 0, scale, scale)

        if hasattr(self, 'canvas_right'):
            self.canvas_right.scale('all', 0, 0, scale, scale)

        self.update_saved_image()
        self.update_all('')

    #draws a rectangle as user moves their mouse after selecting first point
    def zoom_rec(self, event, coords):
        
        coords2 = self.true_coordinates(event.x, event.y)
        
        coords = (coords[0] * self.imscale, coords[1] * self.imscale)
        coords2 = (coords2[0] * self.imscale, coords2[1] * self.imscale)

        #show rec on left canvas
        if len(self.images) > 0:
            im = self.images[self.im_index]
            im = im.convert('RGBA')
            draw = ImageDraw.Draw(im)

            draw.rectangle([coords, coords2], outline=(255, 0, 0), width=1)

            self.im_l = ImageTk.PhotoImage(im)
            rec_im_left = self.canvas.create_image(0, 0, image=self.im_l, anchor=N+W)

        #show rec on right canvas
        if len(self.images_right) > 0:
            im = self.images_right[self.im_index]
            im = im.convert('RGBA')
            draw = ImageDraw.Draw(im)

            draw.rectangle([coords, coords2], outline=(255, 0, 0), width=1)

            self.im_r = ImageTk.PhotoImage(im)
            rec_im_right = self.canvas_right.create_image(0, 0, image=self.im_r, anchor=N+W)
 
    #is space bar pressed, allows pan when dragging canvas and changes cursor
    def allow_pan(self, a):
        if a:
            self.pan = True
            self.parent.config(cursor='target')
        else:
            self.pan = False
            self.parent.config(cursor='tcross')

    #when dragging canvas, save initial coordinates
    def move_from(self, event):
        if self.pan:
            x = event.x
            y = event.y

            self.canvas.scan_mark(x, y)

            if hasattr(self, 'canvas_right'):
                self.canvas_right.scan_mark(x, y)
        else:
            self.add_point(event)

    #get new coordinates that user dragged to and move canvas
    def move_to(self, event):
        if self.pan:
            x = event.x
            y = event.y

            self.canvas.scan_dragto(x, y, gain=1)

            if hasattr(self, 'canvas_right'):
                self.canvas_right.scan_dragto(x, y, gain=1)

    #add point or zoom in with a rectangle when canvas clicked
    def add_point(self, event):
        #if zoom enabled and first point not placed, save initial coords
        if self.zoom and not hasattr(self, 'im_l'):
            self.parent.config(cursor='hand1')
            coords = self.true_coordinates(event.x, event.y)

            self.canvas.bind('<Motion>', lambda event, coords = coords : self.zoom_rec(event,coords))

            self.zoom_coords = event

        #if zoom enabled and first point placed, save rectangle and calculate zoom/pan required
        elif self.zoom:
            self.parent.config(cursor='tcross')
            rec = [(self.zoom_coords.x, self.zoom_coords.y),
                   (self.zoom_coords.x, event.y),
                   (event.x, event.y),
                   (event.x, self.zoom_coords.y)]

            top_left = np.array(rec[0])

            #find top left corner
            for i in range(1,4):
                if rec[i][0] < top_left[0]:
                    top_left[0] = rec[i][0]
                if rec[i][1] < top_left[1]:
                    top_left[1] = rec[i][1]

            #zoom in
            orig = self.imscale

            if top_left[0] < top_left[1]:
                self.imscale *= self.canvas.winfo_width() / abs(rec[0][0] - rec[2][0])
            else:
                self.imscale *= self.canvas.winfo_height() / abs(rec[0][1] - rec[2][1])

            factor = abs(self.imscale) / orig

            if len(self.images) > 0: #save zoomed
                im = self.images[self.im_index]
                self.update_saved_image()

                self.im_left = ImageTk.PhotoImage(self.images[self.im_index])
                self.im_left_cn = self.canvas.create_image(0,0,image=self.im_left, anchor=N+W)
            if len(self.images_right) > 0:
                im = self.images_right[self.im_index]
                self.update_saved_image()

                self.im_right = ImageTk.PhotoImage(self.images[self.im_index])
                self.im_right_cn = self.canvas.create_image(0,0,image=self.im_right, anchor=N+W)

            #pan to rectangle
            c = self.true_coordinates(top_left[0], top_left[1])

            x = c[0] * factor * self.imscale
            y = c[1] * factor * self.imscale

            #height and width move over
            self.canvas.scan_mark(int(x - self.canvas.canvasx(0)), 
                                  int(y - self.canvas.canvasy(0)))
            self.canvas.scan_dragto(0, 0, gain=1)
            self.canvas.update()

            if hasattr(self, 'canvas_right'):
                self.canvas_right.scan_mark(int(x - self.canvas_right.canvasx(0)), 
                                      int(y - self.canvas_right.canvasy(0)))
                self.canvas_right.scan_dragto(0, 0, gain=1)
                self.canvas_right.update()

            #reset 
            self.canvas.unbind('<Motion>')
            del self.zoom_coords
            if hasattr(self, 'im_l'):
                del self.im_l
            if hasattr(self, 'im_r'):
                del self.im_r
            self.zoom = False

            self.update_all('zoom')

        #otehrwise, user selects a point to add, updated poits list and draw circle on canvas
        elif len(self.images) > 0 or len(self.images_right) > 0:
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

            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)

            o = self.canvas.create_oval(x-1, y-1, x+1, y+1, fill='blue', outline='blue')
            self.ovals.append(o)
            self.canvas.update()

            if hasattr(self, 'canvas_right'):
                self.canvas_right.create_oval(x-1, y-1, x+1, y+1, fill='blue', outline='blue')
                self.canvas_right.update()
        
    #undo point and redraw all canvas circles/shapes (quicker than redrawing image)
    def undo_point(self):
        curr = len(self.points[self.im_index]) - 1

        if self.points[self.im_index] == None or self.points[self.im_index][curr] == None:
            self.error.set('no points selected to undo')
        elif self.points[self.im_index][curr] == [None] and len(self.points[self.im_index]) > 1:
            del self.points[self.im_index][curr]
            del self.data[-1]

            self.change_image(self.im_index+1, 'left', 'point')
        elif len(self.points[self.im_index][curr]) == 1:
            self.points[self.im_index][curr] = [None]
        elif len(self.points[self.im_index][curr]) > 1:
            del self.points[self.im_index][curr][-1]

        if len(self.ovals) > 0:
            self.canvas.delete(self.ovals[-1])
            del self.ovals[-1]
            self.canvas.update()

        if hasattr(self, 'scale_right'):
            self.deleteall_canvas(self.canvas_right)
            self.duplicate_objects(self.canvas, self.canvas_right, 'blue')

    #calculate area and append info to table
    def save_contour(self):
        #add with target to df array: slice + target + coords
        if self.target_input.get() == '':
            print('enter target id')
            self.error.set('enter target id')
        elif self.points[self.im_index][-1] == None or self.points[self.im_index][-1] == [None]:
            self.error.set('no points selected')
        else:
            self.error.set('')
            #divide by upsample val for points and area
            points = self.points[self.im_index][-1]
            area = self.area(points)

            self.data.append([self.im_index, self.target_input.get(), 
                              points, area])
            self.points[self.im_index].append([None])

            self.draw_contours(self.images[self.im_index])

    #reset entire canvas by reinitializing
    def reset(self):
        self.__init__(self.parent)

    #draw all the saved contours on the image
    def image_with_contours(self, points, index, im):
        if points[index] != None:
            for i in range (0, len(points[index])):
                cont = points[index][i]
                if cont != None:
                    cont_scaled = []
                    #draw contour points
                    draw = ImageDraw.Draw(im)
                    for j in range(0, len(cont)):
                        p = cont[j]
                        if p != None:
                            p = (p[0] * self.imscale, p[1] * self.imscale)
                            cont_scaled.append(p)
                            draw.ellipse((p[0], p[1], p[0]+1, p[1]+1), fill='blue', outline='blue')

                    #draw connecting lines
                    if len(cont) > 1:
                        self.connect_points(cont_scaled, draw)

                    #colour in contour if not line
                    if len(cont) > 2 and i != len(points[index])-1:
                        poly = im.copy()
                        poly_draw = ImageDraw.Draw(poly)
                        poly_draw.polygon(cont_scaled, fill='blue')

                        im = Image.blend(im, poly, 0.2)

        return im

    #exports datatable to user-chosen location
    def export(self):
        print('export')

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

    #converts all images with drawn contours to a tiff stack
    def to_tiff(self, ims, fpath):
        fpath = fpath.replace('*', '')
        with tiff.TiffWriter(fpath) as stack:
            for i in range(0, len(ims)):
                #draw contours on images
                im = self.image_with_contours(self.points, i, ims[i].convert('RGBA'))
                stack.write(np.array(im))

    #finds image coords given canvas coords, decimal pixels relative to original size
    def true_coordinates(self, x, y):
        true_x = (x + self.canvas.canvasx(0)) / self.imscale
        true_y = (y + self.canvas.canvasy(0)) / self.imscale

        return (true_x, true_y)

    #find area given point list
    def area(self, cont):
        area = 0.0
        n = len(cont)
        for i in range(n):
            j = (i + 1) % n
            area += cont[i][0] * cont[j][1] #x1y2 - x2y1
            area -= cont[j][0] * cont[i][1]
        area = abs(area) / 2.0

        return area

    #updates left and right canvas depedning if they exist
    def update_all(self, event):
        if len(self.images) > 0:
            self.change_image(self.im_index+1, 'left', event)
        if len(self.images_right) > 0:
            self.change_image(self.im_index+1, 'right', event)
 

#start
root = Tk()
SegmentMRI(root)
root.mainloop()

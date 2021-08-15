from tkinter import *
from tkinter import filedialog

import os
import zipfile
from io import BytesIO

def explore(file, win=None, zip=None):
    if win:
        win.destroy()

    if zipfile.is_zipfile(file): #open zip givenfile path
        win = Toplevel(root)

        zip = zipfile.ZipFile(file)
        filelist = zip.namelist()

        for i in range(0, len(filelist)):
            f = filelist[i]
            if f.split('/')[-1] == '': #directories
                btn = Button(win, text=f, 
                             command=lambda win=win, zip=zip, name=f : explore(name, win, zip))
                btn.grid(row=i, column=0)

    elif zip and file.split('.')[-1] != 'zip': #open directory from zip
        prev_path = file.split('/')
        filelist = zip.namelist()

        win = Toplevel(root)
        for i in range(0, len(filelist)):
            f = filelist[i]
            new_path = f.split('/')

            if prev_path[len(prev_path)-2] == new_path[len(new_path)-2] and file != f:
                btn = Button(win, text=f, 
                             command=lambda win=win, zip=zip, name=f: explore(name, win, zip))
                btn.grid(row=i, column=0)

    elif zip: #open zip from directory in zipfile object
        newzip_data = BytesIO(zip.read(file))
        newzip = zipfile.ZipFile(newzip_data)
        filelist = newzip.namelist()

        win = Toplevel(root)
        for i in range(1, len(filelist)):
            f = filelist[i]
            btn = Button(win, text=f, 
                             command=lambda win=win, zip=zip, name=f: explore(name, win, zip))
            btn.grid(row=i, column=0)

    #if all in window are dcm images, option to select folder
    if win: 
        is_dcm = True
        for w in win.winfo_children():
            if w.cget('text').split('.')[-1] != 'dcm':
                is_dcm = False
                break

        if is_dcm:
            #select button header
            select_btn = Button(win, text='Select', background='blue',
                                command=lambda win=win, zip=zip, name=file : select(name, win, zip))
            select_btn.grid(row=win.grid_size()[1], column=0)

def select(file, win, zip):
    win.destroy()

    #loop thorugh images in folder and add to array



root = Tk()

file = filedialog.askopenfilename()
explore(file)

root.mainloop()


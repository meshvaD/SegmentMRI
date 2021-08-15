from tkinter import *

class Simple(Frame):
    def __init__(self, parent):
        self.canvas = Canvas(parent, width=400, height=400, bg='white')
        self.canvas.grid(row=1, column=1, sticky = N+S+E+W, pady=5)

        self.canvas.bind('<MouseWheel>', self.scroll)

    def scroll(self, delta):
        print('do something')

root = Tk()
Simple(root)
root.mainloop()


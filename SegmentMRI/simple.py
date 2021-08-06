import pydicom as dicom
from PIL import Image, ImageShow
import numpy as np
from skimage import exposure


ds = dicom.dcmread('C:/Users/HS student/Downloads/15-t1_tse_cor_1_5mm_post/E1S15I001.MR.dcm')
#ds = dicom.dcmread('C:/Users/HS student/Downloads//01-localizer/E1S1I001.MR.dcm')

if 'WindowWidth' in ds:
    print('Dataset has windowing')

#ds2 = dicom.pixel_data_handlers.util.apply_voi_lut(ds.pixel_array, ds)
#ds2 = np.array(ds2, dtype='uint16')

ds2 = exposure.equalize_adapthist(ds.pixel_array)

#ds2 = cv.cvtColor(ds2, cv.COLOR_BGR2RGB)

im2 = Image.fromarray(ds2 * 255)
im2.show(title='ds 2')

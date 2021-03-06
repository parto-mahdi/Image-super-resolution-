# -*- coding: utf-8 -*-
"""CNN_Code_Kyriazis_Creato_Parto

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1aolZddOHVhLOnvjWcvn6phD8Uk0LiriL

##Image Super resolution project for DRRA course


> Authors : Athanasios , Elisea , Mahdi
"""

# Commented out IPython magic to ensure Python compatibility.
# Install TensorFlow
try:
#   %tensorflow_version 2.x
except Exception:
  pass

import tensorflow as tf

# %load_ext tensorboard

from tensorflow.python.client import device_lib

print('Tensorflow version:')
!python3 -c 'import tensorflow as tf; print(tf.__version__)'

import datetime, os

import numpy as np
import matplotlib.pyplot as plt
import glob
import PIL as pil

from tensorflow import keras
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D, AveragePooling2D, InputLayer
from tensorflow.keras.losses import binary_crossentropy, categorical_crossentropy
from tensorflow.keras.optimizers import SGD
from tensorflow.keras.metrics import Precision, Recall
from tensorflow.keras.utils import to_categorical

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth, files
from oauth2client.client import GoogleCredentials

# Google drive accessing - follow instructions
auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
googledrive = GoogleDrive(gauth)

# Google drive accessing - follow instructions
from google.colab import drive
drive.mount('drive')

# Accessing Elisea's drive because zip files of dataset are in her Google drive
id_train_HR = '1NDIYmpaAVdNadQPvEvFgaybLIPDJqme5'   # train HR
id_train_LR =  '1TfoSS3PZXKbmB1c4tE-JN8QwODZTSOY_'  # train LR (bicubic, 2x)
id_valid_HR = '1DFaZaoGbeL6yXxV5MXqcg_IIA6Rm0pc_'   # validation HR
id_valid_LR = '1WGGm3q5tYzeKcxytziLRwptnPGmis7ym'   # validation LR (bicubic, 2x)


## Unziping in Colab-provided space
train_HR = googledrive.CreateFile({'id': id_train_HR})
train_HR.GetContentFile('DIV2K_train_HR.zip')
!unzip 'DIV2K_train_HR.zip'

train_LR = googledrive.CreateFile({'id': id_train_LR})
train_LR.GetContentFile('DIV2K_train_LR_bicubic_X2.zip')
!unzip 'DIV2K_train_LR_bicubic_X2.zip'

valid_HR = googledrive.CreateFile({'id': id_valid_HR})
valid_HR.GetContentFile('DIV2K_valid_HR.zip')
!unzip 'DIV2K_valid_HR.zip'

valid_LR = googledrive.CreateFile({'id': id_valid_LR})
valid_LR.GetContentFile('DIV2K_valid_LR_bicubic_X2.zip')
!unzip 'DIV2K_valid_LR_bicubic_X2.zip'

''' 
Load datasets based on their role:
    - 'train' - for training dataset
    - 'valid' - for validation dataset
    - returns a tuple of two lists:
        data_lr: list of low-res full-paths
        data_hr: list of high-res full-paths
'''
def get_data(dataset):
    data_lr = []
    data_hr = []

    if dataset == 'train':
      print(f'Loading {dataset}-dataset')
      home_folderLR = 'DIV2K_train_LR_bicubic/X2/'
      home_folderHR = 'DIV2K_train_HR/'

      image_lr_list = sorted(os.listdir(home_folderLR))
      image_hr_list = sorted(os.listdir(home_folderHR))

    elif dataset == 'valid':
      print(f'Loading {dataset}-dataset')
      home_folderLR = 'DIV2K_valid_LR_bicubic/X2/'
      home_folderHR = 'DIV2K_valid_HR/'

      image_lr_list = sorted(os.listdir(home_folderLR))
      image_hr_list = sorted(os.listdir(home_folderHR))

      assert len(image_lr_list) == len(image_hr_list)
    else:
       raise Exception("Unknown dataset")

    for i in range(len(image_lr_list)):
      data_lr.append(os.path.join(home_folderLR, image_lr_list[i]))
      data_hr.append(os.path.join(home_folderHR, image_hr_list[i]))
      
    print(f'Finished {dataset}-dataset')
    return data_lr, data_hr

### Utility functions

'''
Rescale range [0, 255] to range [0, 1]
'''
def normalize(im):
    if im.max() > 1.0:
        im = np.divide(im, 255., dtype=np.float32)  # to float32 instead of uint8
    assert im.max() <= 1.0
    return im


'''
Given the full-path of a file, return its name.
'''
def extractName(filepath):
  return filepath.split('/')[-1]


'''
Outputs dimensions without loading the image to memory.
Important in filtering-out based on image size.
'''
def extractDimensions(imagePath):
  fp = pil.Image.open(imagePath)
  size = fp.size
  fp.close
  return size


''' 
Filtering-out images whose smaller dimension is larger than a threshold.
We work on LR, but we also filter out the respective HR.
  - threshold: The selection of the threshold is desribed in the report.
'''
def filterLarge(lrPathlist, hrPathlist, low_res_height_threshold = 678):
  lr_list = []
  hr_list = []
  for index, imgPath in enumerate(lrPathlist):
    if min(extractDimensions(imgPath)) >= low_res_height_threshold:
      lr_list.append(imgPath)
      hr_list.append(hrPathlist[index])
  return lr_list, hr_list


'''
For every possible image-smallest-dimension (threshold_i), calculates and
plots how many images have image-smallest-dimension < threshold_i
'''
def threshold_plotter():
  
  threshold_i = 0  # The smallest dimension.
  l=[]
  x=[]
  t_data = get_data('train')
  
  # For every threshold, collect the number of accepted images.
  while threshold_i < 1020:  # The largest min(width, height)encountered is 1020.
    x.append(threshold_i)
    l.append(len(filterLarge(t_data[0], t_data[1], threshold_i)[0]))
    threshold_i+=1
  
  # Plotting
  plt.figure()
  plt.title('Accepted images for every threshold')
  plt.plot(x,l,'.', label = 'No of images')
  plt.xlabel('Threshold')
  plt.ylabel('No of accepted images') 
  plt.grid()
  plt.axhline(678, color='r', linestyle='--', label = 'Chosen threshold')
  plt.legend()


'''
If an image has a "portrait" orientation, rotate to "lanscape".
'''
def landscapizeImage(img):
    img = plt.imread(img)
    h, w = img.shape[0], img.shape[1]
    if h > w: 
      return np.rot90(img)
    else:
      return img


'''
Assuming the subject is centered, we prefer to crop symmetrically to 
maintain the central region.
'''
def cropImage(img, finalHeight):
  initHeight, initWidth = img.shape[0], img.shape[1]
  if initHeight == finalHeight:
    return img
  else:
    centerHeight = initHeight//2
    # Width has beem checked and is always good. No change.
    return img[centerHeight - finalHeight//2 : centerHeight + finalHeight//2, :] 


'''
Cut the border of an image by a certain amount. 
Used on HR dataset to allign with the size reduction caused by convolution on 
LR dataset.
'''
def crop_y(img, amount):
  if amount == 0:
    return img
  else:
    return img[amount : -amount, amount : -amount, :]


'''
Store an image in a specified directory path.
'''
def storeImage(img, dst): 
  # For our use, wee first convert to [0, 255].
  im = pil.Image.fromarray((img*255).astype(np.uint8))
  im.save(dst)

'''
Operates on the filtered images. Makes sure that all are cropped and in
"lanscape" oritentation. Saved in different directory; originals are maintained.
  - imgPathlist: List of paths of filtered images.
  - store_dir: The target directory
  - threshold: see cropImage inline comment.
'''
def pre_process(imgPathlist, store_dir, threshold):
  
  for image in imgPathlist:
    name = extractName(image)
    dstPath = os.path.join(store_dir, 'pp' + name)
    
    image_l = landscapizeImage(image)
    image_lc = cropImage(image_l, threshold)
    
    storeImage(image_lc, dstPath)

# Plot threshold graph (produce threshold analysis graph)
threshold_plotter()

### CREATE THE PREPROCESSED DATASET

## MAKE THE DIRECTORIES 
#!rm -r preProcessed  # Uncomment to clean before mkdir and start fresh.
!mkdir -p preProcessed/train/pp_lr
!mkdir -p preProcessed/train/pp_hr
!mkdir -p preProcessed/valid/pp_lr
!mkdir -p preProcessed/valid/pp_hr

## PREPROCESSING PIPELINE  

'''
Creates a new directory and prepares the dataset for feeding to the neural network:
    - train - for training dataset
    - valid - for validation dataset
At the end we have images with the same size and rotaion for both training and validation dataset
'''
def prepareImages(low_res_threshold, dataset_role):
  start_time = datetime.datetime.now().replace(microsecond=0)
  xRaw, yRaw = get_data(dataset_role)

  if dataset_role == 'train':
    mainDir = 'preProcessed/train'
  elif dataset_role == 'valid':
    mainDir = 'preProcessed/valid'
  
  xFilt, yFilt = filterLarge(xRaw, yRaw, low_res_threshold)
  
  pre_process(xFilt, os.path.join(mainDir,'pp_lr'),low_res_threshold)
  pre_process(yFilt, os.path.join(mainDir,'pp_hr'),low_res_threshold*2)

  print(f'Images Ready {len(xFilt)} x2 processed')
  print(f'Time elapsed: {datetime.datetime.now().replace(microsecond=0)-start_time}')

# PREPROCESSING for training dataset
# It takes about 18-19 min to complete.
prepareImages(678, 'train')

# PREPROCESSING for validation dataset
prepareImages(678, 'valid')

# It checks and verifies that all images of low and high resolution have the proper size
import cv2

def dimensionAssertion(directory, default_shape):
  for el in os.listdir(directory):
    assert extractDimensions((os.path.join(directory,el))) == default_shape
  print(f'Directory: {directory}, asserted')

dimensionAssertion('preProcessed/train/pp_lr', (1020, 678))  
dimensionAssertion('preProcessed/train/pp_hr', (2040, 1356))
dimensionAssertion('preProcessed/valid/pp_lr', (1020, 678))  
dimensionAssertion('preProcessed/valid/pp_hr', (2040, 1356))

### Defining the MODEL
'''
Creating a clip function to force the output of the network between 0 and 1
'''
def clip_values(x):
  return tf.clip_by_value(x, 0, 1)
'''
Construct the CNN model.
  - f1: Filter-size in the first layer
  - f3: Filter-size in the third layer
  - Filter-size in the second layer is 1
'''
def get_model_CNN(f1, f3, loss_f, learn_rate):  
  # redefine for convenience
  precision, recall = Precision(), Recall()

  model = Sequential()
  model.epoch = 0  # to save amount of epochs trained

  model.add(InputLayer((1356, 2040, 3)))
  # 64 filters in layer 1.
  model.add(Conv2D(64, (f1,f1), activation='relu'))
  # 32 filters in layer 2.
  model.add(Conv2D(32, (1,1), activation='relu'))
  # 3 filters in layer 3.
  model.add(Conv2D(3, (f3,f3), activation=clip_values)) 
  model.compile(loss=loss_f,
              optimizer=SGD(learn_rate),
              metrics=['accuracy', precision, recall])
  return model

### MODEL CONFIGURATION PARAMETERS

##Learning rate
lr_rate = 1e-1

## Kernel sizes
f1 = 9  # Filter-size in the first layer
f3 = 5  # Filter-size in the third layer

## Convolution intrinsically cuts the border, based on filter sizes.
conv_border_cut = (f1+f3-2)//2

# Instantiate the model
CNN_model = get_model_CNN(f1, f3, 'mean_squared_error', lr_rate)

# Prints a summary of our model.
CNN_model.summary()

# creating a folder in the Drive to store weights and logs
CNN_imageSR = 'drive/My Drive/CNN_imageSR'
logs_folder = os.path.join(CNN_imageSR, 'logs')
weights_folder = os.path.join(CNN_imageSR, 'weights')
if not os.path.exists(weights_folder):
    os.makedirs(weights_folder)

# Attempt to use a non-stopping generator. (based on documentation comments)
# Because of the size of data, we cannot store all images in one array so we need a generator.
import cv2
 
def generate_pairs2(role, batch_size=3, crop_size=6):
  if role == 'train':
    home_folder = 'preProcessed/train/'
  elif role == 'valid':
    home_folder = 'preProcessed/valid/'
  
  lrPath = os.path.join(home_folder,'pp_lr')
  lrPathList = sorted(os.listdir(lrPath))

  hrPath = os.path.join(home_folder,'pp_hr')
  hrPathList = sorted(os.listdir(hrPath))

  upscaling_factor = 2
  
  j = 0  # It is a counter for going through all data and also we need a condition to avoid 
         # out of index error
  while True:  
    if j>len(lrPathList)-56-batch_size:  # We kept the last 56 six images out of 656 for testing 
      j = 0   # If it wants to go out of index for images, it reset the counter
    batch_features = []
    batch_labels = []
    for i in range(batch_size):
      img = cv2.imread(os.path.join(lrPath, lrPathList[i+j]), cv2.IMREAD_UNCHANGED)
      img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
      width = int(img.shape[1] * upscaling_factor)
      height = int(img.shape[0] * upscaling_factor)
      dim = (width, height)
      x_resized = cv2.resize(img, dim, interpolation = cv2.INTER_CUBIC)  # Resizing images by Bicubic Interpolation method
      x_resized = normalize(x_resized)
      batch_features.append(x_resized)
      y = plt.imread(os.path.join(hrPath, hrPathList[i+j]))
      y = crop_y(y, crop_size)
      batch_labels.append(y)
    j += batch_size
    batch_features = np.array(batch_features)
    batch_labels = np.array(batch_labels)
    yield (batch_features, batch_labels)  # Generating two arreys in size batch size of both features and labels

# Train the network

# Generate the data for both training and validation dataset
g_train = generate_pairs2('train',4)
g_valid = generate_pairs2('valid',4)

# Creating checkpoints for saving weights and logs in google drive
t_now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
logdir = os.path.join(logs_folder, t_now)
tensorboard_callback = tf.keras.callbacks.TensorBoard(logdir, write_graph=False)
weightdir = os.path.join(weights_folder,  f"{t_now}_" + "{epoch}.hdf5")
checkpoint = tf.keras.callbacks.ModelCheckpoint(weightdir)


CNN_model.fit_generator(g_train, epochs=20, steps_per_epoch=150, validation_data = g_valid, validation_steps=22, callbacks = [tensorboard_callback, checkpoint])

# Commented out IPython magic to ensure Python compatibility.
# Creating and plotting graphs for both accuracy and loss according to saved logs
!kill 6216
# %tensorboard --logdir 'drive/My Drive/CNN_imageSR'

### Settings: Running the training for a range of different learning to find the best learning rate according to loss  
import math

n_lr = 14  # The number of learning rates which are being tested
lr = 1e-6 # The starting learning rate
step = math.sqrt(10) # The step used for increasing the learning rate

### Initialisation

# new model, new inititialisation of weights.


lst_train_cost = []
lst_valid_cost = []
g_train = generate_pairs2('train',4)
g_valid = generate_pairs2('valid',4)

for i in range(n_lr):  
  print('Number:',i)
  CNN_model = None  
  CNN_model = get_model_CNN(f1,f3,'mean_squared_error', 0)
  CNN_model.compile(loss='mse',
              optimizer=SGD(lr), # setting the learning rate
              metrics=['accuracy'])
  
  hist = CNN_model.fit_generator(g_train, epochs=2, steps_per_epoch=150, validation_data = g_valid, validation_steps=22)
            
  lst_train_cost.append(hist.history['loss'])
  lst_valid_cost.append(hist.history['val_loss'])
  
  lr = lr*step

## Plotting the graph for different learning rates
from statistics import mean
lr = 1e-6
lst_lr = []
for i in range (n_lr):
  lst_train_cost[i]=mean(lst_train_cost[i])
  lst_valid_cost[i]=mean(lst_valid_cost[i])
  lst_lr.append(lr)
  lr = lr*step
plt.figure()
plt.plot(lst_lr, lst_train_cost, label='training data')
plt.plot(lst_lr, lst_valid_cost, label='validation data')

plt.xlabel('learning rate')
plt.ylabel('loss')
plt.xscale('log')
plt.title('Loss in while increasing the learning rate')
plt.legend()

"""## Calculating PSNR"""

## It calculates PSNR between two images or between two arrays of images
import math

def psnr(img1, img2):
  mse = np.mean( (img1 - img2) ** 2 )
  if mse == 0:
    return 100
  PIXEL_MAX = 1
  return 20 * math.log10(PIXEL_MAX / math.sqrt(mse))

"""## For ploting one image to campare"""

home_folder = 'preProcessed/train/'

lrPath = os.path.join(home_folder,'pp_lr')
lrPathList = sorted(os.listdir(lrPath))

hrPath = os.path.join(home_folder,'pp_hr')
hrPathList = sorted(os.listdir(hrPath))
i = 639  # The number of an image in dataset which we want to visualize 

img = cv2.imread(os.path.join(lrPath, lrPathList[i]), cv2.IMREAD_UNCHANGED)
img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)

width = int(img.shape[1] * 2)
height = int(img.shape[0] * 2)
dim = (width, height)

# resize LR to uLR before feeding to the network
x_resized = cv2.resize(img, dim, interpolation = cv2.INTER_CUBIC)
x = normalize(x_resized)  # convert to [0,1] value range


y = plt.imread(os.path.join(hrPath, hrPathList[i]))

# cut the border of the HR image to have the same size with the CNN output (due to convolution)
y = crop_y(y, 6)
print("The original")
plt.imshow(y)

# Predicting of one specific image by trained network
d = []
d.append(x)
d = np.array(d)
y_pred = CNN_model.predict(d)
plt.imshow(y_pred[0])

d=psnr(y,y_pred[0])
print('Predicted image')
print('PSNR=',d)

# Printing the image resized by bicubic interpolation
x = crop_y(x, 6)
plt.imshow(x)
d=psnr(y,x)
print('Resized image by bicubic interpolation')
print('PSNR=',d)

"""## Testing"""

def test_function(model, num_sample,crop_size = 6):

  home_folder = 'preProcessed/train/'

  lrPath = os.path.join(home_folder,'pp_lr')
  lrPathList = sorted(os.listdir(lrPath))

  hrPath = os.path.join(home_folder,'pp_hr')
  hrPathList = sorted(os.listdir(hrPath))

  upscaling_factor = 2
  psnr_list_bicubic = []
  psnr_list_SR = []
  for i in range(len(lrPathList)-num_sample,len(lrPathList)):
      x_test = []
      img = cv2.imread(os.path.join(lrPath, lrPathList[i]), cv2.IMREAD_UNCHANGED)
      img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
      width = int(img.shape[1] * upscaling_factor)
      height = int(img.shape[0] * upscaling_factor)
      dim = (width, height)
      x_resized = cv2.resize(img, dim, interpolation = cv2.INTER_CUBIC)
      x_resized = normalize(x_resized)
      x_test.append(x_resized)
      y = plt.imread(os.path.join(hrPath, hrPathList[i]))
      true_img = crop_y(y, crop_size)
      x_test = np.array(x_test)
      true_img = np.array(true_img)
      y_pred = CNN_model.predict(x_test)
      y_pred = np.array(y_pred)
      x = crop_y(x_test[0], crop_size)
      psnr_list_bicubic.append(psnr(x,true_img))
      psnr_list_SR.append(psnr(y_pred[0],true_img))
  psnr_list_bicubic = np.array(psnr_list_bicubic)
  psnr_list_SR = np.array(psnr_list_SR)
  return np.mean(psnr_list_bicubic) , np.mean(psnr_list_SR)

# Testing of the whole test dataset and calculating mean PSNR
psnr_bicubic ,psnr_SR = test_function(CNN_model, 56)
print('PSNR for Bicubic interpolation', psnr_bicubic)
print('PSNR for Super resolution', psnr_SR)

# For calculting PSNR for differnet epochs because of time limit we couldn't run this for a wide range of ephocs
def psnr_compare(num_sample,learning_rate, max_ephochs,crop_size = 6):
  epochs_list = []
  psnr_bicubic_f = []
  psnr_SR_f = []
  for i in range(max_ephochs):
    epochs_list.append(i+1)
    CNN_model = None  
    CNN_model = get_model_CNN(f1,f3,'mean_squared_error', learning_rate)
    CNN_model.compile(loss='mse',
            optimizer=SGD(learning_rate), # setting the learning rate
            metrics=['accuracy'])

    CNN_model.fit_generator(g_train, epochs=i+1, steps_per_epoch=150, validation_data = g_valid, validation_steps=22)

    a ,b = test_function(CNN_model, num_sample, crop_size)
    psnr_bicubic_f.append(a)
    psnr_SR_f.apend(b)
  plt.figure()
  plt.plot(epochs_list, psnr_bicubic_f, label='Bicubic interpolation mean PSNR')
  plt.plot(epochs_list, psnr_SR_f, label='Super resolution mean PSNR')

  plt.xlabel('Number of epochs')
  plt.ylabel('Mean PSNR')
  plt.title('PSNR')
  plt.legend()

# Runing the function for calculating PSNR
psnr_compare(56,lr_rate, 10)
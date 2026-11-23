from PIL import Image
import numpy as np
im=Image.open(r'C:\Users\LENOVO\Downloads\123.png').convert('RGB'); a=np.array(im)
for x in [1600,1650,1700,1750,1800,2000,2150]:
 m=np.all(a[:,x]>=255,axis=1); runs=[];on=False
 for y,v in enumerate(m):
  if v and not on: st=y;on=True
  elif not v and on:
   if y-st>=10:runs.append((st,y-1,y-st))
   on=False
 print('x',x,runs[:30])

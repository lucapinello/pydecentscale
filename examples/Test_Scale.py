#!/usr/bin/env python
# coding: utf-8

# In[1]:


from pydecentscale import DecentScale
import asyncio
import time


# In[2]:


#Create the DecentScale object
ds=DecentScale()


# In[3]:


#Scan and connect to the first available decent scale
ds.auto_connect()

#Alternatively you can connect with a custom address with the method ds.connect(address)


# In[4]:


#The current weight is stored in ds.weight, however initially it is set to None
print('Weight value without notification enabled is:', ds.weight)


# In[5]:


#To read the current weight we need to first enable the BLE notifications
print('Enabling notifications...')
ds.enable_notification()
time.sleep(1)


# In[6]:


#Now we can read the current value, this read constinously values for 5 secondasad as fast as they arrive
print('Reading values...')
for i in range(50):
    if ds.weight:
        print('Current weight:%.1f' % ds.weight, end='\r')
    asyncio.run( asyncio.sleep(0.1))


# In[7]:


print('Testing led display...')

#Turn the led display on
ds.led_on()
time.sleep(1)


# In[8]:


#Turn the led display off
ds.led_off()
time.sleep(1)


# In[9]:


#Let's turn it back on so we can see the timer
ds.led_on()
time.sleep(1)


# In[10]:


print('Testing tare fuction...')
#Tare the scale
ds.tare()
time.sleep(1)


# In[11]:


print('Testing timer...')
#Start the timer
ds.start_time()
time.sleep(5)


# In[12]:


#Stop the timer
ds.stop_time()
time.sleep(1)


# In[13]:


#Reset the timer
ds.reset_time()
time.sleep(1)


# In[14]:


#This disable the BLE notifications for reading the weight
ds.disable_notification()
time.sleep(1)


# In[15]:


print('Disconnecting...')
#Finally we can disconnect
ds.disconnect()


# In[16]:


print('All done. Ciao!')






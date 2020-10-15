import os
import h5py

from datetime import datetime

with h5py.File("/home/suhong/research/carla_data/steer103_v5_town02/default_ImageSizeX=800_WeatherId=01/data_00005.h5", 'r') as data:
    # ['CameraLeft', 'CameraMiddle', 'CameraRight', 'SegLeft', 'SegMiddle', 'SegRight', 'targets']
    # print(type(data['CameraLeft'][0]))
    # for i in data['CameraMiddle']:
    #     print(i.shape)
    print(data['CameraMiddle'][1].shape)
    print(data['targets'][0].shape)
    print(1024*768)

print(str(datetime.now()))
current_date_and_time = datetime.now()
current_date_and_time_string = str(current_date_and_time)
extension = ".txt"
file_name =  current_date_and_time_string + extension
file = open(file_name, 'w')
file.close()
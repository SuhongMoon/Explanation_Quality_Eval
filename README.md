# Data Collection for Evaluating Explanation Quality
This repository is to collect data for evaluating explanation quality in CARLA 0.9.9. 
## Installation
### Install CARLA
You can find CARLA 0.9.9 in this [link](https://github.com/carla-simulator/carla/releases/tag/0.9.9). Please following these steps to install CARLA simulator.
1. Make directory you want to install CARLA. Here, we use ~/carla.
2. Download and unzip CARLA_0.9.9.4.tar.gz into ~/carla you want to unizp.
3. Download AdditionalMaps_0.9.9.4.tar.gz but do not unzip this file but place this file in ~/carla/Import.
4. Move to ~/carla and run ./ImportAssets.sh. 
5. Move to ~/carla/carla/PythonAPI/carla/dist and install CARLA python package with following command:
    ```
    easy_install carla-0.9.9-py3.7-linux-x86_64.egg
    ```
### Install Dependencies
After setting up CARLA, clone this repository and install the dependencies with the following command:
```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
conda create -n carla python=3.7
conda activate carla
pip install -r requirements.txt
pip install -r requirements.txt
```
## Running the Simulator
1. Run ./CarlaUE4.sh in ~/carla
2. Run following command to run manual controller when driving car aggressively:
    ```
    ./manual_control_image_augmentation.py --style aggressive 
    ```
    Otherwise, run following command:
    ```
    ./manual_control_image_augmentation.py --style cautious
    ```
3. If you press R after running manual controller, it starts to record your play.
4. When you playing with this controller, please annotate your explanation. You can annotate your explanation in any form but we prefer you to record your voice.
5. After running the controller 5 minutes ~ 10 minutes for each driving styles, send me (suhong.moon@berkeley.edu) the data you collect. Collected data is hdf5 format and saved in "/_out" subdirectory in cloned directory.
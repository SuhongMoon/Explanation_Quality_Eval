import h5py
import cv2
import numpy as np
import sys
import carla
import queue

from carla import ColorConverter as cc


labels_list = [
            "acceleartion", 
            "velocity", 
            "speed", 
            "location", 
            "rotation",
            "brake",
            "gear",
            "hand_brake",
            "manual_gear_shift",
            "reverse",
            "steer",
            "throttle"
        ]

def image2numpy(image):
    image.convert(cc.Raw)
    array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
    array = np.reshape(array, (image.height, image.width, 4))
    array = array[:, :, :3]
    array = array[:, :, ::-1]

    return array 

def to_numpy(vector):
    if isinstance(vector, carla.Vector3D):
        return np.array([vector.x, vector.y, vector.z])
    elif isinstance(vector, carla.Rotation):
        return np.array([vector.pitch, vector.yaw, vector.roll])

def get_labels(player):
    acceleartion = to_numpy(player.get_acceleration()) # m/s^2
    velocity = to_numpy(player.get_velocity()) # m/s
    speed = np.sqrt((velocity**2).sum()) # m/s
    transform = player.get_transform()
    location = to_numpy(transform.location) # m
    rotation = to_numpy(transform.rotation) # degrees
    control = player.get_control()
    brake = control.brake
    gear = control.gear
    hand_brake = control.hand_brake
    manual_gear_shift = control.manual_gear_shift
    reverse = control.reverse
    steer = control.steer
    throttle = control.throttle

    labels_dict = dict(
        acceleartion=acceleartion,
        velocity=velocity,
        speed=speed,
        location=location,
        rotation=rotation,
        brake=brake,
        gear=gear,
        hand_brake=hand_brake,
        manual_gear_shift=manual_gear_shift,
        reverse=reverse,
        steer=steer,
        throttle=throttle
    )

    return labels_dict

class CarlaSyncMode(object):
    """
    Context manager to synchronize output from different sensors. Synchronous
    mode is enabled as long as we are inside this context
        with CarlaSyncMode(world, sensors) as sync_mode:
            while True:
                data = sync_mode.tick(timeout=1.0)
    """

    def __init__(self, world, *sensors, **kwargs):
        self.world = world
        self.sensors = sensors
        self.frame = None
        self.delta_seconds = 1.0 / kwargs.get('fps', 20)
        self._queues = []
        self._settings = None

    def __enter__(self):
        self._settings = self.world.get_settings()
        self.frame = self.world.apply_settings(carla.WorldSettings(
            no_rendering_mode=False,
            synchronous_mode=True,
            fixed_delta_seconds=self.delta_seconds))

        def make_queue(register_event):
            q = queue.Queue()
            register_event(q.put)
            self._queues.append(q)

        make_queue(self.world.on_tick)
        for sensor in self.sensors:
            make_queue(sensor.listen)
        return self

    def tick(self, timeout):
        self.frame = self.world.tick()
        data = [self._retrieve_data(q, timeout) for q in self._queues]
        assert all(x.frame == self.frame for x in data)
        return data

    def __exit__(self, *args, **kwargs):
        self.world.apply_settings(self._settings)

    def _retrieve_data(self, sensor_queue, timeout):
        while True:
            data = sensor_queue.get(timeout=timeout)
            if data.frame == self.frame:
                return data

def generate_rgb_cam(world, cam_transform, attach_to, height=144, width=256):
    blueprint_library = world.get_blueprint_library()
    camera_bp = blueprint_library.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', str(width))
    camera_bp.set_attribute('image_size_y', str(height))
    camera_rgb = world.spawn_actor(
            camera_bp,
            cam_transform[0],
            attach_to=attach_to,
            attachment_type = cam_transform[1])
    
    return camera_rgb

def read_hdf5_test(hdf5_file):
    with h5py.File(hdf5_file, 'r') as dataset:
        mid_image = np.array(dataset["CameraMiddle"])
        right_image = np.array(dataset["CameraRight"])
        left_image = np.array(dataset["CameraLeft"])

        labels_dict = dict()

        for label in labels_list:
            labels_dict[label] = np.array(dataset[label])
    return mid_image, right_image, left_image, labels_dict


def treat_single_image(rgb_data, bb_vehicles_data, bb_walkers_data, depth_data, save_to_many_single_files=False):
    # raw rgb
    if save_to_many_single_files:
        cv2.imwrite('raw_img.jpeg', rgb_data)

    # bb
    bb_vehicles = bb_vehicles_data
    bb_walkers = bb_walkers_data
    if all(bb_vehicles != -1):
        for bb_idx in range(0, len(bb_vehicles), 4):
            coordinate_min = (int(bb_vehicles[0 + bb_idx]), int(bb_vehicles[1 + bb_idx]))
            coordinate_max = (int(bb_vehicles[2 + bb_idx]), int(bb_vehicles[3 + bb_idx]))
            cv2.rectangle(rgb_data, coordinate_min, coordinate_max, (0, 255, 0), 1)
    if all(bb_walkers != -1):
        for bb_idx in range(0, len(bb_walkers), 4):
            coordinate_min = (int(bb_walkers[0 + bb_idx]), int(bb_walkers[1 + bb_idx]))
            coordinate_max = (int(bb_walkers[2 + bb_idx]), int(bb_walkers[3 + bb_idx]))

            cv2.rectangle(rgb_data, coordinate_min, coordinate_max, (0, 0, 255), 1)
    if save_to_many_single_files:
        cv2.imwrite('filtered_boxed_img.png', rgb_data)

    # depth
    depth_data[depth_data==1000] = 0.0
    normalized_depth = cv2.normalize(depth_data, depth_data, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    normalized_depth = np.stack((normalized_depth,)*3, axis=-1)  # Grayscale into 3 channels
    # normalized_depth = cv2.applyColorMap(normalized_depth, cv2.COLORMAP_HOT)
    if save_to_many_single_files:
        cv2.imwrite('depth_minmaxnorm.png', normalized_depth)
    return rgb_data, normalized_depth


def create_video_sample(hdf5_file):
    with h5py.File('./_out/'+hdf5_file, 'r') as dataset:
        frame_width = dataset.attrs['sensor_width']
        frame_height = dataset.attrs['sensor_height']
        # fps = dataset.attrs['fps']
        fps = 10

        video_name = hdf5_file.split('.')[0]
        print(hdf5_file.split('.'))
        print(video_name)
        out = cv2.VideoWriter('{}.mp4'.format(video_name), cv2.VideoWriter_fourcc('m', 'p', '4', 'v'), fps, (frame_width, frame_height))

        mid_images = dataset['CameraMiddle']
        labels_dict = dict()

        for label in labels_list:
            labels_dict[label] = np.array(dataset[label])
        
        for idx in range(len(mid_images)):
            mid_image = np.uint8(mid_images[idx])
            mid_image = cv2.cvtColor(mid_image, cv2.COLOR_BGR2RGB)
            cv2.putText(mid_image, 'speed : {}'.format(labels_dict['speed'][idx]), (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            out.write(mid_image)

            sys.stdout.write("\r")
            sys.stdout.write('Recording video. Frame {0}/{1}'.format(idx, len(mid_images)))
            sys.stdout.flush()
        # for time_idx, time in enumerate(dataset['timestamps']['timestamps']):
        #     rgb_data = np.array(dataset['rgb'][str(time)])
        #     bb_vehicles_data = np.array(dataset['bounding_box']['vehicles'][str(time)])
        #     bb_walkers_data = np.array(dataset['bounding_box']['walkers'][str(time)])
        #     depth_data = np.array(dataset['depth'][str(time)])

        #     sys.stdout.write("\r")
        #     sys.stdout.write('Recording video. Frame {0}/{1}'.format(time_idx, len(dataset['timestamps']['timestamps'])))
        #     sys.stdout.flush()
        #     rgb_frame, depth_frame = treat_single_image(rgb_data, bb_vehicles_data, bb_walkers_data, depth_data)
        #     if show_depth:
        #         composed_frame = np.hstack((rgb_frame, depth_frame))
        #     else:
        #         composed_frame = rgb_frame                
        #     cv2.putText(composed_frame, 'timestamp', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        #     cv2.putText(composed_frame, str(time), (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        #     out.write(composed_frame)

    print('\nDone.')


if __name__ == "__main__":
    # mid_image, right_image, left_image, labels_dict = read_hdf5_test("./_out/2020-10-12 21:16:56.678067.hdf5")
    create_video_sample("2020-10-13 15:44:49.556247.hdf5")
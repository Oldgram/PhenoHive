
'''
Script python qui récupère les images et les mesures de poids et les envoies à la base de données influxDB
'''

import time
import datetime
import RPi.GPIO as gpio
from picamera2 import Picamera2, Preview
from image_processing import get_height_pix
import configparser
import ST7735 as TFT
import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as SPI
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from hx711 import HX711
from show_display import show_image, show_logo, show_measuring_menu, show_menu, show_cal_prev_menu, show_cal_menu

def init():
    # Parse Config.ini file
    parser = configparser.ConfigParser()
    parser.read('config.ini')

    global LED, token, org, bucket, url, path, pot_limit, channel, kernel_size, fill_size, cam, client, disp, WIDTH, HEIGHT, but_left, but_right, hx
    LED = int(parser["Pins"]["led"])
        
    token = str(parser["InfluxDB"]["token"])
    org = str(parser["InfluxDB"]["org"])
    bucket = str(parser["InfluxDB"]["bucket"])
    url = str(parser["InfluxDB"]["url"])
        

    path = str(parser["Path_to_save_img"]["absolute_path"])

    pot_limit = int(parser["image_arg"]["pot_limit"])
    channel = str(parser["image_arg"]["channel"])
    kernel_size = int(parser["image_arg"]["kernel_size"])
    fill_size = int(parser["image_arg"]["fill_size"])
        
    # InfluxDB client initialization
    client = InfluxDBClient(url=url, token=token, org=org)

    #Hx711 
    hx = HX711(dout_pin=5, pd_sck_pin=6)
        
    # Screen initialization
    WIDTH = 128
    HEIGHT = 160
    SPEED_HZ = 4000000
    DC = 24
    RST = 25
    SPI_PORT = 0
    SPI_DEVICE = 0
        
    disp = TFT.ST7735(
        DC,
        rst=RST,
        spi=SPI.SpiDev(
            SPI_PORT,
            SPI_DEVICE,
            max_speed_hz=SPEED_HZ))
        
        
    # Camera and LED init
    cam = Picamera2()
    gpio.setwarnings(False)
    gpio.setup(LED, gpio.OUT)
    gpio.output(LED,gpio.HIGH)
        
    #Button init
    but_left = 21
    but_right = 16
    gpio.setup(but_left, gpio.IN, pull_up_down=gpio.PUD_UP)
    gpio.setup(but_right, gpio.IN, pull_up_down=gpio.PUD_UP)



def photo(path, preview = False, time_to_wait = 8):
    cam.start_preview(Preview.NULL)
    cam.start()
    time.sleep(time_to_wait)
    if preview == False:
        name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")      
    else :
        name = "img" 
        
    path_img = path + "/%s.jpg"  % name
    cam.capture_file(path_img)
    cam.stop_preview()
    cam.stop()
    return path_img
    
    
def send_to_db(client, bucket, point, field, value): 
    write_api = client.write_api(write_options=SYNCHRONOUS)
    p = Point(point).field(field, int(value))
    write_api.write(bucket=bucket, record=p)


def get_weight():
    raw_weight = sum(hx.get_raw_data())/5
    return raw_weight
    

def start_measuring():
    
    while True:
        # Take photo
        gpio.output(LED, gpio.LOW)
        path_img = photo(path)
        time.sleep(2)
        gpio.output(LED,gpio.HIGH)
        # Get numerical value from the photo
        growth_value = get_height_pix(image_path=path_img, pot_limit=pot_limit, channel=channel, kernel_size=kernel_size, fill_size=fill_size)
        print(growth_value)
        # Send data to the DB
        send_to_db(client, bucket, "my_measurement", "Growth_station_test", growth_value)
        time.sleep(1190)
  
    
def main():

    init()
    disp.clear()
    disp.begin()
    show_image(disp, WIDTH, HEIGHT, "/home/pi/Desktop/phenostation/assets/logo_elia.jpg")
    
    while True:
        show_menu(disp, WIDTH, HEIGHT)
        #Main menu loop

        if gpio.input(but_left) == False:
            # Configuration Menu loop
            show_cal_prev_menu(disp, WIDTH, HEIGHT)
            time.sleep(1)
            while True:

                if gpio.input(but_right) == False:
                    # Preview loop
                    while True:
                        path_img = photo("/home/pi/Desktop/phenostation/assets", preview = True, time_to_wait=1)
                        show_image(disp, WIDTH, HEIGHT, path_img)

                        if gpio.input(but_right) == False:
                                # Go back to the main menu
                                break
                    time.sleep(1)
                    break

                if gpio.input(but_left) == False:
                    # Calibration loop
                    tare = get_weight()
                    raw_weight = 0
                    while True:
                        show_cal_menu(disp, WIDTH, HEIGHT, raw_weight, tare)
                        if gpio.input(but_left) == False:
                                # Get measurement
                                raw_weight = get_weight()
        
                        if gpio.input(but_right) == False:
                                # Go back to the main menu
                                break
                    time.sleep(1)
                    break

                
            
        if gpio.input(but_right) == False:
            # Measuring loop
            show_measuring_menu(disp, WIDTH, HEIGHT)
            start_measuring()

    

if __name__ == "__main__":

    main()
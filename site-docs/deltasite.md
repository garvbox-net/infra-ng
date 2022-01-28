# Notes: Deltasite Pi and Cams

2x Raspberry pi + some switches based in attic near VF gigabox

## PiHole
DHCP and DNS come from a pi2 in

## Docker
Pi server node - deltapi4
Running docker-compose, from directories in `~garvin/docker-compose` - one directory for
each application. e.g. Shinobi, Zoneminder, Unifi


## Cameras

Camera IPs 192.168.1.[20-25]
IPs/names (cam[1-5]) are reserved in DHCP (pihole)

Typical Camera Stream URLs (pulled from Shinobi ONVIF probe):
        `rtsp://192.168.1.20:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream`

ONVIF Probe example for cam1:
streams :
0 :
index : 0
codec_name : h264
codec_long_name : H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
profile : Baseline
codec_type : video
codec_time_base : 0/2
codec_tag_string : [0][0][0][0]
codec_tag : 0x0000
width : 1280
height : 720

# Notes: Deltasite Pi and Cams

2x Raspberry pi + some switches based in attic near VF gigabox

## PiHole
DHCP and DNS come from a pi2 in

## Docker
Pi server node - deltapi4
Running docker-compose, from directories in `~garvin/docker-compose` - one directory for
each application. e.g. Shinobi, Zoneminder, Unifi


## Cameras

Camera IPs 192.168.1.[20-25]
IPs/names (cam[1-5]) are reserved in DHCP (pihole)

Typical Camera Stream URLs (pulled from Shinobi ONVIF probe):
        `rtsp://192.168.1.20:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream`

ONVIF Probe example for cam1:
```
streams :
0 :
index : 0
codec_name : h264
codec_long_name : H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
profile : Baseline
codec_type : video
codec_time_base : 0/2
codec_tag_string : [0][0][0][0]
codec_tag : 0x0000
width : 1280
height : 720
coded_width : 1280
coded_height : 720
has_b_frames : 0
pix_fmt : yuv420p
level : 31
chroma_location : left
field_order : progressive
refs : 1
is_avc : false
nal_length_size : 0
r_frame_rate : 6/1
avg_frame_rate : 0/0
time_base : 1/90000
bits_per_raw_sample : 8
disposition :
default : 0
```

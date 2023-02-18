# Notes: Deltasite Pi and Cams

2x Raspberry pi + some switches based in attic near VF gigabox

## Docker

Pi server node - deltapi4
Running docker-compose, from directories in `~garvin/docker-compose` - one directory for
each application. e.g. Zoneminder, Unifi

**NOTE**: Infra components (traefik etc) have been moved to standard ansible-controlled
setup using this repository

### Zoneminder Docker Image

Zoneminder needs to be built for ARM as the docker hub images are x86 only.
There is a copy of the ZM repo from [here](https://github.com/ZoneMinder/zmdockerfiles) cloned locally on the machine at `~garvin/git/zmdockerfiles`.

From that location you can build using a command like below, note the tags used to identify the image locally, these are re-used with the docker compose setup.

```bash
docker build -t zoneminder-armhf:v1.36 -t zoneminder-armhf:latest -f release/ubuntu20.04/Dockerfile
```

There is a docker compose file at `~garvin/docker-compose/ZoneMinder` which can be used to bring up ZM.
You should be able to build and update fairly non-disruptively as the database etc are all on dedicated volumes.  
Note that the docker image build isnt aware of updates to the apt repos in docker so you might have
to delete old images to force a rebuild or use `--no-cache` option to docker build.

TODO: We may be able to improve on this process, a nice setup would be a docker image repo
hosted somewhere in the infra which we can build working and tested ZM images for Arm on
and just rely on watchtower for the updates.

## Cameras

Camera IPs 192.168.1.[20-25]
IPs/names (cam[1-5]) are reserved in DHCP (pihole)

Typical Camera Stream URLs (pulled from Shinobi ONVIF probe):
        `rtsp://192.168.1.20:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream`

ONVIF Probe example for cam1:

```text
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

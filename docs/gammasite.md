
# Gammasite

## servapi4

Raspberry Pi4 8GB Module in built case with USB-SATA adapter and booting off
USB3. Used for lightweight infra services and monitoring.

Changelog:

* LXD Removed and replaced with docker to host Homeassistant with Traefik
* Removed HomeAssistant - moved to kubernetes, MQTT broker left in place for local
  isolation and forwarding to kube HA

### Config

* Docker using official repo and apt packages
  * Data path in `/data/docker` under seperate FS (symlinked from `/var/lib/docker`)
* Services Running
  * Mosquitto - MQTT Broker for smart devices
  * Watchtower - auto-updates for containers
  * InfluxDB - Data store for monitoring and graphs

## gammatron

Build Date: 2022-08-20
Repurposed Z87-A Based Workstation, single-node Kube cluster for production services

### Hardware + Config

* CPU: Intel Core i7 4770k
* Added 16GB Patriot memory Kit - 32GB @1866Mhz
* Removed Sound card, Wifi
* Nvidia GTX 1070
* Drives:
  * Intel 250G SSD Boot
  * Sabrent 2TB Nvme High Speed working data
  * OCZ 450 - 128GB Storage Cache
  * 4x 4TB WD Red (to be moved from kraken)
* BIOS Settings
  * XMP Memory Profile set to get 1866Mhz
  * CPU overclocking removed, auto frequency boost at stock for stability
  * All non-essential features disabled

### Measurements

Power measurements taken using tasplug8. Temps mostly ignored due to variance, no high temps
seen under load during any stage.
60C Max CPU Temp under load

* CPU Load Power
  * With GPU - idle: 56W
  * With GPU - Load: 117W
  * Without GPU - idle: 38W
  * Without GPU - load: 99W

### OS Build

* Ubuntu Server 22.04.01 LTS
* Minimal install just the basics configured and a few packages
  * nvidia server drivers
  * lm-sensors for monitoring
  * stress and stress-ng for testing load
* Graphics Drivers
  * Installed nvidia-headless-515 for minimal headless driver (also was server package not sure what the diff is)

#### Config Decisions

* Single-Node or Multi-Node K3S
  *
* Use of LXD
  * Could have multiple kube nodes on the same host
  * Could run a DB server on a container - keep out of kubernetes
  * Extra IPs to manage, OSes to patch etc
* Data Storage Location
  * Option 1: Continue using kraken as a backing store - more power usage, two points of failure instead of
    one, but much more flexibility for expansion
  * Option 2: LocalPath Stores - mount directly as hostpaths in kube for optimum performance, or use
    loopback NFS shares or iSCSI (not worth the overhead there - unlikely to expand this setup)

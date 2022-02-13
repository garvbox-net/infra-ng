
# Gammasite

Hostname: servapi4

Previous LXD Setup:
```
$ lxc list
+------------+---------+---------------------+------+-----------+-----------+
|    NAME    |  STATE  |        IPV4         | IPV6 |   TYPE    | SNAPSHOTS |
+------------+---------+---------------------+------+-----------+-----------+
| haproxy    | RUNNING | 192.168.0.10 (eth0) |      | CONTAINER | 0         |
+------------+---------+---------------------+------+-----------+-----------+
| hassoo     | RUNNING | 192.168.0.14 (eth0) |      | CONTAINER | 0         |
+------------+---------+---------------------+------+-----------+-----------+
| m-cuteetee | RUNNING | 192.168.0.15 (eth0) |      | CONTAINER | 0         |
+------------+---------+---------------------+------+-----------+-----------+
```

Three LXD Containers:
* haproxy
  * Vanilla HAproxy install on ubuntu container
  * basic config copied from alphasite HAproxy
  * Script for periodic Cert refresh [update-certs-haproxy.py](https://gitlab.com/garvinob/admin-scripts/-/blob/master/update_certs_haproxy.py)
* hassoo
  * Homeassistant core on ubuntu container
  * Python virtualenv for homeassistant user
  * start/stop with systemd unit
* m-cuteetee
  * MQTT server on ubuntu container
  * smart plugs manually pointed at this

## Replacement Plan: Dockerization
* First Remove LXD containers, backing up HAproxy and HomeAssistant
* Adapt the standardised solution design as per [infra-design](infra-design.md)

## Services
### HomeAssistant
Compose File: [here](../deploy/gammasite/homeassistant/docker-compose.yml)  
Services: homeassistant, mqtt

Note MQTT needs ports forwarded directly, but HomeAssistant can just sit behind Traefik.  
Some helpful info found on the homeassistant site
[here](https://community.home-assistant.io/t/sharing-your-configuration-on-github/195144#step-2-creating-gitignore)
for version-controlling the HA config.

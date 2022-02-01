# infra-ng - IaC Solution

Infrastructure Docs, Code, Config, Playbooks

## Solution Design

### Requirements

* Ability to handle multiple sites (eg alphasite, delta, gamma etc)
* handle multiple nodes within the site
* testable deployments
* containerised applications (docker/swarm/k8s)
* Automated proxying with SSL (traefik/haproxy)

Optional/Nice-To-Have:
* Automatic DNS updates, handling each of the different sites
* Integration of public DNS for automatic routing

### Example List of services by site:
The below list shows the various web facing services on each site.
```yaml
alphasite:
  - sonarr
  - radarr
  - plex
  - owncloud
  - gitea
  - web apps (Cathal)
deltasite:
  - Dogwatch (Zoneminder)
gammasite:
  - HomeAssistant
omegasite (future):
  - HomeAssistant
  - NextCloud
```


## DNS

`garvbox.net` domain currently using NameCheap DNS
Up for renewal pretty soon - looking at alternatives.
Noted that Namecheap has a limit of 150 records in a domain, should be enough for hosting a lot of services  
**DECISION:** Move to CloudFlare DNS as it has better support for LetsEncrypt automated renewal using DNS-01 challenge - allowing wildcards

CNAME Records offer a simple way of redirecting a bunch of services to one name. eg. could have `homeassistant.deltasite.garvbox.net` redirecting to `deltasite.garvbox.net` for easy public access and allowing traefik to route appropriately by name. 

Example DNS Record:
```
garvin@G15:~$ nslookup hass-test.deltasite.garvbox.net 8.8.8.8
Server:         8.8.8.8
Address:        8.8.8.8#53

Non-authoritative answer:
hass-test.deltasite.garvbox.net canonical name = deltasite.garvbox.net.
Name:   deltasite.garvbox.net
Address: 109.76.118.164
```


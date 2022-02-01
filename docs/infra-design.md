# infra-ng - IaC Solution

Infrastructure Docs, Code, Config, Playbooks

## Solution Design

### Requirements

* Ability to handle multiple sites (eg alphasite, delta, gamma etc)
* handle multiple nodes within the site
* testable deployments
* containerised applications (docker/swarm/k8s)
* Automated proxying with SSL (traefik/haproxy)
* Easy standardised way to add services without requiring admin privileges over base infra (e.g. gitlab subgroups)
* Automatic DNS updates, handling each of the different sites

### Example List of services by site:
The below list shows the various web facing services on each site.
```yaml
alphasite:
  - sonarr
  - radarr
  - plex
  - owncloud
  - gitea
deltasite:
  - Dogwatch (Zoneminder)
gammasite:
  - HomeAssistant
omegasite:  # Future site to be built :)
  - HomeAssistant
  - NextCloud
```


## DNS

`garvbox.net` domain currently using NameCheap DNS. This is up for renewal pretty soon - looking at alternatives.  
**Update** - Feb 2022 - Moved to CloudFlare DNS along with dynamic IP updaters across three sites, working OK. CF has better support for LetsEncrypt automated renewal using DNS-01 challenge - allowing wildcards  

### Application Subdomains
Public subdomains offer offer a simple way of managing multiple services per site. eg. could have `homeassistant.deltasite.garvbox.net` redirecting to `deltasite.garvbox.net` for easy public access and allowing traefik to route appropriately by name.  
This would require some integration with whatever deployment management solution (standalone script or hook) to add CNAME records on deployment as mentioned in requirements above.

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


# infra-ng - IaC Solution

Infrastructure Docs, Code, Config, Playbooks


## Requirements

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

## App Hosting

### Docker Servers
Docker is used for all apps for ease of deployment and management. Standardised Docker Installation and Configuration across server nodes, using an ansible [playbook](../ansible/docker-install.yml). They just need to be in the group docker-host for your inventory file.

If manual install/config is required, the source is here;
* Docker CE installed as per [Ubuntu Docker Install](https://docs.docker.com/engine/install/ubuntu/)
* Docker Compose V2 - [Docker Compose CLI Install](https://docs.docker.com/compose/cli-command/#install-on-linux). Note the links there assume architecture is x86_64 - this would need to be changed on rpi.


### Container Management

**OLD/Current** Manual Container management approach - used in deltasite for zoneminder and Unifi
* Directory in user home: `~/docker-compose` - containing directory for each service to be hosted, with docker-compose yaml files in each, and any Dockerfiles if there are locally-built containers
* manual deployment with docker compose
* no backups or version control
* isolated and requires manual interaction
* no status reporting, monitoring or auto recovery


Management & Monitoring Tools To explore:
* cAdvisor + Prometheus exporter -> Grafana
* watchtower - image updates


### Auto-Deployed Containers

**TODO**: Design, Test and document GitOps multi-site Solution :)

Notes/Ideas:
* Deployment targeting using project environment in gitlab - smart deployment hooks on each target node


### DNS

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


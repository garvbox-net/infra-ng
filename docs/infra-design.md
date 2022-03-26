# infra-ng: Infrastructure Design
This document describes the design of a self-hosted server app platform with following desirable attributes:
* Ability to handle multiple sites (eg alphasite, delta, gamma etc)
* handle multiple nodes within the site
* testable deployments
* containerised applications (docker/swarm/k8s)
* Automated proxying with SSL (traefik/haproxy)
* Easy standardised way to add services without requiring admin privileges over base infra (e.g. gitlab subgroups)
* Automatic DNS updates, handling each of the different sites

This design attempts to mitigate legacy infra issues outlined in [legacy](legacy.md)


## Overview: Standardised Docker Infra & Apps
Docker (and compose) is chosen as the solution for the following reasons:
* Simplicity: Kubernetes (k3s) was investigated but the overhead is a bit too much for raspberry
  pis and its total overkill given the lack of infra reduncancy and limited capacity we have
* multi-platform: easy to run across a variety of server types and networks
* flexible: easy to script and automate deployment, huge customisation available with Dockerfiles and automated build from compose

### Remaining Issues
Some minor issues outstanding with this design to be resolved in the next iteration:
* Theres still a lot of site-specific repetition in the layout, eg per-site traefik config
* One-step IaC deployment non trivial, recreating a site to test a change would be challenging


## Docker Servers
Docker used for all apps for ease of deployment and management. Standardised Docker Installation and 
Configuration across server nodes, using an ansible [playbook](../ansible/docker-install.yml). 
They just need to be in the group docker-host for your inventory file.

If manual install/config is required, the source is here;
* Docker CE installed as per [Ubuntu Docker Install](https://docs.docker.com/engine/install/ubuntu/)
* Docker Compose V2 - [Docker Compose CLI Install](https://docs.docker.com/compose/cli-command/#install-on-linux).
Note the links there assume architecture is x86_64 - this would need to be changed on rpi.

## Configuration file Structure
Configuration Structure hosted within this project for infra components and core apps on each site.  
Structure as follows:

```
infra-ng
+-- deploy
|   +-- <site-name>
|   |   +-- infra
|   |   |   +-- docker-compose.yml
|   |   |   +-- traefik
|   |   |   |   +-- acme.json
|   |   |   |   +-- traefik.yaml
|   |   +-- <app>
|   |   |   +-- docker-compose.yml
|   |   |   +-- <supporting-app-content>
|   |   |   |   +-- <app-files>
```

Additional Notes:
* `<site-name>`: Name of the site e.g. gammasite. Top-level directory for the site.
* `infra`: It is expected that each site should have an infra section for site-specific traefik
  and management services.
* `<app>`: Application directory per app group containing a docker-compose file for the services
* `<supporting-app-content>` - supporting files for the apps contained e.g. Dockerfiles, scripts, config files

Future Enhancements:
* Config for managed applications stored in a gitlab group structure allowing group members to add
  and deploy apps very easily
* allow for multi-node sites (likely using swarm)


## Standardised Infra Containers
As seen in the above structure there is a standardised `infra` compose project for each site. 
This is for sitewide infrastructure services, managing deployments etc. Keeping this seperate from
user facing applications should be a fairly manageable config and allow smoother transition to
fully automated deployments in future.

Future enhancements may improve standardisation by templating this between the sites and only storing
site-specific customisations in each site directory.

**TODO:** Management & Monitoring Tools To explore:
* cAdvisor + Prometheus exporter -> Grafana

### Traefik
Traefik was chosen as the load balancer/proxy for its nice integration with docker and automated
certificate management. 

**NOTE:** You must manually create the `web` network before bringing Traefik or anything online,
it is treated as external on all containers to prevent cross-app dependencies.

    # docker network create web

Application web access, https and other details can be seen [below](#traefik-web-access)

### Watchtower
App updates are provided with [watchtower](https://containrrr.dev/watchtower/). This is disabled by
default for safety, and can be enabled and configured as shown [below](#watchtower-automatic-updates)


## App Containers
**TODO**: Design, Test and document GitOps multi-site Solution.  
Interim solution is manual management of containers using docker-compose from this repo.

### Traefik: Web access
**TODO:** Add instructions and examples for traefik plumbing to apps

### Watchtower: Automatic Updates
**TODO:** Add instructions and examples enabling watchtower


## Testing
**TODO:** Develop and document deployment testing approaches

## Secrets Management

**TODO:** Development of secrets management solutions across apps and infra components


## DNS & Subdomains

### DNS Infrastructure

**Update** - Feb 2022 - `garvbox.net` domain Moved to CloudFlare DNS along with dynamic IP updaters
across three sites, working OK. CF has better support for LetsEncrypt automated renewal using
DNS-01 challenge - allowing wildcards  

**TODO:** Document plans for DNS auto-updates and maintenance

### Application Sub-Domains
Public subdomains offer offer a simple way of managing multiple services per site. 
eg. could have `homeassistant.deltasite.garvbox.net` redirecting to `deltasite.garvbox.net` for
easy public access and allowing traefik to route appropriately by name.  
This would require some integration with whatever deployment management solution
(standalone script or hook) to add CNAME records on deployment as mentioned in requirements above.


# Portainer Edge Nodes

TODO: Explore Portainer Edge Nodes idea
Use kube cluster on kraken (and others) as the main hub with portainer running on it as a controller for the raspberry pis
using the edge node setups they could have handy central control...


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

## Design rework - Kubernetes core

The previous docker-based setup (documented [here](./docker-compose.md)) is under review,
it works nicely for the rasperry pi's in gammasite and deltasite but doesnt meet some of the needs
like version control with gitops, testable deployments and rollbacks, at least
not without some very heavy automation on top of it.

If going to that level of effort it is looking far more preferable (and more valuable experience)
to just go in on kubernetes, if not on the edge at least at the core and use that to control the edge nodes.
The edge sites will stay on docker compose

See documentation on kubernetes exploration, setup guides etc: [Kubernetes on K3S](./kube-k3s.md)

Some Ideas under exploration:

* Use kube cluster on kraken (and others) as the main hub with portainer running on it as a
  controller for the raspberry pis using the edge node setups they could have handy central control...
* Kubernetes edge mode for edge pi's
* Kube cluster with kraken, ark and a VM on ultron as the controller nodes an
  * GlusterFS highly available NFS share for main storage and pod backing

## Networking

Documentation about the internal network config, site to site links and public DNS setups.

### Site to Site Connections

**Objectives**:

* Seamless Connections between all managed sites requiring no VPN software on endpoints
* DNS lookups from any site to any other
* Firewall monitoring and traffic reporting between sites

See [Network Design](./networking.md#site-to-site-connections) for site connectivity details.

### DNS & Subdomains

#### DNS Infrastructure

**Update** - Feb 2022 - `garvbox.net` domain Moved to CloudFlare DNS along with dynamic IP updaters
across three sites, working OK. CF has better support for LetsEncrypt automated renewal using
DNS-01 challenge - allowing wildcards  

**TODO:** Document plans for DNS auto-updates and maintenance

#### Application Sub-Domains

Public subdomains offer offer a simple way of managing multiple services per site.
eg. could have `homeassistant.deltasite.garvbox.net` redirecting to `deltasite.garvbox.net` for
easy public access and allowing traefik to route appropriately by name.  
This would require some integration with whatever deployment management solution
(standalone script or hook) to add CNAME records on deployment as mentioned in requirements above.

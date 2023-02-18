# Legacy Infra

This section briefly covers the legacy infra and the issues with the same. The legacy infra has
two styles, `lxd` setup for full system containers, and `docker` setup for apps.

## Legacy LXD

LXD is the older of the two approaches and has been in production for a very long time. It has been
stable and has some nice benefits like flexibility, total app independence, and having a dedicated
IP address for any services but there is a lot of management overhead.

**Issues:**

* no automated build capability
* poor repeatability, no backups
* no standardisation across services
* minimal automation of proxy (limited ansible usage)
* lots of sysadmin and manual interaction
* no status reporting, monitoring or auto recovery

## Legacy Docker Compose

Manual Docker Container management approach - used in deltasite for zoneminder and Unifi

* Directory in user home: `~/docker-compose` - containing directory for each service to be hosted,
  with docker-compose yaml files in each, and any Dockerfiles if there are locally-built containers
* manual deployment with docker compose

**Issues:**

* no backups or version control
* no standardisation across containers
* no common approach to load balancing
* isolated and requires manual interaction
* no status reporting, monitoring or auto recovery

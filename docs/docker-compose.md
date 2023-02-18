# Overview: Standardised Docker Infra & Apps

Docker (and compose) is chosen as the solution on edge nodes for the following reasons:

* Simplicity: Kubernetes (k3s) was investigated but the overhead is a bit too much for raspberry
  pis and its total overkill given the lack of infra reduncancy and limited capacity we have
* flexible: easy to script and automate deployment, huge customisation available with Dockerfiles and automated build from compose

## Docker Servers

Docker used for all apps for ease of deployment and management. Standardised Docker Installation and
Configuration across server nodes, using an ansible [playbook](../ansible/README.md#docker-servers).

If manual install/config is required, the source is here;

* Docker CE installed as per [Ubuntu Docker Install](https://docs.docker.com/engine/install/ubuntu/)
* Docker Compose V2 - [Docker Compose CLI Install](https://docs.docker.com/compose/cli-command/#install-on-linux).
Note the links there assume architecture is x86_64 - this would need to be changed on rpi.

## Configuration and Deployment

The Deployment strategy for apps is pretty simple: There is a variable for each site `deploy_apps`,
which is a list of the application task files for the site which will be automatically imported
by the `docker-deploy-site.yml` playbook.  
Deployment is done using ansible, using the playbooks documented [here](../ansible/README.md).

In a previous iteration there was a tree of docker compose yaml files and application config files per
site located in this repository. This had a few challenges:

* Lots of repetition
* Could not account for apps that control their own config (eg Home Assistant yaml files)

A slightly adjusted approach is taken for configuration managment because of this:

* Infrastructure component (e.g. Traefik) config is completely standardised and deployed with
  dedicated ansible playbooks that adapt to the site.
* Application config may be seeded on a per-app basis for initial deployment but is generally not touched afterwards unless it can be easily and safely standardised.

For Example, HomeAssistant configuration is seeded to allow the initial setup to work, getting past its fear of proxies and adding the docker standard IP range as allowed proxy servers. But theres no point in config-controlling HA beyond this as it can edit its config via the UI.

## Standardised Infra Containers

As mentioned above there is a standardised `infra` compose project for each site.
This is for sitewide infrastructure services, e.g. load balancer, monitoring etc

### Traefik

Traefik was chosen as the load balancer/proxy for its nice integration with docker and automated
certificate management.

## Backups

**TODO: Build a backup solution!!!**

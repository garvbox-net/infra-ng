# Ansible Infra Deployments
Playbooks for configuration and setup of infra components

These are all intended to be used with dedicated hosts files (per-site),
so to run a playbook will typically look like:
```
ansible_playbook -i <hosts file> <playbook.yaml> -K
```
SSH key setups, user accounts etc are all left to be handled as normal (except for deployment
of new LXD containers - we will auto add the SSH key for the current user then).

Note: Global secrets are kept in `group_vars/all/vault`, per-site/per-group vars stored in `group_vars/{site_name}/vault`.


## Playbooks
### LXD Containers
Automatic deployment of containers and initial configuration (user etc).
* Playbook: `lxd-provision.yml`
  * This will deploy a new ubuntu container and do basic user and networking setup
* Extra Vars:
  * `-e container=<container_name>`
* Notes:
  * Temporarily deploys the current user's SSH key as trusted by the root user on the remote machine
    and removes it after. make sure to remove it manually if there are issues with the deployment.

### Docker Servers
Installation of docker, docker compose, and required host setup

* Playbook: `docker-install.yml`
* Notes:
  * Requires escalation, generally password must be provided with `-K` if remote user has sudo privileges.
  * If Deploying on an LXD container, make sure to set the `lxd_docker_host` variable for the host,
    so that the LXD security policy gets set

### Docker Sites and Apps
Deployment of Standardised App hosting servers as per [docker-compose](../docs/docker-compose.md)
* Playbook: `docker-deploy-site.yml`
* Notes:
  * Tags available:
    * `apps` - this deploys only the docker hosted apps (non-infra ones), useful for pushing config updates
    * `client` - This installs the required client libraries on the docker host machine (docker-compose python libs for ansible to use)
    * `infra` - This deploys the infrastructure components: traefik, watchtower with standard config
  * Each site has an ansible group (e.g. `testsite`) with dedicated config for the site name, DNS for TLS, and a list of non-infra apps to deploy. See example: [testsite](./group_vars/testsite/vars.yml)

### Kubernetes (K3S)
Installation of Kube cluster and joining nodes
* Playbook: `k3s-deploy.yml`
* Notes:
  * Requires galaxy role xanmanning.k3s.
    Extra docs [here](https://galaxy.ansible.com/xanmanning/k3s)  
    `ansible-galaxy install xanmanning.k3s`
  * Requires host groups `masters` and `workers` as children of group `k3s_cluster`
  * A master node does not have to be added to workers as it will automatically be a worker node
  * Single node and multi node setups are automatically handled

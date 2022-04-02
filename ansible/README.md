# Ansible Infra Deployments
Playbooks for configuration and setup of infra components

These are all intended to be used with dedicated hosts files (per-site),
so to run a playbook will typically look like:
```
ansible_playbook -i <hosts file> <playbook.yaml> -K
```
SSH key setups, user accounts etc are all left to be handled as normal

## LXD Containers

Automatic deployment of containers and initial configuration (user etc).
* Playbook: `lxd-provision.yml`
* Notes:
  * This must be run from the LXD server as remote LXD commands dont really work well.
  * This will deploy a new ubuntu container and do basic user and networking setup

## Docker Servers
Installation of docker, docker compose

* Playbook: `docker-install.yml`



## Kubernetes (K3S)
Installation of Kube cluster and joining nodes
* Playbook: `k3s-deploy.yml`
* Notes:
  * Requires galaxy role xanmanning.k3s.
    Extra docs [here](https://galaxy.ansible.com/xanmanning/k3s)  
    `ansible-galaxy install xanmanning.k3s`
  * Requires host groups `masters` and `workers` as children of group `k3s_cluster`
  * A master node does not have to be added to workers as it will automatically be a worker node
  * Single node and multi node setups are automatically handled

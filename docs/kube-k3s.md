
# Experiment and Explore K3S

K3S is a very interesting option instead of docker-compose, and argubly more flexible
and powerful for rollout to multiple sites. It would help in standardising storage and
make the core management infra for each site generic (mostly).

# Current Clusters

The clusters are configured with Flux as documented [below](#gitops-with-flux). Not much
details are recorded here as things can change and its easiest just to see that repo for
the current state.

## Gammasite

Runs on: `gammatron`  
This is the main prod cluster, a single-node beefy machine with lots of local storage.
Running a single node is not ideal but it does minimise overhead and the local storage is very
fast, with a decent CPU and Nvidia GTX 1070 for plex. It has good memory too (32G) and pretty
power efficient. See below for details on the gpu [setup](#nvidia-gpu)

## Testsite

Runs on: `servapi4`  
Setup is usually powered down and is a `k3d` cluster. To start it, on servapi4

It uses the `staging` branch of the gitops cluster as it is only for testing major config changes
e.g. load balancer setup, major config rollouts to multiple services etc.  
To start it run the following:
    $ k3d cluster start testsite

# Environment setup

The easiest way to test is with K3D as its a one-liner to get up and running. Testing on LXD is viable
also with some shenanigans to get it work as below.
Using LXD is powerful as you can replicate a bare-metal install network fairly closely and play with things
like MetalLB load balancer in a somewhat realistic setup. Below Sections show how to Install and Configure each.

## How to Install K3S on LXD

* Create LXD container to use as k3s host (ubuntu image works well)
* Ensure IP forwarding enabled on the host machine (since they share the kernel)
  * Check the output of: `sysctl net.ipv4.ip_forward`, if it is set to 1 already then nothing needs to be changed, skip forward to LXD config
  * Otherwise add the setting to sysctl: `echo net.ipv4.ip_forward=1 | sudo tee /etc/sysctl.d/90-enable-ipforward.conf`
  * Load settings: `sysctl --system`
* Configure LXD Container, edit the config:
`lxc config edit <container name>`
  * Add the below lines under the `config:` block if needed:

    ```text
      linux.kernel_modules: ip_tables,ip6_tables,netlink_diag,nf_nat,overlay
    raw.lxc: |-
      lxc.apparmor.profile=unconfined
      lxc.mount.auto=proc:rw sys:rw cgroup:rw
      lxc.cap.drop=
      lxc.cgroup.devices.allow=a
      security.nesting: "true"
      security.privileged: "true"
    ```

* Customise K3S server command for LXD - create `/etc/rancher/k3s/config.yaml` with the below content:

  ```yaml
  disable: servicelb
  snapshotter: native
  ```

  Note: We also disable the default ServiceLB from K3S (klipper) as MetalLB provides a more flexible setup.  
  You can also add `data-dir: /path/to/dir` to move the storage location (e.g. on RPI)
* Install K3S: `curl -sfL https://get.k3s.io | sh -`
* (After Some time) check k3s is up and running: `kubectl get pods -A`

See Custom DNS Setup using metalLB to reserve an IP on [reddit](https://www.reddit.com/r/homelab/comments/ipsc4r/howto_k8s_metallb_and_external_dns_access_for/)
Possible to enhance this to use coreDNS instead of an extra DNS service, seen another interesting coredns mod [here](https://github.com/billimek/k8s-gitops/blob/master/kube-system/coredns/coredns.yaml). Note the zoneFiles config and custom domain in there. Could be automated?

**Troubleshooting tips:**

* Check k3s server status: `systemctl status k3s`
* Check k3s server logs: `journalctl -xeu k3s.service`
* You can kill the k3s service and run manually on command line also, can be easier to see whats happening that way:
  * To kill: `# systemctl stop k3s && k3s-killall.sh`
  * To start in console: `# k3s server`

## K3D Setup

[K3D](https://k3d.io) configured on workstation for really quick testing

* Requires docker installed (use ansible [playbook](../ansible/docker-install.yml))
* Install k3d tool from web instructions:  
  `wget -q -O - https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | TAG=v5.0.0 bash`
* Create cluster - for help:  
  `k3d cluster create <cluster-name> -p "8080:80@loadbalancer" -p "8443:443@loadbalancer"`

**Note:** Since k3d is running in docker the IP layout wont be the same as K3S running on bare metal,
and things like MetalLB may not work well with the more complex network.  
You can configure pretty much any K3S server and agent settings (ie disabling traefik etc) and its a good way to test configs out

## SSL Certificates

Cert-manager is used as it is well integrated into kubernetes resources and is ingress controller agnostic.
Installation [instructions](https://cert-manager.io/docs/installation/)

* Add Helm Repo  
  `helm repo add jetstack https://charts.jetstack.io && helm repo update`
* Install with CRDs:  
  `helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --set installCRDs=true`
* Create secret for cloudflare DNS challenge. [ref](https://cert-manager.io/docs/configuration/acme/dns01/cloudflare/)
  * Get CloudFlare API token from UI, store to environment: `CF_API_TOKEN=<cloudflare token>` (see below [secrets management](#secrets-management))
  * Apply secret to cluster  

    ```yaml
    apiVersion: v1
    kind: Secret
    metadata:
      name: cloudflare-api-token-secret
      namespace: cert-manager
    type: Opaque
    stringData:
      api-token: $CF_API_TOKEN
    ```

* After this you can create the Cert Issuer and hook in Traefik with the right certs as
  appropriate for the site. Dont forget to restart the Traefik pods after adding the TLS store

## MetalLB Load Balancer

Normally K3S uses host IP ports if you try to use LoadBalancer service resources, so things that are
greedy with ports like Unifi Controller can be tough to manage and take a lot of messing about with
multiple entrypoints on traefik. An alternative is to use MetalLB to assign LAN IP addresses to services.

To set it up using Helm see [ref](https://metallb.universe.tf/installation/). This is automatically configured
on the gitops repo, see the config there for reference. Manual setup steps are no longer documented here
as they get out of date quick.

## Nvidia GPU

Kubernetes allows you to treat a GPU as a pod resource and pass it in, as detailed in the official
[docs](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/). This is pushing the edge of what you should
be doing with kubernetes but we arent here to make sensible decisions!

The nVidia device plugin [docs](https://github.com/NVIDIA/k8s-device-plugin#preparing-your-gpu-nodes) also help here, however
see the below info as some of the nvidia stuff makes assumptions about setting default devices that dont work well
on the K3S environment.

This [comment](https://github.com/k3s-io/k3s/issues/4391#issuecomment-1233314825) from one of the K3S devs was key in understanding the setup.
Basically K3S will automatically detect the nvidia container runtime but you need to ensure to set up the `RuntimeClass` in
kubernetes to connect it. No messing about with config.toml for containerd needed. You will also need to reference the RuntimeClass
from your deployment/pod.

Setup Steps:

* Add nvidia-container-toolkit repository:

  ```bash
  distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
  curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
  curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/libnvidia-container.list
  ```

* Update apt and install nvidia drivers, tools and container runtime. Note the encode package was needed on older drivers (may be included in newer ones)

  ```bash
  sudo apt update && sudo apt install \
      nvidia-headless-525-server \
      nvidia-utils-525-server \
      nvidia-container-toolkit \
      libnvidia-encode-525-server
  ```

* Reboot to load nvidia driver. It would be a good idea to disable k3s here, stop it and run the `k3s-killall.sh` script
  to avoid needlessly starting up the cluster if you have issues with the nvidia drivers
* Check the nvidia driver is working with `sudo nvidia-smi` which should show the GPU details
* Check the nvidia container runtime works with `nvidia-container-cli info` which should also show GPU details if things are working

At this point the machine is prepped and you can start up k3s if you disabled it. You can check that k3s detected the GPU
after it has started with `sudo grep nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml`

You may proceed to deploying the nvidia-device-plugin pod and workloads after this.

# GitOps with Flux

There are lots of great examples here at [k8s-at-home](https://github.com/k8s-at-home/awesome-home-kubernetes)
of clusters using flux on k3s/k8s. The setup here is inspired by many of those. Note that the GitOps repository
is kept seperate from the local infra repo to keep the activity there limited to pure gitops/automation only.

The manual setup instructions are below, but this has all been automated with the playbook [k3s-deploy](../ansible/k3s-deploy.yml),
the playbook and hosts config serve as self-documenting reference for the infra setup.

## Install and Configure Flux

Official Instructions at <https://fluxcd.io/docs/installation/>. Docs here are specific to our setup on gitlab.com.
Note: Bootstrapping relies on working kubectl config for your cluster and existing git repo for gitops. Note the
path option is important if you wish to share multiple clusters in the same repo.
You need a gitlab personal access token with complete read/write access to gitlab API as it will create deploy
keys for the repo.  
Bootstrapping from an existing repository/cluster location will apply the manifests of that repo to your cluster, handy for backup and restore.

* Install Flux CLI: `curl -s https://fluxcd.io/install.sh | sudo bash`
* Bootstrap:

  ```bash
  export GITLAB_TOKEN=<token>
  flux bootstrap gitlab \
    --owner=<gitlab_group_name> \
    --repository=<repo_name) \
    --branch=main \
    --path=<path_to_cluster_in_repo> \
    --token-auth
  ```

  Note: on k3s you might want to use option: `--kubeconfig /etc/rancher/k3s/k3s.yaml` to use the k3s kubeconfig file

Example Bootstrap Command:
`# flux bootstrap gitlab --owner=garvbox-iac --repository=gitopsokat --branch=main --path=clusters/k3s-lxc-test --token-auth --kubeconfig /etc/rancher/k3s/k3s.yaml`

## Secrets Management

The Flux Guide on SOPS is very good and covers everything needed <https://fluxcd.io/docs/guides/mozilla-sops/>.  
See the [age](https://fluxcd.io/docs/guides/mozilla-sops/#encrypting-secrets-using-age) guide for use of age
instead of gpg - much easier.
Ultimately went with GPG in the test environment over AGE as had more existing repo in k8s-at-home community using
ansible and GPG. Some notes:

* Setup steps:
  * Created a variable `vault_sops_gpg_key` in the vault for testsite, this is the private key for the GPG setup
  * Followed the guide and created the SOPS decryption secret manually with kubectl (and added an ansible step to
    do it during deployment from the vault copy).
  * Created a manifest file for the discord URL secret (`flux-system/notifications/discord-secrets.yaml`) using the
    kubectl CLI. Then used sops to encrypt that in place and committed the encrypted version, pushing it up to see what happens.
* Here I had some issues with the discord notifications secret - flux wasnt decrypting the SOPS content automatically
  and throwing these errors:

  ```log
  2022-04-23T20:56:11.017Z error Kustomization/flux-system.flux-system - Reconciliation failed after 686.569067ms, next try in 10m0s Secret/flux-system/discord-url validation error: error decoding from json: illegal base64 data at input byte 3
  ```

* After re-reading the docs it made more sense, I had forgot to enable decryption in flux...
  The instructions in the guide [here](https://fluxcd.io/docs/guides/mozilla-sops/#configure-in-cluster-secrets-decryption)
  mentioned to do this with a kustomization on the CLI, but it referred to other git repos so didnt
  make a lot of sense to do this.  
  Instead edited `gitk-sync.yaml` to enable decryption as below. Saw others online following this approach too,
  and it seemed to work after removing and re-adding the notifications secrets to kick it into action.

```yaml
  decryption:
  provider: sops
  secretRef:
    name: sops-gpg
```

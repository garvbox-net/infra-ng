
# Experiment and Explore K3S

K3S is a very interesting option instead of docker-compose, and argubly more flexible
and powerful for rollout to multiple sites. It would help in standardising storage and
make the core management infra for each site generic (mostly).

Kube could also make testing much more powerful but theres a lot of challenges to solve:
* Overhead on rpi seems a lot (to be revisited, previous issues were partly due to ZFS)
* Initial config of things like HomeAssistant tricky to get http proxy
* K3S doesnt solve version controlling app config (like HA config files)

## Interesting content:
* https://www.youtube.com/watch?v=icyTnoonRqI
  * MetalLB advised to allow local IP space - [docs](https://metallb.universe.tf/configuration/)
  * Good example on pi for LAN: https://opensource.com/article/20/7/homelab-metallb
* https://github.com/billimek/k8s-gitops


# Current Clusters
The Test clusters are configured with Flux as documented [below](#gitops-with-flux)

List of clusters for reference:
* k3d-test - K3D Single node Test Cluster running on Raspberry Pi 4 (servapi4)
* k3s-lxc-test - K3S single node test cluster running on an LXD container (k3s-test) on kraken

**Note**: Custom Data path on Kraken test environment  
As kraken is mostly zfs, created an LVM volume and a filesystem on it for use with k3s. Container config:
`$ lxc config device add k3s-test lvm-k3s disk source=/dev/mapper/kraken--vg-k3s path=/data`
To make use of the path at /data, the k3s config file is updated:
```yaml
disable: servicelb
data-dir: /data/k3s
```


# Test Environment setup

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
    ```
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

There are two options here:
* Using Traefik native TLS handling: https://traefik.io/blog/traefik-proxy-kubernetes-101/
OR
* Cert-manager like [this](https://it-obey.com/index.php/wildcard-certificates-dns-challenges-and-traefik-in-kubernetes/) 

Cert-manager might be easier to handle secrets and is better integrated into kubernetes if we wanted to use other ingress controllers. 
Installation [instructions](https://cert-manager.io/docs/installation/)
* Add Helm Repo  
  `helm repo add jetstack https://charts.jetstack.io && helm repo update`
* Install with CRDs:  
  `helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --set installCRDs=true`
* Create secret for cloudflare DNS challenge. [ref](https://cert-manager.io/docs/configuration/acme/dns01/cloudflare/)
  * Get CloudFlare API token from UI, store to environment: `CF_API_TOKEN=<cloudflare token>`
  * Apply secret to cluster  
    ```
    cat << EOF | kubectl apply -f -
    apiVersion: v1
    kind: Secret
    metadata:
      name: cloudflare-api-token-secret
      namespace: cert-manager
    type: Opaque
    stringData:
      api-token: $CF_API_TOKEN
    EOF
    ```
* After this you can create the Cert Issuer and hook in Traefik with the right certs as
  appropriate for the site. Dont forget to restart the Traefik pods after adding the TLS store



## MetalLB Load Balancer

Normally K3S uses host IP ports if you try to use LoadBalancer service resources, so things that are
greedy with ports like Unifi Controller can be tough to manage and take a lot of messing about with
multiple entrypoints on traefik. An alternative is to use MetalLB to assign LAN IP addresses to services.

To set it up using Helm (see [ref](https://metallb.universe.tf/installation/)):
* Create a `values.yaml` file for helm to configure MetalLB on deployment. It should look like this:
  ```yaml
  configInline:
    address-pools:
    - name: default
      protocol: layer2
      addresses:
      - 192.168.0.200-192.168.0.250
  ```
* Install on dedicated namespace:
  ```
  helm repo add metallb https://metallb.github.io/metallb
  helm install metallb metallb/metallb -f <path-to-values.yaml> --create-namespace --namespace=metallb-system
  ```

## Secrets Management

The Flux Guide on SOPS is very good and covers everything needed https://fluxcd.io/docs/guides/mozilla-sops/.  
See the [age](https://fluxcd.io/docs/guides/mozilla-sops/#encrypting-secrets-using-age) guide for use of age
instead of gpg - much easier. 


# GitOps with Flux

There are lots of great examples here at [k8s-at-home](https://github.com/k8s-at-home/awesome-home-kubernetes)
of clusters using flux on k3s/k8s. The setup here is inspired by many of those. Note that the GitOps repository
is kept seperate from the local infra repo to keep the activity there limited to pure gitops/automation only.

TODO: Update [infra-design.md](./infra-design.md) with design ref for clusters.


## Install and Configure Flux
Official Instructions at https://fluxcd.io/docs/installation/. Docs here are specific to our setup on gitlab.com.
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


## Repo Structure

The GitOps repo is structured to handle multiple clusters by name, each one is handled seperately using the path
when flux is bootstrapped as above. The yaml files are organised by namespace underneath, using
`kustomization.yaml` in a lot of places for easy enable/disable of directories without removing files.
Generally speaking the consumable applications (like homeassistant, sonarr etc) are placed in the `default` namespace.
Helm repositories for flux visibility are added under `flux-system-repos` but are still in `flux-system`
namespace, this is just to avoid cluttering up the flux system directory created on bootstrap.

```
cluster_1
├── default
│   ├── app1
│   ├── app2
│   └── appN..
└── <namespace> 
    └── appN...
cluster_2
├── default
│   ├── app1
│   ├── app2
│   └── appN..
└── <namespace> 
    └── appN...
```

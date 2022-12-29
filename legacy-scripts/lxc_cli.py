""" LXC CLI Parsers """
import json
import subprocess


def get_running_containers(remote=None):
    """ Get List of Running Container Names

    Args:
        remote (str): Remote LXD Hostname
    Returns:
        list: Running container names
    """
    r_str = remote + ":" if remote else ""
    lxc_list = subprocess.run(
        f"lxc list {r_str} --format json".split(),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    lxc_json = json.loads(lxc_list.stdout)
    running_containers = []
    for c in lxc_json:
        if c.get("status") == "Running":
            running_containers.append(c["name"])
    # print(json.dumps(lxc_json, indent=4))
    return running_containers


def lxc_exec(container, cmd, remote=None):
    """ Run command in container using lxc exec, returning subprocess result

    Args:
        container (str): Container Name
        cmd (str): Command to run
        remote (str): remote LXD hostname
    Returns:
        subprocess.CompletedProcess: result of subprocess.run
    """

    update_cmd = ["lxc", "exec"]
    if remote:
        update_cmd.append(remote + ":" + container)
    else:
        update_cmd.append(container)
    update_cmd += ["--", "sh", "-xc"]
    update_cmd.append(cmd)
    print(f"Running on container {container}, command: {cmd}")
    return subprocess.run(
        update_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

"""Opt-in per-trial networks from an explicit, operator-checked IPv4 pool.

Docker atomically reserves each subnet; no daemon configuration changes.
Only networks carrying this module's exact ownership labels are removed.
"""
import asyncio
import hashlib
import ipaddress
import json
import os
import subprocess

from .remote_docker import RemoteDockerEnvironment

OWNER = "lego-eval-explicit-subnets-v1"


def docker(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=45)


def reserve_network(session):
    pool = ipaddress.ip_network(os.environ["LEGO_EVAL_SUBNET_POOL"], strict=True)
    if pool.version != 4 or not pool.is_private or pool.prefixlen != 20:
        raise ValueError("Require an explicitly checked private IPv4 /20 pool")
    prefix = int(os.environ.get("LEGO_EVAL_SUBNET_PREFIX", "28"))
    if prefix not in (28, 29):
        raise ValueError("Per-trial subnet must be /28 or /29")
    subnets = list(pool.subnets(new_prefix=prefix))
    digest = hashlib.sha256(session.encode()).hexdigest()
    name = "lego-eval-" + digest[:24]
    prior = docker("network", "inspect", name)
    if prior.returncode == 0:
        raise RuntimeError(f"Network already exists; inspect stale trial before retry: {name}")
    offset = int(digest[:8], 16) % len(subnets)
    for i in range(len(subnets)):
        subnet = str(subnets[(offset + i) % len(subnets)])
        result = docker("network", "create", "--driver", "bridge", "--subnet", subnet,
                        "--label", f"lego.owner={OWNER}", "--label", f"lego.session={session}", name)
        if result.returncode == 0:
            return name, subnet
        if "overlap" not in result.stderr.lower():
            raise RuntimeError(result.stderr)
    raise RuntimeError("Project subnet pool exhausted")


def release_network(name, session):
    result = docker("network", "inspect", name)
    if result.returncode:
        if "no such network" in result.stderr.lower() or "not found" in result.stderr.lower():
            return
        raise RuntimeError(result.stderr)
    obj = json.loads(result.stdout)[0]
    labels = obj.get("Labels") or {}
    if labels.get("lego.owner") != OWNER or labels.get("lego.session") != session:
        raise RuntimeError("Refusing to remove a network without matching ownership")
    if obj.get("Containers"):
        raise RuntimeError(f"Network still has containers: {name}")
    result = docker("network", "rm", name)
    if result.returncode:
        raise RuntimeError(result.stderr)


class PooledRemoteDockerEnvironment(RemoteDockerEnvironment):
    @property
    def _docker_compose_paths(self):
        paths = list(super()._docker_compose_paths)
        override = getattr(self, "_explicit_network_override", None)
        if override is not None:
            paths.append(override)
        return paths

    async def start(self, force_build):
        # Synchronous reservation is bounded and cannot outlive cancellation.
        name, subnet = reserve_network(self.session_id)
        self._explicit_network_name = name
        path = self.trial_paths.trial_dir / "docker-compose-explicit-network.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"networks": {"default": {"external": True, "name": name}}}))
        self._explicit_network_override = path
        (self.trial_paths.trial_dir / "explicit_network_audit.json").write_text(
            json.dumps({"network": name, "subnet": subnet, "session": self.session_id}))
        try:
            await super().start(force_build)
        except BaseException:
            await asyncio.shield(self.stop(delete=False))
            raise

    async def stop(self, delete):
        await super().stop(delete)
        name = getattr(self, "_explicit_network_name", None)
        if name:
            release_network(name, self.session_id)
            self._explicit_network_name = None

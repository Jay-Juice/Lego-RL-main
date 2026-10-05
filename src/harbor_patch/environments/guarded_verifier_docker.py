"""Opt-in verifier exec process-group cleanup when Harbor cancels verification."""
import asyncio
import shlex
import uuid

from .pooled_remote_docker import PooledRemoteDockerEnvironment


class GuardedVerifierDockerEnvironment(PooledRemoteDockerEnvironment):
    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        if not env or env.get("LEGO_VERIFIER_PROCESS_GUARD") != "1":
            return await super().exec(command, cwd, env, timeout_sec, user)
        env = dict(env)
        env.pop("LEGO_VERIFIER_PROCESS_GUARD")
        # A unique file inside this trial's container identifies only this exec.
        pidfile = "/tmp/lego-verifier-" + uuid.uuid4().hex + ".pgid"
        inner = f"echo $$ > {pidfile}; exec bash -c {shlex.quote(command)}"
        wrapped = "setsid --wait bash -c " + shlex.quote(inner)
        try:
            return await super().exec(wrapped, cwd, env, timeout_sec, user)
        finally:
            # Killing docker/compose's client does not kill its in-container exec.
            # Terminate that exec's process group before Harbor can retry it.
            cleanup = f"""
for i in $(seq 1 20); do [ -s {pidfile} ] && break; sleep 0.1; done
if [ -s {pidfile} ]; then
  read -r pgid < {pidfile}
  case "$pgid" in ''|*[!0-9]*) exit 2;; esac
  [ "$pgid" -gt 1 ] || exit 2
  kill -TERM -- -"$pgid" 2>/dev/null || true
  sleep 0.5
  kill -KILL -- -"$pgid" 2>/dev/null || true
  rm -f {pidfile}
fi
"""
            await asyncio.shield(super().exec(cleanup, user="root", timeout_sec=10))

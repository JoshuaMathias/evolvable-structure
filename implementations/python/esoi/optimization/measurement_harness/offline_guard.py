"""Refuse a model command or an outbound network connection while an offline run is in progress."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from esoi.optimization.measurement_harness.arm_loading import arm_targets
from esoi.optimization.measurement_harness.run_errors import OfflineViolation, PendingNetwork
from esoi.structure.intent_registry.config import Config


MODEL_COMMANDS = ("claude", "codex", "gemini")   # the commands an offline run may not start


OFFLINE_ENV = "ESOI_OFFLINE"                     # set to 1 during an offline run, for a provider that wants to refuse by itself


class OfflineGuard:
    """Refuses to start a model command while an offline run is in progress. An arm that is not declared live (``PAID = True``, a
    ``paid_arms`` entry, or run with ``--max-calls``) must not call a model, whatever a provider's fallback finds on the machine:
    while the guard is on, ``subprocess.Popen`` raises ``OfflineViolation`` for a command named in ``MODEL_COMMANDS`` and the
    attempt is counted in ``meter.attempted`` (the row's details show it beside the metered calls), and ``ESOI_OFFLINE=1`` is set.

    When the caller already set ``ESOI_OFFLINE=1`` the guard also refuses outbound network: ``socket.socket.connect``,
    ``connect_ex`` and ``socket.create_connection`` raise ``OfflineViolation`` for any address that is not loopback or a unix
    socket, so ``urllib``, ``requests``, ``httpx`` and ``asyncio`` clients (all of which connect through a Python socket) cannot
    reach out, while a local service on 127.0.0.1 or ``::1`` still answers. A client written in C that opens its own sockets is
    not seen."""

    def __init__(self, meter: "CallMeter"):
        self.meter = meter
        self.real: Any = None
        self.before: Optional[str] = None
        self.sockets: Optional[Tuple[Any, Any, Any]] = None

    def start(self) -> None:
        meter, real = self.meter, subprocess.Popen

        class Guarded(real):   # type: ignore[valid-type, misc]
            def __init__(self, args, *rest, **options):
                first = args if isinstance(args, (str, bytes)) else (list(args) or [""])[0]
                word = (os.fsdecode(first).split() or [""])[0]
                if os.path.basename(word) in MODEL_COMMANDS:
                    meter.attempted += 1
                    raise OfflineViolation(f"offline run refused to start {os.path.basename(word)}: the arm is not declared live "
                                           "(PAID = True, paid_arms, or --max-calls)")
                super().__init__(args, *rest, **options)

        self.real, self.before = real, os.environ.get(OFFLINE_ENV)
        subprocess.Popen = Guarded   # type: ignore[misc]
        if self.before == "1":
            self.block_network()
        os.environ[OFFLINE_ENV] = "1"

    def block_network(self) -> None:
        """Refuse a socket connection to anything but loopback or a unix socket for as long as the guard is on."""
        import socket
        meter = self.meter
        real_connect, real_connect_ex, real_create = socket.socket.connect, socket.socket.connect_ex, socket.create_connection
        self.sockets = (real_connect, real_connect_ex, real_create)

        def refuse(address: Any) -> None:
            host = address[0] if isinstance(address, (tuple, list)) and address else None
            if host is None:        # a unix socket path
                return
            host = host.decode() if isinstance(host, bytes) else str(host)
            if host == "localhost" or host.startswith("127.") or host in ("::1", "0.0.0.0", ""):
                return
            meter.attempted += 1
            raise OfflineViolation(f"offline run refused a network connection to {host}: ESOI_OFFLINE=1 is set")

        def connect(self_socket: Any, address: Any) -> Any:
            refuse(address)
            return real_connect(self_socket, address)

        def connect_ex(self_socket: Any, address: Any) -> Any:
            refuse(address)
            return real_connect_ex(self_socket, address)

        def create_connection(address: Any, *rest: Any, **options: Any) -> Any:
            refuse(address)
            return real_create(address, *rest, **options)
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection = connect, connect_ex, create_connection   # type: ignore[assignment]

    def stop(self) -> None:
        if self.real is not None:
            subprocess.Popen = self.real   # type: ignore[misc]
            self.real = None
            if self.sockets is not None:
                import socket
                socket.socket.connect, socket.socket.connect_ex, socket.create_connection = self.sockets   # type: ignore[assignment]
                self.sockets = None
            if self.before is None:
                os.environ.pop(OFFLINE_ENV, None)
            else:
                os.environ[OFFLINE_ENV] = self.before


def refuse_offline_network(config: Config, component: str, impl: str, environ: Optional[Dict[str, str]] = None) -> None:
    """Raise ``PendingNetwork`` when ``ESOI_OFFLINE=1`` and the arm declares a required ``network`` requirement: the same answer
    ``esoi.runtime.assemble_by_name.entry`` gives (pending-network), before any case runs, any provider is built or any row is recorded."""
    from esoi.runtime.assemble_by_name.interface import checking, declarations
    environ = os.environ if environ is None else environ
    if environ.get(OFFLINE_ENV) != "1":
        return
    hosts: List[str] = []
    for target in arm_targets(config, component, impl):
        if target is None:
            continue
        for one in checking.check(declarations.declared(target), environ):
            if isinstance(one.requirement, declarations.Network) and one.blocking and one.requirement.label not in hosts:
                hosts.append(one.requirement.label)
    if hosts:
        raise PendingNetwork(f"pending-network: {component}/{impl} needs {', '.join(hosts)} and {OFFLINE_ENV}=1 is set; "
                             "nothing was started or recorded (run it without ESOI_OFFLINE to measure it)")

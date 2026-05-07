"""PostgREST sidecar container so `supabase-py` can hit a hermetic stack.

The supabase Python client speaks the Supabase REST API
(``{url}/rest/v1/...``), which is PostgREST under the hood. To run the
existing test suite hermetically we boot a `postgrest/postgrest`
container alongside the Postgres testcontainer and point the client
at it. Storage / Auth / Realtime are mocked or unused so we don't
need the rest of the Supabase stack.

Why a hand-rolled `DockerContainer` subclass
============================================

testcontainers ships first-class wrappers for Postgres, Redis, Kafka,
etc., but not PostgREST. We use the generic `DockerContainer` base so
we can configure the env vars PostgREST cares about
(``PGRST_DB_URI``, ``PGRST_DB_SCHEMA``, ``PGRST_DB_ANON_ROLE``,
``PGRST_DB_PRE_REQUEST``, ``PGRST_JWT_SECRET``).

JWT secret + roles
==================

Production Supabase signs JWTs with the project's anon/service_role
keys. The supabase-py client sends an ``Authorization: Bearer
<key>`` header on every call. We:

1. Create a deterministic JWT secret in the test stack.
2. Mint matching anon + service_role JWTs from that secret.
3. Hand them back to the test as ``anon_key`` / ``service_role_key``
   so the existing ``Client(url, key)`` constructor lights up exactly
   as it does in production.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from jose import jwt as pyjwt  # python-jose, already in requirements.txt
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.waiting_utils import wait_for_logs

# Long-enough lifetime that a single CI run never sees an expiring token.
_JWT_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
_DEFAULT_SECRET = "hermetic-test-jwt-secret-please-do-not-ship-in-prod"

# Pinned upstream image. Update deliberately — the wire format and the
# env-var contract here track this version.
POSTGREST_IMAGE = "postgrest/postgrest:v12.2.0"


@dataclass(frozen=True)
class StackEndpoints:
    """Bundle of URLs + keys the test client needs to talk to the stack."""

    base_url: str
    anon_key: str
    service_role_key: str
    db_dsn: str


def _mint_jwt(role: str, secret: str = _DEFAULT_SECRET) -> str:
    payload = {
        "role": role,
        "iss": "supabase-testcontainer",
        "iat": int(time.time()),
        "exp": int(time.time()) + _JWT_TTL_SECONDS,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


class PostgrestContainer(DockerContainer):
    """A PostgREST container wired to an existing Postgres on the same network."""

    def __init__(
        self,
        db_dsn_inside_network: str,
        *,
        jwt_secret: str = _DEFAULT_SECRET,
        anon_role: str = "anon",
    ) -> None:
        super().__init__(POSTGREST_IMAGE)
        self.with_exposed_ports(3000)
        # PostgREST resolves this DSN _from inside_ the docker network, so it
        # uses the shared network alias of the postgres container, not the
        # 127.0.0.1 mapping the host sees.
        self.with_env("PGRST_DB_URI", db_dsn_inside_network)
        self.with_env("PGRST_DB_SCHEMA", "public")
        self.with_env("PGRST_DB_ANON_ROLE", anon_role)
        self.with_env("PGRST_JWT_SECRET", jwt_secret)
        # ``service_role`` is what supabase-py uses for backend writes;
        # mark it pre-request-safe so PostgREST doesn't reject row-level
        # access decisions when the client switches roles via JWT.
        self.with_env("PGRST_DB_PRE_REQUEST", "")

    def wait_ready(self, timeout: int = 30) -> None:
        # PostgREST prints "Listening on port 3000" once it's accepting
        # connections. testcontainers' wait_for_logs polls the container
        # log stream, which is cheaper than HTTP probing here.
        wait_for_logs(self, "Listening on port 3000", timeout=timeout)


def boot_supabase_stack(
    *,
    network: Network | None = None,
    jwt_secret: str = _DEFAULT_SECRET,
    db_image: str = "postgres:16-alpine",
) -> tuple[StackEndpoints, list[DockerContainer], Network]:
    """Boot Postgres + PostgREST on a shared docker network.

    The two containers must share a network so PostgREST can reach the
    DB by its container alias (testcontainers exposes container ports
    on the host, but PostgREST is _inside_ the docker network when it
    dials the DB). Returns the endpoints the test client needs plus the
    underlying container handles so the caller can stop them on
    teardown.

    The migration runner is intentionally _not_ called here — callers
    apply the SQL after this returns so they can swap migration sets
    in property-based tests.
    """
    from testcontainers.postgres import PostgresContainer

    own_network = network is None
    network = network or Network()
    if own_network:
        network.create()

    pg = PostgresContainer(
        image=db_image,
        username="postgres",
        password="postgres",
        dbname="postgres",
    )
    pg.with_network(network)
    pg.with_network_aliases("postgres")
    pg.start()

    # The DSN PostgREST sees from inside the network points at the alias
    # we just created; the DSN the host (test runner) sees points at the
    # mapped port on 127.0.0.1.
    dsn_inside = "postgresql://postgres:postgres@postgres:5432/postgres"
    dsn_host = pg.get_connection_url().replace("+psycopg2", "")

    pgrst = PostgrestContainer(dsn_inside, jwt_secret=jwt_secret)
    pgrst.with_network(network)
    pgrst.with_network_aliases("postgrest")
    pgrst.start()
    pgrst.wait_ready()

    host = pgrst.get_container_host_ip()
    port = pgrst.get_exposed_port(3000)
    base_url = f"http://{host}:{port}"

    endpoints = StackEndpoints(
        base_url=base_url,
        anon_key=_mint_jwt("anon", jwt_secret),
        service_role_key=_mint_jwt("service_role", jwt_secret),
        db_dsn=dsn_host,
    )
    return endpoints, [pg, pgrst], network


__all__ = [
    "POSTGREST_IMAGE",
    "PostgrestContainer",
    "StackEndpoints",
    "boot_supabase_stack",
]

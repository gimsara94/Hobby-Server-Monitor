"""Check local LXD connectivity without modifying containers or configuration."""

import argparse
import json
import sys

from pylxd import Client
from pylxd.exceptions import ClientConnectionFailed, LXDAPIException, NotFound
from requests.exceptions import RequestException


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", help="Also inspect a named test container.")
    args = parser.parse_args()

    try:
        client = Client(timeout=5)
        environment = client.host_info.get("environment", {})
        version = environment.get("server_version", "unknown")
        if not version.startswith("5."):
            print(
                f"Expected LXD 5.x for this task; received {version}.",
                file=sys.stderr,
            )
            return 1

        result = {
            "lxd_version": version,
            "containers": [
                {"name": container.name, "status": container.status}
                for container in client.containers.all()
            ],
        }
        if args.container:
            container = client.containers.get(args.container)
            result["test_container"] = {
                "name": container.name,
                "status": container.status,
                "cpu_limit": container.expanded_config.get("limits.cpu"),
                "memory_limit": container.expanded_config.get("limits.memory"),
                "privileged": container.expanded_config.get(
                    "security.privileged", "false"
                ),
            }
        print(json.dumps(result, indent=2))
        return 0
    except NotFound:
        print(f"Container {args.container!r} does not exist.", file=sys.stderr)
    except (ClientConnectionFailed, LXDAPIException, RequestException, OSError) as error:
        print(f"Cannot connect to local LXD: {error}", file=sys.stderr)
        print(
            "Install and initialize LXD, check that its daemon is running, "
            "and verify your current session belongs to the lxd group. "
            "See README.md.",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

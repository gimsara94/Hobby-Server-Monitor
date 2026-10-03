# Hobby Server Monitor

An interview project for an efficient, secure LXD management dashboard. See
[task.md](task.md) for the complete requirements.

See [PLAN.md](PLAN.md) for the staged completion plan and milestone checks.

Current stage: the local LXD connection is verified and the Falcon backend
foundation is implemented. The dashboard, authentication, database, and collector
have not been implemented yet.

## Phase 1: local development environment

Checked on October 3, 2026: native Ubuntu 24.04.2, Python 3.12.3, Node.js 22.18.0,
and npm 10.9.3. The repository already has an `origin` remote. LXD was not installed.
The host had approximately 24 GiB free disk space and 7.6 GiB total RAM at inspection.

Subsequently verified: LXD 5.21.8, the `default` loop-backed ZFS pool, `lxdbr0`,
and Python access to the running `phase1-test` container with one CPU core,
512 MiB RAM, and unprivileged mode.

### 1. Install LXD 5.x

Run these commands in your own terminal; `sudo` requires your password:

```bash
sudo snap install lxd --channel=5.21/stable
sudo usermod -aG lxd "$USER"
```

Log out of Ubuntu and log back in to refresh group membership, then reopen your
terminal and editor. Check:

```bash
id -nG
lxd --version
```

The groups should include `lxd`; the version should begin with `5.21`.
Only give this group to trusted local administrators: access to the LXD socket
effectively grants host root privileges. Future dashboard users must not receive
local group membership or direct socket access.

### 2. Initialize storage and networking

For this fresh installation, run:

```bash
lxd init
```

Use these choices when the wizard asks:

- Clustering: no.
- Create a storage pool: yes; keep the name `default`.
- Storage driver: use the suggested `zfs` driver if available; `btrfs` is another
  quota-capable option.
- Use an existing block device: no. Use a loop-backed pool for development.
- Pool size: choose a modest size that leaves space for Ubuntu. For this machine's
  approximately 24 GiB of free disk space, `8GiB` is a reasonable initial test pool.
  Recheck `df -h /` before choosing; this is a development example, not an application
  quota or a universal default.
- MAAS: no.
- Create a local network bridge: yes; keep `lxdbr0` and automatic address choices.
- Expose LXD over the network: no.
- Automatic image updates: yes.
- Print a YAML preseed: optional.

Question order and available storage drivers can vary. Never select a physical
disk or partition containing your files. Do not reinitialize an existing LXD setup
without inspecting it first.

Although the task permits `lxd init --minimal`, its default `dir` storage driver
lacks disk quotas. Interactive initialization avoids needing a storage migration
when implementing disk allocation enforcement.

Check the resulting configuration:

```bash
lxc storage list
lxc network list
lxc profile show default
lxc list
```

Expect a storage pool, a managed bridge, and a default profile containing a root
disk device and network device.

### 3. Create and manage a disposable test container

Use a fresh name; these commands create a container on your machine:

```bash
lxc launch ubuntu:24.04 phase1-test -c limits.cpu=1 -c limits.memory=512MiB -c security.privileged=false
lxc list
lxc exec phase1-test -- cat /etc/os-release
lxc stop phase1-test
lxc start phase1-test
lxc info phase1-test
```

The first launch downloads an Ubuntu image and can take a few minutes. The limits
are conservative settings for this disposable test, not the future dashboard's
runtime bounds. Keep the container running for the Python check below.

### 4. Install Python dependencies and verify pylxd

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/check_lxd.py --container phase1-test
```

If creating a virtual environment reports that `ensurepip` is unavailable, install
`python3-venv` with `sudo apt install python3-venv`, then retry.

The checker uses the local Unix socket and a five-second HTTP timeout. It only
reads daemon and container information; it does not run commands or change state.
Expected output includes LXD version `5.21...`, the test container with status
`Running`, CPU limit `1`, memory limit `512MiB`, and privileged mode `false`.

If the connection fails, check:

```bash
id -nG
snap services lxd
lxc list
```

Do not solve socket access errors by making the socket world-writable. If you
recently joined the `lxd` group, log out and back in, including restarting the editor.

### 5. Optional cleanup and phase completion

After verifying the Python connection, delete only the disposable test container
if you no longer need it. Deletion removes its files permanently:

```bash
lxc stop phase1-test
lxc delete phase1-test
```

Phase 1 is complete when you have created, stopped, started, inspected, and
optionally deleted a real container, and the Python checker has connected
successfully. Record the real time spent and any errors in [REPORT.md](REPORT.md).

Review changes, then commit the setup work:

```bash
git status
git add .gitignore README.md REPORT.md requirements.txt scripts/check_lxd.py
git commit -m "Set up local LXD development environment"
git push -u origin HEAD
```

## Phase 2: run the Falcon backend foundation

From the repository root, install the dependencies:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Use `.env.example` as the template for a private `.env` file. If you already filled
in `.env`, keep it. Otherwise, copy the template and edit the values locally:

```bash
cp -n .env.example .env
chmod 600 .env
```

The loader reads the repository's `.env`; explicit process environment variables
override file values. It does not change the process environment or expand variable
references inside file values. Credential fields are excluded from the settings'
debug representation. `.env` and downloaded `client_secret*.json` files are excluded
from Git; keep downloaded OAuth credentials outside the repository as well.

| Variable | Meaning | Default |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` | Web application OAuth client ID. | Empty |
| `GOOGLE_CLIENT_SECRET` | Private OAuth client secret. | Empty |
| `GOOGLE_REDIRECT_URI` | Callback URL registered with Google. | `http://localhost:8000/auth/google/callback` |
| `BOOTSTRAP_ADMIN_EMAIL` | Google account intended to become the initial Admin. | Empty |
| `LXD_SOCKET_PATH` | Absolute path to the local LXD Unix socket. | `/var/snap/lxd/common/lxd/unix.socket` |
| `LXD_TIMEOUT_SECONDS` | Per-request connect/read timeout, greater than zero and at most 30 seconds. | `5` |

The OAuth fields are loaded now, but login and the callback endpoint are not
implemented yet. Empty credentials do not prevent the diagnostic endpoints from
starting. Successful health checks do not validate Google credentials or invitations.

Start the local server:

```bash
.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 2 'backend.app:create_app()'
```

One worker and two threads provide a modest initial process count while allowing
a liveness request during a slow LXD check. Actual resource use still needs to be
measured. The loopback bind is for development on this machine. The backend user
needs permission to access the LXD socket; LXD's network listener is not required.
Press Ctrl+C to stop the server.

In another terminal:

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

| Endpoint | Successful response | Purpose |
| --- | --- | --- |
| `GET /health` | HTTP 200, `{"status":"ok"}` | Liveness: the API can serve a request without contacting LXD. |
| `GET /ready` | HTTP 200, `{"status":"ready"}` | Readiness: the API can reach a trusted LXD 5.x daemon. |

These diagnostic routes are public and do not return container information or
credentials. Both prevent response caching. Every readiness request uses a fresh
local LXD connection, closed even on failure. A daemon/socket/request failure returns
HTTP 503 with `{"error":{"code":"lxd_unavailable","message":"LXD is unavailable."}}`
and a `Retry-After: 5` header. A later request can recover without restarting the API.
The request timeout is not a deadline for an entire operation.

Unexpected errors return a generic HTTP 500 response; logs record the exception
type rather than raw exception text. Unknown routes return 404, and unsupported
HTTP methods return 405 while preserving the `Allow` header.

Run the automated checks:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

Verified on October 3, 2026: all 10 tests passed, dependency checks passed, and a
temporary Gunicorn server returned HTTP 200 for both endpoints with real local LXD.
Outage/recovery tests use injected failures; the real daemon was not stopped.
The temporary server was stopped after verification. SQLite models, Google login,
protected container APIs, collector, and Astro UI remain to be implemented.

## References

- [LXD installation and first steps](https://canonical.com/lxd/docs/default/tutorial/first_steps/)
- [LXD initialization and storage choices](https://canonical.com/lxd/docs/default/howto/initialize/)
- [LXD security boundary](https://canonical.com/lxd/docs/default/explanation/security/)
- [pylxd installation](https://pylxd.readthedocs.io/en/latest/installation.html)
- [Falcon WSGI tutorial](https://falcon.readthedocs.io/en/stable/user/tutorial.html)

The rest of the setup guide, architecture, data model, API reference, and application
configuration will be documented as those components are implemented.

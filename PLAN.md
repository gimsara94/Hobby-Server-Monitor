# Staged completion plan

This plan follows [task.md](task.md). Target delivery: **October 7, 2026**;
hard deadline: **October 9, 2026**. Dates are in Asia/Colombo time.
The schedule is a target, not a record of completed work.

## Current position

- Verified: LXD 5.21.8, initialized ZFS storage and bridge, and Python access to
  the running unprivileged test container with the expected CPU/RAM limits.
- Implemented and verified: Falcon configuration loading, health/readiness routes,
  local LXD readiness service, sanitized errors, and 10 automated checks.
- User reports Google OAuth client, local credentials, and test users prepared;
  login itself is not implemented or verified. Stop/start exercise is not recorded.
- Pending: remaining backend, authentication, databases, collector, dashboard, container
  management, user quotas, command execution, deployment, and measurements.

Complete each stage's checks before marking it done. Record actual hours,
decisions, issues, and AI-assisted changes in REPORT.md throughout the project.
Make a meaningful commit at each working milestone.

## Stage 1 — Verify prerequisites

**Target: October 3. Status: LXD connection verified; OAuth setup reported ready.**

- Complete the LXD setup in README.md, including a quota-capable storage pool.
- Create, stop, start, and inspect a disposable unprivileged Ubuntu container.
- Run `scripts/check_lxd.py` successfully against the real daemon.
- Prepare Google OAuth credentials and development callback configuration.
- Choose two Google accounts for the Admin and invited-user acceptance checks.

**Done when:** the Python checker reads a running container, its limits, and
daemon information; OAuth credentials are available without committing secrets.

## Stage 2 — Build the backend and data foundation

**Target: October 3. Depends on: Stage 1 for real LXD checks.**

Progress: configuration loading, Falcon app factory, local LXD readiness wrapper,
health/readiness endpoints, and structured errors implemented and tested. Real
Gunicorn HTTP checks passed against LXD. Database work and reconciliation remain.

- Create the Falcon application, configuration loader, and structured errors.
- Add SQLite initialization/migrations, foreign keys, and parameterized queries.
- Model users, invitations, sessions, container records, assignments, per-user
  quotas, and audit events.
- Give each managed container a stable application ID and one quota owner.
  Keep ownership separate from access assignments so shared access does not
  double-count allocated resources.
- Define how existing host containers are discovered and how missing, renamed,
  or deleted LXD containers are reconciled with application records.
- Wrap pylxd behind a service with bounded timeouts and useful unavailable errors.
- Add `.env.example`, secret exclusions, and health/readiness endpoints.

**Done when:** a clean database initializes repeatably, the API starts from
documented configuration, and LXD failure produces a controlled response.

## Stage 3 — Implement Google login and authorization

**Target: October 3–4. Depends on: Stage 2.**

- Use an explicit `BOOTSTRAP_ADMIN_EMAIL` for the initial Admin and document it.
- Implement Google login/callback validation, including OAuth state, provider
  identity verification, verified email, and the invitation/bootstrap allowlist.
- Store opaque sessions server-side; set HttpOnly/Secure/SameSite cookies,
  expire sessions, and invalidate them on logout and user revocation.
- Add CSRF protection for cookie-authenticated mutations.
- Guard API endpoints by default, with centralized role and container-access checks.
- Apply the same access rules to metrics, history, and command execution.
- Prevent accidental removal of the final active Admin.

**Done when:** the configured Admin can sign in; an uninvited account is rejected;
an invited user cannot call Admin APIs or access an unassigned container (`403`).
Logout and revocation invalidate access.

## Stage 4 — Implement container operations and quota enforcement

**Target: October 4. Depends on: Stages 2–3.**

- Discover host capacity, pool availability, images, bridges, and eligible profiles.
- Add list/detail, create, start, stop, restart, freeze, update-limits, and delete APIs.
- Validate names and every option server-side; expose RAM, CPU cores/allowance,
  disk, network, pool, ephemeral mode, autostart, and description.
- Derive bounds from host capacity, existing allocations, and the quota owner's
  remaining budget. Define units, reservation headroom, and stopped-container accounting.
- Reject privileged containers and unsafe device/profile/configuration options.
- Enforce quotas with serialized reservations so concurrent requests cannot
  over-allocate; reconcile reservations after failed or interrupted LXD operations.
- Audit destructive actions and limit changes with actor, target, result, and time.
- Preserve audit history while cleaning up assignments when a container is deleted.
- Implement invitations, role/revocation changes, access assignments, quotas, and
  host/per-user allocation summaries.

**Done when:** real containers can be created and managed; invalid options,
capacity violations, and concurrent quota violations are rejected; allocations
remain consistent after failed operations and deletion.

## Stage 5 — Add independent metrics collection and history

**Target: October 4–5. Depends on: Stage 2; Stage 3 for protected read APIs.**

- Run a separate worker that collects all containers every 10 seconds.
- Store timestamped samples in TinyFlux using stable container IDs.
- Collect CPU, RAM, disk, network totals/rates, state, uptime, process count,
  OS/image information, and IPv4 where available.
- Calculate rates from consecutive samples and handle counter resets, restarts,
  stopped containers, missing fields, and stale readings explicitly.
- Give TinyFlux one writer. Choose and document coordinated reads, bounded
  retention/compaction, disk budget, and capped/downsampled history responses.
- Continue retrying after LXD outages without overlapping polling cycles or
  blocking the web API. Resume cleanly after a worker restart.

**Done when:** samples continue with every browser closed; collection resumes
after LXD returns; history queries are bounded; retention actually removes old
data. Record a measured growth projection for 30 days.

## Stage 6 — Build the Astro browser workflows

**Target: October 5–6. Depends on: Stages 3–5.**

- Build role-appropriate login, dashboard, container detail, and quota views.
- Show live metrics with a modest refresh interval and stop polling in hidden tabs.
- Add creation and limit forms driven by runtime options from the API.
- Add lifecycle controls and explicit deletion confirmation.
- Add Admin screens for invitations, assignments, roles, revocation, and quotas.
- Add selectable history charts and per-container consumption summaries.
- Show loading, empty, unauthorized, stale-data, daemon-down, and operation-error states.

**Done when:** the Admin can manage containers and users from the browser;
the invited user sees only assigned containers and their own allocation budget;
charts show real stored samples and form errors are understandable.

## Stage 7 — Add bounded container command execution

**Target: October 6. Depends on: Stages 3–4 and the container detail UI.**

- Implement command submission and output through real pylxd container exec.
- Re-check active session and container assignment for every execution request.
- Keep execution inside unprivileged containers; never interpolate a command
  into a host shell or expose the LXD socket, host mounts, or arbitrary devices.
- Bound command duration, captured output, request size, and concurrent executions;
  document how timed-out commands are terminated and cleaned up.
- Audit execution metadata without recording credentials or sensitive output.
- Explain the container isolation boundary, remaining escape risks, and why
  restricting command strings alone is not a sufficient defense.

**Done when:** both roles can execute a command in an authorized container;
unauthorized, stopped-container, long-running, and excessive-output cases behave
predictably without compromising API responsiveness.

## Stage 8 — Verify security, resilience, and resource use

**Target: October 6–7. Depends on: Stages 1–7.**

- Add focused tests for login/session handling, RBAC, CSRF, quota concurrency,
  input validation, auditing, retention, and failure recovery.
- Run the nine baseline workflows in task.md against real LXD and two Google accounts.
- Verify that forged container IDs fail in detail, history, mutation, and exec APIs.
- Exercise LXD outages, worker/API restarts, container deletion, user revocation,
  and multiple browser tabs.
- Measure idle API/worker CPU and RAM, loaded browser behavior, collector cost,
  and TSDB growth. Record hardware, container count, duration, and methodology.
- Add service definitions and verify startup ordering, restart behavior, and reboot
  recovery. Document which service holds LXD privileges and the resulting risk.

**Done when:** every baseline workflow passes, meaningful security/failure checks
pass, collection cost stays independent of browser-tab count, and REPORT.md
contains actual measurements rather than estimates presented as measurements.

## Stage 9 — Finish documentation and prepare submission

**Target: October 7; October 8–9 reserved for fixes. Depends on: Stage 8.**

- Complete README.md with clean setup, Google OAuth, architecture diagram, data
  model, API examples/permissions, security notes, and every environment variable.
- Finalize REPORT.md with actual hours, decisions, failures, measurements,
  limitations, and detailed AI-tool disclosure.
- Rehearse setup from a clean database/configuration and verify dependency manifests.
- Review the repository for secrets, generated data, missing files, and misleading claims.
- Review and push incremental commits; prepare the repository link and submission
  email text for the developer to send before the hard deadline.
- Prepare a short browser demo and explanations of sessions, authorization,
  quotas, terminal isolation, polling, retention, and resource trade-offs.

**Done when:** another developer can reproduce the app, all baseline requirements
are demonstrated, documentation matches behavior, and the repository is ready
for submission. Sending the invitation-email reply remains a developer action.

## Schedule and scope control

| Date | Intended checkpoint |
| --- | --- |
| October 3 | Real LXD connection, OAuth preparation, backend/data foundation |
| October 4 | Authentication, authorization, container/user/quota APIs |
| October 5 | Collector/history plus initial dashboard |
| October 6 | Complete browser workflows and command execution |
| October 7 | Acceptance checks, measurements, documentation, delivery target |
| October 8–9 | Fix failures, rehearse clean setup, complete submission |

This is an aggressive schedule for the remaining scope. Resolve LXD and OAuth
prerequisites first. If work slips, defer visual polish and optional alerts/extra
features; keep all nine baseline workflows, security checks, real measurements,
and reproducible documentation in scope. Do not report mocked integrations as
completed real-world checks.

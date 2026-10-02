# Interview Task: Software Engineer Intern — Hobby Server Monitor

**Contact:** [dev@roboticgen.co](https://www.google.com/search?q=mailto%3Adev%40roboticgen.co)

---

## 👤 Role

You are a Software Engineer Intern. There is an old Linux machine in the office, and your job is to turn it into an on-premises server for testing purposes.

You will use LXD to manage containers on that machine, and you will build an admin dashboard and control panel on top of it so the server can be managed and monitored from a browser.

Two constraints run through the whole task and are weighted heavily in evaluation:

1. **Resource efficiency:** The tool runs on the server it monitors. It must consume as little CPU and RAM as possible while still doing its job.
2. **Security:** This is a server with container-level privileges. Authentication, authorization, and input handling must be done correctly.

---

## 📋 Prerequisites

* **WSL2 (Windows)** or a **native Ubuntu machine (preferred)** to test LXD functionality. (LXD does not run on macOS natively; use a VM if needed.)
* **Python 3.10+**
* **Node.js 18+** (for Astro)
* **LXD 5.x** installed and initialized (`lxd init --minimal` is enough for development)
* A **Google Cloud project** with OAuth 2.0 credentials (free tier without adding a card)

---

## 📘 Project Summary

### Users & Roles

| Role | Capabilities |
| --- | --- |
| **Admin** | Create, update, view, and delete containers. Manage users and container assignments. Full terminal access. |
| **Container User** | View metrics for containers explicitly assigned to them. Terminal access to those containers only. |

### Authentication

* Users sign in via **Google OAuth 2.0**.
* The first user to sign in becomes the Admin, or a bootstrap admin email is set via an environment variable. Document whichever you choose.
* Users who have never been invited by an Admin must not gain access simply by signing in with a Google account.

---

## 🧭 System Flow Overview

### 🔄 Main Process

#### 1. Admin logs into the admin dashboard

##### 1.1 Dashboard metrics overview

The dashboard shows all containers with key metrics. A starting set (decide what else earns space on the screen and what is noise):

* CPU usage (%)
* RAM usage (used / allocated, %)
* Disk usage (used / allocated, %)
* Network I/O (RX / TX bytes and rate)
* Container state (`Running` / `Stopped` / `Frozen` / `Error`)
* Uptime
* Process count
* Image / OS version
* IPv4 address

##### 1.2 Container creation

Admin can create a new container through an interactive form covering:

* Container name (validated: lowercase alphanumeric + hyphens, following LXD naming rules)
* Base image / Ubuntu version (selected from a list of available aliases)
* RAM allocation (slider with enforced min/max bounds)
* CPU allocation (slider or stepper for core count, plus CPU allowance %)
* Disk size (slider, bounded by available storage pool capacity)
* Network configuration (available bridges / profiles, discovered at runtime)
* Storage pool selection
* Ephemeral toggle
* Autostart on boot toggle
* Optional description

> **Note:** Bounds must be derived from actual host capacity and the requesting user's remaining quota, not hard-coded. The API must re-validate every value server-side. Explore `pylxd` for further configurable options, add what makes sense, and document what you added and why.

##### 1.3 Container management & lifecycle

* Start / stop / restart / freeze.
* Change resource limits on a running container.
* Delete container (with an explicit confirmation step).
* Destructive and limit-changing actions must leave an audit trail.

##### 1.4 User & quota management

* Invite users by Google account email.
* Assign / revoke container access.
* Change a user's role or revoke a user entirely.
* Set a resource quota per user: maximum RAM, CPU cores, and disk that user's containers may collectively consume.

##### 1.5 Usage accounting

* Total allocated vs. total available RAM, CPU, and disk for the host.
* Per-user allocated total against that user's quota.
* Per-container consumption over a selectable period, derived from the TSDB.

---

#### 2. Container User

* **2.1** Sees metrics only for containers assigned to them. Requesting an unassigned container by ID must return `403 Forbidden`.
* **2.2** Sees their own quota and how much of it is currently allocated.

---

#### 3. Common Terminal Access

Both roles can access a terminal for containers they have access to: send a command from the UI and view the result (a real `pylxd` exec is preferred).

> **Security Challenge:** This feature allows a logged-in user to execute arbitrary commands on a machine you control. Ensure this cannot be used to escape the container or compromise the host machine. You will be evaluated on your defense strategy.

---

### 🔄 Background Process

* Poll resource metrics for every container every **10 seconds**.
* Store samples in a TSDB (**TinyFlux**).
* The collector must keep working when LXD is temporarily unavailable.
* Metric collection cost must **not** scale with the number of open browser tabs.
* Storage growth must be bounded (e.g., retention policies, downsampling, or file-size capping) so running for a month on a small server does not exhaust disk space.

---

## 🛠️ Tech Stack

| Layer | Preferred Tech |
| --- | --- |
| **Backend** | Falcon |
| **Dashboard** | Astro |
| **LXD Client** | pylxd |
| **Relational DB** | sqlite3 |
| **TSDB** | TinyFlux |

*Substitutions are allowed only with clear justification in the final report. Choosing a familiar heavyweight framework simply because it is familiar is not considered valid justification.*

---

## 🎯 Scope & Expectations

### The Baseline

The tool is not finished until someone can, from a browser:

1. Sign in with Google and land in a view appropriate to their role.
2. As an Admin, view every container on the host with live resource metrics.
3. Create a container through a form that enforces valid runtime options.
4. Modify limits on, restart, and delete an existing container.
5. Invite a user, define their resource budget, and grant access to specific containers.
6. Sign in as that invited user and see only their assigned resources.
7. Inspect historical behavior over past minutes and hours via charts.
8. Run a command inside a container and view output safely.
9. Verify that metric collection runs continuously in the background and survives page reloads and daemon restarts.

### Key Architectural Decisions Left to You

Be prepared to justify your implementation for choices such as:

* How session persistence works and what logging out actually invalidates.
* Where authorization checks live and how new endpoints are guarded by default.
* Quota measurement precision and handling when limits are exceeded.
* Handling `pylxd` root/socket privileges safely.
* Push vs. poll frontend data updates and their idle overhead.
* TSDB storage retention and downsampling strategies over 30+ days.
* Interactive terminal security boundary and escape prevention.
* Schema integrity during container deletion or renaming.
* Downsampling payload sizes for 24-hour metric queries.
* UI and worker resilience when LXD daemon is unresponsive.
* First-admin bootstrap mechanism and privilege escalation defense.
* Service daemonization (e.g., systemd) and recovery after reboot.

### Non-Negotiables

* The metrics collector runs independently of the UI.
* You measured your resource footprint and published the actual numbers.
* You can explain and defend every line of code submitted.

---

## 📦 Expected Deliverables

### 🔹 Source Code

* Public or shared Git repository with backend, frontend, and operational scripts.
* Meaningful, incremental commit history.
* `.env.example` detailing all required environment variables.
* Dependency manifests (`requirements.txt` / `pyproject.toml`, `package.json`).
* Automated migration or `init_db` script from a clean machine state.

### 🔹 Documentation (`README.md`)

* **Setup Guide:** Step-by-step from clean Ubuntu/WSL machine to running app, including `lxd init` and Google Cloud OAuth configuration.
* **Architecture:** Block diagram and inter-service communication flow.
* **Data Model:** SQLite relational schema and TinyFlux schema/tag layout.
* **API Reference:** Endpoints, HTTP methods, authorization roles, and request/response payloads.
* **Security Notes:** Threat model summary and LXD socket access isolation.
* **Configuration:** Exhaustive documentation of all environment variables.

### 🔹 Final Report (`REPORT.md`)

* **Time Breakdown:** Logged hours across backend, frontend, LXD integration, and debugging.
* **Issues & Solutions:** Real implementation hurdles, failed attempts, and resolutions.
* **Learnings:** Key technical takeaways.
* **Bonus Features:** Optional value-add extensions implemented.
* **Resource Measurements:** Measured idle RAM/CPU footprint and profiling methodology.
* **Known Limitations:** Honest accounting of edge cases, gaps, or simulated components.
* **AI Tool Usage:** Full disclosure of tools used (e.g., Claude, Cursor, Copilot), what code was accepted, rejected, or debugged, and why.

---

## ✅ Evaluation Criteria

Reviews consist of a code assessment followed by a 30–45 minute technical interview.

| # | Area | Weight | Evaluation Focus |
| --- | --- | --- | --- |
| **1** | **Judgment & Defense** | 25% | Rationale behind trade-offs and alternative architectures considered. |
| **2** | **Security & Correctness** | 20% | API-level RBAC, robust input validation, secure terminal execution, and LXD privilege management. |
| **3** | **Functional Completeness** | 20% | End-to-end execution of baseline requirements on a clean environment. |
| **4** | **Code Quality** | 10% | Clean modular structure, explicit error handling, and maintainability. |
| **5** | **Documentation & Report** | 10% | Reproducibility of setup steps and critical depth of `REPORT.md`. |
| **6** | **Resource Efficiency** | 10% | Verified low idle CPU/RAM usage and bounded TSDB disk usage. |
| **7** | **UX** | 5% | Smooth handling of loading, empty, and error states. |
| **+** | **Bonus** | Up to +10% | Automated unit/integration tests, CI workflows, systemd configurations, or custom metric alerting. |

---

## 🔗 Starter Repository & Submission

1. **Repository Setup:**
* Use the GitHub template: `roboticgen-se-interview-task-Hobby-Server-Monitor-Template`
* Or fork directly from: [https://github.com/RoboticGen/roboticgen-se-interview-task-Hobby-Server-Monitor-Template](https://github.com/RoboticGen/roboticgen-se-interview-task-Hobby-Server-Monitor-Template)


2. **Submission:**
* Push all commits to your repository.
* Reply to the invitation email with your repository link before the hard deadline.



---

## 📅 Deadlines

| Type | Date | Note |
| --- | --- | --- |
| **Soft Deadline** | **2026-10-07** | Target delivery date demonstrating proactive time management. |
| **Hard Deadline** | **2026-10-09** | Strict cutoff. No submissions accepted after this date. |

---

## 🔗 Technical References

* **Astro:** [https://astro.build/](https://astro.build/)
* **Falcon:** [https://falcon.readthedocs.io/en/stable/](https://falcon.readthedocs.io/en/stable/)
* **pylxd:** [https://pylxd.readthedocs.io/en/latest/](https://pylxd.readthedocs.io/en/latest/)
* **TinyFlux:** [https://tinyflux.readthedocs.io/en/latest/index.html](https://tinyflux.readthedocs.io/en/latest/index.html)
* **SQLite3:** [https://docs.python.org/3/library/sqlite3.html](https://docs.python.org/3/library/sqlite3.html)
* **LXD:** [https://canonical.com/lxd](https://canonical.com/lxd)
* **Google OAuth 2.0:** [https://developers.google.com/identity/protocols/oauth2](https://developers.google.com/identity/protocols/oauth2)
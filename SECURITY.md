# Security Policy: AIStore ETL

## Reporting a Vulnerability

Do not open a public issue or pull request. Report vulnerabilities privately using one of these methods:

1. **NVIDIA Vulnerability Disclosure Program (preferred):** Submit the [official NVIDIA vulnerability report](https://www.nvidia.com/en-us/security/report-vulnerability/).
2. **GitHub private vulnerability reporting:** Open this repository's **Security** tab and select **Report a vulnerability**.
3. **Email:** Send vulnerability details to [psirt@nvidia.com](mailto:psirt@nvidia.com) and copy [aistore@nvidia.com](mailto:aistore@nvidia.com) for AIStore-specific coordination.

Include the affected version or branch, vulnerability type, reproduction steps, proof of concept if available, and expected impact. NVIDIA PSIRT will acknowledge, assess, and coordinate remediation and disclosure.

## Security Architecture and Context

This repository provides runtime images and example transformer containers for executing ETL workloads through AIStore on Kubernetes. ETL containers receive object data over HTTP or from AIStore storage and may run user-selected code, packages, and native processing tools.

**Repository Exposure Classification:** Public. Basis: published in a public NVIDIA GitHub repository.

**Service Exposure Classification:** External / Regulated (high confidence). Basis: externally distributed ETL runtime and transformer images.

### Threat Model

1. **Unauthorized code execution:** `runtime/python/bootstrap.py` deserializes an ETL class and can install requested Python or operating-system packages. Anyone allowed to initialize an ETL must be treated as authorized to execute code in its container.
2. **Malicious or oversized input:** Transformers parse archives, media, compressed data, images, and Parquet files. Crafted objects can exploit their parsers or exhaust CPU, memory, or storage.
3. **Container boundary escape or lateral access:** Transformers can contact AIStore through `AIS_TARGET_URL`; some example specifications support file paths or host-mounted data. A compromised container may reach resources available to its pod.
4. **Untrusted dependencies or images:** Runtime package installation, base images, transformer images, and third-party processing libraries form part of the execution trust chain.

### Critical Security Assumptions

- [AIStore AuthN](https://github.com/NVIDIA/aistore/blob/main/docs/authn.md) currently has one control for ETL creation: when AuthN is enabled, only administrators can create ETLs. There is no finer-grained ETL permission, so administrators with this access must be trusted to execute code in ETL containers.
- Kubernetes enforces pod, service-account, network, resource, and storage isolation appropriate to the deployment.
- AIStore authentication and TLS protect ETL initialization and data access; example transformers do not provide that boundary themselves.
- Operators review images and dependencies and treat transformed object data as untrusted input.

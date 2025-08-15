# AIStore ETL (AIS ETL)

This repository contains the components and examples used to run **Extract-Transform-Load (ETL)** operations on an [AIStore](https://github.com/NVIDIA/aistore) cluster.

For more information on how ETL works in AIStore, refer to the following documentation:
- [AIS ETL Docs](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md)
- [AIS ETL CLI Docs](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md)
- [AIS Python SDK Docs](https://github.com/NVIDIA/aistore/blob/main/docs/python_sdk.md) (includes ETL usage)

## Repository Structure

- [transformers](/transformers/README.md) — ready-to-use ETL transformers that can be deployed on an AIStore cluster
- [runtime](/runtime/README.md) — ETL runtime definitions for `init_class` function
- [deploy](/deploy/README.md) — utility tools and deployment configurations
- [examples](/examples) — example scripts for using and testing ETL features
- [docs](/docs/README.md) — documentation-related content

### Deploying AIStore for ETLs

To begin using ETLs in AIStore, you must first deploy an AIStore cluster on Kubernetes. Two reference deployments are provided, each serving a different purpose:

#### 1. AIStore development with local Kubernetes

- **Folder:** `deploy/dev/k8s`
- **Intended for:** Local AIStore development and functional testing of ETL transformers.
- **How to use:** Start a local Kubernetes cluster (for example, with **kind** or **minikube**) and follow the step-by-step instructions in the referenced folder to deploy a minimal AIS cluster configured for ETL development.
- **Documentation:** [README](https://github.com/NVIDIA/aistore/tree/main/deploy/dev/k8s)

#### 2. Production deployment with Kubernetes

- **Folder:** `deploy/prod/k8s`
- **Intended for:** Production-grade deployments of AIStore at scale.
- **How to use:** Use the provided Dockerfiles to build AIS images and follow the tooling in the companion repository to install, upgrade, and monitor the cluster.
- **Documentation:** [AIS/K8s Operator and Deployment Playbooks](https://github.com/NVIDIA/ais-k8s)

### Verify your deployment

After deploying the AIS cluster, you can confirm that it is reachable by running:

```bash
$ ais etl show

```

A blank list (`[]`) and the absence of error messages indicate that the cluster is healthy and ready for you to register ETL transformers.

> **Note**
> For the ETL functionality you must first initialize the transformation logic so that the cluster can execute it. The following folders and examples in this repository demonstrate how to build and register your own transformers.

> **⚠️ BETA NOTICE**  
> This software is currently in beta phase. Please be aware that:
> - Changes may not be backward compatible
> - AIS-ETL runs user code in containers within the AIStore environment, which may pose security risks if not properly controlled. Use with caution in production environments.
> - Not yet audited by NVIDIA’s security team

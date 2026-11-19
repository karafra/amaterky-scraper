# Amaterky Scraper Helm Repository

This repository hosts the Helm chart for [amaterky-scraper](https://github.com/karafra/amaterky-scraper), which periodically collects listings and serves the latest results with Nginx.

## Add the repository

```sh
helm repo add amaterky https://karafra.github.io/amaterky-scraper/
helm repo update
helm search repo amaterky
```

## Install

```sh
helm install amaterky amaterky/amaterky-scraper
```

The chart requires a Kubernetes storage class that supports **ReadWriteMany**. To select one, use:

```sh
helm install amaterky amaterky/amaterky-scraper \
  --set storage.storageClassName=<your-rwx-storage-class>
```

The scraper image defaults to the matching release on GitHub Container Registry. If the image is private, configure your cluster to authenticate to GHCR before installing.

## Configure and upgrade

Inspect the available settings and save them to a file:

```sh
helm show values amaterky/amaterky-scraper > values.yaml
```

Edit `values.yaml`, then upgrade:

```sh
helm repo update
helm upgrade --install amaterky amaterky/amaterky-scraper -f values.yaml
```

For deployment details, see the [deployment documentation](https://github.com/karafra/amaterky-scraper/blob/main/deployment/README.md).

## Uninstall

```sh
helm uninstall amaterky
```

Review the remaining persistent volume claim and its storage reclaim policy before deleting data.

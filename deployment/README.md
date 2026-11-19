# Deployment and releases

The Helm chart and Kustomize manifests deploy a scraper CronJob and a separate
Nginx server. Both use a shared ReadWriteMany volume; set the Helm
`storage.storageClassName` or adapt the Kustomize PVC for your cluster.
Nginx serves the most recently completed scrape at `/scraper.json`, metrics at
`/metrics`, and a health check at `/healthz`. For a local chart installation,
set `image.repository` and `image.tag` to an image accessible to your cluster.

## CI and release setup

Pushes and pull requests run the tests and render the deployment manifests.
The **Release** workflow is manually dispatched on `main` or a release branch.
It calls the reusable CI, release publication, and Helm Pages publication
workflows in sequence. The release workflow serializes runs across branches.
It uses stable tags matching `vMAJOR.MINOR.PATCH` to calculate versions:

- On `main`, it increments the minor version of the numerically highest stable
  tag, creates `release/MAJOR.MINOR.x`, and releases its `.0` version. With no
  stable tags, it starts at `v0.1.0`.
- On `release/MAJOR.MINOR.x`, it increments the highest patch tag in that
  series. The branch must already have a matching stable tag.

Each release builds `ghcr.io/<owner>/<repository>:vMAJOR.MINOR.PATCH`, publishes
an image provenance attestation, packages and attests the Helm chart, and
attaches it to a GitHub release. The packaged chart defaults to that image and
uses its `appVersion` as the tag. A `gh-pages` branch retains chart archives
and their Helm index, which is deployed through GitHub Pages.

Before running a release:

1. Enable GitHub Actions, GitHub Pages with source **GitHub Actions**, and
   artifact attestations for the repository. Pages and attestations must be
   available for the repository's visibility and plan.
2. Allow the workflow's `GITHUB_TOKEN` to create release branches, tags,
   releases, packages, attestations, and update `gh-pages`. Configure any
   branch/tag protection rules and the `github-pages` environment accordingly.
3. Ensure cluster nodes can pull the GHCR image. Packages may be private;
   configure package visibility or image pull credentials as appropriate.

After publication, add the Pages site URL shown in the deployment:

```sh
helm repo add amaterky <pages-site-url>
helm repo update
helm install amaterky amaterky/amaterky-scraper
```

Releases involve multiple services and are not atomic. If the Pages job fails
after publication, fix the cause and rerun the failed job in the same workflow
run; it reuses the chart artifact and updates the existing index. If a
`gh-pages` commit was already pushed, the job can deploy it without creating
another commit. For failures earlier in publication, inspect the image,
release branch, tag, and any draft release before retrying. In particular,
a created branch or tag prevents a fresh run from automatically choosing the
same version; clean up only confirmed incomplete artifacts or complete the
release manually. Do not remove published releases or tags without assessing
their consumers.

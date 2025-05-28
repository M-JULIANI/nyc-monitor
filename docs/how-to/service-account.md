# One time service account creation for CI/CD

(Martin you don't need to do this, just documenting for posterity.)

1. Create service account:
```
   gcloud iam service-accounts create atlas-ci-cd \
       --display-name="Atlas CI/CD Service Account"
```

2. Attach role: for cloud run deployments:
```
gcloud projects add-iam-policy-binding atlas-460522 \
    --member="serviceAccount:atlas-ci-cd@atlas-460522.iam.gserviceaccount.com" \
    --role="roles/run.admin"
```

3. Attach role: for container registry access:
```
gcloud projects add-iam-policy-binding atlas-460522 \
    --member="serviceAccount:atlas-ci-cd@atlas-460522.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

4. Download`key.json`:

```
gcloud iam service-accounts keys create key.json \
    --iam-account=atlas-ci-cd@atlas-460522.iam.gserviceaccount.com
```

# One time service account creation for CI/CD

(Martin you don't need to do this, just documenting for posterity.)

1. Create service account:
```
   gcloud iam service-accounts create atlas-ci-cd \
       --display-name="Atlas CI/CD Service Account"
```

2. Attach role: for cloud run deployments:
```
gcloud projects add-iam-policy-binding atlas-460522 \
    --member="serviceAccount:atlas-ci-cd@atlas-460522.iam.gserviceaccount.com" \
    --role="roles/run.admin"
```

3. Attach role: for container registry access:
```
gcloud projects add-iam-policy-binding atlas-460522 \
    --member="serviceAccount:atlas-ci-cd@atlas-460522.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

4. Attach role: for Vertex AI reasoning engines:
```
gcloud projects add-iam-policy-binding atlas-460522 \
    --member="serviceAccount:atlas-ci-cd@atlas-460522.iam.gserviceaccount.com" \
    --role="roles/aiplatform.admin"
```

6. Fix permissions, bind policy to role:

```
gcloud projects add-iam-policy-binding atlas-460522 --member="serviceAccount:atlas-ci-cd@atlas-460522.iam.gserviceaccount.com" --role="roles/aiplatform.admin"
```

7. Download`key.json`:

```
gcloud iam service-accounts keys create key.json \
    --iam-account=atlas-ci-cd@atlas-460522.iam.gserviceaccount.com
```

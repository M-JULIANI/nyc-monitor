# 🛠️ Atlas Project Setup Guide

## 1. Install Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (required for dev containers)
- [Visual Studio Code](https://code.visualstudio.com/)

---

## 2. Install the Dev Containers Extension

1. Open VS Code.
2. Go to the Extensions sidebar (`Ctrl+Shift+X`).
3. Search for **Dev Containers** and install the official extension:
   ![Dev Containers Extension](https://user-images.githubusercontent.com/674621/210176167-6e2e2e7b-2e2e-4e2e-8e2e-2e2e2e2e2e2e.png)

---

## 3. Clone the Repository

```sh
git clone https://github.com/M-JULIANI/atlas-bootstrapped.git
cd atlas-bootstrapped
```

---

## 4. Copy contents of .env file into local .env file at root of repo from [GDrive](https://drive.google.com/drive/folders/11FMQG1ofqvze5Mu7CL_daLPegDAO2GGk?usp=sharing). Remember this file is not commited to version control and is part of .gitignore already/

---

## 5. Google Cloud Authentication

1. **Authenticate with Google Cloud:**
   - Open a terminal in VS Code (inside the dev container).
   - Run:
     ```sh
     gcloud auth login
     gcloud auth application-default login
     ```
   - Follow the prompts in your browser.

2. **Set your project:**
   ```sh
   gcloud config set project atlas-460522
   ```

---

## 6. Open in Dev Container

1. In VS Code, open the project folder (`File > Open Folder...`).
2. Press `F1` and select:
   **Dev Containers: Reopen in Container**
3. VS Code will build and launch the dev container. This may take several minutes the first time.

---


## 7. Install Project Dependencies

```sh
make install
```
- Installs both backend (Python/Poetry) and frontend (Node/NPM) dependencies.

---

# PipeOps CLI - User Guide 🚀

**Pipeline automation made simple for DevOps teams**

PipeOps CLI automates the creation and monitoring of GitLab CI/CD pipelines with built-in failure recovery, especially for OpenShift deployments.

---

## 🎯 Quick Start

### Prerequisites
- Python 3.7+
- GitLab access token with API permissions
- OpenShift CLI (optional, for deploy failure recovery)

### Installation
```bash
pip install -e .
```

### Basic Usage
```bash
pipeops-cli init -p https://gitlab.com/your-group/project -t your-gitlab-token
```

---

## 📋 Complete Usage Guide

### 1. Initialize Pipeline (Basic)
```bash
# Auto-detect project type and create pipeline
pipeops-cli init \
  --project-url https://gitlab.com/group/project \
  --token glpat-xxxxxxxxxxxxx
```

**What happens:**
1. ✅ Analyzes your project (Python/Node.js, service/package)
2. ✅ Shows you the detected configuration
3. ✅ Checks for missing environment variables
4. ✅ Creates pipeline files from templates
5. ✅ Creates merge request
6. ✅ **Monitors pipeline automatically** with failure analysis

### 2. Advanced Options

#### Skip Monitoring
```bash
pipeops-cli init -p URL -t TOKEN --no-monitor
```

#### Use Basic Monitoring (faster)
```bash
pipeops-cli init -p URL -t TOKEN --basic-monitor  
```

#### Auto-Confirm Settings
```bash
pipeops-cli init -p URL -t TOKEN --auto-confirm
```

#### Dry Run (Preview Only)
```bash
pipeops-cli init -p URL -t TOKEN --dry-run
```

#### Custom Configuration
```bash
pipeops-cli init -p URL -t TOKEN --config my-config.yml
```

---

## 🎭 Usage Scenarios

### Scenario 1: New Python Service
**Situation:** You have a new Python Flask API that needs CI/CD

```bash
pipeops-cli init -p https://gitlab.com/company/my-api -t $GITLAB_TOKEN
```

**Expected Flow:**
```
🔍 Detects: Python service (finds app.py, requirements.txt, Dockerfile)
📋 Creates: .gitlab-ci.yml, OpenShift deployment configs
🔄 Pipeline: build → test → deploy to dev/staging/prod
🚨 Monitor: Automatic failure detection and recovery
```

### Scenario 2: Python Package for PyPI
**Situation:** You have a Python library for internal distribution

```bash
pipeops-cli init -p https://gitlab.com/company/my-lib -t $GITLAB_TOKEN
```

**Expected Flow:**
```
🔍 Detects: Python package (finds setup.py, pyproject.toml)
📋 Creates: .gitlab-ci.yml with PyPI publishing
🔄 Pipeline: build → test → publish to PyPI
📦 Result: Automated package releases
```

### Scenario 3: Node.js Service
**Situation:** You have a Node.js Express API

```bash
pipeops-cli init -p https://gitlab.com/company/node-api -t $GITLAB_TOKEN
```

**Expected Flow:**
```
🔍 Detects: Node.js service (finds package.json, server.js, Dockerfile)
📋 Creates: .gitlab-ci.yml, OpenShift deployment configs  
🔄 Pipeline: build → test → deploy
🚚 Deploy: Automated container deployment
```

### Scenario 4: Existing Project (Update Pipeline)
**Situation:** Project already has CI/CD but needs updates

```bash
pipeops-cli init -p https://gitlab.com/company/existing -t $GITLAB_TOKEN
```

**Expected Flow:**
```
⚠️  Detects: Existing .gitlab-ci.yml
🔄 Updates: Pipeline configuration with latest templates
📝 MR: Creates merge request with "Update pipeline" title
🔍 Monitor: Tracks the updated pipeline
```

### Scenario 5: Deploy Failure Recovery
**Situation:** Your deploy job fails due to resource conflicts

**Automatic Recovery:**
```
💥 Deploy failed detected
🔧 ENHANCED DEPLOY FAILURE RECOVERY
🎯 Target resources: my-service-service, my-service-route
🏢 OpenShift cluster: https://api.openshift.company.com

🔧 Recovery plan:
   1. Clean up OpenShift resources
   2. Wait for cleanup to complete
   3. Retry failed deploy jobs

🤔 Proceed with enhanced recovery? [Y/n]: Y
```

**What happens automatically:**
1. 🗑️ Deletes conflicting OpenShift services and routes
2. ⏳ Waits 10 seconds for cleanup
3. 🔄 Retries all failed deploy jobs
4. ✅ Reports success/failure

---

## ⚙️ Configuration

### Environment Variables Setup

The tool will prompt you for missing variables, but you can set them in advance:

#### For Python Services (OpenShift):
```bash
# In GitLab Project/Group Settings → CI/CD → Variables
CI_REGISTRY_URL=registry.gitlab.com
OPENSHIFT_SERVER=https://api.openshift.company.com:6443
OPENSHIFT_TOKEN=your-openshift-token
```

#### For Python Packages (PyPI):
```bash
PYPI_TOKEN=pypi-xxxxxxxxxxxxx
TWINE_USERNAME=__token__
TWINE_PASSWORD=pypi-xxxxxxxxxxxxx  # same as PYPI_TOKEN
```

#### For Node.js Services:
```bash
CI_REGISTRY_URL=registry.gitlab.com
DOCKER_REGISTRY=docker-registry.company.com
NPM_TOKEN=npm-token-if-needed
```

### Custom Pipeline Templates

Create your own `pipeline_definitions.yml`:

```yaml
pipelines:
  my_custom_service:
    template_path: Templates/My-Custom-Service
    description: "Custom service template"
    required_env:
      - CUSTOM_VAR1
      - CUSTOM_VAR2
    files_to_create:
      - .gitlab-ci.yml
      - custom-config.yml
    supported_languages:
      - python
    supported_types:
      - service
```

---

## 🔍 Monitoring & Failure Analysis

### Enhanced Monitoring (Default)

**Features:**
- 📊 **Stage-by-stage breakdown** - See exactly which stage failed
- 🚨 **Critical failure detection** - Identifies deploy vs build/test failures  
- 🤖 **Automated recovery** - OpenShift cleanup and job retry
- 📈 **Detailed analysis** - Failure severity and suggested actions

**Sample Output:**
```
===========================================================
           DETAILED FAILURE ANALYSIS  
===========================================================
🚨 Severity Level: CRITICAL-DEPLOY
📊 Overview: 2/8 jobs failed
🎯 Failed Stages: deploy

💥 Critical Failures:
   🚚 deploy-dev (deploy stage)
   🚚 deploy-staging (deploy stage)

📈 Stage Breakdown:
   ✅ build: All 2 jobs passed
   ✅ test: All 3 jobs passed  
   ❌ deploy: 2 failed, 0 passed

🔧 Suggested Actions:
   🤖 Automated fixes available:
      • Clean up OpenShift resources and retry deploy (priority: high)
      • Retry failed deploy job after cleanup (priority: high)
===========================================================
```

### Basic Monitoring

**Use when:**
- You want faster monitoring
- Enhanced features aren't needed
- Simpler output is preferred

```bash
pipeops-cli init -p URL -t TOKEN --basic-monitor
```

---

## 🚨 Troubleshooting

### Common Issues

#### 1. "Token appears to be too short"
**Solution:** Make sure you're using a GitLab Personal Access Token (starts with `glpat-`)

#### 2. "Pipeline type 'python_service' not found"
**Solution:** Check your configuration file exists and contains the pipeline definition

#### 3. "Missing OpenShift credentials"
**Solution:** Set `OPENSHIFT_SERVER` and `OPENSHIFT_TOKEN` in GitLab CI/CD variables

#### 4. "No pipeline found"
**Solution:** Pipeline might take a few seconds to start. Check GitLab manually if it persists.

#### 5. "Branch 'feature/pipeops' already exists"
**Solution:** The tool will offer to delete and recreate the branch. Choose option 1.

### Getting Help

1. **Check logs** - All operations are logged with detailed information
2. **Enable file logging:**
   ```python
   from Utiles.logger import configure_logging
   configure_logging(enable_file_logging=True)
   ```
3. **Validate configuration:**
   ```bash
   pipeops-cli validate --config your-config.yml
   ```
4. **List available templates:**
   ```bash
   pipeops-cli list --config your-config.yml
   ```

---

## 🔧 Commands Reference

### `init` - Initialize Pipeline
```bash
pipeops-cli init [OPTIONS]

Options:
  -p, --project-url TEXT    GitLab project URL [required]
  -t, --token TEXT          GitLab API token [required]  
  -c, --config PATH         Configuration file [default: Config/pipeline_definitions.yml]
  --dry-run                 Preview changes without applying
  --auto-confirm           Skip confirmation prompts
  --no-monitor             Disable pipeline monitoring
  --basic-monitor          Use basic monitoring instead of enhanced
```

### `validate` - Validate Configuration
```bash
pipeops-cli validate [OPTIONS]

Options:
  -c, --config PATH         Configuration file to validate
```

### `list` - List Templates  
```bash
pipeops-cli list [OPTIONS]

Options:
  -c, --config PATH         Configuration file
```

### `--version` - Show Version
```bash
pipeops-cli --version
```

---

## 🎉 Success Indicators

### Pipeline Created Successfully:
```
🎉 SUCCESS!
==============================
🔀 develop → feature/pipeops → develop
🔗 MR: https://gitlab.com/group/project/-/merge_requests/123
✅ Pipeline setup complete!
💡 Merge the MR to activate
==============================
```

### Pipeline Monitoring Active:
```
🔍 Starting enhanced pipeline monitoring...
⏳ Waiting for pipeline to start...
📊 Pipeline 1936938457: running
🏃 Monitoring with enhanced analysis...
🎉 Pipeline succeeded! (45s)
```

### Deploy Recovery Successful:
```
🔧 ENHANCED DEPLOY FAILURE RECOVERY
✅ Cleanup successful
✅ Deploy job retried
✅ Enhanced recovery completed successfully
🔍 Monitor pipeline progress in GitLab
```

---

## 💡 Best Practices

1. **Set environment variables at group level** for multiple projects
2. **Use --dry-run first** to preview changes
3. **Keep your GitLab token secure** - use environment variables
4. **Monitor the first few pipeline runs** to ensure everything works
5. **Customize templates** for your organization's specific needs

---

**Need help?** Check the logs, use `--dry-run` to preview, or consult your DevOps team! 🤝
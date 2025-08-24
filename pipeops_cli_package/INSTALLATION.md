# PipeOps CLI - Installation Guide 📦

**Simple installation from company Artifactory**

---

## 🚀 Quick Installation

### Prerequisites
- Python 3.7+
- Access to company Artifactory
- GitLab API token

### Install from Artifactory

```bash
# Install PipeOps CLI from company repository
pip install -i https://artifactory.company.internal/artifactory/api/pypi/pypi/simple pipeops-cli

# Verify installation
pipeops-cli --version
```

That's it! Ready to use.

---

## 📋 Basic Usage

### 1. Initialize Pipeline
```bash
# Basic command
pipeops-cli init -p https://gitlab.company.internal/group/project -t your-gitlab-token

# With auto-confirmation (no prompts)
pipeops-cli init -p PROJECT_URL -t TOKEN --auto-confirm

# Preview only (no changes)
pipeops-cli init -p PROJECT_URL -t TOKEN --dry-run
```

### 2. Common Options
```bash
# Skip pipeline monitoring
pipeops-cli init -p PROJECT_URL -t TOKEN --no-monitor

# Use basic monitoring instead of enhanced
pipeops-cli init -p PROJECT_URL -t TOKEN --basic-monitor

# Custom configuration file
pipeops-cli init -p PROJECT_URL -t TOKEN --config my-config.yml
```

---

## ⚙️ Configuration

### Environment Variables

Set these in your environment or GitLab CI/CD variables:

#### For Python Services:
```bash
export GITLAB_TOKEN=glpat-your-token
export CI_REGISTRY_URL=registry.company.internal
export OPENSHIFT_SERVER=https://openshift.company.internal:6443
export OPENSHIFT_TOKEN=your-openshift-token
```

#### For Python Packages:
```bash
export GITLAB_TOKEN=glpat-your-token
export PYPI_TOKEN=your-pypi-token
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=your-pypi-token
```

### GitLab Token Setup

1. Go to GitLab → User Settings → Access Tokens
2. Create token with scopes: `api`, `read_repository`, `write_repository`
3. Copy token (starts with `glpat-`)

### OpenShift Token Setup

```bash
# Login to OpenShift
oc login https://openshift.company.internal:6443

# Get token
oc whoami -t
```

---

## 🎯 Usage Examples

### Python Flask Service
```bash
pipeops-cli init \
  --project-url https://gitlab.company.internal/apis/user-service \
  --token $GITLAB_TOKEN
```
**Result**: Creates CI/CD pipeline with build → test → deploy to OpenShift

### Python Package Library
```bash
pipeops-cli init \
  --project-url https://gitlab.company.internal/libs/common-utils \
  --token $GITLAB_TOKEN
```
**Result**: Creates pipeline with build → test → publish to PyPI

### Node.js Service
```bash
pipeops-cli init \
  --project-url https://gitlab.company.internal/apis/notification-service \
  --token $GITLAB_TOKEN
```
**Result**: Creates pipeline with build → test → deploy to OpenShift

---

## 🔧 Available Commands

```bash
# Initialize pipeline
pipeops-cli init -p PROJECT_URL -t TOKEN [OPTIONS]

# Validate configuration
pipeops-cli validate [--config CONFIG_FILE]

# List available templates
pipeops-cli list [--config CONFIG_FILE]

# Monitor specific pipeline
pipeops-cli monitor -p PROJECT_URL -t TOKEN --pipeline-id PIPELINE_ID

# Show version
pipeops-cli --version

# Show help
pipeops-cli --help
```

---

## 🚨 Troubleshooting

### Common Issues

#### 1. Installation Issues
```bash
# Problem: Package not found
# Solution: Check Artifactory URL
pip install -i https://artifactory.company.internal/artifactory/api/pypi/pypi/simple pipeops-cli

# Problem: SSL certificate issues
# Solution: Use trusted host
pip install --trusted-host artifactory.company.internal -i https://... pipeops-cli
```

#### 2. GitLab Token Issues
```bash
# Test token validity
curl -H "PRIVATE-TOKEN: your-token" \
     "https://gitlab.company.internal/api/v4/user"

# Should return your user info
```

#### 3. Pipeline Not Found
```bash
# Check if pipeline was created
# Go to GitLab project → CI/CD → Pipelines
# Or check merge requests for new pipeline
```

#### 4. OpenShift Deploy Failures
```bash
# The tool will automatically detect and offer cleanup
# Or manual cleanup:
oc delete service your-service-name
oc delete route your-route-name
```

---

## 💡 Best Practices

1. **Use environment variables** instead of passing tokens in commands
2. **Test with --dry-run** before making changes
3. **Set environment variables in GitLab** for team projects
4. **Use --auto-confirm** in CI/CD pipelines
5. **Monitor the first pipeline run** to ensure everything works

---

## 🆘 Need Help?

1. **Check the logs** - All operations are logged
2. **Use --dry-run** to preview changes
3. **Validate configuration**: `pipeops-cli validate`
4. **Contact DevOps team** for support

---

## 🔄 Updates

To update to a newer version:

```bash
# Update PipeOps CLI
pip install --upgrade -i https://artifactory.company.internal/artifactory/api/pypi/pypi/simple pipeops-cli

# Check new version
pipeops-cli --version
```

The DevOps team will announce updates via internal channels.
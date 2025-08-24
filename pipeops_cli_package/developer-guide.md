# PipeOps CLI - Developer Guide 🛠️

**Internal documentation for DevOps developers working on PipeOps CLI**

This guide is for developers who need to understand, maintain, or extend the PipeOps CLI codebase.

---

## 📁 Project Structure Analysis

### Current Architecture Overview
```
Pipeops-cli/
├── cli.py                    # ⚠️  OVERLOADED - needs refactoring
├── Config/
│   └── pipeline_definitions.yml
├── Core/
│   ├── ConfigLoader.py       # ✅ Single responsibility - YAML loading
│   ├── EnvChecker.py        # ✅ Single responsibility - env vars
│   ├── GitLabHandler.py     # ✅ Single responsibility - GitLab API
│   ├── PipelineGenerator.py # ✅ Single responsibility - file generation
│   ├── ProjectAnalyzer.py   # ✅ Single responsibility - project analysis
│   ├── PipelineMonitor.py   # ⚠️  Missing enhanced monitoring logic
│   ├── EnhancedPipelineMonitor.py # ✅ Enhanced monitoring
│   ├── OpenShiftCleaner.py  # ✅ Single responsibility - OpenShift ops
│   └── UserInteractor.py    # ⚠️  Missing some UI logic
├── Templates/               # ✅ Well organized
├── Utiles/
│   └── logger.py           # ✅ Single responsibility
└── README.md
```

### 🚨 Architecture Issues Identified

#### 1. **cli.py is OVERLOADED** (500+ lines, multiple responsibilities):
```python
# SHOULD BE IN cli.py:
- Command definitions (@click commands)
- Basic flow orchestration
- Error handling at top level

# SHOULD NOT BE IN cli.py:
- monitor_merge_request_pipeline_enhanced() → Core/PipelineMonitor.py
- monitor_merge_request_pipeline_basic() → Core/PipelineMonitor.py  
- _display_enhanced_failure_details() → Core/UserInteractor.py
- _log_detailed_failure_analysis() → Core/AnalysisLogger.py (new)
- handle_deploy_failure_enhanced() → Core/DeploymentManager.py (new)
- handle_deploy_failure_basic() → Core/DeploymentManager.py (new)
```

#### 2. **Missing Classes:**
```python
# NEEDED:
Core/DeploymentManager.py    # Deploy failure handling
Core/AnalysisLogger.py       # Structured failure logging  
Core/MonitoringOrchestrator.py # Monitoring flow control
```

#### 3. **Inconsistent Responsibilities:**
- `UserInteractor` handles some UI but not failure displays
- `PipelineMonitor` doesn't contain all monitoring logic
- Logging scattered across files

---

## 🏗️ Recommended Refactoring Plan

### Phase 1: Extract Classes from CLI

#### A. Create `Core/DeploymentManager.py`
```python
class DeploymentManager:
    """Handles deploy failure detection and recovery"""
    
    def __init__(self, gitlab_handler, env_checker):
        self.gitlab = gitlab_handler
        self.env_checker = env_checker
    
    def handle_deploy_failure_basic(self, pipeline_id: int) -> bool:
        # Move from cli.py
    
    def handle_deploy_failure_enhanced(self, pipeline_id: int, failure_analysis: dict) -> bool:
        # Move from cli.py
    
    def _setup_openshift_recovery(self, failure_analysis: dict) -> dict:
        # Extract setup logic
```

#### B. Create `Core/AnalysisLogger.py`
```python
class AnalysisLogger:
    """Structured logging for pipeline failure analysis"""
    
    def log_detailed_failure_analysis(self, pipeline_id: int, failure_analysis: dict, recovery_actions: list):
        # Move from cli.py
    
    def log_monitoring_event(self, event_type: str, pipeline_id: int, **kwargs):
        # Structured event logging
    
    def log_recovery_action(self, action_type: str, pipeline_id: int, success: bool, **kwargs):
        # Recovery action logging
```

#### C. Create `Core/MonitoringOrchestrator.py`
```python
class MonitoringOrchestrator:
    """Orchestrates pipeline monitoring workflow"""
    
    def __init__(self, gitlab_handler, env_checker, deployment_manager):
        self.gitlab = gitlab_handler
        self.env_checker = env_checker
        self.deployment_manager = deployment_manager
    
    def monitor_merge_request_pipeline(self, mr_data: dict, use_enhanced: bool = True):
        # Move monitoring logic from cli.py
        
    def _handle_pipeline_failure(self, pipeline_id: int, failure_analysis: dict, enhanced: bool):
        # Centralized failure handling
```

#### D. Extend `Core/UserInteractor.py`
```python
class UserInteractor:
    # Add missing UI methods:
    
    def display_enhanced_failure_details(self, failure_analysis: dict, recovery_actions: list):
        # Move from cli.py
        
    def display_basic_failure_details(self, failed_jobs: list):  
        # Move from cli.py
        
    def confirm_deploy_recovery(self, failure_context: dict) -> bool:
        # Enhanced recovery confirmation
```

### Phase 2: Clean CLI
```python
# cli.py SHOULD ONLY CONTAIN:

@cli.command('init')
def init(project_url: str, token: str, config: str, dry_run: bool, 
         auto_confirm: bool, no_monitor: bool, basic_monitor: bool):
    """Main init command - orchestration only"""
    
    try:
        # Step 1-5: Configuration, analysis, generation (keep)
        
        # Step 6: Monitoring (delegate)
        if monitor_pipeline and mr_url:
            orchestrator = MonitoringOrchestrator(gitlab_handler, env_checker, deployment_manager)
            orchestrator.monitor_merge_request_pipeline(mr_data, use_enhanced=use_enhanced)
            
    except Exception as e:
        # Error handling only
```

---

## 🔧 How to Add New Functionality

### Adding a New Pipeline Type

#### 1. Update Configuration
```yaml
# Config/pipeline_definitions.yml
pipelines:
  golang_service:
    template_path: Templates/Golang-service
    description: "Go service with Docker deployment"
    required_env:
      - CI_REGISTRY_URL
      - DOCKER_REGISTRY
    files_to_create:
      - .gitlab-ci.yml
      - Dockerfile
      - k8s-deployment.yaml
    supported_languages:
      - go
      - golang
    supported_types:
      - service
```

#### 2. Create Template Directory
```bash
mkdir -p Templates/Golang-service
# Add template files with {{variable}} placeholders
```

#### 3. Update ProjectAnalyzer (if needed)
```python
# Core/ProjectAnalyzer.py
def _detect_language(self, files):
    # Add Go detection
    go_indicators = ['go.mod', 'go.sum', 'main.go']
    
    go_count = 0
    for indicator in go_indicators:
        if indicator in files_lower:
            go_count += 1
    
    if go_count > 0:
        return 'go'
```

#### 4. Test
```bash
pipeops-cli init -p https://gitlab.com/test/go-project -t $TOKEN
```

### Adding New Monitoring Features

#### 1. Extend EnhancedPipelineMonitor
```python
# Core/EnhancedPipelineMonitor.py
class EnhancedPipelineMonitor:
    
    def monitor_with_notifications(self, pipeline_id: int, notification_config: dict):
        """Monitor with Slack/Teams notifications"""
        
    def analyze_performance_trends(self, pipeline_id: int) -> dict:
        """Analyze pipeline performance over time"""
        
    def detect_flaky_tests(self, pipeline_id: int) -> list:
        """Detect tests that fail intermittently"""
```

#### 2. Update MonitoringOrchestrator
```python
# Core/MonitoringOrchestrator.py  
def monitor_merge_request_pipeline(self, mr_data: dict, use_enhanced: bool = True, **options):
    if options.get('enable_notifications'):
        # Use notification monitoring
    if options.get('analyze_trends'):  
        # Add trend analysis
```

### Adding New Recovery Actions

#### 1. Extend DeploymentManager
```python
# Core/DeploymentManager.py
class DeploymentManager:
    
    def handle_database_migration_failure(self, pipeline_id: int) -> bool:
        """Handle DB migration failures"""
        
    def handle_security_scan_failure(self, pipeline_id: int) -> bool:
        """Handle security scan failures"""
        
    def rollback_deployment(self, pipeline_id: int, target_version: str) -> bool:
        """Rollback to previous version"""
```

---

## 🧪 Testing Strategy

### Current Testing Gaps
- [ ] No unit tests for CLI logic
- [ ] No integration tests for GitLab API interactions
- [ ] No mocking for external dependencies
- [ ] No test coverage reporting

### Recommended Testing Structure
```
tests/
├── unit/
│   ├── test_config_loader.py
│   ├── test_project_analyzer.py
│   ├── test_pipeline_generator.py
│   ├── test_enhanced_monitor.py
│   └── test_deployment_manager.py
├── integration/
│   ├── test_gitlab_api.py
│   ├── test_openshift_integration.py
│   └── test_end_to_end_flow.py
├── fixtures/
│   ├── sample_projects/
│   ├── mock_responses/
│   └── test_configs/
└── conftest.py
```

### Test Examples
```python
# tests/unit/test_deployment_manager.py
import pytest
from unittest.mock import Mock, patch
from Core.DeploymentManager import DeploymentManager

class TestDeploymentManager:
    
    def setup_method(self):
        self.gitlab_mock = Mock()
        self.env_checker_mock = Mock()
        self.manager = DeploymentManager(self.gitlab_mock, self.env_checker_mock)
    
    @patch('Core.DeploymentManager.cleanup_openshift_resources')
    def test_handle_deploy_failure_basic_success(self, cleanup_mock):
        # Arrange
        cleanup_mock.return_value = True
        self.gitlab_mock.get_pipeline_jobs.return_value = [
            {'name': 'deploy', 'status': 'failed', 'id': 123}
        ]
        self.gitlab_mock.retry_job.return_value = True
        
        # Act
        result = self.manager.handle_deploy_failure_basic(pipeline_id=456)
        
        # Assert
        assert result is True
        cleanup_mock.assert_called_once()
        self.gitlab_mock.retry_job.assert_called_once_with(123)
```

---

## 📊 Code Quality Standards

### Current Issues to Address

#### 1. **Cyclomatic Complexity**
```python
# BEFORE (cli.py - monitor_merge_request_pipeline_enhanced)
# Complexity: ~15 (too high)

def monitor_merge_request_pipeline_enhanced(...):  # 80+ lines
    if current_status in ['pending', 'running']:
        if result['status'] == 'failed':
            if deploy_failures and HAS_OPENSHIFT:
                # Nested logic continues...

# AFTER (MonitoringOrchestrator)
# Complexity: ~5 per method

def monitor_pipeline(self, ...):
    status = self._get_pipeline_status(...)
    if status == 'failed':
        self._handle_failure(...)
        
def _handle_failure(self, ...):
    failure_type = self._classify_failure(...)
    self._execute_recovery(failure_type, ...)
```

#### 2. **Method Length**
```python
# RULE: Methods should be < 20 lines
# CURRENT: Many methods 50+ lines
# SOLUTION: Extract helper methods
```

#### 3. **DRY Violations**
```python
# REPEATED CODE:
logger.error(f"Pipeline {pipeline_id} failed with {len(failed_jobs)} failed jobs:")
for job in failed_jobs:
    logger.error(f"  Failed job: {job_name} (Stage: {job_stage}, ID: {job_id})")

# EXTRACT TO:
def log_failed_jobs(self, pipeline_id: int, failed_jobs: list):
    # Centralized logging
```

### Code Style Guidelines

#### 1. **Class Design**
```python
class PipelineMonitor:
    """
    Single Responsibility: Monitor GitLab pipelines
    
    Dependencies:
    - GitLabHandler: API interactions
    - Logger: Structured logging
    
    Public Interface:
    - monitor_pipeline(id) -> dict
    - analyze_failure(id) -> dict
    
    Private Methods:  
    - _check_status(), _wait_for_completion()
    """
    
    def __init__(self, gitlab_handler: GitLabHandler):
        self.gitlab = gitlab_handler
        
    def monitor_pipeline(self, pipeline_id: int) -> dict:
        """Public interface - simple and clear"""
        
    def _check_status(self, pipeline_id: int) -> str:
        """Private helper - focused task"""
```

#### 2. **Error Handling**
```python
# CONSISTENT ERROR HANDLING:
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Specific operation failed: {e}")
    raise PipeOpsException(f"User-friendly message") from e
except Exception as e:
    logger.error(f"Unexpected error in operation: {e}")
    raise PipeOpsException("Something went wrong") from e
```

#### 3. **Logging Standards**
```python
# STRUCTURED LOGGING:
logger.info(f"Pipeline monitoring started", extra={
    'pipeline_id': pipeline_id,
    'branch': source_branch,
    'monitoring_type': 'enhanced'
})

# CONSISTENT LOG LEVELS:
# DEBUG: Detailed flow information
# INFO: Important events (start/complete)
# WARNING: Recoverable issues
# ERROR: Failures requiring attention
```

---

## 🔍 Common Debugging Scenarios

### 1. **Pipeline Not Found Error**
```python
# DEBUG CHECKLIST:
1. Check branch name in logs: logger.info(f"Looking for pipeline on branch: {branch}")
2. Verify GitLab API response: logger.debug(f"API response: {response.json()}")
3. Check timing: Pipeline might not be created yet
4. Validate permissions: Token might not have access

# DEBUGGING CODE:
def debug_pipeline_search(self, branch: str):
    pipelines = self.gitlab.get_pipelines(ref=branch)
    logger.debug(f"Found {len(pipelines)} pipelines for branch {branch}")
    for p in pipelines:
        logger.debug(f"Pipeline {p['id']}: status={p['status']}, ref={p['ref']}")
```

### 2. **Environment Variable Issues**
```python
# DEBUG CHECKLIST:
1. Check group vs project variables: logger.debug(f"Group vars: {group_vars}")
2. Verify variable names: Case sensitivity, typos
3. Check variable visibility: Protected/masked settings
4. Validate inheritance: Group → Subgroup → Project

# DEBUGGING CODE:  
def debug_env_vars(self):
    all_vars = {}
    logger.debug(f"Project path: {self.project_path}")
    
    # Check group hierarchy
    for group in self._get_group_hierarchy():
        vars = self._get_group_variables_debug(group)
        logger.debug(f"Group {group} vars: {list(vars.keys())}")
```

### 3. **OpenShift Connection Issues**
```python
# DEBUG CHECKLIST:
1. Check oc CLI availability: subprocess.run(['oc', 'version'])
2. Test server connectivity: ping/curl to OPENSHIFT_SERVER
3. Validate token: oc whoami --show-token
4. Check permissions: oc auth can-i create services

# DEBUGGING CODE:
def debug_openshift_connectivity(self, server: str, token: str):
    logger.debug(f"Testing connection to {server}")
    try:
        # Test login without doing actual work
        test_cmd = ['oc', 'whoami', '--server', server, '--token', token]
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        logger.debug(f"oc whoami result: {result.stdout}")
    except Exception as e:
        logger.error(f"OpenShift connectivity test failed: {e}")
```

---

## 🚀 Performance Considerations

### Current Performance Issues

1. **Excessive API Calls**: `get_file_list()` called multiple times
2. **No Caching**: Project info fetched repeatedly  
3. **No Parallel Operations**: Sequential job analysis
4. **Long Polling**: 30-second intervals for monitoring

### Optimization Strategies

#### 1. **Add Caching Layer**
```python
from functools import lru_cache
from typing import Optional
import time

class CachedGitLabHandler:
    def __init__(self, gitlab_handler: GitLabHandler):
        self.gitlab = gitlab_handler
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    @lru_cache(maxsize=128)
    def get_project_info_cached(self, project_id: str) -> dict:
        return self.gitlab.get_project()
    
    def get_file_list_cached(self, ref: str = None) -> list:
        cache_key = f"files_{ref or 'default'}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
        
        files = self.gitlab.get_file_list(ref)
        self._cache[cache_key] = {
            'data': files,
            'timestamp': time.time()
        }
        return files
```

#### 2. **Batch API Operations**
```python
def analyze_multiple_jobs(self, job_ids: list) -> dict:
    """Analyze multiple jobs in parallel"""
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(self.gitlab.get_job_details, job_id): job_id 
            for job_id in job_ids
        }
        
        results = {}
        for future in concurrent.futures.as_completed(futures):
            job_id = futures[future]
            try:
                results[job_id] = future.result()
            except Exception as e:
                logger.error(f"Failed to get job {job_id}: {e}")
        
        return results
```

#### 3. **Adaptive Polling**
```python
def monitor_with_adaptive_polling(self, pipeline_id: int):
    """Reduce polling frequency as pipeline progresses"""
    intervals = [5, 10, 15, 30, 60]  # Increase interval over time
    check_count = 0
    
    while True:
        status = self._check_pipeline_status(pipeline_id)
        if status in ('success', 'failed', 'canceled'):
            break
            
        # Use adaptive interval
        interval_index = min(check_count // 3, len(intervals) - 1)
        sleep_time = intervals[interval_index]
        
        logger.debug(f"Sleeping {sleep_time}s (check #{check_count})")
        time.sleep(sleep_time)
        check_count += 1
```

---

## 🔐 Security Considerations

### Current Security Issues

1. **Token Logging**: GitLab tokens might appear in logs
2. **Sensitive Variable Display**: Environment variables shown in output
3. **No Token Validation**: Tokens not validated before use
4. **Temporary Files**: No cleanup of temporary configurations

### Security Improvements

#### 1. **Token Sanitization**
```python
def sanitize_for_logging(self, data: any) -> any:
    """Remove sensitive data from logs"""
    if isinstance(data, str):
        # Sanitize GitLab tokens
        data = re.sub(r'glpat-[a-zA-Z0-9_-]+', 'glpat-***', data)
        # Sanitize other tokens
        data = re.sub(r'token[=:]\s*[a-zA-Z0-9_-]+', 'token=***', data, re.IGNORECASE)
    elif isinstance(data, dict):
        return {k: self.sanitize_for_logging(v) for k, v in data.items()}
    return data
```

#### 2. **Environment Variable Protection**
```python
def display_env_var_safely(self, var_name: str, var_value: str) -> str:
    """Display environment variables safely"""
    sensitive_patterns = ['token', 'password', 'secret', 'key']
    
    if any(pattern in var_name.lower() for pattern in sensitive_patterns):
        if len(var_value) > 8:
            return f"{var_value[:4]}***{var_value[-4:]}"
        else:
            return "***"
    return var_value
```

---

## 📈 Monitoring & Observability

### Add Structured Metrics
```python
from dataclasses import dataclass
from typing import Dict, List
import time

@dataclass
class PipelineMetrics:
    pipeline_id: int
    duration: float
    stages_completed: int
    stages_failed: int
    retry_count: int
    recovery_attempted: bool
    recovery_successful: bool

class MetricsCollector:
    def __init__(self):
        self.metrics: List[PipelineMetrics] = []
    
    def record_pipeline_completion(self, metrics: PipelineMetrics):
        self.metrics.append(metrics)
        
    def get_success_rate(self, days: int = 7) -> float:
        recent = self._get_recent_metrics(days)
        if not recent:
            return 0.0
        successful = len([m for m in recent if m.stages_failed == 0])
        return successful / len(recent)
    
    def get_average_duration(self, pipeline_type: str = None) -> float:
        # Calculate average pipeline duration
```

---

## 🎯 Future Development Roadmap

### Short Term (Next Sprint)
1. ✅ **Refactor CLI** - Extract classes as outlined above
2. ✅ **Add comprehensive tests** - Unit + integration
3. ✅ **Implement caching** - Reduce API calls
4. ✅ **Security improvements** - Token sanitization

### Medium Term (Next Quarter)  
1. **Multi-platform support** - Add Kubernetes, AWS ECS
2. **Advanced monitoring** - Metrics, alerting, trends
3. **Template marketplace** - Shareable pipeline templates
4. **Web UI** - Optional web interface for configuration

### Long Term (6+ months)
1. **ML-powered failure prediction** - Predict likely failures
2. **Auto-remediation** - Fix common issues automatically  
3. **Enterprise features** - RBAC, audit logs, compliance
4. **Integration ecosystem** - Slack, JIRA, ServiceNow

---

**Ready to contribute? Start with the refactoring plan above, write tests first, and maintain the single-responsibility principle! 🚀**
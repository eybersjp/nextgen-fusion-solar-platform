#!/usr/bin/env pwsh
<#
.SYNOPSIS
    PowerShell validation script for NextGen Fusion Project Management API

.DESCRIPTION
    Comprehensive API validation script that tests all endpoints including:
    - Health and version endpoints
    - Project CRUD operations
    - Task management
    - Critical path analysis
    - Metrics and admin endpoints
    - Error handling and idempotency

.PARAMETER BaseUrl
    Base URL of the API (default: http://localhost:8003)

.PARAMETER Verbose
    Enable verbose output

.EXAMPLE
    .\validate-api.ps1
    .\validate-api.ps1 -BaseUrl "http://localhost:8003" -Verbose
#>

param(
    [string]$BaseUrl = "http://localhost:8003",
    [switch]$Verbose
)

# Global variables
$script:TestResults = @()
$script:ProjectId = $null
$script:TaskId = $null
$script:IdempotencyKey = [System.Guid]::NewGuid().ToString()

# Helper function to log test results
function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = "",
        [object]$Response = $null
    )
    
    $result = @{
        TestName = $TestName
        Passed = $Passed
        Details = $Details
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    }
    
    $script:TestResults += $result
    
    $status = if ($Passed) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($Passed) { "Green" } else { "Red" }
    
    Write-Host "$status - $TestName" -ForegroundColor $color
    if ($Details) {
        Write-Host "    $Details" -ForegroundColor Gray
    }
    
    if ($Verbose -and $Response) {
        Write-Host "    Response: $($Response | ConvertTo-Json -Depth 2)" -ForegroundColor Gray
    }
}

# Helper function to make HTTP requests with error handling
function Invoke-ApiRequest {
    param(
        [string]$Method = "GET",
        [string]$Uri,
        [object]$Body = $null,
        [hashtable]$Headers = @{},
        [int]$ExpectedStatusCode = 200
    )
    
    try {
        $requestParams = @{
            Method = $Method
            Uri = $Uri
            Headers = $Headers
            ContentType = "application/json"
            TimeoutSec = 30
        }
        
        if ($Body) {
            $requestParams.Body = ($Body | ConvertTo-Json -Depth 10)
        }
        
        $response = Invoke-RestMethod @requestParams
        
        return @{
            Success = $true
            Data = $response
            StatusCode = 200  # Invoke-RestMethod doesn't return status code on success
        }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { 
            [int]$_.Exception.Response.StatusCode 
        } else { 
            0 
        }
        
        return @{
            Success = $false
            Error = $_.Exception.Message
            StatusCode = $statusCode
            Data = $null
        }
    }
}

# Test 1: Health Check
function Test-HealthEndpoint {
    Write-Host "`n🔍 Testing Health Endpoint..." -ForegroundColor Cyan
    
    $result = Invoke-ApiRequest -Uri "$BaseUrl/health"
    
    if ($result.Success) {
        $data = $result.Data
        $passed = $data.status -eq "healthy" -and $data.service -eq "project-management"
        Write-TestResult "Health Check" $passed "Status: $($data.status), Service: $($data.service)" $data
    } else {
        Write-TestResult "Health Check" $false "Request failed: $($result.Error)"
    }
}

# Test 2: Version Endpoint
function Test-VersionEndpoint {
    Write-Host "`n🔍 Testing Version Endpoint..." -ForegroundColor Cyan
    
    $result = Invoke-ApiRequest -Uri "$BaseUrl/version"
    
    if ($result.Success) {
        $data = $result.Data
        $passed = $data.service -eq "project-management" -and $data.version
        Write-TestResult "Version Info" $passed "Version: $($data.version), Environment: $($data.environment)" $data
    } else {
        Write-TestResult "Version Info" $false "Request failed: $($result.Error)"
    }
}

# Test 3: Metrics Endpoint
function Test-MetricsEndpoint {
    Write-Host "`n🔍 Testing Metrics Endpoint..." -ForegroundColor Cyan
    
    $result = Invoke-ApiRequest -Uri "$BaseUrl/metrics"
    
    if ($result.Success) {
        $metricsText = $result.Data
        $hasHttpMetrics = $metricsText -like "*http_requests_total*"
        $hasDbMetrics = $metricsText -like "*db_pool_*"
        $hasCacheMetrics = $metricsText -like "*critical_path_cache_*"
        
        $passed = $hasHttpMetrics -and $hasDbMetrics
        $details = "HTTP metrics: $hasHttpMetrics, DB metrics: $hasDbMetrics, Cache metrics: $hasCacheMetrics"
        Write-TestResult "Prometheus Metrics" $passed $details
    } else {
        Write-TestResult "Prometheus Metrics" $false "Request failed: $($result.Error)"
    }
}

# Test 4: Admin Runtime Endpoint
function Test-AdminRuntimeEndpoint {
    Write-Host "`n🔍 Testing Admin Runtime Endpoint..." -ForegroundColor Cyan
    
    $result = Invoke-ApiRequest -Uri "$BaseUrl/admin/runtime"
    
    if ($result.Success) {
        $data = $result.Data
        $hasDbConfig = $data.database -and $data.database.pool_config
        $hasFeatures = $data.features -and $data.features.idempotency_keys
        
        $passed = $hasDbConfig -and $hasFeatures
        $details = "DB config: $hasDbConfig, Features: $hasFeatures, Uptime: $($data.uptime_seconds)s"
        Write-TestResult "Admin Runtime Info" $passed $details $data
    } else {
        Write-TestResult "Admin Runtime Info" $false "Request failed: $($result.Error)"
    }
}

# Test 5: Create Project (with Idempotency)
function Test-CreateProject {
    Write-Host "`n🔍 Testing Project Creation..." -ForegroundColor Cyan
    
    $projectData = @{
        name = "Alpha Plant - PowerShell Test"
        description = "Test project created via PowerShell validation script"
        start_date = (Get-Date).ToString("yyyy-MM-dd")
        end_date = (Get-Date).AddDays(90).ToString("yyyy-MM-dd")
        status = "planning"
        priority = "high"
    }
    
    $headers = @{
        "Idempotency-Key" = $script:IdempotencyKey
    }
    
    $result = Invoke-ApiRequest -Method "POST" -Uri "$BaseUrl/api/v1/projects" -Body $projectData -Headers $headers
    
    if ($result.Success) {
        $data = $result.Data
        $script:ProjectId = $data.id
        $passed = $data.name -eq $projectData.name -and $data.id
        Write-TestResult "Create Project" $passed "Project ID: $($data.id), Name: $($data.name)" $data
        
        # Test idempotency by making the same request again
        $result2 = Invoke-ApiRequest -Method "POST" -Uri "$BaseUrl/api/v1/projects" -Body $projectData -Headers $headers
        if ($result2.Success) {
            $idempotencyPassed = $result2.Data.id -eq $data.id
            Write-TestResult "Idempotency Check" $idempotencyPassed "Same project ID returned: $($result2.Data.id)"
        } else {
            Write-TestResult "Idempotency Check" $false "Second request failed: $($result2.Error)"
        }
    } else {
        Write-TestResult "Create Project" $false "Request failed: $($result.Error)"
    }
}

# Test 6: Get Project
function Test-GetProject {
    if (-not $script:ProjectId) {
        Write-TestResult "Get Project" $false "No project ID available (create project failed)"
        return
    }
    
    Write-Host "`n🔍 Testing Get Project..." -ForegroundColor Cyan
    
    $result = Invoke-ApiRequest -Uri "$BaseUrl/api/v1/projects/$($script:ProjectId)"
    
    if ($result.Success) {
        $data = $result.Data
        $passed = $data.id -eq $script:ProjectId -and $data.name
        Write-TestResult "Get Project" $passed "Retrieved project: $($data.name)" $data
    } else {
        Write-TestResult "Get Project" $false "Request failed: $($result.Error)"
    }
}

# Test 7: Update Project
function Test-UpdateProject {
    if (-not $script:ProjectId) {
        Write-TestResult "Update Project" $false "No project ID available (create project failed)"
        return
    }
    
    Write-Host "`n🔍 Testing Update Project..." -ForegroundColor Cyan
    
    $updateData = @{
        description = "Updated description via PowerShell - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        status = "active"
    }
    
    $result = Invoke-ApiRequest -Method "PATCH" -Uri "$BaseUrl/api/v1/projects/$($script:ProjectId)" -Body $updateData
    
    if ($result.Success) {
        $data = $result.Data
        $passed = $data.description -eq $updateData.description -and $data.status -eq $updateData.status
        Write-TestResult "Update Project" $passed "Updated description and status" $data
    } else {
        Write-TestResult "Update Project" $false "Request failed: $($result.Error)"
    }
}

# Test 8: List Projects
function Test-ListProjects {
    Write-Host "`n🔍 Testing List Projects..." -ForegroundColor Cyan
    
    $result = Invoke-ApiRequest -Uri "$BaseUrl/api/v1/projects?limit=5"
    
    if ($result.Success) {
        $data = $result.Data
        $passed = $data -is [array] -or ($data.items -and $data.items -is [array])
        $count = if ($data -is [array]) { $data.Count } else { $data.items.Count }
        Write-TestResult "List Projects" $passed "Retrieved $count projects" $data
    } else {
        Write-TestResult "List Projects" $false "Request failed: $($result.Error)"
    }
}

# Test 9: Create Task
function Test-CreateTask {
    if (-not $script:ProjectId) {
        Write-TestResult "Create Task" $false "No project ID available (create project failed)"
        return
    }
    
    Write-Host "`n🔍 Testing Create Task..." -ForegroundColor Cyan
    
    $taskData = @{
        name = "Array Layout Design"
        description = "Design solar panel array layout"
        depends_on = @()
        estimated_hours = 40
        priority = "high"
        status = "todo"
    }
    
    $headers = @{
        "Idempotency-Key" = [System.Guid]::NewGuid().ToString()
    }
    
    $result = Invoke-ApiRequest -Method "POST" -Uri "$BaseUrl/api/v1/projects/$($script:ProjectId)/tasks" -Body $taskData -Headers $headers
    
    if ($result.Success) {
        $data = $result.Data
        $script:TaskId = $data.id
        $passed = $data.name -eq $taskData.name -and $data.id
        Write-TestResult "Create Task" $passed "Task ID: $($data.id), Name: $($data.name)" $data
    } else {
        Write-TestResult "Create Task" $false "Request failed: $($result.Error)"
    }
}

# Test 10: Critical Path Analysis
function Test-CriticalPath {
    if (-not $script:ProjectId) {
        Write-TestResult "Critical Path Analysis" $false "No project ID available (create project failed)"
        return
    }
    
    Write-Host "`n🔍 Testing Critical Path Analysis..." -ForegroundColor Cyan
    
    $result = Invoke-ApiRequest -Uri "$BaseUrl/api/v1/projects/$($script:ProjectId)/critical-path"
    
    if ($result.Success) {
        $data = $result.Data
        $passed = $data.critical_path -is [array] -and $data.total_duration_days -ne $null
        Write-TestResult "Critical Path Analysis" $passed "Duration: $($data.total_duration_days) days, Tasks: $($data.critical_path.Count)" $data
    } else {
        Write-TestResult "Critical Path Analysis" $false "Request failed: $($result.Error)"
    }
}

# Test 11: Cache Invalidation
function Test-CacheInvalidation {
    if (-not $script:ProjectId) {
        Write-TestResult "Cache Invalidation" $false "No project ID available (create project failed)"
        return
    }
    
    Write-Host "`n🔍 Testing Cache Invalidation..." -ForegroundColor Cyan
    
    $result = Invoke-ApiRequest -Method "DELETE" -Uri "$BaseUrl/api/v1/projects/$($script:ProjectId)/critical-path/cache"
    
    if ($result.Success) {
        $data = $result.Data
        $passed = $data.message -like "*cache*invalidated*" -or $data.status -eq "success"
        Write-TestResult "Cache Invalidation" $passed "Cache invalidated successfully" $data
    } else {
        Write-TestResult "Cache Invalidation" $false "Request failed: $($result.Error)"
    }
}

# Test 12: Error Handling
function Test-ErrorHandling {
    Write-Host "`n🔍 Testing Error Handling..." -ForegroundColor Cyan
    
    # Test 404 error
    $result = Invoke-ApiRequest -Uri "$BaseUrl/api/v1/projects/99999"
    
    if (-not $result.Success -and $result.StatusCode -eq 404) {
        Write-TestResult "404 Error Handling" $true "Correctly returned 404 for non-existent project"
    } else {
        Write-TestResult "404 Error Handling" $false "Expected 404 error not returned"
    }
    
    # Test validation error
    $invalidData = @{
        name = ""  # Empty name should cause validation error
    }
    
    $result = Invoke-ApiRequest -Method "POST" -Uri "$BaseUrl/api/v1/projects" -Body $invalidData
    
    if (-not $result.Success -and ($result.StatusCode -eq 400 -or $result.StatusCode -eq 422)) {
        Write-TestResult "Validation Error Handling" $true "Correctly returned validation error for invalid data"
    } else {
        Write-TestResult "Validation Error Handling" $false "Expected validation error not returned"
    }
}

# Main execution
function Main {
    Write-Host "🚀 NextGen Fusion Project Management API Validation" -ForegroundColor Yellow
    Write-Host "Base URL: $BaseUrl" -ForegroundColor Yellow
    Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Yellow
    Write-Host "=" * 60 -ForegroundColor Yellow
    
    # Run all tests
    Test-HealthEndpoint
    Test-VersionEndpoint
    Test-MetricsEndpoint
    Test-AdminRuntimeEndpoint
    Test-CreateProject
    Test-GetProject
    Test-UpdateProject
    Test-ListProjects
    Test-CreateTask
    Test-CriticalPath
    Test-CacheInvalidation
    Test-ErrorHandling
    
    # Summary
    Write-Host "`n📊 Test Summary" -ForegroundColor Yellow
    Write-Host "=" * 60 -ForegroundColor Yellow
    
    $totalTests = $script:TestResults.Count
    $passedTests = ($script:TestResults | Where-Object { $_.Passed }).Count
    $failedTests = $totalTests - $passedTests
    
    Write-Host "Total Tests: $totalTests" -ForegroundColor White
    Write-Host "Passed: $passedTests" -ForegroundColor Green
    Write-Host "Failed: $failedTests" -ForegroundColor Red
    Write-Host "Success Rate: $([math]::Round(($passedTests / $totalTests) * 100, 2))%" -ForegroundColor $(if ($failedTests -eq 0) { "Green" } else { "Yellow" })
    
    if ($failedTests -gt 0) {
        Write-Host "`n❌ Failed Tests:" -ForegroundColor Red
        $script:TestResults | Where-Object { -not $_.Passed } | ForEach-Object {
            Write-Host "  - $($_.TestName): $($_.Details)" -ForegroundColor Red
        }
    }
    
    # Export results to JSON
    $resultsFile = "api-validation-results-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
    $script:TestResults | ConvertTo-Json -Depth 3 | Out-File -FilePath $resultsFile -Encoding UTF8
    Write-Host "`n📄 Results exported to: $resultsFile" -ForegroundColor Cyan
    
    # Exit with appropriate code
    exit $failedTests
}

# Run the main function
Main
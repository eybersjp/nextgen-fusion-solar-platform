# NextGen Fusion Commercial Solar Platform - Operations Runbook

## Starting All Services

### Prerequisites

- Node.js v24.1.0 or later
- Python 3.13 or later
- Git
- PowerShell (Windows)

### Service Startup Sequence

#### 1. Start FastAPI Backend Service (svc-design)

```powershell
# Navigate to the svc-design directory
cd svc-design

# Start the FastAPI service with auto-reload
uvicorn simple_main:app --host 0.0.0.0 --port 8001 --reload
```

**Expected Output:**
- Service starts on http://0.0.0.0:8001
- Health endpoint available at http://localhost:8001/health
- OpenAPI docs at http://localhost:8001/docs

#### 2. Start React Frontend Development Server

```powershell
# Navigate to project root (open new terminal)
cd "C:\Users\renew\Downloads\NextGen Fusion Commercial"

# Install dependencies (first time only)
npm install

# Start the development server
npm run dev
```

**Expected Output:**
- Vite dev server starts on http://localhost:5173
- Hot module replacement enabled
- TypeScript compilation active

### Service URLs

| Service | URL | Purpose |
|---------|-----|----------|
| FastAPI Backend | http://localhost:8001 | Solar design API |
| FastAPI Health | http://localhost:8001/health | Health check |
| FastAPI Docs | http://localhost:8001/docs | API documentation |
| React Frontend | http://localhost:5173 | User interface |

## Smoke Tests

### PowerShell Smoke Test Commands

Run these commands to verify all services are operational:

#### 1. Test FastAPI Health Endpoint

```powershell
# Test health endpoint
Invoke-WebRequest -Uri "http://localhost:8001/health" -Method GET
```

**Expected Response:**
- Status Code: 200
- Content-Type: application/json
- Body: `{"status":"healthy"}`

#### 2. Test FastAPI OpenAPI Documentation

```powershell
# Test OpenAPI docs endpoint
Invoke-WebRequest -Uri "http://localhost:8001/docs" -Method GET
```

**Expected Response:**
- Status Code: 200
- Content-Type: text/html
- Body: Contains Swagger UI HTML

#### 3. Test React Frontend

```powershell
# Test frontend root
Invoke-WebRequest -Uri "http://localhost:5173" -Method GET
```

**Expected Response:**
- Status Code: 200
- Content-Type: text/html
- Body: Contains React application HTML

#### 4. Test CORS Preflight (if applicable)

```powershell
# Test CORS preflight request
Invoke-WebRequest -Uri "http://localhost:8001/health" -Method OPTIONS -Headers @{"Origin"="http://localhost:5173"; "Access-Control-Request-Method"="GET"}
```

**Expected Response:**
- Status Code: 200
- Headers: Contains CORS headers

### Complete Smoke Test Script

```powershell
# Complete smoke test script
Write-Host "Starting NextGen Fusion Platform Smoke Tests..." -ForegroundColor Green

# Test 1: FastAPI Health
Write-Host "\n1. Testing FastAPI Health Endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -Method GET
    Write-Host "✅ FastAPI Health: Status $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ FastAPI Health: Failed - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: FastAPI OpenAPI
Write-Host "\n2. Testing FastAPI OpenAPI Docs..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/docs" -Method GET
    Write-Host "✅ FastAPI Docs: Status $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ FastAPI Docs: Failed - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: React Frontend
Write-Host "\n3. Testing React Frontend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5173" -Method GET
    Write-Host "✅ React Frontend: Status $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ React Frontend: Failed - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "\n🎉 Smoke tests completed!" -ForegroundColor Green
```

## Troubleshooting

### Common Issues

#### FastAPI Service Won't Start

1. **Check Python dependencies:**
   ```powershell
   cd svc-design
   pip install -r requirements.txt
   ```

2. **Check port availability:**
   ```powershell
   netstat -an | findstr :8001
   ```

3. **Check Python version:**
   ```powershell
   python --version
   ```

#### React Frontend Won't Start

1. **Check Node.js version:**
   ```powershell
   node --version
   npm --version
   ```

2. **Clear npm cache:**
   ```powershell
   npm cache clean --force
   ```

3. **Reinstall dependencies:**
   ```powershell
   rm -rf node_modules package-lock.json
   npm install
   ```

#### Port Conflicts

- **FastAPI (8001):** Change port in uvicorn command
- **React (5173):** Vite will auto-increment to next available port

### Service Status Check

```powershell
# Check if services are running
Get-Process | Where-Object {$_.ProcessName -like "*uvicorn*" -or $_.ProcessName -like "*node*"}

# Check port usage
netstat -an | findstr ":8001\|:5173"
```

## Maintenance

### Regular Tasks

1. **Update dependencies:**
   ```powershell
   # Python dependencies
   cd svc-design
   pip list --outdated
   
   # Node.js dependencies
   cd ..
   npm outdated
   ```

2. **Database maintenance:**
   ```powershell
   # Check SQLite database size
   cd svc-design
   dir nextgen_design.db
   ```

3. **Log rotation:**
   - FastAPI logs are handled by uvicorn
   - Frontend logs are in browser console

---

*Last updated: September 25, 2025*  
*Version: v0.1.0-dev-baseline*
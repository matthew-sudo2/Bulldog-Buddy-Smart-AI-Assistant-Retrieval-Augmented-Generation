# Setup Environment Files
# This script helps you create and configure .env files securely

# Load System.Web for URL encoding
Add-Type -AssemblyName System.Web

Write-Host "🔒 Bulldog Buddy - Security Setup Script" -ForegroundColor Cyan
Write-Host "=" * 60

# Check if .env files already exist
$rootEnvExists = Test-Path ".env"
$frontendEnvExists = Test-Path "frontend\.env"
$infrastructureEnvExists = Test-Path "infrastructure\.env"

if ($rootEnvExists -and $frontendEnvExists -and $infrastructureEnvExists) {
    Write-Host "✅ All .env files already exist!" -ForegroundColor Green
    $overwrite = Read-Host "Do you want to regenerate them? (y/N)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Exiting without changes." -ForegroundColor Yellow
        exit
    }
}

# Function to generate random password
function Generate-Password {
    param([int]$Length = 32)
    $bytes = New-Object byte[] $Length
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

Write-Host "`n📝 Setting up environment files..." -ForegroundColor Yellow

# Copy templates
if (-not $rootEnvExists -or $overwrite -eq "y" -or $overwrite -eq "Y") {
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Created .env from template" -ForegroundColor Green
}

if (-not $frontendEnvExists -or $overwrite -eq "y" -or $overwrite -eq "Y") {
    Copy-Item "frontend\.env.example" "frontend\.env"
    Write-Host "✅ Created frontend\.env from template" -ForegroundColor Green
}

if (-not $infrastructureEnvExists -or $overwrite -eq "y" -or $overwrite -eq "Y") {
    Copy-Item "infrastructure\.env.example" "infrastructure\.env"
    Write-Host "✅ Created infrastructure\.env from template" -ForegroundColor Green
}

Write-Host "`n🔐 Generating secure secrets..." -ForegroundColor Yellow

# Generate secure passwords
$dbPassword = Generate-Password -Length 24
$sessionSecret = Generate-Password -Length 32

Write-Host "✅ Generated database password" -ForegroundColor Green
Write-Host "✅ Generated session secret" -ForegroundColor Green

# URL-encode the password for DATABASE_URL (special characters need encoding)
$encodedPassword = [System.Web.HttpUtility]::UrlEncode($dbPassword)

# Update root .env
Write-Host "`n📝 Updating root .env file..." -ForegroundColor Yellow
$rootEnv = Get-Content ".env"
$rootEnv = $rootEnv -replace 'DB_PASSWORD=your_secure_password_here', "DB_PASSWORD=$dbPassword"
$rootEnv = $rootEnv -replace 'SESSION_SECRET=your-long-random-secret-key-change-in-production', "SESSION_SECRET=$sessionSecret"
$rootEnv = $rootEnv -replace 'DATABASE_URL=postgresql://username:password@localhost:5432/database_name', "DATABASE_URL=postgresql://postgres:$encodedPassword@localhost:5432/bulldog_buddy"
$rootEnv | Set-Content ".env"
Write-Host "✅ Updated root .env" -ForegroundColor Green

# Update frontend .env
Write-Host "📝 Updating frontend\.env file..." -ForegroundColor Yellow
$frontendEnv = Get-Content "frontend\.env"
$frontendEnv = $frontendEnv -replace 'DB_PASSWORD=your_secure_password_here', "DB_PASSWORD=$dbPassword"
$frontendEnv = $frontendEnv -replace 'SESSION_SECRET=your-long-random-secret-key-change-in-production', "SESSION_SECRET=$sessionSecret"
$frontendEnv | Set-Content "frontend\.env"
Write-Host "✅ Updated frontend\.env" -ForegroundColor Green

# Update infrastructure .env
Write-Host "📝 Updating infrastructure\.env file..." -ForegroundColor Yellow
$infrastructureEnv = Get-Content "infrastructure\.env"
$infrastructureEnv = $infrastructureEnv -replace 'DB_PASSWORD=your_secure_password_here', "DB_PASSWORD=$dbPassword"
$infrastructureEnv | Set-Content "infrastructure\.env"
Write-Host "✅ Updated infrastructure\.env" -ForegroundColor Green

Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "✅ Environment files created successfully!" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Cyan

Write-Host "`n📋 IMPORTANT NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Update your PostgreSQL password:" -ForegroundColor White
Write-Host "   psql -U postgres -c `"ALTER USER postgres WITH PASSWORD '$dbPassword';`"" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Add your Google OAuth credentials to both .env files:" -ForegroundColor White
Write-Host "   GOOGLE_CLIENT_ID=your_client_id" -ForegroundColor Gray
Write-Host "   GOOGLE_CLIENT_SECRET=your_client_secret" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Review and edit .env files if needed:" -ForegroundColor White
Write-Host "   notepad .env" -ForegroundColor Gray
Write-Host "   notepad frontend\.env" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Start the system:" -ForegroundColor White
Write-Host "   python start.py" -ForegroundColor Gray
Write-Host ""

Write-Host "🔒 Generated credentials (save these securely):" -ForegroundColor Cyan
Write-Host "   Database Password: $dbPassword" -ForegroundColor White
Write-Host "   Session Secret:    $sessionSecret" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  NEVER commit .env files to git!" -ForegroundColor Red
Write-Host ""

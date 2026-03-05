# Test AI Provider Round-Robin Rotation
Write-Host "🧪 Testing AI Provider Round-Robin System" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor DarkGray
Write-Host ""

# Test 1: Check initial provider status
Write-Host "📊 Test 1: Initial Provider Status" -ForegroundColor Yellow
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/chat/providers" -Method Get
Write-Host "Configured providers: $($response.providers.configured_providers -join ', ')" -ForegroundColor Green
Write-Host "Active chain: $($response.providers.active_chain -join ', ')" -ForegroundColor Green
Write-Host "Rotation index: $($response.providers.rotation_index)" -ForegroundColor Green
Write-Host "Demo mode: $($response.providers.demo_mode)" -ForegroundColor Green
Write-Host ""

# Test 2: Send 5 messages and observe rotation
Write-Host "🔄 Test 2: Sending 5 Messages - Observe Rotation" -ForegroundColor Yellow

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

for ($i = 1; $i -le 5; $i++) {
    Write-Host "Message $i..." -NoNewline -ForegroundColor Cyan
    
    $body = @{
        message = "Hello number $i"
    } | ConvertTo-Json
    
    try {
        $chatResponse = Invoke-RestMethod `
            -Uri "http://localhost:5000/api/chat/message" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -WebSession $session `
            -ErrorAction Stop
        
        $provider = $chatResponse.provider.ToUpper()
        $demoMode = if ($chatResponse.demo_mode) { " 🎭" } else { " ✅" }
        
        Write-Host " → $provider$demoMode" -ForegroundColor Green
        
        # Show partial response
        $shortResponse = $chatResponse.response.Substring(0, [Math]::Min(50, $chatResponse.response.Length))
        Write-Host "   Response: $shortResponse..." -ForegroundColor DarkGray
        
        Start-Sleep -Milliseconds 500
    }
    catch {
        Write-Host " → ERROR" -ForegroundColor Red
        Write-Host "   $($_.Exception.Message)" -ForegroundColor DarkRed
    }
}

Write-Host ""

# Test 3: Check final provider status with usage counts
Write-Host "📊 Test 3: Final Provider Status (Usage Counts)" -ForegroundColor Yellow
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/chat/providers" -Method Get

Write-Host "Provider Health:" -ForegroundColor Cyan
foreach ($provider in $response.providers.configured_providers) {
    $health = $response.providers.provider_health.$provider
    
    if ($health.healthy) {
        $status = "✅ Healthy"
        $color = "Green"
    }
    else {
        if ($health.is_quota_error) {
            $cooldownMin = [Math]::Round($health.cooldown_remaining_minutes, 1)
            $status = "🚫 QUOTA (cooldown: ${cooldownMin}min)"
            $color = "Red"
        }
        else {
            $cooldownMin = [Math]::Round($health.cooldown_remaining_minutes, 1)
            $status = "⚠️  ERROR (cooldown: ${cooldownMin}min)"
            $color = "Yellow"
        }
    }
    
    $usage = if ($health.usage_count) { $health.usage_count } else { 0 }
    Write-Host "  $($provider.ToUpper()): $status [Usage: $usage]" -ForegroundColor $color
}

Write-Host ""
Write-Host "Last provider used: $($response.providers.last_provider_used.ToUpper())" -ForegroundColor Magenta
Write-Host "Total rotation index: $($response.providers.rotation_index)" -ForegroundColor Magenta
Write-Host "Demo mode: $($response.providers.demo_mode)" -ForegroundColor $(if ($response.providers.demo_mode) { "Red" } else { "Green" })

Write-Host ""
Write-Host "=" * 60 -ForegroundColor DarkGray
Write-Host "✅ Test Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Tip: Mở browser http://localhost:5000 để xem status bar real-time!" -ForegroundColor Cyan

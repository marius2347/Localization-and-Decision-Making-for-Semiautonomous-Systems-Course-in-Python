<#
.SYNOPSIS
    AVD VM monthly reboot script - runs daily on the VM via Task Scheduler.
    Checks if current time is within the maintenance window (2nd full week's weekend,
    Saturday 21:00 - Sunday 06:00 CET/CEST). If yes, reboots the machine.

.DESCRIPTION
    Schedule this script to run daily (e.g. every hour on Sat-Sun, or daily at 22:00)
    via Windows Task Scheduler on the AVD session host VM itself.
    No Azure modules or permissions needed - it just reboots itself.

.NOTES
    Deploy via GPO, Intune, or manual Task Scheduler setup on each session host.
#>

param(
    [int]$ShutdownDelaySec = 60,   # Seconds before reboot (gives users time to save)
    [switch]$WhatIf,
    [switch]$Install              # Use -Install to register the scheduled task
)

# ============================================================
# LOGGING
# ============================================================
$logFile = "C:\Windows\Temp\avd-maintenance-reboot.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$timestamp] $Message"
    Add-Content -Path $logFile -Value $entry
    Write-Host $entry
}

# ============================================================
# SCHEDULE CALCULATION
# ============================================================
function Get-MaintenanceSaturday {
    <#
    .SYNOPSIS
        Returns the Saturday of the 2nd full week's weekend for a given month/year.
        A "full week" = Mon-Sun entirely within the month.
        Examples: Apr 2026 -> 18th, Mar 2026 -> 14th, May 2026 -> 16th, Jun 2026 -> 13th
    #>
    param(
        [int]$Year = (Get-Date).Year,
        [int]$Month = (Get-Date).Month
    )

    $firstOfMonth = Get-Date -Year $Year -Month $Month -Day 1
    $dayOfWeek = $firstOfMonth.DayOfWeek

    # Find first Monday that starts a full Mon-Sun week within the month
    if ($dayOfWeek -eq [DayOfWeek]::Monday) {
        $firstFullWeekMonday = $firstOfMonth
    } else {
        $daysUntilMonday = (8 - [int]$dayOfWeek) % 7
        if ($daysUntilMonday -eq 0) { $daysUntilMonday = 7 }
        $firstFullWeekMonday = $firstOfMonth.AddDays($daysUntilMonday)
    }

    # 2nd full week Monday + 5 days = Saturday
    $secondFullWeekMonday = $firstFullWeekMonday.AddDays(7)
    $maintenanceSaturday = $secondFullWeekMonday.AddDays(5)

    return $maintenanceSaturday
}

function Test-InMaintenanceWindow {
    <#
    .SYNOPSIS
        Returns $true if current time (CET/CEST) is Saturday 21:00 - Sunday 06:00
        of the 2nd full week's weekend.
    #>
    $cetZone = [TimeZoneInfo]::FindSystemTimeZoneById("Central European Standard Time")
    $nowCet = [TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $cetZone)

    $maintenanceSaturday = Get-MaintenanceSaturday -Year $nowCet.Year -Month $nowCet.Month

    $windowStart = $maintenanceSaturday.Date.AddHours(21)  # Saturday 21:00
    $windowEnd   = $maintenanceSaturday.Date.AddDays(1).AddHours(6)  # Sunday 06:00

    return ($nowCet -ge $windowStart -and $nowCet -lt $windowEnd)
}

# ============================================================
# SELF-INSTALL: Register this script as a Scheduled Task
# ============================================================
if ($Install) {
    Write-Host "Installing scheduled task..." -ForegroundColor Cyan
    $scriptPath = $MyInvocation.MyCommand.Path
    $scriptDir = Split-Path -Parent $scriptPath

    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`"" `
        -WorkingDirectory $scriptDir

    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At "21:00"

    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    Register-ScheduledTask -TaskName "AVD Monthly Maintenance Reboot" `
        -Action $action -Trigger $trigger -Settings $settings `
        -User "SYSTEM" -RunLevel Highest -Force

    Write-Host "[DONE] Task 'AVD Monthly Maintenance Reboot' registered successfully." -ForegroundColor Green
    Write-Host "Script location: $scriptPath" -ForegroundColor Green
    exit 0
}

# ============================================================
# MAIN
# ============================================================
Write-Log "=== AVD Maintenance Reboot Check ==="
Write-Log "Computer: $env:COMPUTERNAME"

# Show what the maintenance date is for this month
$cetZone = [TimeZoneInfo]::FindSystemTimeZoneById("Central European Standard Time")
$nowCet = [TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $cetZone)
$sat = Get-MaintenanceSaturday -Year $nowCet.Year -Month $nowCet.Month
Write-Log "This month's maintenance Saturday: $($sat.ToString('yyyy-MM-dd'))"
Write-Log "Current time (CET/CEST): $($nowCet.ToString('yyyy-MM-dd HH:mm:ss'))"

if (Test-InMaintenanceWindow) {
    Write-Log "[MATCH] Currently in maintenance window!"

    # Check if we already rebooted this window (prevent reboot loops)
    $markerFile = "C:\Windows\Temp\avd-reboot-marker-$($sat.ToString('yyyyMMdd')).txt"
    if (Test-Path $markerFile) {
        Write-Log "[SKIP] Already rebooted this maintenance window (marker exists). Exiting."
        exit 0
    }

    if ($WhatIf) {
        Write-Log "[WhatIf] Would reboot $env:COMPUTERNAME in $ShutdownDelaySec seconds."
    } else {
        # Create marker so we don't reboot again after coming back up
        Set-Content -Path $markerFile -Value "Rebooted at $($nowCet.ToString('yyyy-MM-dd HH:mm:ss'))"
        Write-Log "[ACTION] Initiating reboot in $ShutdownDelaySec seconds..."

        # Notify logged-in users
        shutdown.exe /r /t $ShutdownDelaySec /c "Scheduled monthly maintenance reboot. The system will restart in $ShutdownDelaySec seconds. Please save your work." /d p:4:1

        Write-Log "[ACTION] Reboot command issued. Machine will restart shortly."
    }
} else {
    Write-Log "[NO MATCH] Not in maintenance window. No action."
}

Write-Log "=== Check complete ==="
exit 0

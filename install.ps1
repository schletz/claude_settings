<#
.SYNOPSIS
    Installs the Claude Code configuration of this repository (settings.json, CLAUDE.md and the
    bundled skills) and/or the matching Codex CLI equivalents (AGENTS.md and skills), depending on
    which of the two tools is detected on this machine.

.DESCRIPTION
    Detects Claude Code and Codex CLI by checking whether their commands are on PATH or their
    config folders (%USERPROFILE%\.claude / %USERPROFILE%\.codex) already exist. Only the tools
    that are actually detected get installed:
      - Claude Code only  -> only settings.json, CLAUDE.md and the skills go into .claude.
      - Codex CLI only    -> only AGENTS.md (copied from CLAUDE.md) and the skills go into
                              .codex and .agents\skills; .claude is left untouched.
      - Both detected     -> both are installed automatically, no confirmation needed.
      - Neither detected  -> falls back to installing Claude Code only, since that is this
                              repository's primary target.
    There is no Codex equivalent for settings.json (config.toml uses a different format and
    different keys), so that file is never copied to the Codex side.

    Downloads the repository as a ZIP archive, extracts it to a temporary folder and copies the
    configuration items to their target folders. Existing items are replaced without a backup, so
    local modifications to them are lost.

.EXAMPLE
    Download first, run afterwards, both lines in cmd.exe. Microsoft Defender blocks the
    "download and pipe into iex" one liner on current Windows 11 builds (the pattern abused by
    ClickFix campaigns), so the script is fetched as a file:

    curl.exe -sL -o "%TEMP%\install_claude.ps1" https://raw.githubusercontent.com/schletz/claude_settings/main/install.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\install_claude.ps1"
#>

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repoZipUrl = 'https://github.com/schletz/claude_settings/archive/refs/heads/main.zip'
$claudeDir = Join-Path $env:USERPROFILE '.claude'
$codexDir = Join-Path $env:USERPROFILE '.codex'
$agentsSkillsDir = Join-Path $env:USERPROFILE '.agents\skills'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$workDir = Join-Path $env:TEMP "claude_settings-$stamp"

# Claude Code items: path inside the repository -> path inside the .claude directory
$claudeItems = @(
    @{ Source = 'settings.json'; Target = 'settings.json' },
    @{ Source = 'CLAUDE.md'; Target = 'CLAUDE.md' },
    @{ Source = 'skills\document-software'; Target = 'skills\document-software' },
    @{ Source = 'skills\playwright-cli'; Target = 'skills\playwright-cli' },
    @{ Source = 'skills\asciidoc'; Target = 'skills\asciidoc' }
)

# Codex CLI equivalents: CLAUDE.md becomes AGENTS.md, skills use the identical SKILL.md format.
# There is no equivalent for settings.json (config.toml has a different format and different keys).
$codexAgentsItem = @(
    @{ Source = 'CLAUDE.md'; Target = 'AGENTS.md' }
)
$codexSkillItems = @(
    @{ Source = 'skills\document-software'; Target = 'document-software' },
    @{ Source = 'skills\playwright-cli'; Target = 'playwright-cli' },
    @{ Source = 'skills\asciidoc'; Target = 'asciidoc' }
)

function Install-RepoItems {
    param(
        [string]$RepoRoot,
        [string]$TargetBaseDir,
        [array]$Items
    )
    if (-not (Test-Path $TargetBaseDir)) {
        New-Item -ItemType Directory -Path $TargetBaseDir -Force | Out-Null
    }
    foreach ($item in $Items) {
        $source = Join-Path $RepoRoot $item.Source
        $target = Join-Path $TargetBaseDir $item.Target
        if (-not (Test-Path $source)) { throw "Im Repository nicht gefunden: $($item.Source)" }

        # Remove the target first: a plain copy would keep files that no longer exist upstream
        if (Test-Path $target) {
            Remove-Item -Path $target -Recurse -Force
        }

        $parent = Split-Path -Parent $target
        if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        Copy-Item -Path $source -Destination $target -Recurse -Force
        Write-Host "  Installiert: $target"
    }
}

# A tool counts as "installed" if its CLI command is on PATH or its config folder already exists
# (the folder alone is not enough on a brand new machine, the command alone is not enough if the
# folder was created by an older, now removed installation).
$claudeDetected = [bool](Get-Command -Name 'claude' -ErrorAction SilentlyContinue) -or (Test-Path $claudeDir)
$codexDetected = [bool](Get-Command -Name 'codex' -ErrorAction SilentlyContinue) -or (Test-Path $codexDir)

$installClaude = $claudeDetected
$installCodex = $codexDetected

if (-not $claudeDetected -and -not $codexDetected) {
    Write-Host 'Weder Claude Code noch Codex CLI wurden auf diesem Rechner gefunden.'
    Write-Host 'Installiere versuchsweise trotzdem die Claude-Code-Konfiguration (Standardverhalten).'
    $installClaude = $true
} elseif ($installClaude -and $installCodex) {
    Write-Host "Claude Code und Codex CLI gefunden ($claudeDir, $codexDir). Installiere Config und Skills fuer beide."
} elseif ($installCodex) {
    Write-Host "Nur Codex CLI gefunden ($codexDir), die Claude-Installation wird uebersprungen."
}

if (-not $installClaude -and -not $installCodex) {
    Write-Host 'Nichts zu installieren.'
    exit 0
}

Write-Host ''
if ($installClaude) { Write-Host "Zielverzeichnis (Claude Code): $claudeDir" }
if ($installCodex) { Write-Host "Zielverzeichnis (Codex CLI): $codexDir und $agentsSkillsDir" }
Write-Host 'Vorhandene Dateien werden dabei ohne Sicherung ueberschrieben.'

New-Item -ItemType Directory -Path $workDir -Force | Out-Null

try {
    $zipPath = Join-Path $workDir 'repo.zip'
    Write-Host ''
    Write-Host 'Lade Konfiguration von GitHub ...'
    Invoke-WebRequest -Uri $repoZipUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $workDir -Force

    # A GitHub ZIP archive always contains exactly one top level folder <repo>-<branch>
    $repoRoot = Get-ChildItem -Path $workDir -Directory | Select-Object -First 1
    if (-not $repoRoot) { throw 'Das heruntergeladene Archiv ist leer.' }

    if ($installClaude) {
        Install-RepoItems -RepoRoot $repoRoot.FullName -TargetBaseDir $claudeDir -Items $claudeItems
    }

    if ($installCodex) {
        Write-Host ''
        Write-Host "Installiere Codex-Aequivalente nach $codexDir und $agentsSkillsDir ..."
        Install-RepoItems -RepoRoot $repoRoot.FullName -TargetBaseDir $codexDir -Items $codexAgentsItem
        Install-RepoItems -RepoRoot $repoRoot.FullName -TargetBaseDir $agentsSkillsDir -Items $codexSkillItems
    }

    Write-Host ''
    if ($installClaude -and $installCodex) {
        Write-Host 'Fertig. Claude Code und Codex CLI neu starten, damit die Einstellungen wirksam werden.'
    } elseif ($installClaude) {
        Write-Host 'Fertig. Claude Code neu starten, damit die Einstellungen wirksam werden.'
    } else {
        Write-Host 'Fertig. Codex CLI neu starten, damit die Einstellungen wirksam werden.'
    }

    # Console output stays ASCII only so the file works with and without a UTF-8 BOM
    if ($installClaude) {
        Write-Host ''
        Write-Host 'WICHTIG: Die CLAUDE.md beschreibt die lokale Umgebung des Autors (installierte' -ForegroundColor Yellow
        Write-Host 'Frameworks und Versionen, IDEs, Home-Verzeichnis, Browserpfad). Bitte an den' -ForegroundColor Yellow
        Write-Host 'eigenen Rechner anpassen, sonst geht Claude von falscher Software aus:' -ForegroundColor Yellow
        Write-Host "  $claudeDir\CLAUDE.md" -ForegroundColor Yellow
    }

    if ($installCodex) {
        Write-Host ''
        Write-Host 'WICHTIG: Die AGENTS.md enthaelt denselben Abschnitt "Lokale Umgebung" und muss' -ForegroundColor Yellow
        Write-Host 'ebenso an den eigenen Rechner angepasst werden:' -ForegroundColor Yellow
        Write-Host "  $codexDir\AGENTS.md" -ForegroundColor Yellow
        Write-Host ''
        Write-Host 'HINWEIS: settings.json wurde NICHT nach config.toml uebertragen, da sich Format' -ForegroundColor Yellow
        Write-Host 'und Schluessel unterscheiden. Siehe README, Abschnitt "Aequivalent fuer Codex-User".' -ForegroundColor Yellow
    }

    if ($installClaude) {
        Write-Host ''
        Write-Host 'ACHTUNG: Die settings.json setzt "defaultMode": "bypassPermissions". Claude Code' -ForegroundColor Red
        Write-Host 'fragt damit vor KEINER Aktion mehr nach: es liest, aendert und loescht Dateien,' -ForegroundColor Red
        Write-Host 'fuehrt Shell-Befehle aus und ruft Webseiten ab - alles ohne Bestaetigung.' -ForegroundColor Red
        Write-Host 'Jeder muss selbst entscheiden, ob er so arbeiten will. Wer das nicht will,' -ForegroundColor Red
        Write-Host 'entfernt in der settings.json die Zeilen "defaultMode": "bypassPermissions"' -ForegroundColor Red
        Write-Host 'und "skipDangerousModePermissionPrompt": true:' -ForegroundColor Red
        Write-Host "  $claudeDir\settings.json" -ForegroundColor Red
    }
}
finally {
    Remove-Item -Path $workDir -Recurse -Force -ErrorAction SilentlyContinue
}

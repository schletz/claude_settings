<#
.SYNOPSIS
    Installs the configuration files of this repository: settings.json and CLAUDE.md for Claude Code
    and/or AGENTS.md for the Codex CLI, depending on which of the two tools is detected on this
    machine. Skills are no longer installed by this script, they come from "npx skills" instead.

.DESCRIPTION
    Detects Claude Code and Codex CLI by checking whether their commands are on PATH or their
    config folders (%USERPROFILE%\.claude / %USERPROFILE%\.codex) already exist. Only the tools
    that are actually detected get installed:
      - Claude Code only  -> only settings.json and CLAUDE.md go into .claude.
      - Codex CLI only    -> only AGENTS.md (copied from CLAUDE.md) goes into .codex;
                              .claude is left untouched.
      - Both detected     -> both are installed automatically, no confirmation needed.
      - Neither detected  -> falls back to installing Claude Code only, since that is this
                              repository's primary target.
    There is no Codex equivalent for settings.json (config.toml uses a different format and
    different keys), so that file is never copied to the Codex side.

    The files are downloaded individually from the repository's main branch into a temporary
    folder and moved to their target folders afterwards, so a failed download never leaves a
    truncated file behind. Existing items are replaced without a backup, so local modifications
    to them are lost.

.EXAMPLE
    Download first, run afterwards, both lines in cmd.exe. Microsoft Defender blocks the
    "download and pipe into iex" one liner on current Windows 11 builds (the pattern abused by
    ClickFix campaigns), so the script is fetched as a file:

    curl.exe -sL -o "%TEMP%\install_claude.ps1" https://raw.githubusercontent.com/schletz/claude_settings/main/install.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\install_claude.ps1"
#>

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$rawBaseUrl = 'https://raw.githubusercontent.com/schletz/claude_settings/main'
$claudeDir = Join-Path $env:USERPROFILE '.claude'
$codexDir = Join-Path $env:USERPROFILE '.codex'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$workDir = Join-Path $env:TEMP "claude_settings-$stamp"

# Claude Code items: file name in the repository -> file name inside the .claude directory
$claudeItems = @(
    @{ Source = 'settings.json'; Target = 'settings.json' },
    @{ Source = 'CLAUDE.md'; Target = 'CLAUDE.md' }
)

# Codex CLI equivalent: CLAUDE.md becomes AGENTS.md, the content is identical.
# There is no equivalent for settings.json (config.toml has a different format and different keys).
$codexItems = @(
    @{ Source = 'CLAUDE.md'; Target = 'AGENTS.md' }
)

function Install-RepoFiles {
    param(
        [string]$BaseUrl,
        [string]$WorkDir,
        [string]$TargetBaseDir,
        [array]$Items
    )
    if (-not (Test-Path $TargetBaseDir)) {
        New-Item -ItemType Directory -Path $TargetBaseDir -Force | Out-Null
    }
    foreach ($item in $Items) {
        # Download into the work folder first: a failed request must not truncate the target file
        $download = Join-Path $WorkDir $item.Source
        Invoke-WebRequest -Uri "$BaseUrl/$($item.Source)" -OutFile $download -UseBasicParsing

        $target = Join-Path $TargetBaseDir $item.Target
        Move-Item -Path $download -Destination $target -Force
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
    Write-Host "Claude Code und Codex CLI gefunden ($claudeDir, $codexDir). Installiere die Config fuer beide."
} elseif ($installCodex) {
    Write-Host "Nur Codex CLI gefunden ($codexDir), die Claude-Installation wird uebersprungen."
}

Write-Host ''
if ($installClaude) { Write-Host "Zielverzeichnis (Claude Code): $claudeDir" }
if ($installCodex) { Write-Host "Zielverzeichnis (Codex CLI): $codexDir" }
Write-Host 'Vorhandene Dateien werden dabei ohne Sicherung ueberschrieben.'

New-Item -ItemType Directory -Path $workDir -Force | Out-Null

try {
    Write-Host ''
    Write-Host 'Lade Konfiguration von GitHub ...'

    if ($installClaude) {
        Install-RepoFiles -BaseUrl $rawBaseUrl -WorkDir $workDir -TargetBaseDir $claudeDir -Items $claudeItems
    }

    if ($installCodex) {
        Install-RepoFiles -BaseUrl $rawBaseUrl -WorkDir $workDir -TargetBaseDir $codexDir -Items $codexItems
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
    Write-Host ''
    Write-Host 'NAECHSTER SCHRITT: Die Skills sind nicht Teil dieses Skripts. Sie werden mit der' -ForegroundColor Cyan
    Write-Host 'skills-CLI installiert (Node.js wird benoetigt):' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  npx skills@latest add schletz/claude_settings --skill document-software --skill asciidoc -g' -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'Der Skill playwright-cli bringt einen eigenen Installer mit:' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  npm install -g @playwright/cli@latest' -ForegroundColor Cyan
    Write-Host '  playwright-cli install --skills' -ForegroundColor Cyan

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

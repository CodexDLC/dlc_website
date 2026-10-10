[CmdletBinding()]
param(
    [switch]$Push,
    [switch]$Deploy,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_.-]*$')]
    [string]$SshAlias
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-GitChecked {
    param([string[]]$Arguments)
    $result = & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Git command failed.' }
    return $result
}

$sha = (Invoke-GitChecked @('rev-parse', 'HEAD')).Trim()
if ($sha -notmatch '^[0-9a-f]{40}$') { throw 'Expected a full commit SHA.' }
$branch = (Invoke-GitChecked @('branch', '--show-current')).Trim()
if (-not $branch) { throw 'Select a branch before publication or deployment.' }
if (($Push -or $Deploy) -and $branch -ne 'main') {
    throw 'This release helper publishes and deploys main only.'
}
if (Invoke-GitChecked @('status', '--porcelain')) {
    throw 'Commit or separately preserve local changes first. Deployment uses committed files only.'
}
$origin = (Invoke-GitChecked @('remote', 'get-url', 'origin')).Trim()
if ($origin -notin @('https://github.com/CodexDLC/dlc_website.git', 'git@github.com:CodexDLC/dlc_website.git')) {
    throw 'The origin remote must be the DLC website repository.'
}
Write-Host "Release commit: $sha"
Write-Host "Branch: $branch"
if ($Deploy -and -not $SshAlias) { throw 'Specify your existing SSH alias with -SshAlias before deployment.' }

if ($Push) {
    Invoke-GitChecked @('push', 'origin', "${branch}:${branch}")
    $published = Invoke-GitChecked @('ls-remote', 'origin', "refs/heads/$branch")
    if (-not $published -or ($published -split '\s+')[0] -ne $sha) {
        throw 'The remote branch does not match the selected release commit.'
    }
}

if (-not $Deploy) {
    Write-Host 'No server changes requested. Add -Deploy to deploy the published commit.'
    return
}

# Only the validated hexadecimal SHA is substituted into the remote shell script.
# SSH uses the existing local configuration; private keys are never copied to GitHub.
$remoteScript = @'
set -eu
umask 077
sha='__COMMIT_SHA__'
env_file=/srv/dlc/shared/.env.prod
test -f "$env_file" || { echo 'Create the private /srv/dlc/shared/.env.prod first.' >&2; exit 1; }
test "$(stat -c '%a' "$env_file")" = 600 || { echo 'The private env file must have mode 600.' >&2; exit 1; }
mkdir -p /srv/dlc/releases
release="/srv/dlc/releases/$sha"
if [ ! -d "$release" ]; then
    git clone https://github.com/CodexDLC/dlc_website.git "$release"
    git -C "$release" checkout --detach "$sha"
fi
test "$(git -C "$release" rev-parse HEAD)" = "$sha"
test -z "$(git -C "$release" status --porcelain)"
cd "$release"
export DLC_IMAGE_TAG="$sha"
compose() {
    docker compose --project-name dlc --env-file "$env_file" -f deploy/compose.test-server.yml "$@"
}
compose config --quiet
compose build web
compose up -d --wait db redis
compose run --rm --no-deps --interactive=false -T migrate
compose run --rm --no-deps --interactive=false -T collectstatic
compose up -d --wait web
test -d /var/www/dlc-static || { echo 'Prepare the public static directory before deployment.' >&2; exit 1; }
docker cp "$(compose ps -q web):/app/staticfiles/." /var/www/dlc-static/
ln -s "$release" "/srv/dlc/.current-$sha"
mv -Tf "/srv/dlc/.current-$sha" /srv/dlc/current
compose ps
echo "DLC release started: $sha"
echo 'Verify the public HTTPS URL separately. Existing database and uploaded files are preserved.'
'@
$remoteScript = $remoteScript.Replace('__COMMIT_SHA__', $sha).Replace("`r`n", "`n")
$remoteScript | & ssh -o BatchMode=yes -o StrictHostKeyChecking=yes $SshAlias bash -s
if ($LASTEXITCODE -ne 0) { throw 'Deployment failed. Inspect the failed step before retrying.' }

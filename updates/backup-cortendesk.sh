#!/usr/bin/env bash
# Offline migration backup. Run on the OLD Ubuntu server as root.
set -Eeuo pipefail
umask 077

container=${1:-cortendesk}
output=${2:-/home/ubuntu}
[[ $EUID -eq 0 ]] || { echo 'Run with sudo bash.'; exit 1; }
for tool in docker python3 tar gzip sha256sum; do command -v "$tool" >/dev/null; done
[[ -d $output ]] || { echo 'Output directory does not exist.'; exit 1; }
stamp=$(date -u +%Y%m%d-%H%M%S)
work=$(mktemp -d /var/tmp/cortendesk-migration.XXXXXXXX)
archive="$output/cortendesk-migration-$stamp.tar.gz"
restart_needed=0
finish() {
    status=$?
    trap - EXIT INT TERM
    if (( restart_needed )); then
        if ! docker start "$container" >/dev/null; then
            echo "IMPORTANT: could not restart $container. Run: sudo docker start $container" >&2
            status=1
        fi
    fi
    if (( status != 0 )); then
        echo "Backup did not finish. Private working files retained in: $work" >&2
        echo 'Do not use a partial archive for migration.' >&2
    fi
    exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo 'Checking container and database (no secrets printed)...'
[[ $(docker inspect -f '{{.State.Running}}' "$container") == true ]] || {
    echo 'Container must be running for the preflight check.'; exit 1;
}
docker inspect "$container" > "$work/container-inspect.json"
image=$(docker inspect -f '{{.Image}}' "$container")
docker image inspect "$image" > "$work/image-inspect.json"
docker exec -w /app "$container" php -r '
require "vendor/autoload.php";
$app = require "bootstrap/app.php";
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$driver = config("database.default");
echo json_encode(["driver" => $driver, "sqlite_path" => $driver === "sqlite" ? config("database.connections.sqlite.database") : null]);
' > "$work/database-info.json"
python3 - "$work" <<'PY'
import json, pathlib, sys
work = pathlib.Path(sys.argv[1])
db = json.loads((work/'database-info.json').read_text())
if db['driver'] != 'sqlite':
    raise SystemExit('External/non-SQLite database detected. A separate database dump is required; nothing has been stopped.')
if not isinstance(db['sqlite_path'], str) or not db['sqlite_path'].startswith('/'):
    raise SystemExit('SQLite database path is not absolute. Stop and inspect before backing up.')
container = json.loads((work/'container-inspect.json').read_text())[0]
(work/'data-mounted.txt').write_text('yes' if any(m['Destination'] == '/data' for m in container['Mounts']) else 'no')
sources = []
for mount in container['Mounts']:
    source = mount['Source']
    if mount['Type'] not in ('bind', 'volume') or not source.startswith('/'):
        raise SystemExit('Unsupported mount: '+mount['Type'])
    path = pathlib.Path(source)
    if path.resolve() in map(pathlib.Path, ['/', '/etc', '/var', '/var/lib', '/var/lib/docker', '/home', '/opt', '/srv']) or path.is_socket():
        raise SystemExit('Broad host-directory or socket mount requires manual review: '+source)
    if source not in sources:
        sources.append(source)
with (work/'mount-sources.bin').open('wb') as output:
    for source in sources:
        output.write(source.encode()+b'\0')
PY
db_path=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sqlite_path"])' "$work/database-info.json")
docker exec "$container" test -f "$db_path"
mkdir "$work/mounts" "$work/extra-container-files"
df -h "$output" /var/tmp
echo 'Stopping CortenDesk for a consistent copy. Remote sessions will disconnect.'
restart_needed=1
docker stop -t 60 "$container" >/dev/null
if [[ $(docker inspect -f '{{.State.ExitCode}}' "$container") == 137 ]]; then
    echo 'Container needed a forced stop; aborting rather than claiming a consistent backup.'; exit 1
fi

index=0
while IFS= read -r -d '' source; do
    index=$((index + 1))
    echo "Archiving Docker data mount $index..."
    tar --numeric-owner --acls --xattrs -C / -cpf "$work/mounts/mount-$index.tar" -- "${source#/}"
done < "$work/mount-sources.bin"

# Keep ephemeral Laravel storage and configuration as well as mounted data.
if [[ $(cat "$work/data-mounted.txt") == no ]]; then
    docker cp "$container:/data" "$work/extra-container-files/data"
fi
docker cp "$container:/app/storage" "$work/extra-container-files/storage"
docker cp "$container:$db_path" "$work/extra-container-files/database.sqlite"
for suffix in -wal -shm; do
    docker cp "$container:$db_path$suffix" "$work/extra-container-files/database.sqlite$suffix" 2>/dev/null || true
done
docker cp "$container:/app/.env" "$work/extra-container-files/.env" 2>/dev/null || true

paths=()
for path in /opt/cortendesk /etc/apache2 /etc/letsencrypt /srv/stdesk-updates /etc/cron.d /var/spool/cron/crontabs; do
    [[ ! -e $path ]] || paths+=("${path#/}")
done
tar --numeric-owner --acls --xattrs -C / -cpf "$work/host-files.tar" -- "${paths[@]}"
# Old cloud network settings are reference material, NOT restoration instructions.
ip address show > "$work/old-network-addresses.txt"
ip route show > "$work/old-network-routes.txt"
mkdir "$work/network-reference-only"
[[ ! -d /etc/netplan ]] || cp -a /etc/netplan "$work/network-reference-only/"

echo 'Restarting CortenDesk...'
docker start "$container" >/dev/null
restart_needed=0

echo 'Saving exact Docker image for restoration without downloading it...'
docker image save -o "$work/docker-image.tar" "$image"
cat > "$work/RESTORE-NOTES.txt" <<'TXT'
PRIVATE BACKUP: database, passwords/tokens, APP_KEY, ID/relay private keys,
TLS certificates, Docker environment, Apache settings, and update installers.
Do not upload this archive to GitHub or the public /client/ directory.

Verify the adjacent SHA256 file before extracting on a new server.
The archive is a migration bundle, NOT a script to restore blindly over a server.
Use container-inspect.json for environment, original mount destinations, port
bindings and restart policy. Use image-inspect.json for exact image identity.
Docker image: docker load -i docker-image.tar (after extraction).
Mount tar files retain OLD HOST paths for reference; map them to new bind paths
or newly created Docker volumes. Never overwrite the entire /var/lib/docker tree.
Restore bind/volume data before starting the new container. The separate SQLite
copy may have adjacent -wal/-shm files: keep the complete set together while closed.
Use /opt/cortendesk compose files where available, adapting mount source paths.
Do not restore old bootstrap config caches blindly on different paths.

host-files.tar contains Apache, Let's Encrypt, /opt/cortendesk and
/srv/stdesk-updates, plus cron files when present. Review cron before enabling.
Preserve APP_KEY, server ID/relay keys, SQLite and all mounted data.
Keep desk.status16.ru and its /client/ URL to preserve existing client settings
and update channels. Install Apache modules/certbot/Docker on the new OS as needed.
Review Apache paths, permissions and symlinks; configtest before starting Apache.
Do NOT apply network-reference-only/netplan from the old cloud to the new server.
Firewall/security groups and DNS must be configured for the new provider.
Test the new server before switching DNS, then stop the old one at cutover.
Do not run both writable copies indefinitely: changes after this backup are absent.
TXT
echo 'Compressing and checking archive (CortenDesk is running again)...'
tar -C "$work" -czf "$archive" .
tar -tzf "$archive" >/dev/null
(cd "$output"; sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256")
chmod 600 "$archive" "$archive.sha256"
owner=${SUDO_USER:-ubuntu}
if id "$owner" >/dev/null 2>&1; then chown "$owner" "$archive" "$archive.sha256"; fi
# Only delete the exact private directory returned by mktemp above.
case "$work" in /var/tmp/cortendesk-migration.*) rm -rf -- "$work" ;; esac
echo "Backup ready: $archive"
echo "Checksum: $archive.sha256"
echo 'Keep both files privately and copy them off this server.'

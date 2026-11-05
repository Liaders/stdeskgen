"""Exercise the supplied VirtualHost in an isolated official Apache container."""
import http.client
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import time
import uuid


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        root.chmod(0o755)
        public = root / 'public'
        public.mkdir(mode=0o755)
        samples = {
            '/client/windows-x64.json': b'{"app_name":"CortenDesk RustDesk", "schema":2}',
            '/client/client-windows-x64.exe': b'MZ\x00CortenDesk\x00RustDesk\xff',
            '/client/branding.html': b'<html>CortenDesk RustDesk</html>',
        }
        for url, content in samples.items():
            (public / url.rsplit('/', 1)[1]).write_bytes(content)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(root / 'key.pem'), '-out', str(root / 'cert.pem'),
                        '-days', '1', '-subj', '/CN=desk.status16.ru'],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        config = Path(__file__).with_name('desk.status16.ru.conf').read_text(encoding='utf-8')
        config = config.replace('/etc/letsencrypt/live/desk.status16.ru/fullchain.pem', '/test/cert.pem')
        config = config.replace('/etc/letsencrypt/live/desk.status16.ru/privkey.pem', '/test/key.pem')
        # Load modules normally enabled by a2enmod on the user's Ubuntu server.
        modules = ['ssl', 'http2', 'headers', 'rewrite', 'proxy', 'proxy_http',
                   'proxy_wstunnel', 'substitute', 'filter']
        prefix = ''.join(f'<IfModule !{name}_module>\nLoadModule {name}_module modules/mod_{name}.so\n</IfModule>\n'
                         for name in modules)
        (root / 'vhost.conf').write_text(prefix + '\nListen 443\n' + config, encoding='utf-8')
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        name = 'stdesk-apache-test-' + uuid.uuid4().hex
        options = ['docker', 'run', '--rm', '--name', name,
                   '-e', 'APACHE_LOG_DIR=/usr/local/apache2/logs',
                   '-v', str(root) + ':/test:ro',
                   '-v', str(public) + ':/srv/stdesk-updates/public:ro']
        image = ['httpd:2.4', 'httpd', '-C', 'Include /test/vhost.conf']
        subprocess.run([*options, *image, '-t'], check=True)
        process = subprocess.Popen([*options, '-p', f'127.0.0.1:{port}:443', *image, '-DFOREGROUND'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def get(url, headers=None):
            connection = http.client.HTTPSConnection('127.0.0.1', port,
                context=ssl._create_unverified_context(), timeout=5)
            try:
                connection.request('GET', url, headers={'Host': 'desk.status16.ru', **(headers or {})})
                response = connection.getresponse()
                return response.status, response.read(), dict(response.getheaders())
            finally:
                connection.close()

        try:
            for attempt in range(60):
                try:
                    get('/client/windows-x64.json')
                    break
                except (OSError, http.client.HTTPException):
                    if process.poll() is not None:
                        raise RuntimeError('Apache exited during startup')
                    time.sleep(0.5)
            else:
                raise RuntimeError('Apache did not become ready')
            for url, content in samples.items():
                status, body, headers = get(url)
                assert status == 200 and body == content, (url, status, body)
            status, body, _ = get('/client/windows-x64.json', {'Connection': 'Upgrade', 'Upgrade': 'websocket'})
            assert status == 200 and body == samples['/client/windows-x64.json']
            assert get('/client/missing.json')[0] == 404
            assert get('/client/')[0] == 403
            status, _, headers = get('/client')
            assert status == 301 and headers.get('Location', '').endswith('/client/'), (status, headers)
            # No backend is running in this container: a proxy error proves the
            # original login/API/WebSocket routes still reach the proxy path.
            assert get('/login')[0] in (502, 503)
            assert get('/api/peers')[0] in (502, 503)
            assert get('/ws/id', {'Connection': 'Upgrade', 'Upgrade': 'websocket'})[0] in (502, 503)
            print('Apache VirtualHost: TLS, exact update bytes, branding exclusion, redirects and proxy routing passed')
        finally:
            subprocess.run(['docker', 'stop', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.wait(timeout=30)


if __name__ == '__main__':
    main()

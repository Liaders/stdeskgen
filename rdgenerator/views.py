import io
from pathlib import Path
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_protect
from .local_build import LocalBuildError, dispatch_local, collect_images, local_status, recent_local_builds, get_local_record
from django.shortcuts import render, get_object_or_404
from django.core.files.base import ContentFile
import os
import secrets
import re
import requests
import base64
import json
import uuid
import pyzipper
from django.conf import settings as _settings
from django.db.models import Q
from .forms import GenerateForm
from customization.profile import validate_profile
from .models import GithubRun
from PIL import Image
from urllib.parse import quote

# get_png, download and save_custom_client build file paths from request values;
# only accept a UUID and a plain file name so "../" or absolute paths cannot escape png/ and exe/.
_UUID_RE = re.compile(r'^[0-9a-fA-F-]{36}$')
_NAME_RE = re.compile(r'^[\w.-]+$')

def _safe_parts(uuid_val, filename):
    if not uuid_val or not _UUID_RE.match(uuid_val):
        return False
    if filename is not None and (not _NAME_RE.match(filename) or filename.startswith('.')):
        return False
    return True


def generate_custom_client(params, full_url):
    """
    Core generation logic shared by web form and JSON API.

    Args:
        params: dict containing all configuration fields (keys match GenerateForm field names)
        full_url: the full URL of this service (protocol + host)

    Returns:
        dict with 'success' key. On success: also includes 'uuid', 'filename', 'platform', 'log_url'.
        On failure: includes 'error' and optionally 'status_code'.
    """
    user_secret = params.get('sh_secret_field', '')
    selfhosted = (_settings.SH_SECRET == user_secret)
    platform = params.get('platform', 'windows')
    version = params.get('version', '1.5.0')
    try:
        ui_profile = validate_profile(params.get('ui_profile'), version, platform, selfhosted)
    except ValueError as exc:
        return {'success': False, 'error': str(exc), 'status_code': 400}
    local_mode = _settings.LOCAL_GITHUB_BUILD
    if local_mode and (platform not in ('windows', 'windows-x86', 'linux', 'macos', 'android') or version not in ('1.5.0','1.5.1') or params.get('sh_secret_field')):
        return {'success': False, 'error': 'Local GitHub builds support Windows, Linux, macOS and Android with RustDesk 1.5.0/1.5.1.', 'status_code': 400}
    from updates.config import validate as validate_update_config
    try:
        raw_updates = params.get('updates_config')
        if params.get('auto_update_enabled') is False:
            raw_updates = None
        elif local_mode and not raw_updates and platform in ('windows','windows-x86') and version in ('1.5.0','1.5.1') and params.get('installation', 'installationY') == 'installationY' and params.get('direction', 'both') != 'outgoing' and not selfhosted and not params.get('update_public_key'):
            raw_updates = {'base_url':'https://desk.status16.ru/client', 'product':'statusdesk', 'channel':'stable', 'revision':1}
        updates_config = validate_update_config(raw_updates, version, platform)
        if updates_config and (selfhosted or params.get('update_public_key')):
            raise ValueError('Use StatusDesk updates without the legacy update patch or self-hosted generator mode')
        if updates_config and params.get('installation') == 'installationN':
            raise ValueError('Auto updates require an installable Windows client')
        if updates_config and params.get('direction') == 'outgoing':
            raise ValueError('Auto updates currently require an incoming-capable Windows service')
    except ValueError as exc:
        return {'success': False, 'error': str(exc), 'status_code': 400}
    app_version = params.get('app_version', '')
    if params.get('build_number') not in (None, ''):
        app_version = version + '.' + str(params['build_number'])
    # app_version overrides the version string embedded in the built client
    # without changing the git tag that version selects. If left empty, the
    # RustDesk build's own version (from the checked-out tag) is used.
    delayFix = params.get('delayFix', True)
    xOffline = params.get('xOffline', False)
    hidecm = params.get('hidecm', False)
    removeNewVersionNotif = params.get('removeNewVersionNotif', False)
    update_public_key = params.get('update_public_key', '')
    # If a custom update public key is provided, force the "remove new version
    # notification" behaviour off so the client keeps checking for updates via
    # the self-hosted update URL instead.
    if update_public_key:
        removeNewVersionNotif = False
    server = params.get('serverIP', '')
    serverPort = params.get('serverPort', '')
    key = params.get('key', '')
    apiServer = params.get('apiServer', '')
    urlLink = params.get('urlLink', '')
    downloadLink = params.get('downloadLink', '')
    if not server:
        server = 'rs-ny.rustdesk.com' #default rustdesk server
    if not serverPort:
        serverPort = '21116' #default rustdesk rendezvous port
    if not key:
        key = 'OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=' #default rustdesk key
    if not apiServer:
        apiServer = server+":21114"
    if not urlLink:
        urlLink = "https://rustdesk.com"
    if not downloadLink:
        downloadLink = "https://desk.status16.ru/client/" if updates_config else "https://rustdesk.com/download"
    direction = params.get('direction', 'both')
    installation = params.get('installation', 'installationY')
    settings = params.get('settings', 'settingsY')
    appname_display = params.get('appname', '')
    if not appname_display:
        appname_display = "StatusDesk" if local_mode and platform == "android" else "rustdesk"
    appname = re.sub(r"[:|\\/]", "", appname_display).replace(" ", "")
    filename = params.get('exename', 'rustdesk')
    compname = params.get('compname', '')
    if not compname:
        compname = "Purslane Ltd"
    androidappid = params.get('androidappid', '')
    if local_mode and platform == "android" and androidappid in ("", "com.carriez.flutter_hbb"):
        androidappid = "ru.status16.statusdesk"
    elif not androidappid:
        androidappid = "com.carriez.flutter_hbb"
    compname = compname.replace("&","\\&")
    permPass = params.get('permanentPassword', '')
    theme = 'system' if platform == 'windows-x86' else params.get('theme', 'system')
    themeDorO = params.get('themeDorO', 'default')
    passApproveMode = params.get('passApproveMode', 'password-click')
    denyLan = params.get('denyLan', False)
    enableDirectIP = params.get('enableDirectIP', False)
    autoClose = params.get('autoClose', False)
    permissionsDorO = params.get('permissionsDorO', 'default')
    permissionsType = params.get('permissionsType', 'custom')
    enableKeyboard = params.get('enableKeyboard', True)
    enableClipboard = params.get('enableClipboard', True)
    enableFileTransfer = params.get('enableFileTransfer', True)
    enableAudio = params.get('enableAudio', True)
    enableTCP = params.get('enableTCP', True)
    enableRemoteRestart = params.get('enableRemoteRestart', True)
    enableRecording = params.get('enableRecording', True)
    enableBlockingInput = params.get('enableBlockingInput', True)
    enableRemoteModi = params.get('enableRemoteModi', False)
    removeWallpaper = params.get('removeWallpaper', True)
    defaultManual = params.get('defaultManual', '')
    overrideManual = params.get('overrideManual', '')
    enablePrinter = params.get('enablePrinter', True)
    enableCamera = params.get('enableCamera', True)
    enableTerminal = params.get('enableTerminal', True)

    if all(char.isascii() for char in filename):
        filename = re.sub(r'[^\w\s-]', '_', filename).strip()
        filename = filename.replace(" ","_")
    else:
        filename = "rustdesk"
    if not all(char.isascii() for char in appname):
        appname = "rustdesk"
    myuuid = str(uuid.uuid4())

    if local_mode:
        try:
            image_params = params if platform != 'windows-x86' else {k:v for k,v in params.items() if k not in ('privacyfile','privacybase64')}
            local_images = collect_images(image_params)
        except LocalBuildError as exc:
            return {'success': False, 'error': str(exc), 'status_code': 400}
        iconlink_url = 'local' if 'icon.png' in local_images else 'false'
        # The legacy x86 client uses the light logo regardless of its settings.
        if platform == 'windows-x86' and 'logo_light.png' in local_images:
            local_images['logo.png'] = local_images['logo_light.png']
        if platform == 'windows-x86':
            local_images.pop('logo_light.png', None)
            local_images.pop('logo_dark.png', None)
        logolink_url = 'local' if any(name in local_images for name in ('logo.png','logo_light.png','logo_dark.png')) else 'false'
        privacylink_url = 'local' if 'privacy.png' in local_images else 'false'
        iconlink_uuid = iconlink_file = logolink_uuid = logolink_file = privacylink_uuid = privacylink_file = 'false'
    else:
        try:
            iconfile = params.get('iconfile')
            if not iconfile:
                iconfile = params.get('iconbase64')
            iconlink_url, iconlink_uuid, iconlink_file = save_png(iconfile,myuuid,full_url,"icon.png")
        except:
            print("failed to get icon, using default")
            iconlink_url = "false"
            iconlink_uuid = "false"
            iconlink_file = "false"
        try:
            logofile = params.get('logofile')
            if not logofile:
                logofile = params.get('logobase64')
            logolink_url, logolink_uuid, logolink_file = save_png(logofile,myuuid,full_url,"logo.png")
        except:
            print("failed to get logo")
            logolink_url = "false"
            logolink_uuid = "false"
            logolink_file = "false"
        try:
            privacyfile = params.get('privacyfile')
            if not privacyfile:
                privacyfile = params.get('privacybase64')
            privacylink_url, privacylink_uuid, privacylink_file = save_png(privacyfile,myuuid,full_url,"privacy.png")
        except:
            print("failed to get logo")
            privacylink_url = "false"
            privacylink_uuid = "false"
            privacylink_file = "false"

    ###create the custom.txt json here and send in as inputs below
    decodedCustom = {}
    if direction != "Both":
        decodedCustom['conn-type'] = direction
    if installation == "installationN":
        decodedCustom['disable-installation'] = 'Y'
    if settings == "settingsN":
        decodedCustom['disable-settings'] = 'Y'
    if appname.upper != "rustdesk".upper and appname != "":
        decodedCustom['app-name'] = appname_display
    decodedCustom['override-settings'] = {}
    decodedCustom['default-settings'] = {}
    if permPass != "":
        decodedCustom['password'] = permPass
    if theme != "system":
        if themeDorO == "default":
            if platform == "windows-x86":
                decodedCustom['default-settings']['allow-darktheme'] = 'Y' if theme == "dark" else 'N'
            else:
                decodedCustom['default-settings']['theme'] = theme
        elif themeDorO == "override":
            if platform == "windows-x86":
                decodedCustom['override-settings']['allow-darktheme'] = 'Y' if theme == "dark" else 'N'
            else:
                decodedCustom['override-settings']['theme'] = theme
    decodedCustom['enable-lan-discovery'] = 'N' if denyLan else 'Y'
    #decodedCustom['direct-server'] = 'Y' if enableDirectIP else 'N'
    decodedCustom['allow-auto-disconnect'] = 'Y' if autoClose else 'N'

    if permissionsDorO == "default":
        decodedCustom['default-settings']['access-mode'] = permissionsType
        decodedCustom['default-settings']['enable-keyboard'] = 'Y' if enableKeyboard else 'N'
        decodedCustom['default-settings']['enable-clipboard'] = 'Y' if enableClipboard else 'N'
        decodedCustom['default-settings']['enable-file-transfer'] = 'Y' if enableFileTransfer else 'N'
        decodedCustom['default-settings']['enable-audio'] = 'Y' if enableAudio else 'N'
        decodedCustom['default-settings']['enable-tunnel'] = 'Y' if enableTCP else 'N'
        decodedCustom['default-settings']['enable-remote-restart'] = 'Y' if enableRemoteRestart else 'N'
        decodedCustom['default-settings']['enable-record-session'] = 'Y' if enableRecording else 'N'
        decodedCustom['default-settings']['enable-block-input'] = 'Y' if enableBlockingInput else 'N'
        decodedCustom['default-settings']['allow-remote-config-modification'] = 'Y' if enableRemoteModi else 'N'
        decodedCustom['default-settings']['direct-server'] = 'Y' if enableDirectIP else 'N'
        decodedCustom['default-settings']['verification-method'] = 'use-permanent-password' if hidecm else 'use-both-passwords'
        decodedCustom['default-settings']['approve-mode'] = passApproveMode
        decodedCustom['default-settings']['allow-hide-cm'] = 'Y' if hidecm else 'N'
        decodedCustom['default-settings']['allow-remove-wallpaper'] = 'Y' if removeWallpaper else 'N'
        decodedCustom['default-settings']['enable-remote-printer'] = 'Y' if enablePrinter else 'N'
        decodedCustom['default-settings']['enable-camera'] = 'Y' if enableCamera else 'N'
        decodedCustom['default-settings']['enable-terminal'] = 'Y' if enableTerminal else 'N'
        

    else:
        decodedCustom['override-settings']['access-mode'] = permissionsType
        decodedCustom['override-settings']['enable-keyboard'] = 'Y' if enableKeyboard else 'N'
        decodedCustom['override-settings']['enable-clipboard'] = 'Y' if enableClipboard else 'N'
        decodedCustom['override-settings']['enable-file-transfer'] = 'Y' if enableFileTransfer else 'N'
        decodedCustom['override-settings']['enable-audio'] = 'Y' if enableAudio else 'N'
        decodedCustom['override-settings']['enable-tunnel'] = 'Y' if enableTCP else 'N'
        decodedCustom['override-settings']['enable-remote-restart'] = 'Y' if enableRemoteRestart else 'N'
        decodedCustom['override-settings']['enable-record-session'] = 'Y' if enableRecording else 'N'
        decodedCustom['override-settings']['enable-block-input'] = 'Y' if enableBlockingInput else 'N'
        decodedCustom['override-settings']['allow-remote-config-modification'] = 'Y' if enableRemoteModi else 'N'
        decodedCustom['override-settings']['direct-server'] = 'Y' if enableDirectIP else 'N'
        decodedCustom['override-settings']['verification-method'] = 'use-permanent-password' if hidecm else 'use-both-passwords'
        decodedCustom['override-settings']['approve-mode'] = passApproveMode
        decodedCustom['override-settings']['allow-hide-cm'] = 'Y' if hidecm else 'N'
        decodedCustom['override-settings']['allow-remove-wallpaper'] = 'Y' if removeWallpaper else 'N'
        decodedCustom['override-settings']['enable-remote-printer'] = 'Y' if enablePrinter else 'N'
        decodedCustom['override-settings']['enable-camera'] = 'Y' if enableCamera else 'N'
        decodedCustom['override-settings']['enable-terminal'] = 'Y' if enableTerminal else 'N'
        if direction == 'incoming':
            decodedCustom['override-settings']['custom-rendezvous-server'] = server
            decodedCustom['override-settings']['api-server'] = apiServer

    if defaultManual:
        for line in defaultManual.splitlines():
            if '=' in line:
                k, value = line.split('=', 1)
                decodedCustom['default-settings'][k.strip()] = value.strip()

    if overrideManual:
        for line in overrideManual.splitlines():
            if '=' in line:
                k, value = line.split('=', 1)
                decodedCustom['override-settings'][k.strip()] = value.strip()
    
    if updates_config:
        decodedCustom['default-settings'].setdefault('allow-auto-update', 'Y')
    elif local_mode and platform in ('windows','windows-x86') and params.get('auto_update_enabled') is False:
        decodedCustom['override-settings']['allow-auto-update'] = 'N'
    decodedCustomJson = json.dumps(decodedCustom)

    string_bytes = decodedCustomJson.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    encodedCustom = base64_bytes.decode("ascii")

    ####from here run the github action, we need user, repo, access token.
    if platform == 'windows':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows.yml/dispatches'
        if selfhosted:
            url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/sh-generator-windows.yml/dispatches'
    if platform == 'windows-x86':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows-x86.yml/dispatches'
    elif platform == 'linux':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-linux.yml/dispatches'
    elif platform == 'android':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-android.yml/dispatches'
    elif platform == 'macos':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-macos.yml/dispatches'
    else:
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows.yml/dispatches'
        if selfhosted:
            url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/sh-generator-windows.yml/dispatches'

    inputs_raw = {
        "server":server,
        "serverPort":serverPort,
        "key":key,
        "apiServer":apiServer,
        "custom":encodedCustom,
        "uuid":myuuid,
        "iconlink_url":iconlink_url,
        "iconlink_uuid":iconlink_uuid,
        "iconlink_file":iconlink_file,
        "logolink_url":logolink_url,
        "logolink_uuid":logolink_uuid,
        "logolink_file":logolink_file,
        "privacylink_url":privacylink_url,
        "privacylink_uuid":privacylink_uuid,
        "privacylink_file":privacylink_file,
        "appname":appname,
        "genurl":_settings.GENURL,
        "urlLink":urlLink,
        "downloadLink":downloadLink,
        "delayFix": 'true' if delayFix else 'false',
        "rdgen":'true',
        "xOffline": 'true' if xOffline else 'false',
        "removeNewVersionNotif": 'true' if removeNewVersionNotif else 'false',
        "update_public_key": update_public_key,
        "compname": compname,
        "androidappid":androidappid,
        "filename":filename
    }

    if platform=='android': inputs_raw['android_architecture']=params.get('android_architecture') or 'all'
    if updates_config:
        inputs_raw['stdesk_update_b64'] = base64.b64encode(json.dumps(updates_config).encode('utf-8')).decode('ascii')
    if ui_profile is not None:
        inputs_raw['ui_profile_b64'] = base64.b64encode(json.dumps(ui_profile).encode('utf-8')).decode('ascii')

    if local_mode:
        try:
            return dispatch_local(inputs_raw, local_images, version, app_version, platform=platform)
        except LocalBuildError as exc:
            return {'success': False, 'error': str(exc), 'status_code': 502}

    temp_json_path = f"data_{uuid.uuid4()}.json"
    zip_filename = f"secrets_{uuid.uuid4()}.zip"
    zip_path = "temp_zips/%s" % (zip_filename)
    Path("temp_zips").mkdir(parents=True, exist_ok=True)

    with open(temp_json_path, "w") as f:
        json.dump(inputs_raw, f)

    with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(_settings.ZIP_PASSWORD.encode())
        zf.write(temp_json_path, arcname="secrets.json")

    if os.path.exists(temp_json_path):
        os.remove(temp_json_path)

    zipJson = {}
    zipJson['url'] = full_url
    zipJson['file'] = zip_filename

    zip_url = json.dumps(zipJson)

    data = {
        "ref":_settings.GHBRANCH,
        "inputs":{
            "version":version,
            "app_version":app_version,
            "zip_url":zip_url
        },
        "return_run_details": True
    } 
    headers = {
        'Accept':  'application/vnd.github+json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+_settings.GHBEARER,
        'X-GitHub-Api-Version': '2026-03-10'
    }
    new_github_run = GithubRun(
        uuid=myuuid,
        status="Starting generator...please wait"
    )
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 204 or response.status_code == 200:
            github_data = response.json()
            print(github_data)
            new_github_run.github_run_id = github_data.get('workflow_run_id')
            new_github_run.status = "in_progress"
            new_github_run.save()

            return {
                "success": True,
                "uuid": myuuid,
                "filename": filename,
                "platform": platform,
                "log_url": github_data.get('html_url')
            }
        else:
            return {
                "success": False,
                "error": "GitHub rejected the start request",
                "status_code": 500
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}",
            "status_code": 500
        }


def _get_run_status(uuid_val):
    """
    Core status-check logic shared by web form and JSON API.

    Args:
        uuid_val: the UUID string of the generation run

    Returns:
        dict with 'found', 'status', 'github_log_url', and optionally 'gh_run'.
        If not found, 'found' is False.
    """
    try:
        gh_run = GithubRun.objects.get(uuid=uuid_val)
    except GithubRun.DoesNotExist:
        return {"found": False}

    github_log_url = f"https://github.com/{_settings.GHUSER}/{_settings.REPONAME}/actions/runs/{gh_run.github_run_id}"

    if gh_run.status not in ['success', 'failure', 'cancelled', 'timed_out', 'skipped']:
        headers = {
            "Authorization": f"Bearer {_settings.GHBEARER}",
            "Accept": "application/vnd.github+json"
        }
        api_url = f"https://api.github.com/repos/{_settings.GHUSER}/{_settings.REPONAME}/actions/runs/{gh_run.github_run_id}"
        
        try:
            gh_response = requests.get(api_url, headers=headers)
            if gh_response.status_code == 200:
                gh_data = gh_response.json()
                
                if gh_data['status'] == 'completed':
                    gh_run.status = gh_data['conclusion']
                    gh_run.save()
        except Exception as e:
            print(f"Error checking GitHub: {e}")

    return {
        "found": True,
        "status": gh_run.status,
        "github_log_url": github_log_url,
        "gh_run": gh_run
    }


@csrf_protect
def generator_view(request):
    if _settings.LOCAL_GITHUB_BUILD and request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1'):
        return HttpResponseForbidden('Local constructor only.')
    if _settings.LOCAL_GITHUB_BUILD:
        from .build_monitor import start
        start()
    if request.method == 'POST':
        batch = _settings.LOCAL_GITHUB_BUILD and request.POST.get('build_scope') == 'all'
        posted = request.POST.copy()
        if batch:
            posted['platform'] = 'windows'
            posted['ui_profile'] = posted.get('batch_ui_profile', posted.get('ui_profile', ''))
            posted['auto_update_enabled'] = posted.get('batch_auto_update_enabled', '')
        form = GenerateForm(posted, request.FILES)
        if form.is_valid():
            params = form.cleaned_data
            full_url = f"{_settings.PROTOCOL}://{request.get_host()}" if _settings.GENURL else f"{_settings.PROTOCOL}://{request.get_host()}"
            if batch:
                from .batch_build import build_all
                builds = build_all(params, full_url)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'builds': builds, 'success': all(b['success'] for b in builds)})
                return render(request, 'build_batch.html', {'builds': builds})
            result = generate_custom_client(params, full_url)
            if result['success']:
                if result.get('local_build'):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse(result)
                    return render(request, 'local_waiting.html', result)
                return render(request, 'waiting.html', {
                    'filename': result['filename'],
                    'uuid': result['uuid'],
                    'status': "Starting generator...please wait",
                    'platform': result['platform'],
                    'log_url': result['log_url']
                })
            else:
                if _settings.LOCAL_GITHUB_BUILD:
                    form.add_error(None, result['error'])
                else:
                    return JsonResponse({"error": result['error']}, status=result.get('status_code', 500))
    else:
        form = GenerateForm()
    #return render(request, 'maintenance.html')
    default_config = None
    default_config_error = ''
    if _settings.LOCAL_GITHUB_BUILD and request.method == 'GET':
        from .default_config import load
        try: default_config = load()
        except (OSError, ValueError) as exc: default_config_error = 'Не удалось прочитать default-config.json: ' + str(exc)
    if _settings.LOCAL_GITHUB_BUILD and request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Проверьте параметры конфигурации.', 'fields': form.errors.get_json_data()}, status=400)
    return render(request, 'generator.html', {'form': form, 'local_constructor': _settings.LOCAL_GITHUB_BUILD, 'default_config': default_config, 'default_config_error': default_config_error})


def _expected_files_for_platform(filename, platform):
    """Return the list of expected output filenames for a given platform."""
    if platform == 'windows':
        return [f"{filename}.exe", f"{filename}.msi"]
    elif platform == 'windows-x86':
        return [f"{filename}.exe"]
    elif platform == 'linux':
        return [
            f"{filename}-x86_64.deb",
            f"{filename}-unattended-wayland-x86_64.deb",
            f"{filename}-x86_64.rpm",
            f"{filename}-suse-x86_64.rpm",
            f"{filename}-x86_64.pkg.tar.zst",
            f"{filename}-aarch64.deb",
            f"{filename}-aarch64.rpm",
            f"{filename}-suse-aarch64.rpm",
            f"{filename}-aarch64.pkg.tar.zst",
            f"{filename}-x86_64.AppImage",
            f"{filename}-aarch64.AppImage",
            f"{filename}-x86_64.flatpak",
            f"{filename}-aarch64.flatpak",
        ]
    elif platform == 'android':
        return [
            f"{filename}-aarch64.apk",
            f"{filename}-x86_64.apk",
            f"{filename}-armv7.apk",
        ]
    elif platform == 'macos':
        return [
            f"{filename}-x86_64.dmg",
            f"{filename}-aarch64.dmg",
        ]
    return []


def check_for_file(request):
    filename = request.GET.get('filename')
    uuid = request.GET.get('uuid')
    platform = request.GET.get('platform')

    result = _get_run_status(uuid)
    if not result['found']:
        from django.http import Http404
        raise Http404("Run not found")

    gh_run = result['gh_run']
    github_log_url = result['github_log_url']

    if gh_run.status == "success":
        expected = _expected_files_for_platform(filename, platform)
        existing_files = []
        missing_files = []
        for f in expected:
            file_path = os.path.join('exe', uuid, f)
            if os.path.isfile(file_path):
                existing_files.append(f)
            else:
                missing_files.append(f)

        return render(request, 'generated.html', {
            'filename': filename,
            'uuid': uuid,
            'platform': platform,
            'existing_files': existing_files,
            'missing_files': missing_files,
            'github_log_url': github_log_url,
        })
        
    elif gh_run.status in ['failure', 'cancelled', 'timed_out', 'skipped', 'action_required']:
        return render(request, 'failure.html', {
            'log_url': github_log_url, 
            'filename': filename, 
            'uuid': uuid, 
            'platform': platform,
            'status': gh_run.status
        })
        
    else:
        return render(request, 'waiting.html', {
            'filename': filename, 
            'uuid': uuid, 
            'status': gh_run.status, 
            'platform': platform, 
            'log_url': github_log_url
        })

def download(request):
    filename = request.GET['filename']
    uuid = request.GET['uuid']
    if not _safe_parts(uuid, filename):
        return HttpResponseForbidden("Invalid filename")
    file_path = os.path.join('exe', uuid, filename)
    with open(file_path, 'rb') as file:
        content = file.read()
    response = HttpResponse(content, headers={
        'Content-Type': 'application/vnd.microsoft.portable-executable',
        'Content-Disposition': f'attachment; filename="{filename}"'
    })
    return response

def get_png(request):
    filename = request.GET['filename']
    uuid = request.GET['uuid']
    if not _safe_parts(uuid, filename):
        return HttpResponseForbidden("Invalid filename")
    file_path = os.path.join('png',uuid,filename)
    with open(file_path, 'rb') as file:
        response = HttpResponse(file, headers={
            'Content-Type': 'application/vnd.microsoft.portable-executable',
            'Content-Disposition': f'attachment; filename="{filename}"'
        })

    return response

def create_github_run(myuuid):
    new_github_run = GithubRun(
        uuid=myuuid,
        status="Starting generator...please wait"
    )
    new_github_run.save()

def update_github_run(request):
    data = json.loads(request.body)
    myuuid = data.get('uuid')
    mystatus = data.get('status')
    GithubRun.objects.filter(Q(uuid=myuuid)).update(status=mystatus)
    return HttpResponse('')

def resize_and_encode_icon(imagefile):
    maxWidth = 200
    try:
        with io.BytesIO() as image_buffer:
            for chunk in imagefile.chunks():
                image_buffer.write(chunk)
            image_buffer.seek(0)

            img = Image.open(image_buffer)
            imgcopy = img.copy()
    except (IOError, OSError):
        raise ValueError("Uploaded file is not a valid image format.")

    # Check if resizing is necessary
    if img.size[0] <= maxWidth:
        with io.BytesIO() as image_buffer:
            imgcopy.save(image_buffer, format=imagefile.content_type.split('/')[1])
            image_buffer.seek(0)
            return_image = ContentFile(image_buffer.read(), name=imagefile.name)
        return base64.b64encode(return_image.read())

    # Calculate resized height based on aspect ratio
    wpercent = (maxWidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))

    # Resize the image while maintaining aspect ratio using LANCZOS resampling
    imgcopy = imgcopy.resize((maxWidth, hsize), Image.Resampling.LANCZOS)

    with io.BytesIO() as resized_image_buffer:
        imgcopy.save(resized_image_buffer, format=imagefile.content_type.split('/')[1])
        resized_image_buffer.seek(0)

        resized_imagefile = ContentFile(resized_image_buffer.read(), name=imagefile.name)

    # Return the Base64 encoded representation of the resized image
    resized64 = base64.b64encode(resized_imagefile.read())
    #print(resized64)
    return resized64
 
#the following is used when accessed from an external source, like the rustdesk api server
def startgh(request):
    #print(request)
    data_ = json.loads(request.body)
    ####from here run the github action, we need user, repo, access token.
    url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-'+data_.get('platform')+'.yml/dispatches'  
    data = {
        "ref": _settings.GHBRANCH,
        "inputs":{
            "server":data_.get('server'),
            "key":data_.get('key'),
            "apiServer":data_.get('apiServer'),
            "custom":data_.get('custom'),
            "uuid":data_.get('uuid'),
            "iconlink":data_.get('iconlink'),
            "logolink":data_.get('logolink'),
            "appname":data_.get('appname'),
            "extras":data_.get('extras'),
            "filename":data_.get('filename')
        }
    } 
    headers = {
        'Accept':  'application/vnd.github+json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+_settings.GHBEARER,
        'X-GitHub-Api-Version': '2026-03-10'
    }
    response = requests.post(url, json=data, headers=headers)
    print(response)
    return HttpResponse(status=204)

def save_png(file, uuid, domain, name):
    file_save_path = "png/%s/%s" % (uuid, name)
    Path("png/%s" % uuid).mkdir(parents=True, exist_ok=True)

    if isinstance(file, str):  # Check if it's a base64 string
        try:
            header, encoded = file.split(';base64,')
            decoded_img = base64.b64decode(encoded)
            file = ContentFile(decoded_img, name=name) # Create a file-like object
        except ValueError:
            print("Invalid base64 data")
            return None  # Or handle the error as you see fit
        except Exception as e:  # Catch general exceptions during decoding
            print(f"Error decoding base64: {e}")
            return None
        
    with open(file_save_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)
    # imageJson = {}
    # imageJson['url'] = domain
    # imageJson['uuid'] = uuid
    # imageJson['file'] = name
    #return "%s/%s" % (domain, file_save_path)
    return domain, uuid, name

def save_custom_client(request):
    file = request.FILES['file']
    myuuid = request.POST.get('uuid')
    if not _safe_parts(myuuid, file.name):
        return HttpResponseForbidden("Invalid filename")
    file_save_path = "exe/%s/%s" % (myuuid, file.name)
    Path("exe/%s" % myuuid).mkdir(parents=True, exist_ok=True)
    with open(file_save_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)

    return HttpResponse("File saved successfully!")

def cleanup_secrets(request):
    # Pass the UUID as a query param or in JSON body
    data = json.loads(request.body)
    my_uuid = data.get('uuid')
    
    if not my_uuid:
        return HttpResponse("Missing UUID", status=400)

    # 1. Find the files in your temp directory matching the UUID
    temp_dir = os.path.join('temp_zips')
    
    # We look for any file starting with 'secrets_' and containing the uuid
    for filename in os.listdir(temp_dir):
        if my_uuid in filename and filename.endswith('.zip'):
            file_path = os.path.join(temp_dir, filename)
            try:
                os.remove(file_path)
                print(f"Successfully deleted {file_path}")
            except OSError as e:
                print(f"Error deleting file: {e}")

    return HttpResponse("Cleanup successful", status=200)

def get_zip(request):
    filename = request.GET['filename']
    base_dir = os.path.abspath('temp_zips')
    file_path = os.path.abspath(os.path.join(base_dir, filename))
    if not file_path.startswith(base_dir + os.sep):
        return HttpResponseForbidden("Invalid filename")
    with open(file_path, 'rb') as file:
        response = HttpResponse(file, headers={
            'Content-Type': 'application/vnd.microsoft.portable-executable',
            'Content-Disposition': f'attachment; filename="{filename}"'
        })

    return response




def local_build_status_view(request, build_id):
    if request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1'):
        return HttpResponseForbidden('Local constructor only.')
    try:
        from .build_monitor import start
        start()
        record = get_local_record(build_id)
        return JsonResponse({key: record.get(key) for key in ('id','status','conclusion','log_url','cleaned','download_status','download_error','download_directory')})
    except LocalBuildError as exc:
        return JsonResponse({'error': str(exc)}, status=502)


def local_build_page(request, build_id):
    if request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1'):
        return HttpResponseForbidden('Local constructor only.')
    try:
        record = get_local_record(build_id)
        return render(request, 'local_waiting.html', {'uuid': record['id'], 'log_url': record['log_url']})
    except LocalBuildError:
        return HttpResponse('Build not found.', status=404)

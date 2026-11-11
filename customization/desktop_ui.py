"""Stage the shared account header and only explicitly requested Slim UI."""
from desktop_account import apply as apply_account


def apply(root, profile=None):
    profile = profile or {}
    if 'slim_ui' in profile and type(profile['slim_ui']) is not bool:
        raise ValueError('slim_ui must be boolean')
    if profile.get('slim_ui', False):
        from slim_ui import apply as apply_slim_ui
        apply_slim_ui(root)
    apply_account(root)

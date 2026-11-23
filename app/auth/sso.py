# -*- coding: utf-8 -*-
"""General OpenID Connect single sign-on configuration. """
from authlib.integrations.flask_client import OAuth

import config


oauth = OAuth()
PROVIDER_KEY = 'sso'


def available() -> bool:
    """Show the SSO entry point only when SSO is enabled and required settings are complete. """
    return bool(
        config.SSO_ENABLED
        and config.SSO_DISCOVERY_URL
        and config.SSO_CLIENT_ID
        and config.SSO_CLIENT_SECRET
    )


def init_app(app) -> None:
    """Register the OIDC client using the current configuration. """
    if not config.SSO_ENABLED:
        return
    oauth.init_app(app)
    if not available():
        app.logger.warning('SSO is enabled but configuration is incomplete; the SSO entry point will not be enabled')
        return

    client_kwargs = {
        'scope': config.SSO_SCOPE,
        'token_endpoint_auth_method': config.SSO_TOKEN_AUTH_METHOD,
    }
    if config.SSO_USE_PKCE:
        client_kwargs['code_challenge_method'] = 'S256'

    oauth.register(
        name=PROVIDER_KEY,
        client_id=config.SSO_CLIENT_ID,
        client_secret=config.SSO_CLIENT_SECRET,
        server_metadata_url=config.SSO_DISCOVERY_URL,
        client_kwargs=client_kwargs,
    )

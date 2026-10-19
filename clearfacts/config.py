GRAPHQL_URL = "https://api.clearfacts.be/graphql"

OIDC_ISSUER = "https://login.clearfacts.be"
OIDC_AUTHORIZE = f"{OIDC_ISSUER}/oauth2-server/authorize"
OIDC_TOKEN = f"{OIDC_ISSUER}/oauth2-server/token"
OIDC_USERINFO = f"{OIDC_ISSUER}/oauth2-server/userinfo"
OIDC_JWKS = f"{OIDC_ISSUER}/oauth2-server/jwks.json"
OIDC_DISCOVERY = f"{OIDC_ISSUER}/.well-known/openid-configuration"

ALL_SCOPES = [
    "openid", "email", "profile",
    "accountant", "statistics", "read_administrations",
    "associate_read", "associate_actions",
    "journal_read", "contact_read", "upload_document",
    "archive_read", "archive_actions", "archive",
]

DEFAULT_TIMEOUT = 30

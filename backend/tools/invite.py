"""Invite people to Carta Magna. Sign-ups are disabled, so this is the only way in.

    python -m tools.invite ada@example.com bob@example.com   # Supabase emails each invite
    python -m tools.invite ada@example.com --link-only        # print the link instead, to send yourself

Needs SUPABASE_URL and SUPABASE_SECRET_KEY (a server-side "secret" API key from
the Supabase dashboard). Keep the secret key on your machine: never deploy it.
SITE_URL sets where the link lands (default: the production site).

People who already have an account get an error from --link-only invites, so
for them it prints a one-time sign-in link instead. They can also request one
themselves on the sign-in page.
"""
import argparse
import logging
import sys

import httpx

from app.config import get_settings

log = logging.getLogger("tools.invite")


class InviteFailed(Exception):
    pass


def _client() -> httpx.Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise InviteFailed("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
    key = settings.supabase_secret_key
    return httpx.Client(
        base_url=f"{settings.supabase_url}/auth/v1",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=30,
    )


def _error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    return body.get("msg") or body.get("message") or body.get("error_description") or f"HTTP {response.status_code}"


def send_invite(client: httpx.Client, email: str, site_url: str) -> None:
    """Supabase creates the user and emails them an invite link."""
    response = client.post("/invite", params={"redirect_to": site_url}, json={"email": email})
    if response.status_code >= 400:
        raise InviteFailed(f"{email}: {_error(response)}")
    log.info("Invite emailed to %s", email)


def invite_link(client: httpx.Client, email: str, site_url: str) -> str:
    """An invite link for a new user, or a sign-in link for an existing one. Sends no email."""
    for link_type in ("invite", "magiclink"):
        response = client.post(
            "/admin/generate_link", json={"type": link_type, "email": email, "redirect_to": site_url}
        )
        if response.status_code < 400:
            return response.json()["action_link"]
        if response.status_code != 422:  # 422: the user already exists
            break
    raise InviteFailed(f"{email}: {_error(response)}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("emails", nargs="+", metavar="EMAIL")
    parser.add_argument("--link-only", action="store_true", help="print the link instead of emailing it")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # httpx logs request URLs at INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    site_url = get_settings().site_url
    failed = 0
    try:
        with _client() as client:
            for email in args.emails:
                try:
                    if args.link_only:
                        print(f"{email}: {invite_link(client, email, site_url)}")
                    else:
                        send_invite(client, email, site_url)
                except InviteFailed as e:
                    log.error("%s", e)
                    failed += 1
    except InviteFailed as e:
        log.error("%s", e)
        sys.exit(1)
    except httpx.TransportError as e:
        log.error("Could not reach Supabase: %s", type(e).__name__)
        sys.exit(1)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

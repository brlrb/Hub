import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

from hub.client.config import REPORTING_CONFIG_FILE_PATH
from hub.util.bugout_token import BUGOUT_TOKEN
from humbug.consent import HumbugConsent
from humbug.report import HumbugReporter


def save_reporting_config(
    consent: bool, client_id: Optional[str] = None, username: Optional[str] = None
) -> Dict[str, Any]:
    """Modify reporting config.

    Args:
        consent (bool): Enabling and disabling sending crashes and system report to Activeloop Hub.
        client_id (str, optional): Unique client id.
        username (str, optional): Activeloop username.

    Returns:
        The configuration that it just saved.
    """
    reporting_config = {}

    if os.path.isfile(REPORTING_CONFIG_FILE_PATH):
        try:
            with open(REPORTING_CONFIG_FILE_PATH, "r") as ifp:
                reporting_config = json.load(ifp)
        except Exception:
            pass
    else:
        # We should not expect that the parent directory for the reporting configuration will exist.
        # If it doesn't exist, we create the directory, if possible.
        # This mirrors the code for the `write_token` method in hub/client/utils.py.
        path = Path(REPORTING_CONFIG_FILE_PATH)
        os.makedirs(path.parent, exist_ok=True)

    if client_id is not None and reporting_config.get("client_id") is None:
        reporting_config["client_id"] = client_id

    if reporting_config.get("client_id") is None:
        reporting_config["client_id"] = str(uuid.uuid4())

    if username is not None:
        reporting_config["username"] = username

    reporting_config["consent"] = consent

    try:
        with open(REPORTING_CONFIG_FILE_PATH, "w") as ofp:
            json.dump(reporting_config, ofp)
    except Exception:
        pass

    return reporting_config


def get_reporting_config() -> Dict[str, Any]:
    """Get an existing reporting config"""
    reporting_config: Dict[str, Any] = {"consent": False}
    try:
        if not os.path.exists(REPORTING_CONFIG_FILE_PATH):
            client_id = str(uuid.uuid4())
            reporting_config["client_id"] = client_id
            reporting_config = save_reporting_config(True, client_id)
        else:
            with open(REPORTING_CONFIG_FILE_PATH, "r") as ifp:
                reporting_config = json.load(ifp)
    except Exception:
        # Not being able to load reporting consent should not get in the user's way. We will just
        # return the default reporting_config object in which consent is set to False.
        pass
    return reporting_config


def consent_from_reporting_config_file() -> bool:
    """Get consent settings from the existing reporting config"""
    reporting_config = get_reporting_config()
    return reporting_config.get("consent", False)


session_id = str(uuid.uuid4())
client_id = get_reporting_config().get("client_id")

consent = HumbugConsent(consent_from_reporting_config_file)

hub_reporter = HumbugReporter(
    name="activeloopai/Hub",
    consent=consent,
    client_id=client_id,
    session_id=session_id,
    bugout_token=BUGOUT_TOKEN,
    tags=[],
)

hub_user = get_reporting_config().get("username")
if hub_user is not None:
    hub_reporter.tags.append(f"username:{hub_user}")


def feature_report_path(
    path: str, feature_name: str, parameters: dict, starts_with: str = "hub://"
):
    """Helper function for generating humbug feature reports depending on the path"""
    if path.startswith(starts_with):
        parameters["Path"] = str(path)

    hub_reporter.feature_report(
        feature_name=feature_name, parameters=parameters,
    )

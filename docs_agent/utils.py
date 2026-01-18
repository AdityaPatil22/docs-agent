import logging
import os

logger = logging.getLogger(__name__)


def resolve_file_path(env_name: str, default_path: str) -> str:
    """
    Resolve file path using the following priority:
      1. If ENV var `env_name` is set and points to existing file -> return that path.
      2. Else if default_path exists -> return default_path.
      3. Else raise FileNotFoundError with a helpful message.

    env_name: name of env variable that should contain a full path (including filename).
    default_path: package-default path to fall back to (absolute).
    """
    env_value = os.environ.get(env_name)
    if env_value:
        if os.path.isfile(env_value):
            logger.info("Using %s from ENV: %s", env_name, env_value)
            return env_value
        else:
            logger.warning(
                "env variable %s is set to '%s' but file does not exist. using default",
                env_name,
                env_value,
            )

    # either env not set or file missing -> try default
    if os.path.isfile(default_path):
        logger.info("Using default file: %s", default_path)
        return default_path

    # nothing usable found
    raise FileNotFoundError(
        f"Could not resolve file for {env_name}. "
        f"Tried ENV value: '{env_value}' and default path: '{default_path}'."
    )

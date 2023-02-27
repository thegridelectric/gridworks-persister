"""Settings for a GridWorks Persister, readable from environment and/or from env files."""

from typing import Optional

import pendulum
from gridworks.enums import GNodeRole
from gridworks.gw_config import GNodeSettings
from pydantic import SecretStr


class Settings(GNodeSettings):
    g_node_alias: str = "d1.persister"
    g_node_role_value: str = "Persister"
    my_super_alias: str = "d1.super1"
    g_node_id: str = "8d494cfe-2a45-4279-affb-d54f1b240e7a"
    g_node_instance_id: str = "00000000-0000-0000-0000-000000000000"

    class Config:
        env_prefix = "PER_"
        env_nested_delimiter = "__"

""" Persister """
import functools
import logging
import time
from typing import no_type_check

import pendulum
from gridworks.actor_base import ActorBase
from gridworks.enums import GNodeRole
from gridworks.enums import MessageCategorySymbol
from gridworks.enums import UniverseType
from gridworks.message import as_enum
from gwatn.types import SimTimestep
from gwatn.types import SimTimestep_Maker

from gwp.config import Settings
from gwp.types import HeartbeatA


LOG_FORMAT = (
    "%(levelname) -10s %(sasctime)s %(name) -30s %(funcName) "
    "-35s %(lineno) -5d: %(message)s"
)
LOGGER = logging.getLogger(__name__)


class Persister(ActorBase):
    def __init__(self, settings: Settings):
        super().__init__(settings=settings)
        self.settings: Settings = settings
        self.universe_type = as_enum(
            self.settings.universe_type_value, UniverseType, UniverseType.default()
        )
        self._sim_time: float = self.get_initial_time_s()

    def local_rabbit_startup(self) -> None:
        rjb = MessageCategorySymbol.rjb.value
        tc_alias_lrh = self.settings.time_coordinator_alias.replace(".", "-")
        binding = f"{rjb}.{tc_alias_lrh}.timecoordinator.sim-timestep"

        cb = functools.partial(self.on_timecoordinator_bindok, binding=binding)
        self._consume_channel.queue_bind(
            self.queue_name, "timecoordinatormic_tx", routing_key=binding, callback=cb
        )
        LOGGER.info(
            f"Queue {self.queue_name} bound to timecoordinatormic_tx with {binding} "
        )
        self.strategy_rabbit_startup()

    def strategy_rabbit_startup(self) -> None:
        pass

    @no_type_check
    def on_timecoordinator_bindok(self, _unused_frame, binding) -> None:
        LOGGER.info(f"Queue {self.queue_name} bound with {binding}")

    def time(self) -> float:
        if self.universe_type == UniverseType.Dev:
            return self._sim_time
        else:
            return time.time()

    def get_initial_time_s(self) -> float:
        if self.universe_type == UniverseType.Dev:
            return self.settings.initial_time_unix_s
        else:
            return time.time()

    def prepare_for_death(self) -> None:
        self.actor_main_stopped = True

    ########################
    ## Receives
    ########################

    def route_message(
        self, from_alias: str, from_role: GNodeRole, payload: HeartbeatA
    ) -> None:
        self.payload = payload
        if payload.TypeName == SimTimestep_Maker.type_name:
            try:
                self.timestep_from_timecoordinator(payload)
            except:
                LOGGER.exception("Error in timestep_from_timecoordinator")

    def timestep_from_timecoordinator(self, payload: SimTimestep):
        if self._sim_time == 0:
            self._sim_time = payload.TimeUnixS
            self.new_timestep(payload)
            LOGGER.info(f"TIME STARTED: {self.time_str()}")
        elif self._sim_time < payload.TimeUnixS:
            self._sim_time = payload.TimeUnixS
            self.new_timestep(payload)
            LOGGER.debug(f"Time is now {self.time_str()}")
        elif self._sim_time == payload.TimeUnixS:
            self.repeat_timestep(payload)

    def new_timestep(self, payload: SimTimestep) -> None:
        # LOGGER.info("New timestep in atn_actor_base")
        self._sim_time = payload.TimeUnixS

    def repeat_timestep(self, payload: SimTimestep) -> None:
        # LOGGER.info("Timestep received again in atn_actor_base")
        pass

    def time(self) -> float:
        if self.universe_type == UniverseType.Dev:
            return self._sim_time
        else:
            return time.time()

    def time_str(self) -> str:
        return pendulum.from_timestamp(self.time()).strftime("%m/%d/%Y, %H:%M")

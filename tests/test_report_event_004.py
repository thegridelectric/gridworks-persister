"""report.event 004 restores the three propagation axioms: MessageId is
Report.Id, TimeCreatedMs is Report.MessageCreatedMs, Src is
Report.FromGNodeAlias. The journal decodes 004 strictly, dispatches it to
ReportEventPersistor.persist_v004, keys the messages row by the report's own
id and time, and projects the readings exactly as it does for 003.

The fixture is the newest real spruce report.event 003 payload in the
journal DB on 2026-09-15 with Version set to 004 and the three wrapper
fields propagated from the Report (the deployed spruce scada still emitted
003 that day). Hermetic, no DB."""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from gw_data.db.models import ReadingChannelSql

from gjk.report_event_persistor import ReportEventPersistor
from gjk.sema import SemaCodec
from gjk.sema.base import SemaError
from gjk.sema.enums import SinglePicoState
from gjk.sema.types import ReportEvent

SAMPLES = Path(__file__).parent / "data" / "sample_messages" / "ops329"
FIXTURE = SAMPLES / "spruce-report.event-004-2026-09-15.json"
ALIAS = "hw1.isone.me.versant.keene.spruce.scada"
TA = "hw1.isone.me.versant.keene.spruce.ta"


def _fixture_dict() -> dict:
    return json.loads(FIXTURE.read_text())


def _report_event() -> ReportEvent:
    decoded = SemaCodec().from_dict(_fixture_dict(), auto_upgrade=False)
    assert isinstance(decoded, ReportEvent)
    return decoded


def _channel(name: str, unit: str = "W", unit_type: str = "") -> ReadingChannelSql:
    return ReadingChannelSql(
        id=uuid.uuid4(),
        name=name,
        terminal_asset_alias=TA,
        display_name=name,
        unit=unit,
        unit_type=unit_type,
        channel_type="c",
        deactivated_date=None,
    )


def test_fixture_decodes_strictly_as_004_and_satisfies_the_axioms():
    event = _report_event()
    assert event.version == "004"
    assert event.report.version == "003"
    assert event.message_id == event.report.id
    assert event.time_created_ms == event.report.message_created_ms
    assert event.src == event.report.from_g_node_alias


@pytest.mark.parametrize(
    "field, value",
    [
        ("MessageId", str(uuid.uuid4())),
        ("TimeCreatedMs", 1789494600079),
        ("Src", "hw1.isone.me.versant.keene.beech.scada"),
    ],
)
def test_a_004_wrapper_that_disagrees_with_its_report_is_rejected(field, value):
    d = _fixture_dict()
    d[field] = value
    with pytest.raises(SemaError, match="Propagation"):
        SemaCodec().from_dict(d, auto_upgrade=False)


def test_persist_v004_keys_the_message_by_the_reports_own_id_and_time():
    event = _report_event()
    persistor = ReportEventPersistor(logging.getLogger("test"))
    assert getattr(persistor, f"persist_v{event.version}") == persistor.persist_v004
    info = persistor.persist_v004(ALIAS, datetime.now(tz=UTC), event)
    assert info.id == event.report.id
    assert info.created_at == datetime.fromtimestamp(
        event.report.message_created_ms / 1000, tz=UTC
    )
    assert info.additional_db_operations is not None


def test_persist_v004_projects_channel_and_pico_state_readings():
    event = _report_event()
    persistor = ReportEventPersistor(logging.getLogger("test"))
    temp = _channel("buffer-depth1-device", unit="Celcius")
    pico = _channel(
        "buffer-pico-state", unit="Enum", unit_type=SinglePicoState.enum_name()
    )
    db = MagicMock()
    db.info = {}
    db.query.return_value.filter.return_value.all.return_value = [temp, pico]

    info = persistor.persist_v004(ALIAS, datetime.now(tz=UTC), event)
    info.additional_db_operations(db)

    db.execute.assert_called_once()
    rows = db.execute.call_args.args[1]
    temp_rows = [r for r in rows if r["channel_id"] == temp.id]
    source = next(
        c for c in event.report.channel_reading_list if c.channel_name == temp.name
    )
    assert [r["value"] for r in temp_rows] == list(source.value_list)
    assert all(r["message_id"] == uuid.UUID(event.report.id) for r in rows)

    pico_rows = [r for r in rows if r["channel_id"] == pico.id]
    source_state = next(
        s
        for s in event.report.state_list
        if str(s.machine_handle) == "buffer"
        and s.state_enum == SinglePicoState.enum_name()
    )
    assert [r["value"] for r in pico_rows] == [
        SinglePicoState.values().index(v) for v in source_state.state_list
    ]
    assert persistor.enum_fallbacks == {}

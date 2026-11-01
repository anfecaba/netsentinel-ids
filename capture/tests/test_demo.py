import json

from lab_capture.demo import DEMO_PASSWORD, DEMO_USER, DemoGenerator


async def test_demo_marca_todo_como_sintetico():
    generator = DemoGenerator(nodes=5, rate=1000)
    events = await generator.take(40)

    assert events[0]["type"] == "hello"
    assert events[0]["mode"] == "demo"
    assert events[0]["synthetic"] is True
    assert all(event["synthetic"] is True for event in events)


async def test_demo_incluye_credenciales_sinteticas():
    generator = DemoGenerator(nodes=5, rate=1000)
    events = await generator.take(40)

    credentials = [event for event in events if event["type"] == "credential"]
    assert credentials, "el generador debe producir credenciales"

    values = {field["name"]: field["value"] for field in credentials[0]["fields"]}
    assert values["username"] == DEMO_USER
    assert values["password"] == DEMO_PASSWORD


async def test_demo_genera_ids_unicos_y_json_serializable():
    generator = DemoGenerator(nodes=5, rate=1000)
    events = await generator.take(60)

    ids = [event["id"] for event in events if "id" in event]
    assert len(ids) == len(set(ids))
    json.dumps(events)


async def test_demo_incluye_dns_y_flujos():
    generator = DemoGenerator(nodes=5, rate=1000)
    events = await generator.take(40)

    types = {event["type"] for event in events}
    assert "dns" in types
    assert "flow" in types


async def test_demo_respeta_el_numero_de_nodos():
    generator = DemoGenerator(nodes=7, rate=1000)
    events = await generator.take(40)

    sources = {event["sourceIp"] for event in events if "sourceIp" in event}
    assert len(sources) <= 7

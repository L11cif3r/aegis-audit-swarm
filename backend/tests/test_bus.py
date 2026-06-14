import bus


async def test_publish_reaches_subscriber():
    received = []

    async def handler(payload):
        received.append(payload)

    topic = "test.topic"
    bus.subscribe(topic, handler)
    await bus.publish(topic, {"x": 1})
    assert received == [{"x": 1}]


async def test_publish_no_subscribers_is_noop():
    # Should not raise.
    await bus.publish("nobody.listening", {"y": 2})


async def test_handler_exception_does_not_propagate():
    async def bad_handler(payload):
        raise ValueError("boom")

    topic = "test.errtopic"
    bus.subscribe(topic, bad_handler)
    # gather(return_exceptions=True) swallows it.
    await bus.publish(topic, {"z": 3})

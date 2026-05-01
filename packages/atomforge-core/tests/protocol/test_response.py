from atomforge_core.protocol.core import read_response, write_response
from atomforge_core.protocol.response import IncompatibilityResponse


def test_incompatibility_response_round_trip():
    from io import StringIO

    stream = StringIO()
    response = IncompatibilityResponse(
        request_id="test-request",
        task_kind="fake-task",
        reason="unsupported configuration",
        route_kind="model_override",
    )

    write_response(stream, response)
    stream.seek(0)
    parsed = read_response(stream)

    assert isinstance(parsed, IncompatibilityResponse)
    assert parsed == response

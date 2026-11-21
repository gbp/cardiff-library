import pytest

from scrub import scrub_request, scrub_response


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "before_record_request": scrub_request,
        "before_record_response": scrub_response,
        "decode_compressed_response": True,
    }


@pytest.fixture(autouse=True)
def every_recorded_request_is_sent(request):
    marked = request.node.get_closest_marker("vcr")
    cassette = request.getfixturevalue("vcr") if marked else None
    yield
    replaying = request.config.getoption("--record-mode") in (None, "none")
    if cassette is not None and replaying:
        assert cassette.all_played


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request):
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")

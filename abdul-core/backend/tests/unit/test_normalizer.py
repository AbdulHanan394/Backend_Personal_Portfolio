"""Unit tests for source normalization."""

from app.services.normalizer import normalize_github


def test_normalize_github_push_event() -> None:
    """GitHub push events map to the portfolio activity core fields."""

    raw = {
        "id": "123",
        "type": "PushEvent",
        "created_at": "2026-07-18T10:00:00Z",
        "repo": {"name": "AbdulHanan394/abdul-core"},
        "payload": {"commits": [{"sha": "abc"}, {"sha": "def"}]},
    }

    activity = normalize_github(raw)

    assert activity.source_slug == "github"
    assert activity.external_id == "123"
    assert activity.type == "Push"
    assert activity.title == "Pushed 2 commits to AbdulHanan394/abdul-core"
    assert activity.url == "https://github.com/AbdulHanan394/abdul-core"


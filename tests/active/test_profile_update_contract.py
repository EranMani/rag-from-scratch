from agents.nodes import update_profile as node


def test_update_profile_skips_anonymous_user(monkeypatch):
    calls = []
    monkeypatch.setattr(node, "get_profile_by_user_id", lambda user_id: calls.append(user_id))

    result = node.update_profile_node({"user_id": None})  # type: ignore[arg-type]

    assert result == {}
    assert calls == []


def test_update_profile_error_path_increments_count_without_scores(monkeypatch):
    writes = []
    monkeypatch.setattr(
        node,
        "get_profile_by_user_id",
        lambda user_id: {
            "user_id": user_id,
            "interaction_count": 2,
            "topic_scores": {},
            "session_history": {},
            "strengths": [],
            "gaps": [],
            "mastery_level": "novice",
        },
    )
    monkeypatch.setattr(node, "update_profile", lambda user_id, **fields: writes.append((user_id, fields)))

    result = node.update_profile_node(  # type: ignore[arg-type]
        {
            "user_id": "user-1",
            "assessment_error": True,
            "topic_scores_delta": {"rag_pipeline_architecture": 1.0},
        }
    )

    assert result == {}
    assert writes[0][0] == "user-1"
    assert writes[0][1]["interaction_count"] == 3
    assert "topic_scores" not in writes[0][1]

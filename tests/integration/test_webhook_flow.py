from sqlalchemy import text


def test_duplicate_inbound_events_do_not_create_duplicate_records(client, db_session):
    payload = {
        "envelope": {
            "source": "user-1",
            "sourceName": "Alice",
            "sourceDevice": 1,
            "timestamp": 1712700000000,
            "dataMessage": {
                "message": "same event",
                "groupInfo": {"groupId": "group-1", "groupName": "Ops"},
            },
        }
    }
    headers = {"x-signal-secret": "secret"}
    response1 = client.post("/webhooks/signal", json=payload, headers=headers)
    response2 = client.post("/webhooks/signal", json=payload, headers=headers)
    assert response1.status_code == 200
    assert response2.status_code == 200

    rows = db_session.execute(text("SELECT COUNT(*) FROM raw_messages")).scalar_one()
    assert rows == 1


def test_unauthorized_user_dm_is_denied(client, fake_gateway):
    payload = {
        "envelope": {
            "source": "user-denied",
            "sourceName": "Denied",
            "sourceDevice": 1,
            "timestamp": 1712700001000,
            "dataMessage": {"message": "can you help me?"},
        }
    }
    response = client.post("/webhooks/signal", json=payload, headers={"x-signal-secret": "secret"})
    assert response.status_code == 200
    assert response.json()["status"] == "denied"
    assert "Access is limited" in fake_gateway.sent_messages[-1]["message"]

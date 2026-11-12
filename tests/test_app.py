from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def original_activities():
    snapshot = deepcopy(activities)
    try:
        yield snapshot
    finally:
        activities.clear()
        activities.update(snapshot)


@pytest.fixture
def client(original_activities):
    with TestClient(app) as test_client:
        yield test_client


def test_root_redirects_to_activity_page(client):
    # Arrange
    url = "/"

    # Act
    response = client.get(url, follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_includes_details_and_empty_participant_lists(client):
    # Arrange
    expected = {
        "Test Club": {
            "description": "A club for testing",
            "schedule": "Mondays, 4:00 PM",
            "max_participants": 10,
            "participants": ["student@mergington.edu"],
        },
        "Empty Club": {
            "description": "A new club",
            "schedule": "Fridays, 3:00 PM",
            "max_participants": 5,
            "participants": [],
        },
    }
    activities.clear()
    activities.update(deepcopy(expected))

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected


def test_signup_for_unknown_activity_leaves_data_unchanged(client, original_activities):
    # Arrange
    url = "/activities/Missing/signup"
    email = "student@mergington.edu"

    # Act
    response = client.post(url, params={"email": email})
    observed_activities = deepcopy(activities)

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert observed_activities == original_activities


def test_participant_can_sign_up_again_after_unregistering(client, original_activities):
    # Arrange
    email = "returning.student@mergington.edu"
    signup_url = "/activities/Chess%20Club/signup"
    unregister_url = "/activities/Chess%20Club/participants"
    expected = deepcopy(original_activities)
    expected["Chess Club"]["participants"].append(email)

    # Act
    first_signup = client.post(signup_url, params={"email": email})
    unregister = client.delete(unregister_url, params={"email": email})
    after_unregister = client.get("/activities").json()
    second_signup = client.post(signup_url, params={"email": email})
    after_second_signup = client.get("/activities").json()

    # Assert
    assert first_signup.status_code == 200
    assert unregister.status_code == 200
    assert after_unregister == original_activities
    assert second_signup.status_code == 200
    assert after_second_signup == expected


def test_signup_succeeds_and_is_visible_in_activities(client, original_activities):
    # Arrange
    email = "new.student@mergington.edu"
    expected = deepcopy(original_activities)
    expected["Chess Club"]["participants"].append(email)

    # Act
    response = client.post(
        "/activities/Chess%20Club/signup", params={"email": email}
    )
    observed_activities = client.get("/activities").json()

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Chess Club"}
    assert observed_activities == expected


def test_duplicate_signup_is_rejected_without_changing_activities(client, original_activities):
    # Arrange
    email = "michael@mergington.edu"

    # Act
    response = client.post(
        "/activities/Chess%20Club/signup", params={"email": email}
    )
    observed_activities = client.get("/activities").json()

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert observed_activities == original_activities


def test_unregister_preserves_other_participants_and_activities(client, original_activities):
    # Arrange
    email = "michael@mergington.edu"
    expected = deepcopy(original_activities)
    expected["Chess Club"]["participants"].remove(email)

    # Act
    response = client.delete(
        "/activities/Chess%20Club/participants", params={"email": email}
    )
    observed_activities = client.get("/activities").json()

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from Chess Club"}
    assert observed_activities == expected


def test_unregister_removes_duplicates_and_handles_last_participant(client):
    # Arrange
    email = "student+club@mergington.edu"
    url = "/activities/Chess%20Club/participants"
    activities["Chess Club"]["participants"] = [email, email]

    # Act
    response = client.delete(url, params={"email": email})
    remaining_participants = activities["Chess Club"]["participants"].copy()
    repeated = client.delete(url, params={"email": email})

    # Assert
    assert response.status_code == 200
    assert remaining_participants == []
    assert repeated.status_code == 404


def test_unregister_from_unknown_activity_leaves_data_unchanged(client, original_activities):
    # Arrange
    url = "/activities/Missing/participants"
    email = "michael@mergington.edu"

    # Act
    response = client.delete(url, params={"email": email})
    observed_activities = deepcopy(activities)

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert observed_activities == original_activities


def test_unregister_unknown_participant_leaves_data_unchanged(client, original_activities):
    # Arrange
    url = "/activities/Chess%20Club/participants"
    email = "missing@mergington.edu"

    # Act
    response = client.delete(url, params={"email": email})
    observed_activities = deepcopy(activities)

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Participant not found"}
    assert observed_activities == original_activities

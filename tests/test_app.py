import unittest
from copy import deepcopy

from fastapi.testclient import TestClient

from src.app import activities, app


class ActivityRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.original_activities = deepcopy(activities)
        self.client = TestClient(app)

    def tearDown(self):
        activities.clear()
        activities.update(self.original_activities)
        self.client.close()

    def test_signup_succeeds_and_is_visible_in_activities(self):
        email = "new.student@mergington.edu"
        response = self.client.post(
            "/activities/Chess%20Club/signup", params={"email": email}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "message": f"Signed up {email} for Chess Club"
        })
        expected = deepcopy(self.original_activities)
        expected["Chess Club"]["participants"].append(email)
        self.assertEqual(self.client.get("/activities").json(), expected)

    def test_duplicate_signup_is_rejected_without_changing_activities(self):
        response = self.client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            "detail": "Student already signed up for this activity"
        })
        self.assertEqual(self.client.get("/activities").json(), self.original_activities)

    def test_unregister_preserves_other_participants_and_activities(self):
        response = self.client.delete(
            "/activities/Chess%20Club/participants",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "message": "Unregistered michael@mergington.edu from Chess Club"
        })
        expected = deepcopy(self.original_activities)
        expected["Chess Club"]["participants"].remove("michael@mergington.edu")
        self.assertEqual(self.client.get("/activities").json(), expected)

    def test_unregister_removes_duplicates_and_handles_last_participant(self):
        email = "student+club@mergington.edu"
        activities["Chess Club"]["participants"] = [email, email]

        response = self.client.delete(
            "/activities/Chess%20Club/participants", params={"email": email}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(activities["Chess Club"]["participants"], [])
        repeated = self.client.delete(
            "/activities/Chess%20Club/participants", params={"email": email}
        )
        self.assertEqual(repeated.status_code, 404)

    def test_unknown_activity_or_participant_leaves_data_unchanged(self):
        for activity, email, detail in [
            ("Missing", "michael@mergington.edu", "Activity not found"),
            ("Chess Club", "missing@mergington.edu", "Participant not found"),
        ]:
            with self.subTest(activity=activity, email=email):
                response = self.client.delete(
                    f"/activities/{activity}/participants", params={"email": email}
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": detail})
                self.assertEqual(activities, self.original_activities)

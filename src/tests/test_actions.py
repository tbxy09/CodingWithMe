import unittest
from metagpt.actions import Action

class TestActions(unittest.TestCase):
    def test_action(self):
        action = Action("test")
        self.assertEqual(action.name, "test")
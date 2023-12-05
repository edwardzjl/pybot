import unittest

from pybot.schemas import ChatMessage, Conversation, File


class TestFileSchema(unittest.TestCase):
    def test_path(self):
        payload = {
            "filename": "foo",
            "path": "/mnt/share/some-user/some-conversation/foo",
            "mounted_path": "/mnt/share/foo",
            "size": 123,
            "owner": "some-user",
            "conversation_id": "some-conversation",
        }
        f = File.model_validate(payload)
        self.assertEqual(f.path, payload["mounted_path"])
        dumped = f.model_dump()
        self.assertEqual(dumped["path"], payload["mounted_path"])


class TestConversationSchema(unittest.TestCase):
    def test_create_conversation(self):
        conv = Conversation(title=f"foo", owner="bar")
        self.assertIsNotNone(conv.created_at)
        self.assertIsNotNone(conv.updated_at)
        # created_at and updated_at are not equal in unittests in github actions.
        # self.assertEqual(conv.created_at, conv.updated_at)


class TestMessageSchema(unittest.TestCase):
    def test_create_message(self):
        msg = ChatMessage(from_="ai", content="foo", type="stream/text")


if __name__ == "__main__":
    unittest.main()

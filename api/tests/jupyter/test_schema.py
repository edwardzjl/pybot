import unittest

from pybot.jupyter import ExecutionRequest, ExecutionResponse
from pybot.jupyter.schema import ExecutionContent, ExecutionHeader


class TestEGRequestSchema(unittest.TestCase):
    def test_dump_request(self):
        req = ExecutionRequest(
            header=ExecutionHeader(msg_id="2fc2cb39-d47ba9dceb48e194d7d2a90c_9_29"),
            content=ExecutionContent(code="a = 1"),
        )
        expected = {
            "header": {
                "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_29",
                "msg_type": "execute_request",
            },
            "parent_header": {},
            "channel": "shell",
            "content": {
                "code": "a = 1",
                "silent": False,
                "store_history": False,
                "user_expressions": {},
                "allow_stdin": False,
            },
            "metadata": {},
        }
        self.assertDictEqual(req.model_dump(), expected)


class TestEGResponseSchema(unittest.TestCase):
    def test_validate_status_response(self):
        data = {
            "header": {
                "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_29",
                "msg_type": "status",
                "username": "username",
                "session": "2fc2cb39-d47ba9dceb48e194d7d2a90c",
                "date": "2023-11-11T04:39:35.313278Z",
                "version": "5.3",
            },
            "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_29",
            "msg_type": "status",
            "parent_header": {
                "msg_id": "asadfd",
                "msg_type": "execute_request",
                "date": "2023-11-11T04:39:35.313046Z",
                "version": "5.0",
            },
            "metadata": {},
            "content": {"execution_state": "busy"},
            "buffers": [],
            "channel": "iopub",
        }
        ExecutionResponse.model_validate(data)

    def test_validate_reply_response(self):
        data = {
            "header": {
                "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_12",
                "msg_type": "execute_reply",
                "username": "username",
                "session": "2fc2cb39-d47ba9dceb48e194d7d2a90c",
                "date": "2023-11-11T04:31:09.922456Z",
                "version": "5.3",
            },
            "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_12",
            "msg_type": "execute_reply",
            "parent_header": {
                "msg_id": "asadfd",
                "msg_type": "execute_request",
                "date": "2023-11-11T04:31:09.910092Z",
                "version": "5.0",
            },
            "metadata": {
                "started": "2023-11-11T04:31:09.911634Z",
                "dependencies_met": True,
                "engine": "72047b71-1616-4e4d-b6cb-a3388c808663",
                "status": "ok",
            },
            "content": {
                "status": "ok",
                "execution_count": 0,
                "user_expressions": {},
                "payload": [],
            },
            "buffers": [],
            "channel": "shell",
        }
        ExecutionResponse.model_validate(data)

    def test_validate_input_response(self):
        data = {
            "header": {
                "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_11",
                "msg_type": "execute_input",
                "username": "username",
                "session": "2fc2cb39-d47ba9dceb48e194d7d2a90c",
                "date": "2023-11-11T04:31:09.911713Z",
                "version": "5.3",
            },
            "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_11",
            "msg_type": "execute_input",
            "parent_header": {
                "msg_id": "asadfd",
                "msg_type": "execute_request",
                "date": "2023-11-11T04:31:09.910092Z",
                "version": "5.0",
            },
            "metadata": {},
            "content": {"code": "a = 1", "execution_count": 1},
            "buffers": [],
            "channel": "iopub",
        }
        ExecutionResponse.model_validate(data)

    def test_validate_stream_response(self):
        data = {
            "header": {
                "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_16",
                "msg_type": "stream",
                "username": "username",
                "session": "2fc2cb39-d47ba9dceb48e194d7d2a90c",
                "date": "2023-11-11T04:31:41.994060Z",
                "version": "5.3",
            },
            "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_16",
            "msg_type": "stream",
            "parent_header": {
                "msg_id": "asadfd",
                "msg_type": "execute_request",
                "date": "2023-11-11T04:31:41.989268Z",
                "version": "5.0",
            },
            "metadata": {},
            "content": {"name": "stdout", "text": "1\n"},
            "buffers": [],
            "channel": "iopub",
        }
        ExecutionResponse.model_validate(data)

    def test_validate_result_response(self):
        data = {
            "header": {
                "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_21",
                "msg_type": "execute_result",
                "username": "username",
                "session": "2fc2cb39-d47ba9dceb48e194d7d2a90c",
                "date": "2023-11-11T04:32:14.649684Z",
                "version": "5.3",
            },
            "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_21",
            "msg_type": "execute_result",
            "parent_header": {
                "msg_id": "asadfd",
                "msg_type": "execute_request",
                "date": "2023-11-11T04:32:14.646511Z",
                "version": "5.0",
            },
            "metadata": {},
            "content": {
                "data": {"text/plain": "1"},
                "metadata": {},
                "execution_count": 1,
            },
            "buffers": [],
            "channel": "iopub",
        }
        res = ExecutionResponse.model_validate(data)
        self.assertEqual(res.content.data.text_plain, "1")

    def test_validate_error_response(self):
        data = {
            "header": {
                "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_31",
                "msg_type": "error",
                "username": "username",
                "session": "2fc2cb39-d47ba9dceb48e194d7d2a90c",
                "date": "2023-11-11T04:39:35.552284Z",
                "version": "5.3",
            },
            "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_31",
            "msg_type": "error",
            "parent_header": {
                "msg_id": "asadfd",
                "msg_type": "execute_request",
                "date": "2023-11-11T04:39:35.313046Z",
                "version": "5.0",
            },
            "metadata": {},
            "content": {
                "traceback": [
                    "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
                    "\u001b[0;31mNameError\u001b[0m                                 Traceback (most recent call last)",
                    "Cell \u001b[0;32mIn[1], line 1\u001b[0m\n\u001b[0;32m----> 1\u001b[0m \u001b[43mb\u001b[49m\n",
                    "\u001b[0;31mNameError\u001b[0m: name 'b' is not defined",
                ],
                "ename": "NameError",
                "evalue": "name 'b' is not defined",
            },
            "buffers": [],
            "channel": "iopub",
        }
        res = ExecutionResponse.model_validate(data)
        self.assertEqual(res.content.ename, "NameError")

    def test_validate_error_reply_response(self):
        data = {
            "header": {
                "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_32",
                "msg_type": "execute_reply",
                "username": "username",
                "session": "2fc2cb39-d47ba9dceb48e194d7d2a90c",
                "date": "2023-11-11T04:39:35.554345Z",
                "version": "5.3",
            },
            "msg_id": "2fc2cb39-d47ba9dceb48e194d7d2a90c_9_32",
            "msg_type": "execute_reply",
            "parent_header": {
                "msg_id": "asadfd",
                "msg_type": "execute_request",
                "date": "2023-11-11T04:39:35.313046Z",
                "version": "5.0",
            },
            "metadata": {
                "started": "2023-11-11T04:39:35.314544Z",
                "dependencies_met": True,
                "engine": "72047b71-1616-4e4d-b6cb-a3388c808663",
                "status": "error",
            },
            "content": {
                "status": "error",
                "traceback": [
                    "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
                    "\u001b[0;31mNameError\u001b[0m                                 Traceback (most recent call last)",
                    "Cell \u001b[0;32mIn[1], line 1\u001b[0m\n\u001b[0;32m----> 1\u001b[0m \u001b[43mb\u001b[49m\n",
                    "\u001b[0;31mNameError\u001b[0m: name 'b' is not defined",
                ],
                "ename": "NameError",
                "evalue": "name 'b' is not defined",
                "engine_info": {
                    "engine_uuid": "72047b71-1616-4e4d-b6cb-a3388c808663",
                    "engine_id": -1,
                    "method": "execute",
                },
                "execution_count": 0,
                "user_expressions": {},
                "payload": [],
            },
            "buffers": [],
            "channel": "shell",
        }
        ExecutionResponse.model_validate(data)


if __name__ == "__main__":
    unittest.main()

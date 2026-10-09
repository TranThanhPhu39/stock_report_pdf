"""Exercise the real SDK against a mock transport without a paid API call."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from src.analysis.ai_commentary import request_gemini


class GeminiSdkTests(unittest.TestCase):
    def test_real_sdk_serializes_structured_request(self):
        try:
            from google import genai
        except ImportError:
            sys.path.insert(0,str(Path(__file__).resolve().parents[1]/".vendor"))
            try:from google import genai
            except ImportError:self.skipTest("Install requirements.txt to test the real Gemini SDK")
        import httpx
        sent=[]
        def reply(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200,json={"candidates":[{"content":{"parts":[{"text":'{"macro":[],"industry":[],"company_impact":[]}'}],"role":"model"},"finishReason":"STOP"}]})
        client=genai.Client(api_key="fake-local-unit-test",http_options={"client_args":{"transport":httpx.MockTransport(reply)}})
        with patch("google.genai.Client",return_value=client):
            output=request_gemini({"ticker":"ACB","as_of":"2026-10-09","evidence":[]},"fake-local-unit-test","gemini-flash-latest")
        self.assertEqual(len(sent),1)
        self.assertEqual(sent[0]["generationConfig"]["responseMimeType"],"application/json")
        self.assertIn("responseJsonSchema",sent[0]["generationConfig"])
        self.assertIn("2026-10-09",sent[0]["contents"][0]["parts"][0]["text"])
        self.assertEqual(json.loads(output)["macro"],[])

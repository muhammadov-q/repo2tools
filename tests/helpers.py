"""Shared by the test files: a scripted LLM, and the options of `repo2tools generate` with test defaults."""

from argparse import Namespace
from collections import Counter


class ScriptedLLM:
    """Replies from a dict {(stage, subject): [reply, reply, ...]}; repeats the last reply."""

    model, thinking = "scripted", False

    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.tokens, self.requests, self.chats = Counter(), Counter(), []

    async def chat(self, stage, subject, messages, max_tokens=2048):
        self.tokens[stage] += 10
        self.requests[stage] += 1
        self.chats.append((stage, subject, messages))
        replies = self.script[(stage, subject)]
        return replies.pop(0) if len(replies) > 1 else replies[0]


def options(url, **kwargs):
    defaults = dict(url=str(url), commit=None, package=None, base_url=None, model="scripted", tag="test", max_tools=30,
                    repair_rounds=2, concurrency=2, thinking=False, env_only=False)
    return Namespace(**{**defaults, **kwargs})

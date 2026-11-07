#!/usr/bin/env python3
"""Submit one explicitly selected cooperative observed-idle source prototype.

A fresh idle/default/user snapshot selects a start with native inherited
settings and no caller settings overrides. Idle observation is not atomic;
possible submission does not establish receipt or handling. No live claim.
"""
import sys
from codex_ipc_sender import main


if __name__ == "__main__":
    sys.exit(main(idle_intent=True))

# -*- coding: utf-8 -*-
debug_messages = None


def debug(*messages):
    global debug_messages

    if debug_messages is None:
        print("!", *messages)
    else:
        debug_messages.append(messages)

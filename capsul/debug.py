debug_messages = []

def debug(*messages):
    global debug_messages

    debug_messages.append(' '.join(str(i) for i in messages))

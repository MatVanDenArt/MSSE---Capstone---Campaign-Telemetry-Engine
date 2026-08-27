import json
import os

path = os.path.expanduser('~/.gemini/antigravity/brain/6e76ceec-cb33-4973-b609-6fdf8bc28e0e/.system_generated/logs/transcript_full.jsonl')
last_content = None

with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'tool_calls' in data:
                for tc in data['tool_calls']:
                    if tc['name'] == 'write_to_file' and 'simulate_journeys.py' in tc['arguments'].get('TargetFile', ''):
                        last_content = tc['arguments'].get('CodeContent', '')
                    elif tc['name'] == 'replace_file_content' and 'simulate_journeys.py' in tc['arguments'].get('TargetFile', ''):
                        # It's a replace, so it's not the full content
                        pass
        except:
            pass

if last_content:
    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(last_content)
    print(f"Recovered simulate_journeys.py from full transcript! Length: {len(last_content)}")
else:
    print("Could not find full content in transcript_full.jsonl")

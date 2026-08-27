import json
import os

path = os.path.expanduser('~/.gemini/antigravity/brain/6e76ceec-cb33-4973-b609-6fdf8bc28e0e/.system_generated/logs/transcript.jsonl')
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'simulate_journeys.py' in str(data):
                if 'tool_calls' in data:
                    for tc in data['tool_calls']:
                        if tc['name'] == 'write_to_file' and 'simulate_journeys.py' in tc['arguments'].get('TargetFile', ''):
                            print(f"Found write_to_file at step {data['step_index']}")
                        elif tc['name'] == 'replace_file_content' and 'simulate_journeys.py' in tc['arguments'].get('TargetFile', ''):
                            print(f"Found replace_file_content at step {data['step_index']}")
                        elif tc['name'] == 'run_command' and 'simulate_journeys.py' in tc['arguments'].get('CommandLine', ''):
                            print(f"Found run_command at step {data['step_index']}")
        except:
            pass

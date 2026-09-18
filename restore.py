import json
lines = open(r'C:\Users\admin\.gemini\antigravity\brain\eb971b49-62fb-40b2-a422-f4fe83a63fff\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8').readlines()
html=''
for line in lines:
    try:
        d = json.loads(line)
        if 'tool_calls' in d:
            for call in d['tool_calls']:
                if call.get('name') == 'default_api:write_to_file' and 'index.html' in call['arguments'].get('TargetFile', ''):
                    html = call['arguments']['CodeContent']
    except:
        pass

if html:
    open(r'C:\Users\admin\Documents\Agentes\Luffy\dashboard\static\index.html', 'w', encoding='utf-8').write(html)
    print('Restored successfully')
else:
    print('Could not find write_to_file for index.html')

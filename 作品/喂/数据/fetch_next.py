# 取“喂”之后下一个词的真实概率。
import json, math, os, urllib.request
base = os.environ['DASHSCOPE_BASE_URL'].rstrip('/')
key = os.environ['DASHSCOPE_API_KEY']
if '/compatible-mode' in base: base = base.split('/compatible-mode')[0]
if base.endswith('/api/v1'): base = base[:-7]
def post(body):
    req = urllib.request.Request(base + '/compatible-mode/v1/chat/completions', json.dumps(body).encode(), {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
res = []
for model in ['qwen-plus', 'qwen-max']:
    for temp in [1.0]:
        try:
            r = post({'model': model, 'messages': [{'role': 'user', 'content': '喂'}], 'logprobs': True, 'top_logprobs': 5, 'max_tokens': 16, 'temperature': temp})
            c = r['choices'][0]
            res.append({'model': r.get('model'), 'content': c['message']['content'], 'logprobs': c.get('logprobs')})
            print(model, c['message']['content'])
            for t in (c.get('logprobs') or {}).get('content', [])[:6]:
                print(' ', repr(t['token']), [(x['token'], round(math.exp(x['logprob']), 4)) for x in t.get('top_logprobs', [])])
        except Exception as e:
            print(model, 'ERR', getattr(e, 'code', ''), str(e)[:200])
json.dump(res, open('数据/next_token.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)

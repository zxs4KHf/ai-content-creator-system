# 取真实数据：词向量和下一个字的概率。密钥只从环境变量读取。
import json, os, sys, urllib.request
base = os.environ['DASHSCOPE_BASE_URL'].rstrip('/')
key = os.environ['DASHSCOPE_API_KEY']
if '/compatible-mode' in base: base = base.split('/compatible-mode')[0]
if base.endswith('/api/v1'): base = base[:-7]
def post(path, body):
    req = urllib.request.Request(base + path, json.dumps(body).encode(), {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
words = ['喂，你在吗', '喂，听得见吗', '喂，你好', '你好', '在吗', '哈喽', '接电话', '喂猫', '喂奶', '喂饭', '给孩子喂饭', '喂狗粮', '吃饭', '饲料', '烽火', '电报', '光纤']
vecs = []
for i in range(0, len(words), 10):
    r = post('/compatible-mode/v1/embeddings', {'model': 'text-embedding-v3', 'input': words[i:i+10], 'dimensions': 1024})
    vecs += [d['embedding'] for d in r['data']]
json.dump({'model': 'text-embedding-v3', 'words': words, 'vectors': vecs}, open('数据/embeddings.json', 'w', encoding='utf8'), ensure_ascii=False)
print('embeddings', len(vecs), len(vecs[0]))
out = {}
for model in ['qwen-plus', 'qwen-turbo', 'qwen-max']:
    try:
        r = post('/compatible-mode/v1/chat/completions', {'model': model, 'messages': [{'role': 'user', 'content': '喂'}], 'logprobs': True, 'top_logprobs': 5, 'max_tokens': 12, 'temperature': 0})
        out = {'model': r.get('model', model), 'content': r['choices'][0]['message']['content'], 'logprobs': r['choices'][0].get('logprobs')}
        print(model, repr(out['content']), 'logprobs' , bool(out['logprobs']))
        if out['logprobs']: break
    except Exception as e:
        print(model, 'ERR', getattr(e, 'code', ''), str(e)[:120])
json.dump(out, open('数据/next_token.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)

#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path

REQUIRED_FIELDS = [
    'knowledge_id','title','category','funnel_stage','rule','qa_use','visual_cues','audio_cues',
    'negative_cues','example_application','source_type','source_name','source_url','source_notes','leakage_check'
]
STOP = {'the','a','an','and','or','to','of','in','for','on','with','that','this','is','are','as','by','it','if','when','than','at','be','from','into','not','more','often','can','also','about','what','why','how','which','who','will','they','their','them','you','your','use','used','using'}

def norm(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def token_set(text):
    return {t for t in norm(text).split() if t not in STOP and len(t) > 2}

def load_items(path):
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and 'knowledge_base' in obj:
        return obj['knowledge_base']
    raise ValueError('Expected a JSON array or an object with a knowledge_base field')

def main():
    ap = argparse.ArgumentParser(description='Audit an external marketing KB JSON file')
    ap.add_argument('kb_path', help='Path to JSON file')
    ap.add_argument('--overlap-threshold', type=float, default=0.33, help='Jaccard threshold for similar items')
    ap.add_argument('--top-sources', type=int, default=10, help='How many sources to print')
    args = ap.parse_args()

    items = load_items(args.kb_path)
    print(f'items\t{len(items)}')

    missing = []
    for item in items:
        miss = [f for f in REQUIRED_FIELDS if f not in item]
        if miss:
            missing.append((item.get('knowledge_id', '?'), miss))
    print(f'missing_field_items\t{len(missing)}')
    for kid, miss in missing[:20]:
        print(f'missing\t{kid}\t{",".join(miss)}')

    categories = Counter(item.get('category', 'UNKNOWN') for item in items)
    funnels = Counter(item.get('funnel_stage', 'UNKNOWN') for item in items)
    sources = Counter(item.get('source_name', 'UNKNOWN') for item in items)
    print('\ncategory_counts')
    for k, v in categories.most_common():
        print(f'category\t{k}\t{v}')
    print('\nfunnel_counts')
    for k, v in funnels.most_common():
        print(f'funnel\t{k}\t{v}')
    print('\nsource_counts')
    for k, v in sources.most_common(args.top_sources):
        print(f'source\t{v}\t{k}')

    titles = Counter(norm(item.get('title', '')) for item in items)
    dup_titles = [t for t, c in titles.items() if t and c > 1]
    print(f'\nduplicate_titles\t{len(dup_titles)}')
    for t in dup_titles[:20]:
        print(f'dup_title\t{t}\t{titles[t]}')

    overlaps = []
    for i in range(len(items)):
        a = items[i]
        ta = token_set(' '.join([
            a.get('title', ''), a.get('rule', ''), a.get('qa_use', ''),
            ' '.join(a.get('visual_cues', [])), ' '.join(a.get('audio_cues', []))
        ]))
        for j in range(i + 1, len(items)):
            b = items[j]
            tb = token_set(' '.join([
                b.get('title', ''), b.get('rule', ''), b.get('qa_use', ''),
                ' '.join(b.get('visual_cues', [])), ' '.join(b.get('audio_cues', []))
            ]))
            union = len(ta | tb) or 1
            score = len(ta & tb) / union
            if score >= args.overlap_threshold:
                overlaps.append((score, a.get('knowledge_id', '?'), a.get('title', ''), b.get('knowledge_id', '?'), b.get('title', '')))
    overlaps.sort(reverse=True)
    print(f'\nnear_duplicate_pairs\t{len(overlaps)}\tthreshold={args.overlap_threshold}')
    for score, ida, ta, idb, tb in overlaps[:25]:
        print(f'overlap\t{score:.2f}\t{ida}\t{ta}\t{idb}\t{tb}')

if __name__ == '__main__':
    main()

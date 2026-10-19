"""Export aggregate evidence and private-run digest commitments, never identities."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json

from awkeys.io import read_jsonl
from awkeys.reporting import summarize


def analyze(run):
    manifest=json.loads((run/'manifest.private.json').read_text())
    rows=read_jsonl(run/'observations.jsonl')
    status={x['repository_id']:x['status'] for x in manifest['repositories']}
    complete=[r for r in rows if status[r['repository_id']]=='analyzed']
    return {
        'all_available':summarize(rows,manifest),
        'complete_snapshot_sensitivity':summarize(complete),
        'flow':{
            'discovered':manifest['discovered_repository_count'],
            'attempted':len(manifest['repositories']),
            'statuses':dict(Counter(x['status'] for x in manifest['repositories'])),
            'observations_by_snapshot_status':dict(Counter(status[r['repository_id']] for r in rows)),
            'workflow_files_read':sum(x.get('workflow_count',0) for x in manifest['repositories']),
            'workflow_files_enumerated':sum(x.get('workflows_enumerated',0) for x in manifest['repositories']),
            'errors_by_stage':dict(Counter(x['stage'] for x in manifest['errors'])),
        },
        'commitments':{name:hashlib.sha256((run/name).read_bytes()).hexdigest()
                       for name in ('manifest.private.json','observations.jsonl','requests.private.json')},
        'interpretation':'All-available observations include partial snapshots; the complete-snapshot subset is a sensitivity description. Neither is a probability sample, a prevalence estimate, or an independent classification validation.'
    }


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(analyze(a.run),indent=2,sort_keys=True)+'\n')

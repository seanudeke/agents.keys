"""Reproduce deterministic component observations; no model or GitHub write.

Usage: PYTHONPATH=/path/to/agents.keys/src python component_study.py \
    --repository /path/to/agents.keys --output evidence
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import subprocess
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml
from awkeys.broker import Context, Rejected, boundary_checks, validate_proposal
from awkeys.scanner import scan_workflow


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root, output = args.repository.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    tested_paths = sorted([*root.glob('src/awkeys/*.py'), *root.glob('src/awkeys/*.json'), *root.glob('tests/test_*.py')])
    inventory = {str(p.relative_to(root)): digest(p.read_bytes()) for p in tested_paths}
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
    tests = list(flatten(suite))
    test_groups = dict(sorted(Counter(t.id().split('.')[0] for t in tests).items()))
    with (output/'regression-tests.txt').open('w') as log:
        result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit('regression tests failed')
    context = Context('research-owner/sandbox', 1, 'fixture-run', 'a' * 40)
    base = {'version': 1, 'operation': 'add_labels', 'repository': context.repository,
            'issue': 1, 'run_id': context.run_id, 'source_sha': context.source_sha,
            'labels': ['needs-triage']}
    raw = json.dumps(base).encode()
    rejected = {**base, 'labels': ['release-approved']}
    try:
        validate_proposal(json.dumps(rejected).encode(), context)
    except Rejected as exc:
        rejection_reason = str(exc)
    else:
        raise AssertionError('outside-policy label accepted')
    (output/'worked-before.json').write_text(json.dumps(rejected,indent=2)+'\n')
    (output/'worked-after.json').write_text(json.dumps(base,indent=2)+'\n')
    first = validate_proposal(raw, context)
    second = validate_proposal(raw, context)
    semantically_wrong = {**base, 'labels': ['documentation']}
    semantic_receipt = validate_proposal(json.dumps(semantically_wrong).encode(), context)
    expected_for_task = ['needs-triage']
    allowed_sets = []
    for count in (1, 2):
        for labels in itertools.combinations(context.allowed_labels, count):
            receipt = validate_proposal(json.dumps({**base, 'labels': list(labels)}).encode(), context)
            allowed_sets.append(receipt['labels'])
    prefix = 'name: illustration\non: issues\n'
    job = '''jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@EXAMPLE_REFERENCE
        with:
          prompt: ${{ github.event.issue.body }}
'''
    with_secret = job + '          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}\n'
    variants = {
        'declared_write_and_model_key': prefix + 'permissions: {issues: write}\n' + with_secret,
        'declared_read_and_model_key': prefix + 'permissions: {contents: read}\n' + with_secret,
        'declared_read_no_visible_key': prefix + 'permissions: {contents: read}\n' + job,
    }
    fields = ('a_input_indicator', 'b_sensitive_indicator', 'c_declared_repository_write',
              'triple_indicator_candidate', 'egress_enforcement')
    illustrations = []
    for name, text in variants.items():
        row = scan_workflow(text, repository_id='illustration', path='illustration.yml')[0]
        illustrations.append({'case': name, 'workflow_sha256': digest(text.encode()),
                              **{field: row[field] for field in fields}})
    record = {
        'record_kind': 'deterministic_component_observations',
        'empirical_agent_evaluation': False,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'pyyaml': yaml.__version__,
        'working_tree_modified': bool(subprocess.check_output(['git','status','--porcelain'],cwd=root).strip()),
        'tested_source_sha256': inventory,
        'source_version_basis': 'tested_source_sha256, including uncommitted changes at execution time',
        'tested_inventory_sha256': digest(json.dumps(inventory, sort_keys=True).encode()),
        'tested_file_count': len(inventory), 'unit_test_inventory': test_groups,
        'unit_test_count': len(tests),
        'boundary_fixture_checks': boundary_checks(),
        'worked_example': {'before_accepted': False, 'rejection_reason': rejection_reason, 'after_accepted': True, 'execution_authorized': False},
        'replay_probe': {'calls': 2, 'both_accepted': True, 'receipts_equal': first == second,
                         'interpretation': 'The stateless validator does not consume a nonce or prevent replay.'},
        'semantic_probe': {'task_oracle_labels': expected_for_task,
                           'proposed_labels': semantically_wrong['labels'],
                           'schema_accepted': True,
                           'task_oracle_satisfied': semantic_receipt['labels'] == expected_for_task,
                           'interpretation': 'A label can be within the capability policy while wrong for the task.'},
        'accepted_label_sets': allowed_sets,
        'scanner_illustrations': illustrations,
        'interpretation': 'Constructed inputs and regression checks are not deployment prevalence, model attack trials, or independent security review.',
    }
    (output / 'component-observations.json').write_text(json.dumps(record, indent=2) + '\n')
    (output / 'tested-source-inventory.json').write_text(json.dumps(inventory, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'test_inventory': test_groups, 'test_count': len(tests),
                      'boundary_checks': len(record['boundary_fixture_checks']['checks']),
                      'boundary_checks_passed': sum(c['check_passed'] for c in record['boundary_fixture_checks']['checks']),
                      'replay': record['replay_probe'], 'semantic': record['semantic_probe'],
                      'label_sets': allowed_sets, 'illustrations': illustrations}, indent=2))


if __name__ == '__main__':
    main()

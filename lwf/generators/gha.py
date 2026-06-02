"""GHA generator — capability+config → .github/workflows/*.yml"""

import json
from ..parser import topo_sort


def _render_step(step):
    sid = step['id']
    cap = step['capability']
    using = step.get('using', '')
    cfg = step.get('config', {})

    lines = [f'      - name: {sid} · {cap}/{using}']

    # Inject env vars from step config
    env_lines = []
    for k, v in cfg.get('env', {}).items():
        val = v.strip('{}').replace('secrets.', '').strip()
        env_lines.append(f'          {k}: ${{{{ secrets.{val} }}}}')
    if env_lines:
        lines.append('        env:')
        lines.extend(env_lines)

    if cap == 'collect' and using == 'http':
        url = cfg.get('url', '')
        method = cfg.get('method', 'GET')
        lines.append('        run: |')
        lines.append('          mkdir -p ${{ github.workspace }}/data')
        lines.append(f'          curl -sL -o "${{{{ github.workspace }}}}/data/{sid}.json" \\')
        lines.append(f'            -X {method} "{url}"')

    elif (cap in ('collect', 'process') and using == 'script') or (cap == 'process' and using == 'script'):
        script = cfg.get('file', '')
        args = cfg.get('args', '')
        lines.append('        run: |')
        lines.append(f'          pip install -r requirements.txt 2>/dev/null || true')
        lines.append(f'          python3 {script} {args}')

    elif cap == 'process' and using == 'llm':
        prompt = cfg.get('prompt', '')
        model = cfg.get('model', 'qwen2.5-32b')
        api_url = cfg.get('api_url', 'https://api.siliconflow.cn/v1/chat/completions')
        lines.append('        run: |')
        lines.append('          mkdir -p ${{ github.workspace }}/data')
        lines.append('          cat > /tmp/prompt.txt << \'LWF_PROMPT\'')
        lines.append(f'{prompt}')
        lines.append('LWF_PROMPT')
        lines.append(f'          curl -s -o "${{{{ github.workspace }}}}/data/{sid}.json" \\')
        lines.append(f'            "{api_url}" \\')
        lines.append('            -H "Content-Type: application/json" \\')
        lines.append('            -H "Authorization: Bearer ${{ secrets.LLM_KEY }}" \\')
        lines.append(f'            -d "$(jq -n --arg p "$(cat /tmp/prompt.txt)" \'{{model:"{model}",messages:[{{role:"user",content:$p}}]}}\')"')

    elif cap == 'store' and using == 'git':
        msg = cfg.get('commit_message', 'lwf update')
        repo = cfg.get('repo', '${{ secrets.BRIDGE_REPO || github.repository }}')
        lines.append('        run: |')
        lines.append(f'          git config user.name "lwf-bot"')
        lines.append(f'          git config user.email "lwf-bot@users.noreply.github.com"')
        lines.append('          git add -A')
        lines.append(f'          git diff --cached --quiet || (git commit -m "{msg}" && git push)')

    elif cap == 'notify' and using == 'email':
        to = cfg.get('to', '')
        subject = cfg.get('subject', 'LWF 通知')
        lines.append('        run: |')
        lines.append('          python3 -c """')
        lines.append('import smtplib, os')
        lines.append('from email.mime.text import MIMEText')
        lines.append('msg = MIMEText("LWF 工作流通知")')
        lines.append(f'msg["Subject"] = "{subject}"')
        lines.append(f'msg["To"] = "{to}"')
        lines.append('msg["From"] = os.environ.get("EMAIL_FROM", "")')
        lines.append('with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST","smtp.qq.com"), 465) as s:')
        lines.append('    s.login(os.environ.get("EMAIL_FROM",""), os.environ.get("EMAIL_PASS",""))')
        lines.append(f'    s.sendmail(os.environ.get("EMAIL_FROM",""), ["{to}"], msg.as_string())')
        lines.append('          """')
    else:
        lines.append(f'        run: echo "LWF step: {sid} ({cap}/{using})"')

    return '\n'.join(lines)


def generate(name, gha_steps, trigger_schedule=None):
    ordered = topo_sort(gha_steps)
    lines = [
        f'name: {name}', '',
        'on:',
    ]
    if trigger_schedule:
        lines.append(f'  schedule:')
        lines.append(f'    - cron: \'{trigger_schedule}\'')
    lines.extend([
        '  workflow_dispatch:',
        '', 'jobs:', '  run:',
        '    runs-on: ubuntu-latest',
        '    timeout-minutes: 15', '',
        '    steps:',
        '      - uses: actions/checkout@v4',
        '        with:',
        '          repository: ${{ secrets.BRIDGE_REPO || github.repository }}',
        '          token: ${{ secrets.BRIDGE_TOKEN || github.token }}', '',
        '      - uses: actions/setup-python@v5',
        '        with:',
        '          python-version: \'3.11\'', '',
        '      - run: mkdir -p data', '',
    ])
    for s in ordered:
        lines.append(_render_step(s))
        lines.append('')
    lines.extend([
        '      - uses: actions/upload-artifact@v4',
        '        if: always()',
        '        with:',
        f'          name: {name}-${{{{ github.run_id }}}}',
        '          path: data/',
        '          retention-days: 3',
    ])
    return '\n'.join(lines)

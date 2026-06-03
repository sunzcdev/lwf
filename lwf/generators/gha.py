"""GHA generator — capability+config → .github/workflows/*.yml"""

import json
from ..parser import topo_sort


def _render_step(step):
    sid = step['id']
    cap = step['capability']
    using = step.get('using', '')
    cfg = step.get('config', {})
    is_optional = step.get('optional', False)

    lines = [f'      - name: {sid} · {cap}/{using}']

    # 带 id 的步骤可以被后续步骤引用其 outputs
    deps = step.get('depends', [])
    if deps or sid in ('detect', 'collect', 'digest'):
        lines.append(f'        id: {sid}')

    # optional 步骤 + continue-on-error
    if is_optional:
        lines.append('        continue-on-error: true')

    # Inject env vars from step config
    env_lines = []
    for k, v in cfg.get('env', {}).items():
        val = v.strip('{}').replace('secrets.', '').strip()
        env_lines.append(f'          {k}: ${{{{ secrets.{val} }}}}')
    if env_lines:
        lines.append('        env:')
        lines.extend(env_lines)

    # ── detect / script ──
    if cap == 'detect' and using == 'script':
        script = cfg.get('file', '')
        lines.append('        run: |')
        lines.append(f'          bash {script}')

    # ── collect/http ──
    elif cap == 'collect' and using == 'http':
        url = cfg.get('url', '')
        method = cfg.get('method', 'GET')
        lines.append('        run: |')
        lines.append('          mkdir -p ${{ github.workspace }}/data')
        lines.append(f'          curl -sL -o "${{{{ github.workspace }}}}/data/{sid}.json" \\')
        lines.append(f'            -X {method} "{url}"')

    # ── collect/script ──
    elif cap == 'collect' and using == 'script':
        script = cfg.get('file', '')
        args = cfg.get('args', '')
        ext = script.split('.')[-1] if '.' in script else ''
        runner = 'bash' if ext == 'sh' else 'python3'
        lines.append('        run: |')
        lines.append('          pip install -r requirements.txt 2>/dev/null || true')
        lines.append(f'          {runner} {script} {args}')

    # ── process/llm ──
    elif cap == 'process' and using == 'llm':
        prompt = cfg.get('prompt', '')
        model = cfg.get('model', 'qwen2.5-32b')
        api_url = cfg.get('api_url', 'https://api.siliconflow.cn/v1/chat/completions')
        lines.append('        run: |')
        lines.append('          mkdir -p ${{ github.workspace }}/data')
        lines.append("          cat > /tmp/prompt.txt << 'LWF_PROMPT'")
        lines.append(f'{prompt}')
        lines.append('LWF_PROMPT')
        lines.append(f'          curl -s -o "${{{{ github.workspace }}}}/data/{sid}.json" \\')
        lines.append(f'            "{api_url}" \\')
        lines.append('            -H "Content-Type: application/json" \\')
        lines.append('            -H "Authorization: Bearer ${{ secrets.LLM_KEY }}" \\')
        lines.append(f'            -d "$(jq -n --arg p "$(cat /tmp/prompt.txt)" \'{{model:"{model}",messages:[{{role:"user",content:$p}}]}}\')"')

    # ── store/git ──
    elif cap == 'store' and using == 'git':
        msg = cfg.get('commit_message', 'lwf update')
        lines.append('        run: |')
        lines.append('          git config user.name "lwf-bot"')
        lines.append('          git config user.email "lwf-bot@users.noreply.github.com"')
        lines.append('          git add -A')
        lines.append(f'          git diff --cached --quiet || (git commit -m "{msg}" && git push)')

    # ── notify/email ──
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

    # ── notify/rclone ──
    elif cap == 'notify' and using == 'rclone':
        remote = cfg.get('remote', '')
        rtype = cfg.get('type', 'webdav')
        url = cfg.get('url', '')
        vendor = cfg.get('vendor', 'other')
        user_secret = cfg.get('user_secret', '')
        pass_secret = cfg.get('pass_secret', '')
        source = cfg.get('source', '')
        target = cfg.get('target', '')
        remote_upper = remote.upper()
        lines.append('        env:')
        lines.append(f'          RCLONE_CONFIG_{remote_upper}_TYPE: {rtype}')
        lines.append(f'          RCLONE_CONFIG_{remote_upper}_URL: {url}')
        lines.append(f'          RCLONE_CONFIG_{remote_upper}_VENDOR: {vendor}')
        if user_secret:
            lines.append(f'          RCLONE_CONFIG_{remote_upper}_USER: ${{{{ secrets.{user_secret} }}}}')
        if pass_secret:
            lines.append(f'          RCLONE_CONFIG_{remote_upper}_PASS: ${{{{ secrets.{pass_secret} }}}}')
        lines.append('        run: |')
        lines.append('          which rclone >/dev/null 2>&1 || (curl -s https://rclone.org/install.sh | bash)')
        lines.append(f'          rclone copy "{source}" "{remote}:{target}" --progress')
        lines.append(f'          echo "  ✓ rclone: {source} → {remote}:{target}"')

    # ── process/script ──
    elif cap == 'process' and using == 'script':
        script = cfg.get('file', '')
        args = cfg.get('args', '')
        ext = script.split('.')[-1] if '.' in script else ''
        runner = 'bash' if ext == 'sh' else 'python3'
        lines.append('        run: |')
        lines.append('          pip install -r requirements.txt 2>/dev/null || true')
        lines.append(f'          {runner} {script} {args}')

    else:
        lines.append(f'        run: echo "LWF step: {sid} ({cap}/{using})"')

    return '\n'.join(lines)


def generate(name, gha_steps, trigger_schedule=None, bridge_info=None):
    ordered = topo_sort(gha_steps)
    lines = [
        f'name: {name}', '',
        'on:',
    ]
    if trigger_schedule:
        lines.append('  schedule:')
        lines.append(f"    - cron: '{trigger_schedule}'")
    lines.append('  workflow_dispatch:')
    # Check if any step needs workflow_dispatch inputs (like mode)
    has_detect = any(s.get('id') == 'detect' for s in gha_steps)
    if has_detect:
        lines.append('    inputs:')
        lines.append('      mode:')
        lines.append("        description: '模式: daily/weekly/monthly'")
        lines.append('        required: true')
        lines.append("        default: 'weekly'")
        lines.append('        type: choice')
        lines.append('        options: [daily, weekly, monthly]')
    lines.extend([
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
        "          python-version: '3.11'", '',
        '      - run: mkdir -p data', '',
    ])
    for s in ordered:
        lines.append(_render_step(s))
        lines.append('')

    # ── Probe output: data/ 有非空 json 才上传 artifact ──
    lines.extend([
        '      - name: probe-output',
        '        id: probe-output',
        '        run: |',
        '          FOUND=false',
        '          for f in ${{ github.workspace }}/data/*.json; do',
        '            [ -f "$f" ] && [ -s "$f" ] && FOUND=true && break',
        '          done',
        '          if [ "$FOUND" = true ]; then',
        '            echo "has_output=true" >> $GITHUB_OUTPUT',
        '            echo "  有数据 → 上传 artifact"',
        '          else',
        '            echo "has_output=false" >> $GITHUB_OUTPUT',
        '            echo "  无数据 → 跳过 artifact"',
        '          fi',
        '',
        '      - uses: actions/upload-artifact@v4',
        "        if: steps.probe-output.outputs.has_output == 'true'",
        '        with:',
        f'          name: {name}-${{{{ github.run_id }}}}',
        '          path: data/',
        '          retention-days: 3',
    ])

    return '\n'.join(lines)

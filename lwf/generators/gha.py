"""GHA generator — 将 LWF 步骤转换为 GitHub Actions workflow YAML"""

from ..parser import build_dag


def _step_script(action, step_id):
    """根据 action type 生成 GHA step 脚本"""
    t = action['type']
    outfile = f"${{{{ github.workspace }}}}/data/{step_id}.json"

    if t == 'http':
        url = action['url']
        return (
            f'      - name: {step_id} · HTTP\n'
            f'        run: |\n'
            f'          mkdir -p ${{{{ github.workspace }}}}/data\n'
            f'          curl -sL -o "{outfile}" -w "%{{http_code}}" "{url}"\n'
            f'          echo "" >> "{outfile}"'
        )

    elif t == 'llm':
        prompt = action['prompt']
        model = action.get('model', 'qwen2.5-32b')
        return (
            f'      - name: {step_id} · LLM\n'
            f'        run: |\n'
            f'          mkdir -p ${{{{ github.workspace }}}}/data\n'
            f'          cat > /tmp/{step_id}.txt << \'ENDPROMPT\'\n'
            f'{prompt}\n'
            f'ENDPROMPT\n'
            f'          curl -s -o "{outfile}" \\\n'
            f'            https://api.siliconflow.cn/v1/chat/completions \\\n'
            f'            -H "Content-Type: application/json" \\\n'
            f'            -H "Authorization: Bearer ${{{{ secrets.LLM_KEY }}}}" \\\n'
            f'            -d "$(jq -n --arg p "$(cat /tmp/{step_id}.txt)" \'{{model:"{model}",messages:[{{role:"user",content:$p}}],temperature:0.3}}\')"'
        )

    elif t == 'script':
        return (
            f'      - name: {step_id} · script\n'
            f'        run: python {action["file"]}'
        )

    elif t == 'git':
        commit_msg = action.get('commit', f'update {step_id}')
        return (
            f'      - name: {step_id} · git push\n'
            f'        run: |\n'
            f'          git config user.name "lwf-bot"\n'
            f'          git config user.email "lwf-bot@users.noreply.github.com"\n'
            f'          git add -A\n'
            f"          git diff --cached --quiet || (git commit -m '{commit_msg}' && git push)"
        )

    elif t == 'email':
        to = action.get('to', '${{ secrets.EMAIL_TO }}')
        subject = action.get('subject', 'LWF 通知')
        body_file = action.get('body_file', '')
        read_cmd = f'BODY=$(cat {body_file})' if body_file else 'BODY="LWF 通知"'
        return (
            f'      - name: {step_id} · email\n'
            f'        env:\n'
            f'          EMAIL_FROM: ${{{{ secrets.EMAIL_FROM }}}}'
            f'\n          EMAIL_PASS: ${{{{ secrets.EMAIL_PASS }}}}'
            f'\n          EMAIL_HOST: ${{{{ secrets.EMAIL_HOST }}}}'
            f'\n        run: |\n'
            f'          {read_cmd}\n'
            f'          python3 -c "\n'
            f'import smtplib, os, sys\n'
            f'from email.mime.text import MIMEText\n'
            f'msg = MIMEText(sys.argv[1])\n'
            f"msg[\'Subject\'] = \'{subject}\'\n"
            f"msg[\'To\'] = \'{to}\'\n"
            f"msg[\'From\'] = os.environ[\'EMAIL_FROM\']\n"
            f"with smtplib.SMTP_SSL(os.environ[\'EMAIL_HOST\'], 465) as s:\n"
            f"    s.login(os.environ[\'EMAIL_FROM\'], os.environ[\'EMAIL_PASS\'])\n"
            f"    s.sendmail(os.environ[\'EMAIL_FROM\'], [\'{to}\'], msg.as_string())\n"
            f'" "$BODY"'
        )

    elif t == 'gha-trigger':
        workflow = action['workflow']
        return (
            f'      - name: {step_id} · trigger\n'
            f'        run: gh workflow run "{workflow}" --ref ${{{{ github.ref }}}}'
        )

    return (
        f'      - name: {step_id}\n'
        f'        run: echo "skip {step_id}"'
    )


def generate(workflow_name, gha_steps, trigger_schedule=None):
    """生成完整的 GHA workflow YAML"""
    ordered = build_dag(gha_steps)

    lines = [
        f'name: {workflow_name}',
        '',
        'on:',
    ]
    if trigger_schedule:
        lines.append(f'  schedule:')
        lines.append(f'    - cron: \'{trigger_schedule}\'')
    lines.extend([
        '  workflow_dispatch:',
        '',
        'jobs:',
        '  run:',
        '    runs-on: ubuntu-latest',
        '    timeout-minutes: 15',
        '',
        '    steps:',
        '      - uses: actions/checkout@v4',
        '        with:',
        '          repository: ${{ secrets.BRIDGE_REPO || github.repository }}',
        '          token: ${{ secrets.BRIDGE_TOKEN || github.token }}',
        '',
        '      - run: mkdir -p data',
        '',
    ])

    for s in ordered:
        lines.append(_step_script(s['action'], s['id']))
        lines.append('')

    lines.extend([
        '      - uses: actions/upload-artifact@v4',
        '        if: always()',
        '        with:',
        f'          name: {workflow_name}-${{{{ github.run_id }}}}',
        '          path: data/',
        '          retention-days: 3',
    ])

    return '\n'.join(lines)
